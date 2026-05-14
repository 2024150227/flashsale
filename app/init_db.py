from sqlalchemy import create_engine
from app.db.session import Base
from app.models.product import Product
from app.models.order import Order
from app.models.user import User
from app.core.config import settings

def init_db():
    # 创建数据库引擎
    engine = create_engine(settings.database_url)
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()