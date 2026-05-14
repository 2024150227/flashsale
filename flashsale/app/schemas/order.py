from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class OrderCreate(BaseModel):
    user_id: Optional[int] = None
    product_id: int

class OrderResponse(BaseModel):
    status: str
    message: str

class OrderDetail(BaseModel):
    id: int
    user_id: int
    product_id: int
    price: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class OrderListResponse(BaseModel):
    total: int
    orders: List[OrderDetail]