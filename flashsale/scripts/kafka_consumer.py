#!/usr/bin/env python3
"""
Kafka 订单消费者脚本

功能：消费 Kafka 中的订单消息，调用 OrderService.process_order() 扣减库存
"""
import json
import signal
import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from confluent_kafka import Consumer, KafkaError, KafkaException
from app.core.config import settings
from app.services.order_service import OrderService

class OrderConsumer:
    def __init__(self):
        self.running = True
        self.order_service = OrderService()
        # 初始化 Kafka 消费者配置
        consumer_conf = {
            # 客户端ID，用于标识消费者实例
            # 从 Kafka 服务器获取配置
            'client.id': 'flashsale-order-consumer',
            # Kafka 服务器地址
            'bootstrap.servers': settings.kafka_bootstrap_servers,
            'group.id': 'flashsale_order_group',
            # 消费者从哪里开始消费
            # earliest: 从最早的消息开始消费
            # latest: 从最新的消息开始消费
            # none: 从偏移量开始消费
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
        }
        
        try:
            self.consumer = Consumer(consumer_conf)
            self.consumer.subscribe([settings.kafka_topic])
            logger.info(f"Kafka consumer initialized, subscribed to topic: {settings.kafka_topic}")
        except Exception as e:
            logger.error(f"Kafka consumer initialization failed: {e}")
            self.consumer = None

    def process_message(self, msg):
        try:
            order_message = json.loads(msg.value().decode('utf-8'))
            user_id = order_message.get('user_id')
            product_id = order_message.get('product_id')
            
            logger.info(f"Processing order: user_id={user_id}, product_id={product_id}")
            
            success = self.order_service.process_order(order_message)
            # asynchronous=False 表示同步提交偏移量，
            # 确保消息处理完成后提交偏移量
            if success:
                logger.info(f"Order processed successfully: user_id={user_id}, product_id={product_id}")
                self.consumer.commit(asynchronous=False)
            else:
                logger.warning(f"Order processing failed (likely stockout): user_id={user_id}, product_id={product_id}")
                self.consumer.commit(asynchronous=False)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            logger.error(f"Error processing order: {e}")
    # 启动消费者
    # 1. 注册信号处理函数，用于优雅关闭消费者
    # 2. 进入主循环，持续消费消息
    def start(self):
        if not self.consumer:
            logger.error("Consumer not initialized, cannot start")
            return
            
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
        logger.info("Order consumer started, waiting for messages...")
        
        while self.running:
            try:
                # 消费消息,poll() 方法阻塞等待新消息，
                # 超时时间为 1 秒
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                # 处理消息
                # 1. 解析消息内容
                # 2. 调用 OrderService.process_order() 处理订单
                # 3. 提交偏移量
                # 4. 处理异常情况
                if msg.error():
                    # 处理 Kafka 错误
                    # 1. 检查是否是分区结束错误
                    # 2. 其他错误，记录日志并继续消费       
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.info(f"Reached end of partition {msg.partition()}")
                    else:
                        logger.error(f"Kafka error: {msg.error()}")
                else:
                    self.process_message(msg)
                    
            except KafkaException as e:
                logger.error(f"Kafka exception: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                continue
        
        self.shutdown()

    def shutdown(self, signum=None, frame=None):
        logger.info("Shutting down consumer...")
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Consumer closed")

def main():
    logger.info("=" * 60)
    logger.info("Kafka Order Consumer Starting...")
    logger.info("=" * 60) 
    consumer = OrderConsumer()
    consumer.start()

if __name__ == "__main__":
    main()
