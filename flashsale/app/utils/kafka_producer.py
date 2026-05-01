from confluent_kafka import Producer
import json
import logging
from app.core.config import settings

logging.getLogger('kafka').setLevel(logging.WARNING)

_producer = None
_producer_initialized = False

def get_producer():
    global _producer, _producer_initialized
    if _producer_initialized:
        return _producer
    _producer_initialized = True
    try:
        producer_conf = {
            'client.id': 'flashsale-order-producer',
            'bootstrap.servers': settings.kafka_bootstrap_servers,
            'retries': 3,
            'socket.timeout.ms': 5000,
            'api.version.request.timeout.ms': 5000,
            'metadata.max.age.ms': 300000,
            'queue.buffering.max.size': 1000000,
            'message.send.max.retries': 1,
            'retry.backoff.ms': 1000,
        }
        _producer = Producer(producer_conf)
        logging.info("[INFO] Kafka producer initialized successfully")
    except Exception as e:
        _producer = None
        logging.warning(f"[WARNING] Kafka producer initialization failed: {str(e)}")
        return None
    return _producer

def delivery_report(err, msg):
    """Kafka消息发送回调函数"""
    if err is not None:
        logging.error(f"[ERROR] Message delivery failed: {err}")
    else:
        logging.debug(f"[DEBUG] Message delivered to {msg.topic()} [{msg.partition()}]")

def send_order_message(message: dict):
    """发送订单消息到Kafka（异步模式）"""
    producer = get_producer()
    
    if not producer:
        logging.warning(f"[WARNING] Kafka not available, message dropped: {message}")
        return False
    
    try:
        producer.produce(
            settings.kafka_topic, 
            value=json.dumps(message),
            callback=delivery_report
        )
        producer.poll(0)
        logging.info(f"Order message queued: {message}")
        return True
    except Exception as e:
        logging.error(f"[ERROR] Failed to send message to Kafka: {str(e)}")         
        return False