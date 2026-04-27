from pydantic import BaseModel
from typing import Optional

class OrderCreate(BaseModel):
    user_id: int
    product_id: int

class OrderResponse(BaseModel):
    status: str
    message: str