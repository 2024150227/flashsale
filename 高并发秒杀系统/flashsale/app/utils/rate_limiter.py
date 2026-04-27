from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 创建限流器实例
limiter = Limiter(key_func=get_remote_address)