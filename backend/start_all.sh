#!/bin/bash

# 统一启动脚本，用于启动 Redis、后端服务和所有 Celery Worker

set -e  # 遇到错误时退出

echo "开始启动所有服务..."

# 检查是否在 backend 目录下
if [ ! -f "app/main.py" ]; then
    echo "错误: 请在 backend 目录下运行此脚本"
    exit 1
fi

# 启动后端服务
echo "启动后端服务..."
python -m app.main &

# 等待后端服务启动
sleep 3

# 启动 Celery Workers
echo "启动 Celery Workers..."

# 启动 Chat Worker
celery -A app.celery_app worker -l info -Q chat_queue --pool=prefork -n ai_worker@%h -c 2 &

# 启动 Submission Worker
celery -A app.celery_app worker -l info -Q submit_queue --pool=prefork -n submit_worker@%h -c 2 &

# 启动 DB Writer Worker
celery -A app.celery_app worker -l info -Q db_writer_queue --pool=gevent -n db_worker@%h -c 10 &

# 启动 Behavior Worker
celery -A app.celery_app worker -l info -Q behavior_queue --pool=prefork -n behavior_worker@%h -c 2 &

echo "所有服务已启动!"
echo "按 Ctrl+C 停止所有服务"

# 等待所有后台进程
wait