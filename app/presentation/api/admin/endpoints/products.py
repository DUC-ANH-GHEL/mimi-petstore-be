from __future__ import annotations

import itertools
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.dto.admin_product import (
    AdminProductCreateBody,
    AdminProductUpdateBody,
    BulkUpdateVariantsBody,
    GenerateVariantsBody,
)
from app.core.deps import get_current_user, get_db
from app.domain.models.product import (
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductImage,
    ProductVariant,
    VariantAttributeValue,
)
from app.domain.models.user import User
from app.domain.models.order_item import OrderItem
from app.core.admin_api_error import AdminAPIError


router = APIRouter()


def _admin_error(
    *,
    error_code: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> None:
    raise AdminAPIError(error_code=error_code, message=message, status_code=status_code)


async def _slug_exists(db: AsyncSession, slug: str, *, exclude_product_id: Optional[int] = None) -> bool:
    stmt = select(func.count(Product.id)).where(Product.slug == slug)
    if exclude_product_id is not None:
        stmt = stmt.where(Product.id != exclude_product_id)
    return (await db.scalar(stmt)) > 0


async def _skus_in_use(db: AsyncSession, skus: Sequence[str], *, exclude_variant_ids: Optional[Sequence[int]] = None) -> List[str]:
    if not skus:
        return []
    stmt = select(ProductVariant.sku).where(ProductVariant.sku.in_(list(skus)))
    if exclude_variant_ids:
        stmt = stmt.where(~ProductVariant.id.in_(list(exclude_variant_ids)))
    rows = (await db.execute(stmt)).scalars().all()
    return list(set(rows))


def _validate_create_payload(payload: AdminProductCreateBody) -> None:
    if not payload.name:
        _admin_error(error_code="NAME_REQUIRED", message="name is required")

    if payload.has_variants is False:
        if not payload.variants or len(payload.variants) != 1:
            _admin_error(
                error_code="DEFAULT_VARIANT_REQUIRED",
                message="has_variants=false requires exactly 1 default variant",
            )
    else:
        if not payload.variants:
            _admin_error(error_code="VARIANTS_REQUIRED", message="variants is required when has_variants=true")

    seen: set[str] = set()
    for v in payload.variants:
        if not v.sku:
            _admin_error(error_code="SKU_REQUIRED", message="variant.sku is required")
        if v.sku in seen:
            _admin_error(error_code="SKU_DUPLICATE", message="SKU already exists in request")
        seen.add(v.sku)
        if v.price is None or v.price <= 0:
            _admin_error(error_code="PRICE_INVALID", message="variant.price must be > 0")


async def _get_product_or_404(db: AsyncSession, product_id: int) -> Product:
    stmt: Select[tuple[Product]] = (
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.images),
            selectinload(Product.variants)
            .selectinload(ProductVariant.attribute_values)
            .selectinload(VariantAttributeValue.attribute_value),
            selectinload(Product.variants)
            .selectinload(ProductVariant.attribute_values)
            .selectinload(VariantAttributeValue.attribute),
            selectinload(Product.attributes).selectinload(ProductAttribute.values),
        )
    )
    product = (await db.execute(stmt)).scalars().first()
    if not product or product.deleted_at is not None:
        raise AdminAPIError(error_code="NOT_FOUND", message="Product not found", status_code=404)
    return product


async def _load_attribute_value_lookup(db: AsyncSession, product_id: int) -> tuple[Dict[str, ProductAttribute], Dict[tuple[str, str], int]]:
    stmt = (
        select(ProductAttribute)
        .where(ProductAttribute.product_id == product_id)
        .options(selectinload(ProductAttribute.values))
    )
    attrs = (await db.execute(stmt)).scalars().all()
    attribute_by_name: Dict[str, ProductAttribute] = {}
    value_id_by_pair: Dict[tuple[str, str], int] = {}
    for a in attrs:
        attribute_by_name[a.name] = a
        for v in a.values:
            value_id_by_pair[(a.name, v.value)] = v.id
    return attribute_by_name, value_id_by_pair


