from app.utils.redis_client import redis_client
from app.utils.kafka_producer import send_order_message
from app.models.order import Order
from app.models.product import Product
from app.db.session import SessionLocal
import json
from datetime import datetime
from app.core.logger import order_service_logger as logger

class OrderService:
    def create_order(self, user_id: int, product_id: int) -> dict:
        """创建秒杀订单
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
        stock_key = f"flashsale:stock:{product_id}"
        current_stock = redis_client.get(stock_key)

        if current_stock is None:
            raise ValueError(f"商品 {product_id} 不存在或未初始化库存")

        if int(current_stock) <= 0:
            raise ValueError("商品已售罄")

        order_message = {
            "user_id": user_id,
            "product_id": product_id,
            "timestamp": datetime.now().isoformat()
        }

        try:
            send_order_message(order_message)
            logger.info(f"Order queued: {order_message}")
            return {"status": "queued"}
        except Exception as e:
            logger.error(f"Failed to send order message to Kafka: {e}")
            raise e
    
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
        result = decrease_stock(keys=[f"flashsale:stock:{product_id}"])
        
        # 检查库存扣减结果
        if result == 1:
            db = SessionLocal()
            try:
                product = db.query(Product).filter(Product.id == product_id).first()
                if product:
                    order = Order(
                        user_id=user_id,
                        product_id=product_id,
                        price=product.price,
                        status="completed"
                    )
                    db.add(order)
                    db.commit()
                    logger.info(f"Order saved to MySQL: order_id={order.id}, user_id={user_id}, product_id={product_id}")
            except Exception as e:
                logger.error(f"Failed to save order to MySQL: {e}")
                db.rollback()
            finally:
                db.close()
            return True
        else:
            return False