from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ProductStatus = Literal["active", "inactive"]
SortBy = Literal["createdAt", "price", "name"]
SortOrder = Literal["asc", "desc"]


class CategoryRef(BaseModel):
    id: str
    name: str


class ProductImageItem(BaseModel):
    id: str
    url: str


class PublicProductItem(BaseModel):
    id: str
    name: str
    slug: str
    price: float
    original_price: Optional[float] = Field(default=None, alias="originalPrice")
    thumbnail: Optional[str] = None
    stock: int
    status: ProductStatus
    category: CategoryRef
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class PublicProductDetail(PublicProductItem):
    images: List[ProductImageItem] = Field(default_factory=list)


class Pagination(BaseModel):
    page: int
    limit: int
    total_items: int = Field(alias="totalItems")
    total_pages: int = Field(alias="totalPages")
    has_next: bool = Field(alias="hasNext")
    has_prev: bool = Field(alias="hasPrev")

    model_config = ConfigDict(populate_by_name=True)


class ListProductsResponse(BaseModel):
    success: bool = True
    data: List[PublicProductItem]
    pagination: Pagination


class ProductDetailResponse(BaseModel):
    success: bool = True
    data: PublicProductDetail


class CreateProductBody(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    original_price: Optional[float] = Field(default=None, alias="originalPrice")
    category_id: str = Field(alias="categoryId")
    stock: int = 0
    status: ProductStatus = "active"
    thumbnail: Optional[str] = None
    images: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class UpdateProductBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = Field(default=None, alias="originalPrice")
    category_id: Optional[str] = Field(default=None, alias="categoryId")
    stock: Optional[int] = None
    status: Optional[ProductStatus] = None
    thumbnail: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
