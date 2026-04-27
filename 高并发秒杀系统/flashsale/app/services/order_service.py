from app.utils.redis_client import redis_client
from app.utils.kafka_producer import send_order_message
import json

class OrderService:
    def create_order(self, user_id: int, product_id: int) -> dict:
        """创建秒杀订单"""
        # 构造订单消息
        order_message = {
            "user_id": user_id,
            "product_id": product_id,
            "timestamp": json.dumps("2026-04-27T15:30:00Z")
        }
        
        # 发送到Kafka
        send_order_message(order_message)
        
        return {"status": "queued"}
    
    def process_order(self, order_message: dict) -> bool:
        """处理订单（由消费者调用）"""
        user_id = order_message["user_id"]
        product_id = order_message["product_id"]
        
        # 执行Redis Lua脚本扣库存
        lua_script = """
        local stock_key = KEYS[1]
        local current = tonumber(redis.call('GET', stock_key))
        if current and current > 0 then
            redis.call('DECR', stock_key)
            return 1
        else
            return 0
        end
        """
        
        decrease_stock = redis_client.register_script(lua_script)
        result = decrease_stock(keys=[f"stock:product:{product_id}"])
        
        if result == 1:
            # 库存扣减成功，写入MySQL订单表
            # 这里需要实现数据库操作
            return True
        else:
            # 库存不足
            return False