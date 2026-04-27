
---

## 🎯 项目名称  
**「FlashSale」—— 基于 FastAPI 的高并发秒杀系统**

> 项目结构：
```
flashsale/
├── app/
│   ├── main.py                # FastAPI 入口
│   ├── api/
│   │   └── v1
│   │       ├── __init__.py
│   │       ├── products.py    # 商品接口
│   │       └── orders.py      # 秒杀下单接口
│   ├── core/
│   │   ├── config.py          # 配置管理
│   │   └── security.py        # （可选）简单鉴权
│   ├── db/
│   │   └── session.py         # DB 连接池
│   ├── models/                # SQLAlchemy 模型
│   ├── schemas/               # Pydantic 数据校验
│   ├── services/
│   │   ├── product_service.py
│   │   └── order_service.py   # 核心业务逻辑
│   └── utils/
│       ├── redis_client.py
│       ├── kafka_producer.py
│       └── rate_limiter.py    # 限流工具
├── scripts/
│   └── load_test.py           # Locust 压测脚本
├── docker-compose.yml         # 一键启动 MySQL + Redis + Kafka
├── Dockerfile
├── requirements.txt
└── README.md                  # 必须写清楚架构、部署、压测结果！
```

---

## 🧩 系统核心功能

| 功能         | 描述                                          |
| ------------ | --------------------------------------------- |
| **商品展示** | 查看秒杀商品列表及详情（含剩余库存）          |
| **秒杀下单** | 用户点击“立即秒杀”，尝试创建订单              |
| **异步处理** | 下单请求不直接写 DB，而是发到 Kafka           |
| **订单消费** | 后台消费者从 Kafka 取消息，真正扣库存、建订单 |
| **限流保护** | 对秒杀接口做 QPS 限制（如 1000 req/s）        |
| **防超卖**   | 通过 Redis Lua 脚本保证库存原子性             |

---

## 🗺️ 系统架构图（文字版）

```
[用户] 
   │
   ▼
[FastAPI Web 服务] ←─┐
   │                 │
   ├─(1) 查询商品 → [Redis 缓存]
   │                 ▲
   ├─(2) 秒杀请求 → [限流中间件] → [Kafka Producer]
   │                                   │
   │                                   ▼
   │                           [Kafka Topic: flashsale_orders]
   │                                   │
   │                                   ▼
   └─────────────── [Order Consumer Service] ←─┐
                         │                      │
                         ├─(3) 执行 Redis Lua 扣库存（原子）
                         │
                         └─(4) 写入 MySQL 订单表
```

> 💡 说明：整个下单链路是 **异步 + 最终一致性**，但通过 Redis Lua 保证了**库存不会超卖**。

---
