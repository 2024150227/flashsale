from confluent_kafka import Producer, Consumer
import json
import random
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("utils.kafka_service")

class KafkaService:
    """Kafka消息服务 - 支持多生产者负载均衡"""
    
    def __init__(self):
        self.producer_pools = {}
        self.consumers = {}
        self.producer_index = {}
        self.producers_per_topic = 3
    #创建Kafka生产者
    def _create_producer(self, topic: str, instance_id: int) -> Producer:
        producer_conf = {
            #client.id: 生产者ID，用于标识生产者实例
            'client.id': f'flashsale-{topic}-producer-{instance_id}',
            #bootstrap.servers: Kafka集群的引导服务器地址，用于连接Kafka集群
            'bootstrap.servers': settings.kafka_bootstrap_servers,
            #retries: 重试次数，默认3次
            #socket.timeout.ms: 生产者发送请求超时时间，默认5000ms
            'socket.timeout.ms': 5000,
            #acks: 生产者确认机制，'all'表示所有副本都确认，'1'表示首领确认，'0'表示不确认
            'acks': 'all',
            #compression.type: 消息压缩类型，默认lz4，使用lz4压缩算法压缩消息，减少网络传输量
            'compression.type': 'lz4',
            #batch.size: 批量发送消息大小，默认16384字节，增加批量发送效率，减少网络传输次数，16kb
            'batch.size': 16384,
            #linger.ms: 批量发送延迟时间，默认5ms，增加批量发送效率，减少网络传输次数，5ms内
            'linger.ms': 5,
        }
        return Producer(producer_conf)
    #获取Kafka生产者池，每个主题创建多个生产者实例，用于负载均衡发送
    def get_producer_pool(self, topic: str) -> list:
        if topic not in self.producer_pools:
            self.producer_pools[topic] = []
            self.producer_index[topic] = 0
            
            for i in range(self.producers_per_topic):
                producer = self._create_producer(topic, i)
                self.producer_pools[topic].append(producer)
            logger.info(f"[INFO] Created {self.producers_per_topic} producers for topic: {topic}")
        
        return self.producer_pools[topic]
    #获取下一个Kafka生产者
    def _get_next_producer(self, topic: str) -> Producer:
        pool = self.get_producer_pool(topic)
        #index: 当前生产者索引，用于负载均衡发送
        index = self.producer_index[topic]
        producer = pool[index]
        
        self.producer_index[topic] = (index + 1) % len(pool)
        return producer
    #发送Kafka消息
    def send_message(self, topic: str, message: dict, key: str = None):
        producer = self._get_next_producer(topic)
        
        try:
            #produce: 发送消息到Kafka主题，key: 消息键，value: 消息值，callback: 消息交付报告回调, partition: 分区号，默认随机分配
            #partition: 分区号，默认随机分配，用于指定消息发送到哪个分区
            #key: 消息键，用于指定消息发送到哪个分区，key相同的消息会发送到同一个分区
            #callback: 消息交付报告回调，用于确认消息是否成功交付到Kafka集群的副本
            producer.produce(
                topic,
                key=key,
                value=json.dumps(message),
                callback=self._delivery_report
            )
            #poll: 轮询Kafka集群，等待消息交付报告，默认阻塞等待，直到消息交付完成
            #timeout: 轮询超时时间，默认0，表示阻塞等待，直到消息交付完成
            #return: 消息交付报告，包含消息是否成功交付到Kafka集群的副本的信息
            producer.poll(0)
            logger.info(f"Message sent to topic '{topic}' via producer")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to topic '{topic}': {str(e)}")
            return False
    #发送Kafka消息批量
    def send_messages_batch(self, topic: str, messages: list):
        pool = self.get_producer_pool(topic)
        results = []
        
        #partition: 分区号，默认随机分配，用于指定消息发送到哪个分区
        #key: 消息键，用于指定消息发送到哪个分区，key相同的消息会发送到同一个分区
        for i, message in enumerate(messages):
            producer = pool[i % len(pool)]
            try:
                producer.produce(
                    topic,
                    value=json.dumps(message),
                    callback=self._delivery_report
                )
                results.append(True)
            except Exception as e:
                logger.error(f"Batch send failed for message {i}: {str(e)}")
                results.append(False)
        
        for producer in pool:
            producer.poll(0)
        
        return all(results)
    #消息交付报告
    def _delivery_report(self, err, msg):
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")
    #获取Kafka消费者
    def get_consumer(self, topic: str, group_id: str = None) -> Consumer:
        if topic not in self.consumers:
            consumer_conf = {
                'bootstrap.servers': settings.kafka_bootstrap_servers,
                'group.id': group_id or f'flashsale-{topic}-consumer',
                'enable.auto.commit': False,
                'auto.offset.reset': 'latest',
                #fetch.min.bytes: 每次拉取的最小字节数，默认1024字节
                'fetch.min.bytes': 1024,
                #fetch.wait.max.ms: 每次拉取的最大等待时间，默认500ms
                'fetch.min.bytes': 1024,
                #fetch.wait.max.ms: 每次拉取的最大等待时间，默认500ms
                'fetch.wait.max.ms': 500,
            }
            self.consumers[topic] = Consumer(consumer_conf)
            self.consumers[topic].subscribe([topic])
            logger.info(f"[INFO] Kafka consumer initialized for topic: {topic}")
        return self.consumers[topic]
    #消费Kafka消息
    def consume_message(self, topic: str) -> dict:
        consumer = self.get_consumer(topic)
        
        try:
            message = consumer.poll(1.0)
            if message:
                if message.error():
                    logger.error(f"Consumer error: {message.error()}")
                    return None
                
                consumer.commit()
                return json.loads(message.value())
            return None
        except Exception as e:
            logger.error(f"Failed to consume message from topic '{topic}': {str(e)}")
            return None

kafka_service = KafkaService()
#发送订单消息
def send_order_message(message: dict):
    return kafka_service.send_message(settings.kafka_topic_orders, message)
#发送支付消息
def send_payment_message(message: dict):
    return kafka_service.send_message(settings.kafka_topic_payments, message)
#发送通知消息
def send_notification_message(message: dict):
    return kafka_service.send_message(settings.kafka_topic_notifications, message)
#发送日志消息
def send_log_message(message: dict):
    return kafka_service.send_message(settings.kafka_topic_logs, message)
#发送订单消息批量
def send_order_messages_batch(messages: list):
    return kafka_service.send_messages_batch(settings.kafka_topic_orders, messages)