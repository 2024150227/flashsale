#!/usr/bin/env python3
"""
库存同步脚本

功能：
1. 秒杀活动开始1天后执行
2. 将Redis中的真实库存同步到MySQL
3. 确保MySQL数据与Redis一致

用法：
    python scripts/sync_stock.py [--force]

注意：
    正常情况下，脚本会在秒杀开始1天后自动运行
    使用 --force 参数可强制立即执行（用于测试）
"""
import sys
import os
import argparse
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.redis_client import redis_client
from app.models.product import Product
from app.db.session import SessionLocal
from app.core.logger import main_logger as logger

FLASH_SALE_START_KEY = "flashsale:start_time"
DEFAULT_FLASH_SALE_DURATION_DAYS = 1


def get_flash_sale_start_time():
    start_time_str = redis_client.get(FLASH_SALE_START_KEY)
    if start_time_str:
        return datetime.fromisoformat(start_time_str)
    return None


def set_flash_sale_start_time(start_time=None):
    if start_time is None:
        start_time = datetime.now()
    redis_client.set(FLASH_SALE_START_KEY, start_time.isoformat())
    return start_time


def is_sync_allowed(start_time, force=False):
    if force:
        return True

    if start_time is None:
        logger.warning("Flash sale start time not set. Use --force to sync anyway.")
        return False

    elapsed = datetime.now() - start_time
    if elapsed < timedelta(days=DEFAULT_FLASH_SALE_DURATION_DAYS):
        remaining = timedelta(days=DEFAULT_FLASH_SALE_DURATION_DAYS) - elapsed
        logger.info(f"Flash sale not ended. {remaining.total_seconds():.0f} seconds remaining.")
        return False

    return True


def sync_stock_to_mysql(force=False):
    logger.info("=" * 60)
    logger.info("Stock Sync Script Starting...")
    logger.info("=" * 60)

    start_time = get_flash_sale_start_time()
    logger.info(f"Flash sale start time: {start_time}")

    if not is_sync_allowed(start_time, force):
        logger.info("Sync not allowed yet. Exiting.")
        return False

    db = SessionLocal()
    synced_count = 0
    error_count = 0

    try:
        products = db.query(Product).filter(Product.is_active == 1).all()
        logger.info(f"Found {len(products)} active products")

        for product in products:
            redis_key = f"flashsale:stock:{product.id}"
            redis_stock = redis_client.get(redis_key)

            if redis_stock is None:
                logger.warning(f"Product {product.id} ({product.name}): No Redis stock found, skipping")
                continue

            redis_stock_value = int(redis_stock)
            old_stock = product.stock

            product.stock = redis_stock_value
            synced_count += 1

            logger.info(f"Product {product.id} ({product.name}): {old_stock} -> {redis_stock_value}")

        db.commit()
        logger.info(f"Stock sync completed: {synced_count} products updated, {error_count} errors")
        return True

    except Exception as e:
        logger.error(f"Stock sync failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Sync Redis stock to MySQL')
    parser.add_argument('--force', action='store_true', help='Force sync immediately (skip time check)')
    args = parser.parse_args()

    success = sync_stock_to_mysql(force=args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
