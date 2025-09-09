# 部署说明文档

## 项目架构概述

本项目采用以下技术栈：
- 后端：FastAPI + Redis + Celery (5个Worker)
- 前端：HTML + CSS + JavaScript (原生三件套)
- 数据库：SQLite
- 通信：WebSocket

## 部署环境要求

1. Docker Engine 20.10+
2. Docker Compose 1.29+
3. 至少4GB RAM
4. 至少2个CPU核心

## 部署步骤

### 1. 克隆代码库

```bash
git clone <repository-url>
cd adaptive-tutor-system
```

### 2. 构建和启动服务

使用Docker Compose一键部署所有服务：

```bash
docker-compose up -d
```

该命令将启动以下服务（本分支默认端口）：
- Redis数据库 (端口6382)
- 后端API服务 (端口8001)
- 4个Celery Worker服务
- 前端Web服务 (端口8326)

### 3. 访问应用

- 前端界面：http://localhost:8326
- 后端API文档：http://localhost:8001/docs

### 4. 查看服务状态

```bash
docker-compose ps
```

### 5. 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

## 服务说明

### 后端服务 (backend)
- 基于FastAPI框架
- 提供RESTful API接口
- 处理WebSocket连接
- 端口映射：8001:8000

### Redis服务 (redis)
- 使用Redis Stack镜像
- 提供Redis数据库和JSON支持
- 端口映射：6382:6379

### Celery Workers
1. **Chat Worker** (celery-chat-worker)：处理聊天请求
2. **Submission Worker** (celery-submit-worker)：处理提交请求
3. **DB Writer Worker** (celery-db-worker)：处理数据库写入
4. **Behavior Worker** (celery-behavior-worker)：处理行为分析
5. **Beat** (celery-beat)：定时任务调度器

### 前端服务 (frontend)
- 基于Nginx的静态文件服务器
- 代理API请求到后端服务
- 处理WebSocket连接升级
- 端口映射：8326:80

## 与主分支并行部署

为了在同一台服务器上同时运行主分支与本对照组分支，请注意以下事项：

- 端口避让：本分支已将端口错开（Redis 6382、Backend 8001、Frontend 8326），避免与主分支常用的 6381/8000/80 或 8325 冲突。
- 容器命名：已移除固定的 container_name，使用 Compose 项目前缀避免同名冲突。
- 项目前缀：在项目根目录创建 `.env` 文件，设置不同的 `COMPOSE_PROJECT_NAME`，确保网络与卷名称隔离：

```bash
echo COMPOSE_PROJECT_NAME=ats-control > .env
docker compose up -d
```

主分支建议使用另一个项目名（例如 `ats-main`）：

```bash
# 在主分支的项目目录
echo COMPOSE_PROJECT_NAME=ats-main > .env
docker compose up -d
```

也可以在命令行通过 `-p` 指定项目名运行：

```bash
docker compose -p ats-control up -d
```

## 配置说明

### 环境变量
所有环境变量在docker-compose.yml中定义，可根据需要进行修改。

### 数据持久化
- Redis数据：通过redis_data卷持久化
- SQLite数据库：通过backend_data卷持久化

## 维护操作

### 停止服务
```bash
docker-compose down
```

### 重启服务
```bash
docker-compose restart
```

### 更新代码后重新部署
```bash
git pull
docker-compose down
docker-compose up -d --build
```

## 故障排除

### 服务启动失败
1. 检查端口占用情况
2. 查看服务日志：`docker-compose logs -f [service-name]`
3. 确认Docker资源分配是否充足

### 连接问题
1. 确认服务间网络连接正常
2. 检查环境变量配置
3. 验证防火墙设置

### 性能问题
1. 监控容器资源使用情况
2. 调整Celery Worker数量
3. 优化数据库查询
