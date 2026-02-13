from typing import List, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.product import Product, ProductImage

class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.model = Product
    
    async def get_all(self) -> List[Product]:
        """Get all products"""
        result = await self.session.execute(select(Product))
        return result.scalars().all()
    
    async def get_by_id(self, id: int) -> Optional[Product]:
        """Get product by ID"""
        result = await self.session.execute(
            select(Product).where(Product.id == id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, obj_in: Product) -> Product:
        """Create new product"""
        self.session.add(obj_in)
        await self.session.flush()
        return obj_in
    
    async def update(self, id: int, obj_in: Product) -> Optional[Product]:
        """Update product"""
        result = await self.session.execute(
            select(Product).where(Product.id == id)
        )
        product = result.scalar_one_or_none()
        if not product:
            return None
        
        # Update fields
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(product, field, value)
        
        await self.session.flush()
        return product
    
    async def delete(self, id: int) -> bool:
        """Delete product"""
        result = await self.session.execute(
            select(Product).where(Product.id == id)
        )
        product = result.scalar_one_or_none()
        if not product:
            return False
        
        await self.session.delete(product)
        await self.session.flush()
        return True
    
    async def exists(self, id: int) -> bool:
        """Check if product exists"""
        result = await self.session.execute(
            select(Product).where(Product.id == id)
        )
        return result.scalar_one_or_none() is not None
    
    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU"""
        result = await self.session.execute(
            text("SELECT * FROM products WHERE sku = :sku"),
            {"sku": sku}
        )
        return result.scalar_one_or_none()
    
    async def get_active_products(self) -> List[Product]:
        """Get all active products"""
        result = await self.session.execute(
            select(Product).where(Product.is_active == True)
        )
        return result.scalars().all()
    
    async def get_products_by_category(self, category_id: int) -> List[Product]:
        """Get products by category"""
        result = await self.session.execute(
            select(Product).where(Product.category_id == category_id)
        )
        return result.scalars().all()
    
    async def search_products(self, search_term: str) -> List[Product]:
        """Search products by name or description"""
        query = select(Product).where(
            (Product.name.ilike(f"%{search_term}%")) |
            (Product.description.ilike(f"%{search_term}%"))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_products_in_stock(self) -> List[Product]:
        """Get products that are in stock"""
        query = select(Product).where(Product.stock > 0)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_stock(self, product_id: int, quantity: int) -> Optional[Product]:
        """Update product stock"""
        product = await self.get_by_id(product_id)
        if not product:
            return None
        
        product.stock += quantity
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def get_product_images(self, product_id: int) -> List[ProductImage]:
        """Get all images for a product"""
        result = await self.session.execute(
            select(ProductImage).where(ProductImage.product_id == product_id)
        )
        return result.scalars().all()

    async def add_product_image(self, image: ProductImage) -> ProductImage:
        """Add a new image to a product"""
        self.session.add(image)
        await self.session.flush()
        return image

    async def update_product_image(self, image_id: int, image: ProductImage) -> Optional[ProductImage]:
        """Update a product image"""
        result = await self.session.execute(
            select(ProductImage).where(ProductImage.id == image_id)
        )
        existing_image = result.scalar_one_or_none()
        if not existing_image:
            return None
        
        # Update fields
        for field, value in image.dict(exclude_unset=True).items():
            setattr(existing_image, field, value)
        
        await self.session.flush()
        return existing_image

    async def delete_product_image(self, image_id: int) -> bool:
        """Delete a product image"""
        result = await self.session.execute(
            delete(ProductImage).where(ProductImage.id == image_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def set_primary_image(self, product_id: int, image_id: int) -> None:
        """Set an image as the primary image for a product"""
        # First, unset any existing primary image
        await self.session.execute(
            update(ProductImage)
            .where(ProductImage.product_id == product_id)
            .values(is_primary=False)
        )
        # Then set the new primary image
        await self.session.execute(
            update(ProductImage)
            .where(ProductImage.id == image_id)
            .values(is_primary=True)
        )
        await self.session.commit() 