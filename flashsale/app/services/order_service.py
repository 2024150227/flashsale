from app.utils.redis_client import redis_client
from app.utils.kafka_producer import send_order_message
import json
from datetime import datetime
from app.core.logger import order_service_logger as logger

class OrderService:
    def create_order(self, user_id: int, product_id: int) -> dict:
        """创建秒杀订单"""
        # 构造订单消息
        order_message = {
            "user_id": user_id,
            "product_id": product_id,
            "timestamp": json.dumps("2026-04-27T15:30:00Z")
        }
        
        try:
            # 发送到Kafka
            send_order_message(order_message)
        except Exception as e:
            logger.error(f"Failed to send order message to Kafka: {e}")
            # 可以选择抛出异常或返回错误信息
            raise e
        
        # 模拟订单创建
        """
        创建秒杀订单
        权重：1（低频率，但最重要）
        参数：
            user_id: 用户ID
            product_id: 商品ID
        返回：
            dict: 订单信息
        异常处理：
            400: 商品库存不足
            其他: 记录失败日志
        """
        logger.info(f"Order created: {order_message}")
        return {"status": "queued"}
    
    def process_order(self, order_message: dict) -> bool:
        """处理订单（由消费者调用）
        权重：1（低频率，但最重要）
        参数：
            order_message: 订单消息，包含用户ID和商品ID
        返回：
            bool: 是否处理成功
        异常处理：
            400: 商品库存不足
            其他: 记录失败日志
        """
        user_id = order_message["user_id"]
        product_id = order_message["product_id"]
        
        lua_script="""
        --脚本扣库存,stock_key为库存键名,也就是商品ID
        local stock_key=KEYS[1]
        -- 检查库存是否足够,tonumber()将字符串转换为数字类型
        local current=tonumber(redis.call('GET',stock_key))
        if current and current > 0 then
            -- 扣减库存
            redis.call('DECR',stock_key)
            return 1
        else
            return 0
        end
        """
        # 注册Lua脚本
        decrease_stock = redis_client.register_script(lua_script)
        result = decrease_stock(keys=[f"stock:product:{product_id}"])
        
        # 检查库存扣减结果
        if result == 1:
            # 库存扣减成功，写入MySQL订单表
            # 这里需要实现数据库操作，将订单信息写入数据库订单表
            # 例如：
            # from app.db.models import Order
            # order = Order(user_id=user_id, product_id=product_id)
            # db.session.add(order)
            # db.session.commit()
            return True
        else:
            # 库存不足
            return False