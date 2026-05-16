# HTTPS 架构配置说明

## 架构概述

```
用户浏览器 (HTTPS)
        ↓
    Nginx (SSL终止)
    ├─ 端口80 → 重定向到443
    └─ 端口443 → SSL解密 → Kong → FastAPI
        ↓
    Kong (8000, HTTP)
        ↓
    FastAPI应用 (app1/app2/app3)
        ↓
    Redis / Kafka / MySQL
```

## HTTPS 配置说明

### 1. Nginx配置更新 ([nginx/nginx.conf](file:///e:/Desktop/高并发秒杀系统/flashsale/nginx/nginx.conf)

**新增功能：**
- `listen 80` 服务器块 → 301重定向HTTP到HTTPS
- `listen 443 ssl http2` → 启用HTTPS和HTTP/2
- SSL证书配置
- TLS 1.2 / TLS 1.3 协议支持
- `X-Forwarded-Proto https` → 传递协议信息给后端

### 2. Docker Compose配置 ([docker-compose.yml](file:///e:/Desktop/高并发秒杀系统/flashsale/docker-compose.yml)

**新增配置：**
- 端口映射：`443:443`
- SSL证书挂载：`./nginx/ssl:/etc/nginx/ssl:ro`
- Healthcheck更新：使用`curl -k`（忽略自签名证书警告）

## 快速开始

### 1. 生成自签名SSL证书

**Windows用户：**
```powershell
cd flashsale/scripts
powershell -ExecutionPolicy Bypass -File generate-ssl.ps1
```

**Linux/Mac用户：**
```bash
cd flashsale/scripts
chmod +x generate-ssl.sh
./generate-ssl.sh
```

### 2. 启动服务

```bash
cd flashsale
docker-compose down
docker-compose up -d --build
```

### 3. 配置Kong（如果需要）

```bash
docker exec -it flashsale-kong bash /scripts/configure-kong.sh
```

### 4. 访问应用

- **HTTPS访问**: https://localhost/
- **HTTP访问**: http://localhost/ → 自动重定向到HTTPS

**注意**: 浏览器会显示"不安全"警告，因为我们使用的是自签名证书。

## SSL证书说明

### 开发环境（当前）
- 使用自签名证书
- 浏览器显示安全警告
- 适合开发和测试

### 生产环境（推荐）

**方案A: Let's Encrypt（免费）**
```bash
# 使用certbot获取真实证书
# 生产部署时配置自动续期
```

**方案B: 商业CA证书**
- 购买SSL证书
- 替换`nginx/ssl/`下的证书文件
- 更新nginx.conf中的证书路径

## 压测脚本调整

压测脚本访问地址从 `http://localhost:8000` 改为：
```
https://localhost  # 通过Nginx HTTPS
```

Locust配置示例：
```python
--host=https://localhost
```

**注意**: 使用自签名证书时，需要在代码中忽略SSL验证：
```python
# 在requests调用时添加
verify=False
```

## 安全特性

### 1. TLS配置
- TLS 1.2 / TLS 1.3 协议
- 现代加密套件
- HSTS（可添加）

### 2. 请求头传递
- `X-Forwarded-For`: 客户端真实IP
- `X-Forwarded-Proto`: 原始协议（https）
- `X-Forwarded-Ssl`: SSL标记

### 3. 安全响应头（可选）
可在nginx中添加更多安全头：
```nginx
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
```

## 常见问题

### Q: 浏览器显示"您的连接不是私密连接"
**A**: 这是正常的，因为我们使用的是自签名证书。点击"高级"→"继续访问"即可。

### Q: 如何获取真实的SSL证书？
**A**: 使用Let's Encrypt，或者购买商业证书。需要有真实域名。

### Q: 证书文件权限问题？
**A**: 确保证书文件对nginx用户可读（权限644或更安全的600）。

### Q: 如何配置HSTS？
**A**: 在nginx server块中添加：
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```
