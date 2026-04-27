from pydantic import BaseModel
from typing import Optional

class Product(BaseModel):
    id: int
    name: str
    price: float
    stock: int
    description: Optional[str] = None
    is_active: int = 1
    
    class Config:
        from_attributes = True