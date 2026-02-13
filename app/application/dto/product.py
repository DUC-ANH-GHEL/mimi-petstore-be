from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime
from fastapi import UploadFile

class ProductBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    price: float
    sku: str
    affiliate: int
    weight: float
    length: float
    width: float
    height: float
    is_active: bool = True
    category_id: int
    images: List[UploadFile] = Field(default_factory=list)

class ProductCreate(ProductBase):
    images: List[UploadFile] = Field(default_factory=list)

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None
    category_id: Optional[int] = None
    affiliate: Optional[int] = None
    weight: Optional[float] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    images: Optional[List[UploadFile]] = None

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    images: List["ProductImageResponse"] = []

    class Config:
        from_attributes = True

class ProductImageBase(BaseModel):
    url: str
    is_primary: bool = False

class ProductImageCreate(ProductImageBase):
    product_id: int

class ProductImageUpdate(ProductImageBase):
    pass

class ProductImageResponse(ProductImageBase):
    id: int
    product_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Update forward references
ProductResponse.update_forward_refs()

class ProductSpecBase(BaseModel):
    label: str
    value: str

class ProductSpecCreate(ProductSpecBase):
    product_id: int

class ProductSpecUpdate(BaseModel):
    label: Optional[str] = None
    value: Optional[str] = None

class ProductSpecResponse(ProductSpecBase):
    id: int
    product_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProductOut(BaseModel):
    id: int
    name: str
    sku: str
    description: str
    price: float
    affiliate: int
    weight: float
    length: float
    width: float
    height: float
    is_active: bool
    category_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        # orm_mode = True
        from_attributes=True

class ProductList(ProductOut):
    image: Optional[str] = ""
    
class ProductUpdate(ProductCreate):
    id: int
    affiliate: int
    is_active: bool
    listImageCurrent: List[HttpUrl]
    listImageNew: List

