#!/bin/bash
echo "开始配置MySQL主从复制..."

# 等待主库启动
echo "等待主库启动..."
sleep 30

# 在主库上创建复制用户
echo "在主库上创建复制用户..."
docker exec -i flashsale-mysql-master mysql -u root -pmysql123456 << EOF
CREATE USER IF NOT EXISTS 'replica'@'%' IDENTIFIED BY 'replica123';
GRANT REPLICATION SLAVE ON *.* TO 'replica'@'%';
FLUSH PRIVILEGES;
EOF

# 获取主库状态
echo "获取主库状态..."
MASTER_STATUS=$(docker exec -i flashsale-mysql-master mysql -u root -pmysql123456 -e "SHOW MASTER STATUS\G" 2>/dev/null)
MASTER_LOG_FILE=$(echo "$MASTER_STATUS" | grep "File:" | awk '{print $2}')
MASTER_LOG_POS=$(echo "$MASTER_STATUS" | grep "Position:" | awk '{print $2}')

echo "主库日志文件: $MASTER_LOG_FILE"
echo "主库日志位置: $MASTER_LOG_POS"

# 在从库上配置复制
echo "在从库上配置复制..."
docker exec -i flashsale-mysql-slave mysql -u root -pmysql123456 << EOF
STOP SLAVE;
CHANGE MASTER TO 
  MASTER_HOST='mysql-master',
  MASTER_USER='replica',
  MASTER_PASSWORD='replica123',
  MASTER_LOG_FILE='$MASTER_LOG_FILE',
  MASTER_LOG_POS=$MASTER_LOG_POS;
START SLAVE;
EOF

# 检查复制状态
echo "检查复制状态..."
docker exec -i flashsale-mysql-slave mysql -u root -pmysql123456 -e "SHOW SLAVE STATUS\G" 2>/dev/null | grep -E "(Slave_IO_Running|Slave_SQL_Running)"

echo "主从复制配置完成！"