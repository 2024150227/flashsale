from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.local_cache import local_cache, generate_request_cache_key
from app.utils.redis_client import redis_client
from app.core.logger import app_logger as logger
import time
import threading
from collections import defaultdict

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests=1000, window_seconds=60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients = defaultdict(list)
        self._lock = threading.RLock()
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        
        with self._lock:
            now = time.time()
            self.clients[client_ip] = [
                t for t in self.clients[client_ip] 
                if now - t < self.window_seconds
            ]
            
            if len(self.clients[client_ip]) >= self.max_requests:
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                raise HTTPException(
                    status_code=429, 
                    detail="请求过于频繁，请稍后重试"
                )
            
            self.clients[client_ip].append(now)
        
        response = await call_next(request)
        return response

class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, failure_threshold=50, recovery_timeout=60):
        super().__init__(app)
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.is_open = False
        self._lock = threading.RLock()
    
    async def dispatch(self, request: Request, call_next):
        with self._lock:
            if self.is_open:
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.is_open = False
                    self.failure_count = 0
                    logger.info("Circuit breaker reset")
                else:
                    logger.warning("Circuit breaker is open")
                    return JSONResponse(
                        status_code=503,
                        content={"detail": "服务暂时不可用，请稍后重试"}
                    )
        
        try:
            response = await call_next(request)
            if response.status_code >= 500:
                with self._lock:
                    self.failure_count += 1
                    if self.failure_count >= self.failure_threshold:
                        self.is_open = True
                        self.last_failure_time = time.time()
                        logger.error("Circuit breaker opened")
            return response
        except Exception as e:
            with self._lock:
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    self.is_open = True
                    self.last_failure_time = time.time()
                    logger.error(f"Circuit breaker opened due to exception: {e}")
            raise

class AntiSpamMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        path = request.url.path
        method = request.method
        
        request_key = generate_request_cache_key(client_ip, user_agent, path, method)
        
        if local_cache.is_duplicate_request(request_key):
            logger.warning(f"Duplicate request detected: {request_key}")
            raise HTTPException(status_code=400, detail="重复请求，请稍后重试")
        
        try:
            response = await call_next(request)
            return response
        finally:
            local_cache.clear_duplicate_request(request_key)

class DegradationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.degraded_endpoints = set()
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        if path in self.degraded_endpoints:
            logger.warning(f"Endpoint degraded: {path}")
            return JSONResponse(
                status_code=503,
                content={"detail": "该功能暂时不可用"}
            )
        
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            if path.startswith("/api/v1/orders/"):
                logger.error(f"Order service error, degrading: {e}")
                self.degraded_endpoints.add(path)
                return JSONResponse(
                    status_code=503,
                    content={"detail": "订单服务暂时不可用，请稍后重试"}
                )
            raise