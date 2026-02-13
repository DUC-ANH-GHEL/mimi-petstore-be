from fastapi import APIRouter

from app.presentation.api.admin.endpoints.products import router as admin_products_router


admin_api_router = APIRouter()
admin_api_router.include_router(admin_products_router, prefix="/products", tags=["admin-products"])
