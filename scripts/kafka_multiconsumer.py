import logging
from app.utils.kafka_service import kafka_service, settings
from app.services.order_service import OrderService
import json

logging.basicConfig(level=logging.INFO)
order_service = OrderService()

def consume_orders():
    """消费订单消息"""
    while True:
        message = kafka_service.consume_message(settings.kafka_topic_orders)
        if message:
            logging.info(f"[ORDER] Processing order: {message}")
            order_service.process_order(message)

def consume_payments():
    """消费支付消息"""
    while True:
        message = kafka_service.consume_message(settings.kafka_topic_payments)
        if message:
            logging.info(f"[PAYMENT] Processing payment: {message}")
            process_payment(message)

def consume_notifications():
    """消费通知消息"""
    while True:
        message = kafka_service.consume_message(settings.kafka_topic_notifications)
        if message:
            logging.info(f"[NOTIFICATION] Sending notification: {message}")
            send_notification(message)

def consume_logs():
    """消费日志消息"""
    while True:
        message = kafka_service.consume_message(settings.kafka_topic_logs)
        if message:
            logging.info(f"[LOG] Processing log: {message}")
            process_log(message)

def process_payment(message: dict):
    """处理支付回调"""
    order_id = message.get('order_id')
    status = message.get('status')
    
    if status == 'success':
        logging.info(f"Payment successful for order {order_id}")
    else:
        logging.warning(f"Payment failed for order {order_id}")

def send_notification(message: dict):
    """发送用户通知"""
    user_id = message.get('user_id')
    content = message.get('content')
    logging.info(f"Sending notification to user {user_id}: {content}")

def process_log(message: dict):
    """处理操作日志"""
    action = message.get('action')
    user_id = message.get('user_id')
    timestamp = message.get('timestamp')
    logging.info(f"Log recorded: {user_id} - {action} at {timestamp}")

if __name__ == "__main__":
    import threading
    
    threads = []
    
    t1 = threading.Thread(target=consume_orders, daemon=True)
    t2 = threading.Thread(target=consume_payments, daemon=True)
    t3 = threading.Thread(target=consume_notifications, daemon=True)
    t4 = threading.Thread(target=consume_logs, daemon=True)
    
    threads.extend([t1, t2, t3, t4])
    
    for t in threads:
        t.start()
    
    while True:
        pass