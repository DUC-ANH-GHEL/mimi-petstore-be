from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base

class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    url = Column(String, nullable=False)
    public_id = Column(String, nullable=True)
    alt_text = Column(String, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="images")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    slug = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    sale_price = Column(Float, nullable=True)
    currency = Column(String, nullable=False, default="VND")
    sku = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    affiliate = Column(Integer, nullable=True)
    stock = Column(Integer, nullable=False, default=0)

    # Clothing-specific attributes (optional)
    brand = Column(String, nullable=True)
    material = Column(String, nullable=True)
    size = Column(String, nullable=True)
    color = Column(String, nullable=True)
    pet_type = Column(String, nullable=True)
    season = Column(String, nullable=True)
    height = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    length = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    category_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order_items = relationship("OrderItem", back_populates="product")
    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    variants = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)

    sku = Column(String, nullable=False, unique=True, index=True)
    size = Column(String, nullable=True)
    color = Column(String, nullable=True)
    material = Column(String, nullable=True)

    price = Column(Float, nullable=True)
    sale_price = Column(Float, nullable=True)
    stock = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    product = relationship("Product", back_populates="variants")

