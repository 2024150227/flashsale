import bcrypt
import os

os.environ['DATABASE_URL'] = 'mysql+mysqlconnector://root:mysql123456@localhost:3307/flashsale'

from sqlalchemy import create_engine, text

engine = create_engine(os.environ['DATABASE_URL'])
hashed_pwd = bcrypt.hashpw('test123'.encode(), bcrypt.gensalt()).decode()

with engine.connect() as conn:
    conn.execute(text(f"INSERT INTO users (username, hashed_password, name, age) VALUES ('test', '{hashed_pwd}', '测试用户', 25)"))
    conn.commit()

print('用户创建成功')