from app.utils.database_router import get_master_db
from sqlalchemy import text
from app.core.logger import app_logger as logger

class DatabaseLockService:
    """数据库锁服务 - 提供记录锁、间隙锁、临键锁等功能"""

    @staticmethod
    def lock_order_range(user_id: int, product_id: int, session_id: int) -> bool:
        """
        使用临键锁（Next-Key Lock）锁定订单区间
        解决：幻读问题、重复下单问题
        
        参数：
            user_id: 用户ID
            product_id: 商品ID
            session_id: 场次ID
        
        返回：
            bool: 是否成功锁定
        """
        db = next(get_master_db())
        try:
            # 使用 FOR UPDATE 触发临键锁
            sql = text("""
                SELECT id FROM orders 
                WHERE user_id = :user_id 
                AND product_id = :product_id 
                AND seckill_session_id = :session_id
                FOR UPDATE
            """)
            
            db.execute(sql, {
                "user_id": user_id,
                "product_id": product_id,
                "session_id": session_id
            })
            db.commit()
            logger.info(f"Next-Key Lock acquired: user_id={user_id}, product_id={product_id}, session_id={session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to acquire Next-Key Lock: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    @staticmethod
    def lock_product_stock(product_id: int) -> bool:
        """
        锁定商品库存记录
        解决：库存并发修改问题
        
        参数：
            product_id: 商品ID
        
        返回：
            bool: 是否成功锁定
        """
        db = next(get_master_db())
        try:
            sql = text("""
                SELECT id, stock FROM products 
                WHERE id = :product_id
                FOR UPDATE
            """)
            
            result = db.execute(sql, {"product_id": product_id})
            db.commit()
            logger.info(f"Record Lock acquired for product: product_id={product_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to acquire Record Lock: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    @staticmethod
    def lock_gap_by_id(min_id: int, max_id: int) -> bool:
        """
        锁定ID范围（间隙锁）
        解决：范围插入导致的幻读
        
        参数：
            min_id: 最小ID
            max_id: 最大ID
        
        返回：
            bool: 是否成功锁定
        """
        db = next(get_master_db())
        try:
            sql = text("""
                SELECT id FROM orders 
                WHERE id > :min_id AND id < :max_id
                FOR UPDATE
            """)
            
            db.execute(sql, {"min_id": min_id, "max_id": max_id})
            db.commit()
            logger.info(f"Gap Lock acquired: id_range=({min_id}, {max_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to acquire Gap Lock: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    @staticmethod
    def lock_for_share(user_id: int) -> bool:
        """
        共享锁（读锁）- FOR SHARE
        允许多个事务同时读取，但阻止修改
        
        参数：
            user_id: 用户ID
        
        返回：
            bool: 是否成功锁定
        """
        db = next(get_master_db())
        try:
            sql = text("""
                SELECT id FROM orders 
                WHERE user_id = :user_id
                FOR SHARE
            """)
            
            db.execute(sql, {"user_id": user_id})
            db.commit()
            logger.info(f"Share Lock acquired: user_id={user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to acquire Share Lock: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    @staticmethod
    def check_isolation_level() -> dict:
        """
        检查当前事务隔离级别
        """
        db = next(get_master_db())
        try:
            sql = text("SELECT @@transaction_isolation AS isolation_level")
            result = db.execute(sql).fetchone()
            
            sql_global = text("SELECT @@global.transaction_isolation AS global_isolation_level")
            result_global = db.execute(sql_global).fetchone()
            
            return {
                "current_isolation_level": result[0] if result else None,
                "global_isolation_level": result_global[0] if result_global else None
            }
        except Exception as e:
            logger.error(f"Failed to check isolation level: {e}")
            return {}
        finally:
            db.close()

    @staticmethod
    def check_innodb_locks() -> list:
        """
        查询当前InnoDB锁信息（仅用于调试）
        需要PROCESS权限
        """
        db = next(get_master_db())
        try:
            sql = text("""
                SELECT 
                    OBJECT_SCHEMA,
                    OBJECT_NAME,
                    LOCK_TYPE,
                    LOCK_MODE,
                    LOCK_STATUS,
                    LOCK_DATA
                FROM performance_schema.data_locks
            """)
            
            result = db.execute(sql).fetchall()
            locks = []
            for row in result:
                locks.append({
                    "schema": row[0],
                    "table": row[1],
                    "lock_type": row[2],
                    "lock_mode": row[3],
                    "status": row[4],
                    "data": row[5]
                })
            return locks
        except Exception as e:
            logger.error(f"Failed to check InnoDB locks: {e}")
            return []
        finally:
            db.close()