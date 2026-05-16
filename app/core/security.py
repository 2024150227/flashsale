from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import jwt
import bcrypt
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis import Redis
from app.core.config import settings

SECRET_KEY = "flashsale_jwt_secret_key_2026"
JWT_ISSUER = "flashsale-jwt-key"  # 必须与Kong的JWT密钥key一致
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 延长到30分钟
REFRESH_TOKEN_EXPIRE_DAYS = 7

redis_client = None

def get_redis_client() -> Redis:
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
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: Dict[str, any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire, 
        "type": "access",
        "iss": JWT_ISSUER  # Kong JWT插件需要iss声明匹配
    })
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire, 
        "type": "refresh",
        "iss": JWT_ISSUER  # Kong JWT插件需要iss声明匹配
    })
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> Optional[Dict[str, any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("iss") != JWT_ISSUER:
            return None 
        if payload.get("type") != "access":
            return None
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        try:
            user_id: int = int(user_id_str)
        except ValueError:
            return None
        redis = get_redis_client()
        if redis is not None:
            stored_user_id = redis.get(f"access_token:{token}")
            if stored_user_id is None:
                return None
            if int(stored_user_id) != user_id:
                return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def verify_refresh_token(token: str) -> Optional[Dict[str, any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        try:
            user_id: int = int(user_id_str)
        except ValueError:
            return None
        redis = get_redis_client()
        if redis is not None:
            stored_user_id = redis.get(f"refresh_token:{token}")
            if stored_user_id is None:
                return None
            if int(stored_user_id) != user_id:
                return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def store_tokens(access_token: str, refresh_token: str, user_id: int) -> bool:
    redis = get_redis_client()
    if redis is None:
        return False
    try:
        redis.setex(f"access_token:{access_token}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, user_id)
        redis.setex(f"refresh_token:{refresh_token}", REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, user_id)
        redis.sadd(f"user_access_tokens:{user_id}", access_token)
        redis.sadd(f"user_refresh_tokens:{user_id}", refresh_token)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to store tokens in Redis: {str(e)}")
        return False

def revoke_access_token(token: str, user_id: int) -> bool:
    redis = get_redis_client()
    if redis is None:
        return False
    try:
        redis.delete(f"access_token:{token}")
        redis.srem(f"user_access_tokens:{user_id}", token)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to revoke access token: {str(e)}")
        return False

def revoke_refresh_token(token: str, user_id: int) -> bool:
    redis = get_redis_client()
    if redis is None:
        return False
    try:
        redis.delete(f"refresh_token:{token}")
        redis.srem(f"user_refresh_tokens:{user_id}", token)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to revoke refresh token: {str(e)}")
        return False

def revoke_all_tokens(user_id: int) -> bool:
    redis = get_redis_client()
    if redis is None:
        return False
    try:
        access_tokens = redis.smembers(f"user_access_tokens:{user_id}")
        for token in access_tokens:
            redis.delete(f"access_token:{token}")
        redis.delete(f"user_access_tokens:{user_id}")
        refresh_tokens = redis.smembers(f"user_refresh_tokens:{user_id}")
        for token in refresh_tokens:
            redis.delete(f"refresh_token:{token}")
        redis.delete(f"user_refresh_tokens:{user_id}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to revoke all tokens: {str(e)}")
        return False

class JWTBearer:
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(self, request: Request):
        # 首先检查是否由Kong验证通过（有X-Consumer-Username头）
        kong_consumer = request.headers.get("X-Consumer-Username")
        kong_user_id = request.headers.get("X-Consumer-Custom-Id")
        
        if kong_consumer and kong_user_id:
            # Kong已经验证通过
            try:
                return int(kong_user_id)
            except (ValueError, TypeError):
                pass
        
        # 如果没有Kong验证，则自己验证
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
        payload = verify_access_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效或已过期的访问令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return int(payload.get("sub"))

class RefreshTokenBearer:
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(self, request: Request):
        auth_header = request.headers.get("Authorization")
        if auth_header is None:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未提供刷新令牌",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="刷新令牌格式错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = parts[1]
        payload = verify_refresh_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效或已过期的刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return int(payload.get("sub"))