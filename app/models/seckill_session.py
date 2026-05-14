import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.db.session import Base
# 秒杀会话模型，用于管理秒杀会话，一个秒杀会话对应一个商品
class SeckillSession(Base):
    __tablename__ = "seckill_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    product_id = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.now)

    @property
    def session_key(self) -> str:
        return f"seckill_{self.id}"
