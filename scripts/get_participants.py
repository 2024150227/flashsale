#!/usr/bin/env python3
"""
获取秒杀参与人数脚本

功能：统计指定商品和场次的秒杀参与人数
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.utils.bitmap import get_seckill_participants
from app.utils.redis_client import redis_client

def get_participants(product_id: int, session_id: int) -> int:
    """获取指定商品和场次的参与人数"""
    return get_seckill_participants(product_id, session_id)

def main():
    if len(sys.argv) < 3:
        print("用法: python get_participants.py <商品ID> <场次ID>")
        print("示例: python get_participants.py 1001 1")
        return

    try:
        product_id = int(sys.argv[1])
        session_id = int(sys.argv[2])
        count = get_participants(product_id, session_id)
        print(f"商品 {product_id} 场次 {session_id} 的参与人数: {count}")
    except ValueError:
        print("请输入有效的商品ID和场次ID（数字）")

if __name__ == "__main__":
    main()
