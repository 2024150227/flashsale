# JWT 鉴权架构说明

## 架构概述

```
用户请求
    ↓
┌─────────────────────────────────────────────┐
│           Nginx (端口 80)                   │
│    限流、连接限制、静态资源服务             │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│           Kong API 网关                     │
│  - JWT 鉴权 (jwt plugin)                    │
│  - 限流 (rate-limiting plugin)              │
│  - 健康检查 (health-checks plugin)          │
└─────────────────────────────────────────────┘
    ↓
  ┌─────────────────────────────────────┐
  │     app1 / app2 / app3 (8000)       │
  │      FastAPI 应用实例                │
  └─────────────────────────────────────┘
         ↓
    ┌─────────────────────────────────────┐
    │     Redis (缓存/库存预扣)            │
    │     Kafka (异步削峰)                 │
    │     MySQL (主从读写分离)             │
    └─────────────────────────────────────┘
```

## JWT 鉴权流程

### 1. 登录获取 Token

```
POST /api/v1/auth/login
{
  "username": "admin",
  "password": "123456"
}

响应:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. 使用 Token 请求

```
GET /api/v1/auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. Kong 验证流程

1. 请求到达 Kong
2. Kong 检查是否为公共路由（无需鉴权）
3. 如果不是公共路由，启用 JWT 插件验证
4. Kong 验证 JWT 的 `iss` 声明和签名
5. 验证通过后添加以下头部：
   - `X-Consumer-Username`: flashsale-consumer
   - `X-Consumer-ID`: <UUID>
6. 转发到后端 FastAPI 应用
7. FastAPI 应用通过 `X-Consumer-*` 头部获取用户信息

## JWT Token 结构

```json
{
  "sub": "1",
  "type": "access",
  "iss": "flashsale-jwt-key",
  "exp": 1747501459
}
```

关键说明：
- `iss` 必须与 Kong 中的 JWT 密钥的 `key` 一致（`flashsale-jwt-key`）
- `sub` 是用户 ID（字符串或数字）
- `exp` 是过期时间戳

## 配置详情

### Kong 配置

位置: [scripts/configure_kong.sh](file:///e:/Desktop/高并发秒杀系统/flashsale/scripts/configure_kong.sh)

主要配置:
- JWT 密钥: `flashsale-jwt-key`
- JWT Secret: `flashsale_jwt_secret_key_2026`
- 算法: `HS256`

### FastAPI 配置

位置: [app/core/security.py](file:///e:/Desktop/高并发秒杀系统/flashsale/app/core/security.py)

主要配置:
- `SECRET_KEY = "flashsale_jwt_secret_key_2026"`
- `JWT_ISSUER = "flashsale-jwt-key"`

## 公共路由（无需鉴权）

- `/health` - 健康检查
- `/api/v1/auth/login` - 用户登录
- `/api/v1/auth/register` - 用户注册
- `/static/*` - 静态资源
- `/avatars/*` - 头像资源
- `/login` - 登录页面
- `/flashsale` - 秒杀页面
- `/chat.html` - 聊天页面

## 需要鉴权的路由

- `/api/v1/orders/*` - 订单接口
- `/api/v1/auth/me` - 获取当前用户
- `/api/v1/auth/logout` - 用户登出
- `/api/v1/auth/logout-all` - 登出所有设备
- `/api/v1/auth/refresh` - 刷新 Token
- `/api/v1/auth/favorite/*` - 收藏商品
- `/api/v1/auth/avatar/*` - 头像管理

## 部署步骤

### 1. 启动所有服务

```bash
cd flashsale
docker-compose up -d --build
```

### 2. 等待服务启动

```bash
# 检查容器状态
docker-compose ps

# 检查服务日志
docker-compose logs -f
```

### 3. 配置 Kong

```bash
# 方式1: 使用配置脚本
docker exec -it flashsale-kong bash /scripts/configure_kong.sh

# 方式2: 手动配置（可选）
# 参考 scripts/configure_kong.sh 中的各个步骤
```

### 4. 测试登录

```bash
# 注册用户
curl -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "test123", "name": "测试用户"}'

# 登录获取 Token
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "test123"}'
```

### 5. 使用 Token 测试

```bash
# 替换 YOUR_ACCESS_TOKEN 为登录获得的 token
curl http://localhost/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 故障排查

### 1. Kong 鉴权失败

**问题**: 401 Unauthorized，Kong 返回 JWT 验证失败

**解决**:
- 检查 `iss` 声明是否为 `flashsale-jwt-key`
- 检查 secret 是否匹配
- 确认 JWT 未过期

### 2. FastAPI 获取不到用户 ID

**问题**: Kong 验证通过，但 FastAPI 返回用户未找到

**解决**:
- 检查 Kong 是否正确添加了 `X-Consumer-Custom-Id` 头
- 可能需要配置 Kong 的 request-transformer 插件

### 3. 登录成功但请求失败

**问题**: 登录能获取 token，但其他请求失败

**解决**:
- 确认请求经过 Kong 路由（通过 Nginx → Kong → 应用）
- 检查请求路径是否在公共路由列表中

## 可选优化

### 1. 添加用户自定义 ID 到 Consumer

可以修改 Kong 配置，将用户 ID 存储在 Consumer 的 `custom_id` 字段中，这样 Kong 验证通过后会传递 `X-Consumer-Custom-Id` 头。

### 2. 调整限流策略

根据实际需求调整 Kong 的 rate-limiting 插件配置：
- minute: 每分钟请求数
- hour: 每小时请求数

### 3. 添加更多公共路由

如果有其他无需鉴权的接口，在 `configure_kong.sh` 的公共路由配置中添加。
