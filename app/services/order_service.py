from app.utils.redis_client import redis_client
from app.utils.kafka_service import send_order_message, send_order_messages_batch
from app.utils.sales_rank import update_sales_rank
from app.utils.local_cache import local_cache
from app.models.order import Order
from app.models.product import Product
from app.utils.database_router import get_master_db, get_slave_db
from app.core.logger import order_service_logger as logger
from datetime import datetime
import json

class OrderService:
    def _check_local_stock(self, product_id: int) -> bool:
        local_stock = local_cache.get_stock(product_id)
        if local_stock is not None and local_stock <= 0:
            logger.debug(f"Local cache: Product {product_id} stock is 0")
            return False
        return True
    
    def _update_local_stock(self, product_id: int, stock: int):
        local_cache.set_stock(product_id, stock)
    
    def _check_redis_stock(self, product_id: int) -> int:
        stock_key = f"flashsale:stock:{product_id}"
        current_stock = redis_client.get(stock_key)
        if current_stock is None:
            raise ValueError(f"商品 {product_id} 不存在或未初始化库存")
        return int(current_stock)
    
    def _pre_decrease_stock(self, product_id: int) -> bool:
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
        result = decrease_stock(keys=[f"flashsale:stock:{product_id}"])
        return result == 1
    
    def create_order(self, user_id: int, product_id: int, session_id: int) -> dict:
        if not self._check_local_stock(product_id):
            raise ValueError("商品已售罄")
        
        redis_stock = self._check_redis_stock(product_id)
        if redis_stock <= 0:
            self._update_local_stock(product_id, 0)
            raise ValueError("商品已售罄")
        
        if not self._pre_decrease_stock(product_id):
            self._update_local_stock(product_id, 0)
            raise ValueError("商品已售罄")
        
        self._update_local_stock(product_id, redis_stock - 1)
        
        order_message = {
            "user_id": user_id,
            "product_id": product_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            send_order_message(order_message)
            logger.info(f"Order queued: {order_message}")
            return {"status": "queued"}
        except Exception as e:
            redis_client.incr(f"flashsale:stock:{product_id}")
            self._update_local_stock(product_id, redis_stock)
            logger.error(f"Failed to send order message to Kafka: {e}")
            raise e
    
    def get_orders(self, user_id: int) -> list:
        try:
            db = next(get_slave_db())
            orders = db.query(Order).filter(Order.user_id == user_id).all()
            return orders
        except Exception as e:
            logger.error(f"Failed to get orders for user {user_id}: {e}")
            raise e
    
    def process_order(self, order_message: dict) -> bool:
        user_id = order_message["user_id"]
        product_id = order_message["product_id"]
        session_id = order_message["session_id"]
        
        db = next(get_master_db())
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                order = Order(
                    user_id=user_id,
                    product_id=product_id,
                    seckill_session_id=session_id,
                    price=product.price,
                    status="completed"
                )
                db.add(order)
                db.commit()
                logger.info(f"Order saved: order_id={order.id}, user_id={user_id}, product_id={product_id}, session_id={session_id}")
                update_sales_rank(product_id)
                return True
        except Exception as e:
            logger.error(f"Failed to save order to MySQL: {e}")
            db.rollback()
        finally:
            db.close()
        return True
    
    def create_orders_batch(self, orders_data: list) -> dict:
        messages = []
        success_count = 0
        fail_count = 0
        
        for order_data in orders_data:
            user_id = order_data.get('user_id')
            product_id = order_data.get('product_id')
            session_id = order_data.get('session_id')
            
            if not all([user_id, product_id, session_id]):
                fail_count += 1
                continue
            
            try:
                if not self._check_local_stock(product_id):
                    fail_count += 1
                    continue
                
                redis_stock = self._check_redis_stock(product_id)
                if redis_stock <= 0:
                    self._update_local_stock(product_id, 0)
                    fail_count += 1
                    continue
                
                if not self._pre_decrease_stock(product_id):
                    self._update_local_stock(product_id, 0)
                    fail_count += 1
                    continue
                
                self._update_local_stock(product_id, redis_stock - 1)
                
                order_message = {
                    "user_id": user_id,
                    "product_id": product_id,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                messages.append(order_message)
                success_count += 1
            except Exception as e:
                logger.error(f"Batch order error: {e}")
                fail_count += 1
        
        if messages:
            try:
                send_order_messages_batch(messages)
                logger.info(f"Batch orders queued: {len(messages)}")
            except Exception as e:
                logger.error(f"Failed to send batch order messages: {e}")
                raise e
        
        return {"status": "queued", "success_count": success_count, "fail_count": fail_count}