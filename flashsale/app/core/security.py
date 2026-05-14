from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import jwt
import bcrypt
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis import Redis
from app.core.config import settings

# JWT配置
SECRET_KEY = "flashsale_jwt_secret_key_2026"  # 生产环境应该从环境变量读取
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # Token有效期一周（7*24*60分钟）

# Redis连接
redis_client = None

def get_redis_client() -> Redis:
    """
    获取Redis客户端连接

    返回:
        Redis: Redis客户端实例
    """
    global redis_client
    if redis_client is None:
        try:
            redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
            redis_client.ping()
        except Exception as e:
            print(f"[WARNING] Redis connection failed: {str(e)}. Running in degraded mode.")
            redis_client = None
    return redis_client

def hash_password(password: str) -> str:
    """
    对密码进行哈希加密

    参数:
        password: 明文密码

    返回:
        str: 哈希后的密码
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """
    验证密码是否正确

    参数:
        password: 明文密码
        hashed_password: 哈希后的密码

    返回:
        bool: 密码是否匹配
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: Dict[str, any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌

    参数:
        data: 要编码到令牌中的数据（如用户ID）
        expires_delta: 过期时间增量，默认为一周

    返回:
        str: JWT令牌字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, any]]:
    """
    验证JWT令牌并返回解码后的数据

    参数:
        token: JWT令牌字符串

    返回:
        Optional[Dict]: 解码后的令牌数据，如果验证失败返回None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id_str = payload.get("sub")

        if user_id_str is None:
            return None

        try:
            user_id: int = int(user_id_str)
        except ValueError:
            return None

        redis = get_redis_client()
        if redis is not None:
            stored_user_id = redis.get(f"token:{token}")
            if stored_user_id is None:
                return None
            if int(stored_user_id) != user_id:
                return None

        return payload

    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def store_token(token: str, user_id: int) -> bool:
    """
    将token存储到Redis中

    参数:
        token: JWT令牌字符串
        user_id: 用户ID

    返回:
        bool: 存储是否成功
    """
    redis = get_redis_client()
    if redis is None:
        return False

    try:
        redis.setex(f"token:{token}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, user_id)
        redis.sadd(f"user_tokens:{user_id}", token)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to store token in Redis: {str(e)}")
        return False

def revoke_token(token: str, user_id: int) -> bool:
    """
    从Redis中删除token（登出）

    参数:
        token: JWT令牌字符串
        user_id: 用户ID

    返回:
        bool: 删除是否成功
    """
    redis = get_redis_client()
    if redis is None:
        return False

    try:
        redis.delete(f"token:{token}")
        redis.srem(f"user_tokens:{user_id}", token)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to revoke token: {str(e)}")
        return False

def revoke_all_tokens(user_id: int) -> bool:
    """
    撤销用户的所有token（强制登出所有设备）

    参数:
        user_id: 用户ID

    返回:
        bool: 操作是否成功
    """
    redis = get_redis_client()
    if redis is None:
        return False

    try:
        tokens = redis.smembers(f"user_tokens:{user_id}")
        for token in tokens:
            redis.delete(f"token:{token}")
        redis.delete(f"user_tokens:{user_id}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to revoke all tokens: {str(e)}")
        return False

class JWTBearer:
    """
    JWT认证依赖类，用于FastAPI路由的token校验
    """

    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(self, request: Request):
        """
        验证token并返回用户ID

        参数:
            request: FastAPI请求对象

        返回:
            int: 用户ID

        抛出:
            HTTPException: 认证失败时抛出401错误
        """
        auth_header = request.headers.get("Authorization")

        if auth_header is None:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未提供认证令牌",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证令牌格式错误",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = parts[1]

        payload = verify_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效或已过期的令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return int(payload.get("sub"))