from app.utils.redis_client import redis_client
from app.utils.kafka_service import send_order_message, send_order_messages_batch
from app.utils.sales_rank import update_sales_rank
from app.utils.bitmap import mark_user_seckill, has_user_seckill
from app.models.order import Order
from app.models.product import Product
from app.utils.database_router import get_master_db, get_slave_db
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
import json
from datetime import datetime
from app.core.logger import order_service_logger as logger

class OrderService:
    def create_order(self, user_id: int, product_id: int, session_id: int) -> dict:
        """创建秒杀订单
        参数：
            user_id: 用户ID
            product_id: 商品ID
            session_id: 场次ID
        返回：
            dict: 订单信息
        """
        stock_key = f"flashsale:stock:{product_id}"
        current_stock = redis_client.get(stock_key)

        if current_stock is None:
            raise ValueError(f"商品 {product_id} 不存在或未初始化库存")

        if int(current_stock) <= 0:
            raise ValueError("商品已售罄")

        if has_user_seckill(product_id, user_id, session_id):
            raise ValueError("您已购买过该商品，请勿重复下单")

        order_message = {
            "user_id": user_id,
            "product_id": product_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

        try:
            send_order_message(order_message)
            mark_user_seckill(product_id, user_id, session_id)
            logger.info(f"Order queued: {order_message}")
            return {"status": "queued"}
        except Exception as e:
            logger.error(f"Failed to send order message to Kafka: {e}")
            raise e

    def get_orders(self, user_id: int) -> list:
        """获取用户订单列表（读操作，使用从库）"""
        try:
            db = next(get_slave_db())
            orders = db.query(Order).filter(Order.user_id == user_id).all()
            return orders
        except Exception as e:
            logger.error(f"Failed to get orders for user {user_id}: {e}")
            raise e

    def process_order(self, order_message: dict) -> bool:
        """处理订单（写操作，使用主库）"""
        user_id = order_message["user_id"]
        product_id = order_message["product_id"]
        session_id = order_message["session_id"]

        lua_script="""
        local stock_key=KEYS[1]
        local current=tonumber(redis.call('GET',stock_key))
        if current and current > 0 then
            redis.call('DECR',stock_key)
            return 1
        else
            return 0
        end
        """
        decrease_stock = redis_client.register_script(lua_script)
        result = decrease_stock(keys=[f"flashsale:stock:{product_id}"])

        if result == 1:
            db = next(get_master_db())
            try:
                # 方式1：使用 FOR UPDATE 查询，触发临键锁（Next-Key Lock）
                # 锁定区间：user_id = ? AND product_id = ? AND session_id = ?
                existing_order = db.query(Order).filter(
                    Order.user_id == user_id,
                    Order.product_id == product_id,
                    Order.seckill_session_id == session_id
                ).with_for_update().first()

                if existing_order:
                    logger.warning(f"Duplicate order (Next-Key Lock) detected: user_id={user_id}, product_id={product_id}, session_id={session_id}")
                    return True

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
            except IntegrityError:
                db.rollback()
                logger.warning(f"Duplicate order (Unique Constraint) detected: user_id={user_id}, product_id={product_id}, session_id={session_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to save order to MySQL: {e}")
                db.rollback()
            finally:
                db.close()
            return True
        else:
            return False
    
    def create_orders_batch(self, orders_data: list) -> dict:
        """批量创建秒杀订单（使用多生产者负载均衡）
        
        参数：
            orders_data: 订单数据列表，每个元素包含 user_id, product_id, session_id
        
        返回：
            dict: 批量处理结果
        """
        messages = []
        
        for order_data in orders_data:
            user_id = order_data.get('user_id')
            product_id = order_data.get('product_id')
            session_id = order_data.get('session_id')
            
            if not all([user_id, product_id, session_id]):
                continue
            
            stock_key = f"flashsale:stock:{product_id}"
            current_stock = redis_client.get(stock_key)
            
            if current_stock is None:
                continue
            
            if int(current_stock) <= 0:
                continue
            
            if has_user_seckill(product_id, user_id, session_id):
                continue
            
            order_message = {
                "user_id": user_id,
                "product_id": product_id,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
            messages.append(order_message)
            mark_user_seckill(product_id, user_id, session_id)
        
        if messages:
            try:
                send_order_messages_batch(messages)
                logger.info(f"Batch orders queued: {len(messages)}")
            except Exception as e:
                logger.error(f"Failed to send batch order messages: {e}")
                raise e
        
        return {"status": "queued", "count": len(messages)}