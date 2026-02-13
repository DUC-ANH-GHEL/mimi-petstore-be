import httpx
import uuid
import json
from datetime import datetime

API_BASE = "https://partner.viettelpost.vn/v2"

async def create_viettelpost_order(order, shipping, items, db):
    token = await get_viettelpost_token()
    inventory = await get_inventory_info(token)
    # token = shipping.api_token
    headers = {
        "Token": token,
        "Content-Type": "application/json"
    }
    print("token", token);

    # Dùng ID đã có sẵn
    sender_province_id = shipping.sender_province_id
    sender_district_id = shipping.sender_district_id
    sender_ward_id = shipping.sender_ward_id

    receiver_province_id = order.receiver_province_id
    receiver_district_id = order.receiver_district_id
    receiver_ward_id = order.receiver_ward_id

    list_item = []
    order_number = f"ORDER_{order.id or uuid.uuid4().hex[:8]}"

    # for i, item in enumerate(items):
    #     list_item.append({
    #         "ORDER_NUMBER": order_number,
    #         "ORDER_NUMBER_ITEM": f"{order_number}-{i+1}",
    #         # "PRODUCT_NAME": f"{item.quantity} x {item.product_name}",
    #         "PRODUCT_NAME": f"{item['quantity']} x {item['product_name']}",
    #         "PRODUCT_WEIGHT": item.quantity * item.product_weight,
    #         "PRODUCT_QUANTITY": item.quantity,
    #         "PRODUCT_TYPE": "HH",
    #         "PRODUCT_PRICE": float(item.unit_price)
    #     })

    print("MONEY", order.total_amount)


    payload = {
        "ORDER_NUMBER": order_number,
        "GROUPADDRESS_ID": inventory["groupaddressId"],
        "CUS_ID": inventory["cusId"],
        "DELIVERY_DATE": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "SENDER_FULLNAME": inventory["name"],
        "SENDER_PHONE": inventory["phone"],
        "SENDER_ADDRESS": inventory["address"],
        "SENDER_PROVINCE": inventory["provinceId"],
        "SENDER_DISTRICT": inventory["districtId"],
        "SENDER_WARD": inventory["wardsId"],
        "SENDER_LATITUDE": 0,
        "SENDER_LONGITUDE": 0,
        "RECEIVER_FULLNAME": order.receiver_name,
        "RECEIVER_PHONE": order.receiver_phone,
        "RECEIVER_ADDRESS": order.receiver_address,
        "RECEIVER_PROVINCE": receiver_province_id,
        "RECEIVER_DISTRICT": receiver_district_id,
        "RECEIVER_WARD": receiver_ward_id,
        "RECEIVER_EMAIL": "",  # nếu có email thì truyền vào, không thì giữ trống
        "RECEIVER_LATITUDE": 0,
        "RECEIVER_LONGITUDE": 0,
        "PRODUCT_NAME": " + ".join(f"{item['product_name']}({item['quantity']})" for item in items),
        "PRODUCT_DESCRIPTION": "Đơn hàng từ hệ thống",
        "PRODUCT_QUANTITY": sum(item["quantity"] for item in items),
        "PRODUCT_PRICE": float(order.total_amount),
        "PRODUCT_WEIGHT": sum(item["product_weight"] for item in items),
        "PRODUCT_LENGTH": sum(item["product_length"] for item in items),
        "PRODUCT_WIDTH": sum(item["product_width"] for item in items),
        "PRODUCT_HEIGHT": sum(item["product_height"] for item in items),
        "PRODUCT_TYPE": "HH",
        "ORDER_PAYMENT": 3,  # lấy hộ tiền hàng
        "ORDER_SERVICE": "SCOD",
        "ORDER_SERVICE_ADD": "",
        "ORDER_VOUCHER": "",
        "ORDER_NOTE": order.note or "",
        "MONEY_COLLECTION": float(order.total_amount),
        "MONEY_TOTALFEE": 0,
        "MONEY_FEECOD": 0,
        "MONEY_FEEVAS": 0,
        "MONEY_FEEINSURRANCE": 0,
        "MONEY_FEE": 0,
        "MONEY_FEEOTHER": 0,
        "MONEY_TOTALVAT": 0,
        "MONEY_TOTAL": 0,
        "LIST_ITEM": [
            {
                # "PRODUCT_NAME": f"{item.quantity} x {item.product_name}",
                "PRODUCT_NAME": f"{item['quantity']} x {item['product_name']}",
                "PRODUCT_PRICE": float(item["unit_price"]),
                "PRODUCT_WEIGHT": item["product_weight"] * item["quantity"],
                "PRODUCT_QUANTITY": item["quantity"]
            } for item in items
        ]
    }



    print("=== PAYLOAD GỬI VIETTELPOST ===")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE}/order/createOrder", headers=headers, json=payload)

    if response.status_code == 200:
        response_json = response.json()
        data = response_json.get("data")
        if not data:
            raise Exception(f"❌ API trả về status 200 nhưng không có trường 'data':\n{response_json}")

        return {
            "order_code": data.get("ORDER_NUMBER"),
            "tracking_code": data.get("TRACKING_NUMBER"),
            "money_collection": data.get("MONEY_COLLECTION"),
            "fee": data.get("MONEY_TOTAL")
        }

    else:
        raise Exception(
            f"""❌ Gọi API ViettelPost thất bại:
  - Status: {response.status_code}
  - Headers: {response.headers}
  - Response body: {response.text}"""
        )



async def get_viettelpost_token() -> str:
    # url = "https://partner.viettelpost.vn/v2/user/Login"
    url = f"{API_BASE}/user/Login"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "USERNAME": "aduc7246@gmail.com",
        "PASSWORD": "M*3GxT46DgKrdyB"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        response_json = response.json()
        
        if response_json.get("status") == 200 and response_json.get("data"):
            return response_json["data"]["token"]
        else:
            raise Exception(f"Login thất bại: {response_json}")



async def get_inventory_info(token: str) -> dict:
    url = f"{API_BASE}/user/listInventory"
    headers = {
        "Content-Type": "application/json",
        "Token": token  # <-- Fix ở đây
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response_json = response.json()
        if response.status_code == 200 and response_json.get("data"):
            return response_json["data"][0]  # trả về inventory đầu tiên
        else:
            raise Exception(f"❌ Không lấy được thông tin inventory: {response_json}")