def _product_detail_response(product: Product) -> Dict[str, Any]:
    media = [
        {"url": m.url, "type": getattr(m, "type", "image"), "sort_order": m.sort_order}
        for m in sorted(product.images, key=lambda x: x.sort_order)
    ]

    attributes = []
    for a in product.attributes:
        attributes.append(
            {
                "id": a.id,
                "name": a.name,
                "values": [v.value for v in sorted(a.values, key=lambda x: x.id)],
            }
        )

    variants = []
    for v in product.variants:
        attr_map: Dict[str, str] = {}
        for av in v.attribute_values:
            if av.attribute and av.attribute_value:
                attr_map[av.attribute.name] = av.attribute_value.value
        profit = None
        margin_percent = None
        if v.cost_price is not None and v.price is not None:
            profit = v.price - v.cost_price
            if v.price > 0:
                margin_percent = (profit / v.price) * 100
        variants.append(
            {
                "id": v.id,
                "sku": v.sku,
                "price": v.price,
                "compare_price": v.compare_price,
                "cost_price": v.cost_price,
                "stock": v.stock,
                "manage_stock": v.manage_stock,
                "allow_backorder": v.allow_backorder,
                "status": v.status,
                "attribute_values": attr_map,
                "image_url": v.image_url,
                "profit": profit,
                "margin_percent": margin_percent,
            }
        )

    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "status": product.status,
        "featured": product.featured,
        "category_id": product.category_id,
        "brand": product.brand,
        "pet_type": product.pet_type,
        "season": product.season,
        "tags": product.tags or [],
        "shipping": {
            "weight": product.weight or 0,
            "length": product.length or 0,
            "width": product.width or 0,
            "height": product.height or 0,
        },
        "media": media,
        "attributes": attributes,
        "variants": variants,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def admin_create_product(
    payload: AdminProductCreateBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        _validate_create_payload(payload)

        if await _slug_exists(db, payload.slug):
            _admin_error(error_code="SLUG_DUPLICATE", message="Slug already exists", status_code=status.HTTP_409_CONFLICT)

        skus = [v.sku for v in payload.variants]
        existing = await _skus_in_use(db, skus)
        if existing:
            _admin_error(error_code="SKU_DUPLICATE", message=f"SKU already exists: {existing[0]}", status_code=status.HTTP_409_CONFLICT)

        async with db.begin():
            product = Product(
                name=payload.name,
                slug=payload.slug,
                short_description=payload.short_description,
                description=payload.description,
                status=payload.status,
                featured=payload.featured,
                category_id=payload.category_id,
                brand=payload.brand,
                pet_type=payload.pet_type,
                season=payload.season,
                tags=payload.tags,
                has_variants=payload.has_variants,
                weight=payload.shipping.weight,
                length=payload.shipping.length,
                width=payload.shipping.width,
                height=payload.shipping.height,
                is_active=(payload.status == "active"),
            )

            # Back-compat fields (required by current schema)
            product.price = min([v.price for v in payload.variants])
            product.sku = payload.variants[0].sku
            product.stock = sum([v.stock for v in payload.variants])

            db.add(product)
            await db.flush()

            # Media
            for m in payload.media:
                db.add(
                    ProductImage(
                        product_id=product.id,
                        url=m.url,
                        type=m.type,
                        sort_order=m.sort_order,
                        is_primary=(m.sort_order == 1),
                    )
                )

            # Attributes + values
            attribute_by_name: Dict[str, ProductAttribute] = {}
            value_id_by_pair: Dict[tuple[str, str], int] = {}

            for attr in payload.attributes:
                a = ProductAttribute(product_id=product.id, name=attr.name)
                db.add(a)
                await db.flush()
                attribute_by_name[attr.name] = a

                for val in attr.values:
                    av = ProductAttributeValue(attribute_id=a.id, value=val)
                    db.add(av)
                    await db.flush()
                    value_id_by_pair[(attr.name, val)] = av.id

            # Variants + variant_attribute_values
            for v in payload.variants:
                variant = ProductVariant(
                    product_id=product.id,
                    sku=v.sku,
                    price=v.price,
                    compare_price=v.compare_price,
                    cost_price=v.cost_price,
                    stock=v.stock,
                    manage_stock=v.manage_stock,
                    allow_backorder=v.allow_backorder,
                    status=v.status,
                    is_active=(v.status == "active"),
                    image_url=v.image_url,
                )
                db.add(variant)
                await db.flush()

                for attr_name, chosen in (v.attribute_values or {}).items():
                    if attr_name not in attribute_by_name:
                        _admin_error(error_code="ATTRIBUTE_INVALID", message=f"Unknown attribute: {attr_name}")
                    if (attr_name, chosen) not in value_id_by_pair:
                        _admin_error(error_code="ATTRIBUTE_VALUE_INVALID", message=f"Invalid value for {attr_name}: {chosen}")

                    attribute = attribute_by_name[attr_name]
                    attribute_value_id = value_id_by_pair[(attr_name, chosen)]
                    db.add(
                        VariantAttributeValue(
                            variant_id=variant.id,
                            attribute_id=attribute.id,
                            attribute_value_id=attribute_value_id,
                        )
                    )

        return {
            "success": True,
            "message": "Product created successfully",
            "data": {"id": product.id, "slug": product.slug},
        }
    except HTTPException:
        raise
    except AdminAPIError:
        raise
    except Exception as e:
        _admin_error(error_code="INTERNAL_ERROR", message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put("/{product_id}")
async def admin_update_product(
    product_id: int,
    payload: AdminProductUpdateBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        product = await _get_product_or_404(db, product_id)

        if payload.slug and await _slug_exists(db, payload.slug, exclude_product_id=product_id):
            _admin_error(error_code="SLUG_DUPLICATE", message="Slug already exists", status_code=status.HTTP_409_CONFLICT)

        async with db.begin():
            # Update product
            for field in [
                "name",
                "slug",
                "short_description",
                "description",
                "status",
                "featured",
                "category_id",
                "brand",
                "pet_type",
                "season",
                "has_variants",
            ]:
                val = getattr(payload, field)
                if val is not None:
                    setattr(product, field, val)

            if payload.tags is not None:
                product.tags = payload.tags

            if payload.shipping is not None:
                product.weight = payload.shipping.weight
                product.length = payload.shipping.length
                product.width = payload.shipping.width
                product.height = payload.shipping.height

            if payload.status is not None:
                product.is_active = (payload.status == "active")

            # Sync media (replace)
            if payload.media is not None:
                await db.execute(delete(ProductImage).where(ProductImage.product_id == product.id))
                for m in payload.media:
                    db.add(
                        ProductImage(
                            product_id=product.id,
                            url=m.url,
                            type=m.type,
                            sort_order=m.sort_order,
                            is_primary=(m.sort_order == 1),
                        )
                    )

            # Delete attributes explicitly
            if payload.deleted_attribute_ids:
                await db.execute(
                    delete(ProductAttribute).where(
                        ProductAttribute.product_id == product.id,
                        ProductAttribute.id.in_(payload.deleted_attribute_ids),
                    )
                )

            # Sync attributes (upsert-ish)
            attribute_by_name: Dict[str, ProductAttribute] = {}
            value_id_by_pair: Dict[tuple[str, str], int] = {}

            if payload.attributes is not None:
                for attr in payload.attributes:
                    if attr.id:
                        a = (await db.execute(
                            select(ProductAttribute).where(
                                ProductAttribute.product_id == product.id,
                                ProductAttribute.id == attr.id,
                            )
                        )).scalars().first()
                        if not a:
                            _admin_error(error_code="ATTRIBUTE_NOT_FOUND", message=f"Attribute not found: {attr.id}")
                        a.name = attr.name
                    else:
                        a = ProductAttribute(product_id=product.id, name=attr.name)
                        db.add(a)
                        await db.flush()

                    attribute_by_name[attr.name] = a

                    # Replace values for this attribute
                    await db.execute(delete(ProductAttributeValue).where(ProductAttributeValue.attribute_id == a.id))
                    for val in attr.values:
                        av = ProductAttributeValue(attribute_id=a.id, value=val)
                        db.add(av)
                        await db.flush()
                        value_id_by_pair[(attr.name, val)] = av.id
            else:
                attribute_by_name, value_id_by_pair = await _load_attribute_value_lookup(db, product.id)

            # Delete variants explicitly
            if payload.deleted_variant_ids:
                # Block deletion when referenced by order_items
                used_count = await db.scalar(
                    select(func.count(OrderItem.id)).where(OrderItem.product_variant_id.in_(payload.deleted_variant_ids))
                )
                if used_count and used_count > 0:
                    _admin_error(
                        error_code="VARIANT_HAS_ORDERS",
                        message="Cannot delete variant that has order items",
                        status_code=status.HTTP_409_CONFLICT,
                    )
                await db.execute(
                    delete(ProductVariant).where(
                        ProductVariant.product_id == product.id,
                        ProductVariant.id.in_(payload.deleted_variant_ids),
                    )
                )

            # Sync variants
            if payload.variants is not None:
                # Validate sku uniqueness (in request)
                seen: set[str] = set()
                for v in payload.variants:
                    if v.sku in seen:
                        _admin_error(error_code="SKU_DUPLICATE", message="SKU already exists in request")
                    seen.add(v.sku)
                    if v.price is None or v.price <= 0:
                        _admin_error(error_code="PRICE_INVALID", message="variant.price must be > 0")

                incoming_skus = [v.sku for v in payload.variants]
                exclude_ids = [v.id for v in payload.variants if v.id]
                existing = await _skus_in_use(db, incoming_skus, exclude_variant_ids=exclude_ids)
                if existing:
                    _admin_error(error_code="SKU_DUPLICATE", message=f"SKU already exists: {existing[0]}", status_code=status.HTTP_409_CONFLICT)

                for v in payload.variants:
                    if v.id:
                        variant = (await db.execute(
                            select(ProductVariant).where(ProductVariant.product_id == product.id, ProductVariant.id == v.id)
                        )).scalars().first()
                        if not variant:
                            _admin_error(error_code="VARIANT_NOT_FOUND", message=f"Variant not found: {v.id}")
                    else:
                        variant = ProductVariant(product_id=product.id)
                        db.add(variant)
                        await db.flush()

                    variant.sku = v.sku
                    variant.price = v.price
                    variant.compare_price = v.compare_price
                    variant.cost_price = v.cost_price
                    variant.stock = v.stock
                    variant.manage_stock = v.manage_stock
                    variant.allow_backorder = v.allow_backorder
                    variant.status = v.status
                    variant.is_active = (v.status == "active")
                    variant.image_url = v.image_url

                    # Replace mappings
                    await db.execute(delete(VariantAttributeValue).where(VariantAttributeValue.variant_id == variant.id))
                    for attr_name, chosen in (v.attribute_values or {}).items():
                        if (attr_name, chosen) not in value_id_by_pair:
                            _admin_error(error_code="ATTRIBUTE_VALUE_INVALID", message=f"Invalid value for {attr_name}: {chosen}")
                        attribute_value_id = value_id_by_pair[(attr_name, chosen)]
                        attribute_id = attribute_by_name[attr_name].id
                        db.add(
                            VariantAttributeValue(
                                variant_id=variant.id,
                                attribute_id=attribute_id,
                                attribute_value_id=attribute_value_id,
                            )
                        )

                # Update back-compat aggregate fields
                refreshed_variants = (await db.execute(
                    select(ProductVariant).where(ProductVariant.product_id == product.id)
                )).scalars().all()
                if refreshed_variants:
                    product.price = min([rv.price or 0 for rv in refreshed_variants])
                    product.sku = refreshed_variants[0].sku
                    product.stock = sum([rv.stock for rv in refreshed_variants])

            product.updated_at = datetime.utcnow()

        return {"success": True, "message": "Product updated successfully"}
    except HTTPException:
        raise
    except AdminAPIError:
        raise
    except Exception as e:
        _admin_error(error_code="INTERNAL_ERROR", message=str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{product_id}")
async def admin_get_product_detail(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = await _get_product_or_404(db, product_id)
    return _product_detail_response(product)


@router.delete("/{product_id}")
async def admin_soft_delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = await _get_product_or_404(db, product_id)
    async with db.begin():
        product.deleted_at = datetime.utcnow()
        product.is_active = False
        product.status = "inactive"
        product.updated_at = datetime.utcnow()
    return {"success": True, "message": "Product deleted successfully"}


@router.patch("/{product_id}/variants/bulk")
async def admin_bulk_update_variants(
    product_id: int,
    payload: BulkUpdateVariantsBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.variant_ids:
        _admin_error(error_code="VARIANT_IDS_REQUIRED", message="variant_ids is required")
    if len(payload.variant_ids) > 200:
        _admin_error(error_code="TOO_MANY_IDS", message="Max 200 variant IDs per request")

    allowed_fields = {
        "price",
        "stock",
        "compare_price",
        "cost_price",
        "status",
        "manage_stock",
        "allow_backorder",
        "image_url",
    }
    update_data = {k: v for k, v in (payload.update or {}).items() if k in allowed_fields}
    if not update_data:
        _admin_error(error_code="UPDATE_INVALID", message="No valid fields to update")

    async with db.begin():
        stmt = (
            update(ProductVariant)
            .where(ProductVariant.product_id == product_id, ProductVariant.id.in_(payload.variant_ids))
            .values(**update_data)
        )
        result = await db.execute(stmt)

    return {"success": True, "message": "Variants updated successfully", "data": {"updated": result.rowcount}}


@router.post("/generate-variants")
async def admin_generate_variants(
    payload: GenerateVariantsBody,
    current_user: User = Depends(get_current_user),
):
    attrs = [a for a in payload.attributes if a.name and a.values]
    if not attrs:
        return {"variants": []}

    names = [a.name for a in attrs]
    values_lists = [a.values for a in attrs]

    variants = []
    for combo in itertools.product(*values_lists):
        attribute_values = {names[i]: combo[i] for i in range(len(names))}
        variants.append({"attribute_values": attribute_values})

    return {"variants": variants}
