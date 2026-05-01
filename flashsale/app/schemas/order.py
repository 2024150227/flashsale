from pydantic import BaseModel
from typing import Optional

class OrderCreate(BaseModel):
    user_id: Optional[int] = None  # 可选，实际使用token中的用户ID
    product_id: int

class OrderResponse(BaseModel):
    status: str
    message: str