from pydantic import BaseModel

class ContactBase(BaseModel):
    name: str
    phone: str
    message: str
    product_id: int | None = None

class ContactCreate(ContactBase):
    pass

class ContactOut(ContactBase):
    id: int
    class Config:
        orm_mode = True