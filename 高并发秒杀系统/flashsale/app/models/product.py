from sqlalchemy import Column, Integer, String, Float
from app.db.session import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    description = Column(String(1000))
    is_active = Column(Integer, default=1)