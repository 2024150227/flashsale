from confluent_kafka import Consumer
import json
import threading
import time
from typing import Callable, List
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("utils.kafka_consumer_manager")

class KafkaConsumerManager:
    """Kafka消费者管理器 - 支持启动多个消费者实例进行并行消费"""
    
    def __init__(self):
        self.consumers: List[Consumer] = []
        self.consumer_threads: List[threading.Thread] = []
        self.running = False
        self.lock = threading.Lock()
    
    def _create_consumer(self, topic: str, consumer_id: int, group_id: str = None) -> Consumer:
        """创建单个Kafka消费者实例"""
        consumer_conf = {
            'bootstrap.servers': settings.kafka_bootstrap_servers,
            'group.id': group_id or f'flashsale-{topic}-consumer-group',
            'client.id': f'flashsale-{topic}-consumer-{consumer_id}',
            'enable.auto.commit': False,
            'auto.offset.reset': 'latest',
            'fetch.min.bytes': 1024,
            'fetch.wait.max.ms': 500,
        }
        return Consumer(consumer_conf)
    
    def start_consumers(
        self,
        topic: str,
        callback: Callable[[dict], None],
        num_consumers: int = 3,
        group_id: str = None
    ) -> None:
        """
        启动多个Kafka消费者实例
        
        参数:
            topic: 要消费的Kafka主题
            callback: 消息处理回调函数，接收消息字典作为参数
            num_consumers: 消费者实例数量，默认为3
            group_id: 消费者组ID，可选
        """
        with self.lock:
            if self.running:
                logger.warning("[WARNING] Kafka consumers are already running")
                return
            
            self.running = True
            
            for consumer_id in range(num_consumers):
                consumer = self._create_consumer(topic, consumer_id, group_id)
                consumer.subscribe([topic])
                self.consumers.append(consumer)
                
                # 创建并启动消费者线程
                thread = threading.Thread(
                    target=self._consumer_loop,
                    args=(consumer, topic, callback, consumer_id),
                    daemon=True
                )
                self.consumer_threads.append(thread)
                thread.start()
                
                logger.info(f"[INFO] Started Kafka consumer {consumer_id} for topic: {topic}")
            
            logger.info(f"[INFO] Successfully started {num_consumers} Kafka consumers for topic: {topic}")
    
    def _consumer_loop(self, consumer: Consumer, topic: str, callback: Callable[[dict], None], consumer_id: int) -> None:
        """单个消费者的消息循环"""
        while self.running:
            try:
                message = consumer.poll(1.0)
                
                if message:
                    if message.error():
                        logger.error(f"[CONSUMER-{consumer_id}] Consumer error: {message.error()}")
                        continue
                    
                    try:
                        msg_value = json.loads(message.value())
                        logger.debug(f"[CONSUMER-{consumer_id}] Received message from topic '{topic}'")
                        
                        # 调用回调函数处理消息
                        callback(msg_value)
                        
                        # 手动提交偏移量
                        consumer.commit()
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"[CONSUMER-{consumer_id}] Failed to decode message: {str(e)}")
                        consumer.commit()
                    except Exception as e:
                        logger.error(f"[CONSUMER-{consumer_id}] Failed to process message: {str(e)}")
                        # 处理失败也提交偏移量，避免重复消费
                        consumer.commit()
            
            except Exception as e:
                logger.error(f"[CONSUMER-{consumer_id}] Unexpected error in consumer loop: {str(e)}")
                time.sleep(1)
    
    def stop_consumers(self) -> None:
        """停止所有消费者"""
        with self.lock:
            if not self.running:
                return
            
            self.running = False
            
            # 等待线程结束
            for thread in self.consumer_threads:
                if thread.is_alive():
                    thread.join(timeout=5)
            
            # 关闭所有消费者连接
            for consumer in self.consumers:
                try:
                    consumer.close()
                except Exception as e:
                    logger.error(f"Failed to close consumer: {str(e)}")
            
            logger.info("[INFO] All Kafka consumers have been stopped")
            
            # 清理资源
            self.consumers.clear()
            self.consumer_threads.clear()

# 全局消费者管理器实例
kafka_consumer_manager = KafkaConsumerManager()