"""
秒杀系统压测脚本 - 防超卖专项测试
专注测试：库存一致性、防超卖机制、订单吞吐
"""
import random
import json
import os
import threading
import time
from locust import HttpUser, task, between, events, LoadTestShape
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_tokens():
    # 从tokens.json文件加载所有Token
    # 确保tokens.json文件与脚本在同一目录下
    # 如果文件不存在，提示用户运行generate_tokens.py生成Token
    # 如果文件存在，加载Token
    token_file = os.path.join(os.path.dirname(__file__), "tokens.json")
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            tokens = json.load(f)
        logger.info(f"已加载 {len(tokens)} 个Token")
        return tokens
    else:
        logger.error("Token文件不存在，请先运行 generate_tokens.py")
        return []

TOKEN_POOL = load_tokens()

class OrderStats:
    def __init__(self):
        self._lock = threading.Lock()
        self.success_count = 0
        self.fail_count = 0
        self.stockout_count = 0
        self.start_time = None

    def record_success(self):
        with self._lock:
            self.success_count += 1

    def record_fail(self, is_stockout=False):
        with self._lock:
            self.fail_count += 1
            if is_stockout:
                self.stockout_count += 1

    def set_start_time(self, t):
        with self._lock:
            self.start_time = t

    def get_stats(self):
        with self._lock:
            if self.start_time:
                elapsed = time.time() - self.start_time
                tps = self.success_count / elapsed if elapsed > 0 else 0
            else:
                elapsed = 0
                tps = 0
            return {
                "success": self.success_count,
                "fail": self.fail_count,
                "stockout": self.stockout_count,
                "elapsed": elapsed,
                "tps": tps
            }

ORDER_STATS = OrderStats()

class FlashSaleUser(HttpUser):
    wait_time = between(0.01, 0.05)  # 极短等待，模拟秒杀峰值
    
    def on_start(self):
        if TOKEN_POOL:
            self.token = random.choice(TOKEN_POOL)
    
    def _get_headers(self):
        headers = {"Content-Type": "application/json"}
        if hasattr(self, 'token') and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # 秒杀目标商品列表（仅测试这3个）
    TARGET_PRODUCTS = [1, 2, 3]
    
    @task(1)
    def create_order(self):
        """秒杀下单 - 核心测试：防超卖、库存一致性"""
        # 只针对指定的3个商品进行秒杀
        product_id = random.choice(self.TARGET_PRODUCTS)
        self.client.post(
            "/api/v1/orders/",
            headers=self._get_headers(),
            json={"product_id": product_id},
            name="/api/v1/orders/"
        )

class FlashSaleLoadShape(LoadTestShape):
    """秒杀场景负载模型：渐进式加压（避免服务崩溃）"""
    stages = [
        {"duration": 30, "users": 20, "spawn_rate": 5},    # 温和启动
        {"duration": 60, "users": 50, "spawn_rate": 10},   # 缓慢提升
        {"duration": 90, "users": 100, "spawn_rate": 10},  # 逐步增加
        {"duration": 120, "users": 150, "spawn_rate": 10}, # 稳定运行
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    if name == "/api/v1/orders/":
        if response is None or exception:
            ORDER_STATS.record_fail()
        elif response.status_code == 200:
            ORDER_STATS.record_success()
            logger.info(f"成功创建订单: {response.json()}")
        elif response.status_code in (400, 409) and response.json().get("message") == "库存不足":
            ORDER_STATS.record_fail(is_stockout=True)
            logger.info(f"库存不足: {response.json()}")
        else:
            ORDER_STATS.record_fail()

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    ORDER_STATS.set_start_time(time.time())
    logger.info("=== 秒杀系统防超卖压测开始 ===")
    logger.info(f"Token池大小: {len(TOKEN_POOL)}")
    logger.info("测试目标: 防超卖机制、库存一致性、订单吞吐")
    logger.info("负载模型: 渐进式加压（避免服务崩溃）") 

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = ORDER_STATS.get_stats()
    logger.info("=== 秒杀系统防超卖压测结束 ===")
    logger.info("========== TPS 统计报告 ==========")
    logger.info(f"测试时长: {stats['elapsed']:.2f} 秒")
    logger.info(f"成功订单数: {stats['success']}")
    logger.info(f"失败请求数: {stats['fail']}")
    logger.info(f"库存不足次数: {stats['stockout']}")
    logger.info(f"TPS (每秒成功订单数): {stats['tps']:.2f}")
    logger.info("===================================")
