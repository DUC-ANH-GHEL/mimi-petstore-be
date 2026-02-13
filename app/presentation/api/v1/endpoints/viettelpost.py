# 📁 app/api/viettelpost.py
from fastapi import APIRouter, HTTPException
import httpx
from pydantic import BaseModel

router = APIRouter()

VIETTEL_USERNAME = "aduc7246@gmail.com"
VIETTEL_PASSWORD = "M*3GxT46DgKrdyB"
API_BASE = "https://partner.viettelpost.vn/v2"

# class ShippingServiceInput(BaseModel):
#     sender_province: int
#     sender_district: int
#     receiver_province: int
#     receiver_district: int
#     order_service:str
#     product_type: str
#     product_weight: int
#     product_price: int
#     money_collection: int
#     national_type: int

class ShippingServiceInput(BaseModel):
    PRODUCT_WEIGHT: int
    PRODUCT_PRICE: int
    MONEY_COLLECTION: int
    ORDER_SERVICE_ADD: str = ""
    ORDER_SERVICE: str
    SENDER_PROVINCE: str = "32"
    SENDER_DISTRICT: str = "357"
    RECEIVER_PROVINCE: str
    RECEIVER_DISTRICT: str
    PRODUCT_TYPE: str
    NATIONAL_TYPE: int

@router.get("/viettelpost/token")
async def get_viettelpost_token():
    url = f"{API_BASE}/user/Login"
    headers = {"Content-Type": "application/json"}
    data = {
        "USERNAME": VIETTEL_USERNAME,
        "PASSWORD": VIETTEL_PASSWORD
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        response_json = response.json()

        if response.status_code == 200 and response_json.get("status") == 200:
            return {"token": response_json["data"]["token"]}
        else:
            raise HTTPException(status_code=400, detail=f"Login thất bại: {response_json}")

@router.post("/viettelpost/get-price")
async def get_shipping_price(payload: ShippingServiceInput):
    token_response = await get_viettelpost_token()
    token = token_response["token"]

    url = f"{API_BASE}/order/getPrice"
    headers = {
        "Content-Type": "application/json",
        "Token": token
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload.dict(), headers=headers)
        response_json = response.json()

        if response.status_code == 200 and response_json.get("status") == 200:
            return response_json
        else:
            raise HTTPException(status_code=400, detail=f"Lấy giá vận chuyển thất bại: {response_json}")
