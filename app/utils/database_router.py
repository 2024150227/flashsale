from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app.core.config import settings

# 主库引擎（写操作）
master_engine = create_engine(
    settings.database_url_master,
    pool_size=20,
    max_overflow=50,
    pool_timeout=30,
    pool_recycle=1800
)

# 从库引擎（读操作）
slave_engine = create_engine(
    settings.database_url_slave,
    pool_size=20,
    max_overflow=50,
    pool_timeout=30,
    pool_recycle=1800
)

# 主库会话工厂
MasterSession = scoped_session(sessionmaker(bind=master_engine))

# 从库会话工厂
SlaveSession = scoped_session(sessionmaker(bind=slave_engine))

def get_master_db():
    """获取主库连接（写操作）"""
    db = MasterSession()
    try:
        yield db
    finally:
        db.close()

def get_slave_db():
    """获取从库连接（读操作）"""
    db = SlaveSession()
    try:
        yield db
    finally:
        db.close()

def get_db(read_only: bool = False):
    """根据需求选择数据库"""
    if read_only:
        return get_slave_db()
    return get_master_db()