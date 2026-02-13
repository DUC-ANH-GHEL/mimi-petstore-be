from typing import Optional, List
from app.domain.models.product import Product, ProductImage
from app.infrastructure.repositories.product_repository import ProductRepository
from app.application.services.base import BaseServiceImpl
from app.application.dto.product import (
    ProductCreate,
    ProductUpdate,
    ProductImageCreate,
    ProductImageUpdate,
    ProductImageResponse
)
from app.core.exceptions import ValidationException, NotFoundException
from sqlalchemy.ext.asyncio import AsyncSession
from app.cloudinary_config import cloudinary
import json
import cloudinary.uploader

class ProductService(BaseServiceImpl[Product, ProductCreate, ProductUpdate]):
    """Product service implementation"""
    
    def __init__(self, repository: ProductRepository):
        super().__init__(repository)
        self.repository = repository
    
    async def create(self, product_in: ProductCreate) -> Product:
        """Create new product"""
        # Check if SKU already exists
        existing_product = await self.repository.get_by_sku(product_in.sku)
        if existing_product:
            raise ValidationException(f"Product with SKU {product_in.sku} already exists")
        
        # Create product
        product = Product(**product_in.dict(exclude={'images'}))
        product = await self.repository.create(product)
        
        # Upload images if any
        if product_in.images:
            for image_file in product_in.images:
                try:
                    # Upload to Cloudinary
                    result = cloudinary.uploader.upload(
                        image_file.file,
                        folder="products",
                        resource_type="auto"
                    )
                    
                    # Create product image
                    image = ProductImage(
                        product_id=product.id,
                        url=result['secure_url'],
                        public_id=result['public_id'],
                        is_primary=len(product_in.images) == 1  # First image is primary
                    )
                    await self.repository.add_product_image(image)
                except Exception as e:
                    raise ValidationException(f"Error uploading image: {str(e)}")
        
        return product
    
    async def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        product = await self.repository.get_by_id(product_id)
        if not product:
            raise NotFoundException(f"Product with ID {product_id} not found")
        return product
    
    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU"""
        return await self.repository.get_by_sku(sku)
    
    async def get_active_products(self) -> List[Product]:
        """Get all active products"""
        return await self.repository.get_active_products()
    
    async def get_products_by_category(self, category_id: int) -> List[Product]:
        """Get products by category"""
        return await self.repository.get_products_by_category(category_id)
    
    async def update(self, product_id: int, product_in: ProductUpdate) -> Optional[Product]:
        """Update product"""
        product = await self.repository.get_by_id(product_id)
        if not product:
            raise NotFoundException(f"Product with ID {product_id} not found")
        
        # Update product
        updated_product = await self.repository.update(product_id, product_in)
        return updated_product
    
    async def update_stock(self, product_id: int, quantity: int) -> Optional[Product]:
        """Update product stock"""
        product = await self.repository.get_by_id(product_id)
        if not product:
            raise NotFoundException(f"Product with ID {product_id} not found")
        
        # Update stock
        product.stock += quantity
        if product.stock < 0:
            raise ValidationException("Stock cannot be negative")
        
        updated_product = await self.repository.update(product_id, product)
        return updated_product
    
    async def get_product_images(self, product_id: int) -> List[ProductImage]:
        """Get all images for a product"""
        return await self.repository.get_product_images(product_id)
    
    async def add_product_image(self, image: ProductImageCreate) -> ProductImage:
        """Add a new image to a product"""
        # Upload to Cloudinary
        try:
            result = cloudinary.uploader.upload(
                image.file.file,
                folder="products",
                resource_type="auto"
            )
            
            # Create product image
            product_image = ProductImage(
                product_id=image.product_id,
                url=result['secure_url'],
                public_id=result['public_id'],
                is_primary=image.is_primary
            )
            return await self.repository.add_product_image(product_image)
        except Exception as e:
            raise ValidationException(f"Error uploading image: {str(e)}")
    
    async def update_product_image(self, image_id: int, image: ProductImageUpdate) -> Optional[ProductImage]:
        """Update a product image"""
        return await self.repository.update_product_image(image_id, image)

    def _map_dto_to_entity(self, dto: ProductCreate | ProductUpdate) -> Product:
        """Map DTO to Product entity"""
        if isinstance(dto, ProductCreate):
            return Product(
                name=dto.name,
                description=dto.description,
                price=dto.price,
                stock=dto.stock,
                sku=dto.sku,
                is_active=dto.is_active,
                category_id=dto.category_id
            )
        else:
            return Product(**dto.dict(exclude_unset=True))

    async def search_products(self, search_term: str) -> List[Product]:
        """Search products by name or description"""
        return await self.repository.search_products(search_term)
    
    async def get_products_in_stock(self) -> List[Product]:
        """Get products that are in stock"""
        return await self.repository.get_products_in_stock()

    async def delete_product_image(self, image_id: int) -> bool:
        """Delete a product image"""
        return await self.repository.delete_product_image(image_id)

    async def set_primary_image(self, product_id: int, image_id: int) -> None:
        """Set an image as the primary image for a product"""
        # Verify both product and image exist
        product = await self.repository.get(product_id)
        if not product:
            raise ValidationException(f"Product with ID {product_id} not found")

        image = await self.repository.get(ProductImage, image_id)
        if not image:
            raise ValidationException(f"Image with ID {image_id} not found")

        if image.product_id != product_id:
            raise ValidationException(f"Image does not belong to product {product_id}")

        await self.repository.set_primary_image(product_id, image_id) 