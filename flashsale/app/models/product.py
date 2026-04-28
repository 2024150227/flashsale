import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.session import Base
# 商品模型
class Product(Base):
    # 商品模型的表名
    __tablename__ = "products"
    #允许ID自增
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    description = Column(String(1000))
    is_active = Column(Integer, default=1)
    #添加created_at和updated_at时间戳字段
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)