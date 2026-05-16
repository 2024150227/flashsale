#!/bin/bash

KONG_ADMIN_URL="http://kong:8001"
SERVICE_NAME="flashsale-api"
JWT_SECRET="flashsale_jwt_secret_key_2026"
JWT_ALGORITHM="HS256"

wait_for_kong() {
    echo "等待 Kong 启动..."
    while ! curl -s "$KONG_ADMIN_URL/health" > /dev/null; do
        sleep 2
    done
    echo "Kong 已启动"
}

create_service() {
    echo "创建服务: $SERVICE_NAME"
    curl -s -X POST "$KONG_ADMIN_URL/services" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "'"$SERVICE_NAME"'",
            "host": "app1",
            "port": 8000,
            "protocol": "http"
        }'
}

create_upstream() {
    echo "创建上游服务器组"
    curl -s -X POST "$KONG_ADMIN_URL/upstreams" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "flashsale-upstream"
        }'

    echo "添加上游服务器"
    curl -s -X POST "$KONG_ADMIN_URL/upstreams/flashsale-upstream/targets" \
        -H "Content-Type: application/json" \
        -d '{"target": "app1:8000", "weight": 100}'

    curl -s -X POST "$KONG_ADMIN_URL/upstreams/flashsale-upstream/targets" \
        -H "Content-Type: application/json" \
        -d '{"target": "app2:8000", "weight": 100}'

    curl -s -X POST "$KONG_ADMIN_URL/upstreams/flashsale-upstream/targets" \
        -H "Content-Type: application/json" \
        -d '{"target": "app3:8000", "weight": 100}'
}

create_route() {
    echo "创建路由"
    curl -s -X POST "$KONG_ADMIN_URL/services/$SERVICE_NAME/routes" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "flashsale-route",
            "paths": ["/api/v1/"],
            "strip_path": true,
            "preserve_host": false
        }'

    echo "创建公共路由（无需鉴权）"
    curl -s -X POST "$KONG_ADMIN_URL/services/$SERVICE_NAME/routes" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "flashsale-public-route",
            "paths": ["/health", "/api/v1/auth/login", "/api/v1/auth/register", "/static", "/avatars", "/login", "/flashsale", "/chat.html"],
            "strip_path": false,
            "preserve_host": false,
            "protocols": ["http"]
        }'
}

create_jwt_consumer() {
    echo "创建 JWT 消费者"
    local CONSUMER_NAME="flashsale-consumer"
    
    curl -s -X POST "$KONG_ADMIN_URL/consumers" \
        -H "Content-Type: application/json" \
        -d '{
            "username": "'"$CONSUMER_NAME"'"
        }'

    echo "为消费者创建 JWT 密钥"
    curl -s -X POST "$KONG_ADMIN_URL/consumers/$CONSUMER_NAME/jwt" \
        -H "Content-Type: application/json" \
        -d '{
            "key": "flashsale-jwt-key",
            "secret": "'"$JWT_SECRET"'",
            "algorithm": "'"$JWT_ALGORITHM"'",
            "rsa_public_key": null,
            "iss": null
        }'
}

configure_jwt_plugin() {
    echo "配置 JWT 插件"
    curl -s -X POST "$KONG_ADMIN_URL/services/$SERVICE_NAME/plugins" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "jwt",
            "config": {
                "key_claim_name": "iss",
                "secret_is_base64": false,
                "claims_to_verify": ["exp"],
                "cookie_names": ["token"],
                "uri_param_names": ["jwt_token"]
            }
        }'
}

configure_plugins() {
    echo "配置限流插件"
    curl -s -X POST "$KONG_ADMIN_URL/services/$SERVICE_NAME/plugins" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "rate-limiting",
            "config": {
                "minute": 10000,
                "hour": 100000,
                "policy": "local"
            }
        }'

    echo "配置健康检查插件"
    curl -s -X POST "$KONG_ADMIN_URL/services/$SERVICE_NAME/plugins" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "health-checks",
            "config": {
                "active": {
                    "type": "http",
                    "http_path": "/health",
                    "timeout": 5,
                    "interval": 10,
                    "unhealthy_threshold": 3,
                    "healthy_threshold": 2
                },
                "passive": {
                    "type": "http",
                    "unhealthy_threshold": 5,
                    "healthy_threshold": 5
                }
            }
        }'
}

main() {
    wait_for_kong
    create_service
    create_upstream
    create_route
    create_jwt_consumer
    configure_jwt_plugin
    configure_plugins
    echo "Kong 配置完成，JWT 鉴权已启用"
    echo "JWT 密钥配置："
    echo "  Secret: $JWT_SECRET"
    echo "  Algorithm: $JWT_ALGORITHM"
}

main "$@"
