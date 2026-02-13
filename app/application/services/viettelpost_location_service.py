import httpx
from typing import Optional

API_BASE = "https://partnerdev.viettelpost.vn/v2"

async def get_province_id_by_name(name: str, token: str) -> int:
    if not name:
        raise Exception("Tên tỉnh không được để trống")
    
    url = "https://partnerdev.viettelpost.vn/v2/categories/listProvince"
    headers = {"Token": token}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Lỗi khi lấy danh sách tỉnh: {response.text}")

    provinces = response.json().get("data", [])
    for p in provinces:
        if p["PROVINCE_NAME"].strip().lower() == name.strip().lower():
            return p["PROVINCE_ID"]

    raise Exception(f"Không tìm thấy tỉnh với tên: {name}")




async def get_district_id_by_name(province_id: int, name: str, token: str) -> int:
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{API_BASE}/categories/listDistrict?provinceId={province_id}", headers={"Token": token})
        res.raise_for_status()
        for d in res.json().get("data", []):
            if d["DISTRICT_NAME"].strip().lower() == name.strip().lower():
                return d["DISTRICT_ID"]
        raise ValueError(f"Quận không hợp lệ: {name}")

async def get_ward_id_by_name(district_id: int, name: str, token: str) -> int:
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{API_BASE}/categories/listWards?districtId={district_id}", headers={"Token": token})
        res.raise_for_status()
        for w in res.json().get("data", []):
            if w["WARDS_NAME"].strip().lower() == name.strip().lower():
                return w["WARDS_ID"]
        raise ValueError(f"Phường không hợp lệ: {name}")
