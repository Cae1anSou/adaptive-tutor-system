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

该命令将启动以下服务：
- Redis数据库 (端口6380)
- 后端API服务 (端口8000)
- 5个Celery Worker服务
- 前端Web服务 (端口80)

### 3. 访问应用

- 前端界面：http://localhost
- 后端API文档：http://localhost:8000/docs

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
- 端口映射：8000

### Redis服务 (redis)
- 使用Redis Stack镜像
- 提供Redis数据库和JSON支持
- 端口映射：6380

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
- 端口映射：80

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