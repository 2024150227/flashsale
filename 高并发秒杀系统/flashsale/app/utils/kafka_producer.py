from confluent_kafka import Producer
import json
from app.core.config import settings

# 初始化Kafka生产者
producer = Producer({'bootstrap.servers': settings.kafka_bootstrap_servers})

def send_order_message(message: dict):
    """发送订单消息到Kafka"""
    producer.produce(settings.kafka_topic, value=json.dumps(message))
    producer.flush()