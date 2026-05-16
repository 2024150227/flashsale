import time
import threading
import hashlib
from typing import Any, Optional, Callable, Dict
from functools import lru_cache
from cachetools import TTLCache, LRUCache

class LocalCache:
    def __init__(self):
        self._lock = threading.RLock()
        
        self.session_time_cache: Dict[int, Dict[str, float]] = {}
        
        self.hot_product_cache = TTLCache(
            maxsize=1000,
            ttl=120
        )
        
        self.stock_cache = TTLCache(
            maxsize=5000,
            ttl=10
        )
        
        self.user_cache = TTLCache(
            maxsize=10000,
            ttl=300
        )
        
        self.duplicate_request_cache = TTLCache(
            maxsize=10000,
            ttl=5
        )
    
    def set_session_time(self, session_id: int, start_time: float, end_time: float):
        with self._lock:
            self.session_time_cache[session_id] = {
                'start_time': start_time,
                'end_time': end_time
            }
    
    def get_session_time(self, session_id: int) -> Optional[Dict[str, float]]:
        return self.session_time_cache.get(session_id)
    
    def is_session_active(self, session_id: int) -> bool:
        session_data = self.get_session_time(session_id)
        if not session_data:
            return False
        now = time.time()
        return session_data['start_time'] <= now <= session_data['end_time']
    
    def set_hot_product(self, product_id: int, product: Dict):
        self.hot_product_cache[product_id] = product
    
    def get_hot_product(self, product_id: int) -> Optional[Dict]:
        return self.hot_product_cache.get(product_id)
    
    def delete_hot_product(self, product_id: int):
        if product_id in self.hot_product_cache:
            del self.hot_product_cache[product_id]
    
    def set_stock(self, product_id: int, stock: int):
        self.stock_cache[product_id] = stock
    
    def get_stock(self, product_id: int) -> Optional[int]:
        return self.stock_cache.get(product_id)
    
    def delete_stock(self, product_id: int):
        if product_id in self.stock_cache:
            del self.stock_cache[product_id]
    
    def set_user(self, user_id: int, user: Dict):
        self.user_cache[user_id] = user
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        return self.user_cache.get(user_id)
    
    def delete_user(self, user_id: int):
        if user_id in self.user_cache:
            del self.user_cache[user_id]
    
    def is_duplicate_request(self, request_key: str) -> bool:
        if request_key in self.duplicate_request_cache:
            return True
        self.duplicate_request_cache[request_key] = True
        return False
    
    def clear_duplicate_request(self, request_key: str):
        if request_key in self.duplicate_request_cache:
            del self.duplicate_request_cache[request_key]
    
    def get_hot_product_count(self) -> int:
        return len(self.hot_product_cache)
    
    def get_stock_cache_count(self) -> int:
        return len(self.stock_cache)
    
    def get_user_cache_count(self) -> int:
        return len(self.user_cache)

local_cache = LocalCache()

@lru_cache(maxsize=128)
def get_default_session_config():
    return {
        'default_start_time': 0,
        'default_end_time': 0
    }

@lru_cache(maxsize=1024)
def generate_request_cache_key(client_ip: str, user_agent: str, path: str, method: str) -> str:
    key_string = f"{client_ip}:{user_agent}:{path}:{method}"
    return hashlib.md5(key_string.encode()).hexdigest()