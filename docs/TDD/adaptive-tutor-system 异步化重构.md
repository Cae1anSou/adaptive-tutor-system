# 技术设计文档： adaptive-tutor-system 异步化重构

**版本**: 1.0
**作者**: cxz
**日期**: 2025-08-22
**状态**: 草稿

## 1. 项目背景与目标

本系统是一个自适应学习辅导系统，其核心是通过 AI 聊天机器人与学生互动，追踪学生的认知、情感和行为状态，并提供个性化的辅导。随着用户量的预期增长，当前的同步、单体式架构在**可扩展性**和**用户响应性**方面将面临严峻挑战。

本次重构旨在将系统的核心交互（特别是 `/ai/chat` API）从同步模式重构为异步模式，以解决以下核心问题：

1.  **可扩展性瓶颈**: `UserStateService` 使用进程内内存缓存 (`_state_cache`)，导致无法进行水平扩展。
2.  **用户体验不佳**: 对外部 LLM 服务的同步调用导致 API 响应时间过长（3-5秒），影响用户交互的流畅性。
3.  **系统可靠性不足**: 使用 FastAPI 的 `BackgroundTasks` 处理关键的日志和快照任务，在服务崩溃时存在任务丢失的风险。

### 重构目标 (成功指标)

-   **P99 响应时间**: 将 `/ai/chat` API 的 P99 响应时间从 3-5秒降低到 **500ms** 以下。
-   **水平扩展能力**: 架构支持至少 **10 个并发**的服务实例，且用户状态保持强一致性。
-   **任务可靠性**: 确保关键的后台任务（如状态快照、事件记录）在服务重启或崩溃后仍能被最终执行。

## 2. 当前架构分析

-   **Web 框架**: FastAPI
-   **核心服务**: `DynamicController` 编排 `UserStateService`, `RAGService`, `LLMGateway` 等。
-   **状态管理**: `UserStateService` 通过进程内字典 (`_state_cache`) 缓存 `StudentProfile` 对象，并定期通过快照持久化到 SQLite 数据库。
-   **后台任务**: 使用 FastAPI 的 `BackgroundTasks` 处理非阻塞任务。
-   **依赖管理**: 手动实现的单例模式和依赖注入 (`dependency_injection.py`)。

## 3. 重构范围与目标架构

-   **重构范围**:
    -   核心改造 `UserStateService` 的状态管理机制。
    -   改造 `/ai/chat` API Endpoint，将其处理逻辑异步化。
    -   引入并配置 Celery 和 Redis。
    -   调整依赖注入系统以适应 Celery Worker 环境。
-   **目标架构**:
    -   **Web 层**: FastAPI 仍然负责处理 HTTP 请求，但对于耗时操作，它将作为任务的生产者。
    -   **消息队列 (Broker)**: Redis，用于接收和缓存来自 FastAPI 的任务。
    -   **任务处理层 (Worker)**: Celery Worker 集群，作为任务的消费者，独立于 Web 进程执行核心业务逻辑。
    -   **结果存储 (Backend)**: Redis，用于存储 Celery 任务的执行结果。
    -   **中心化状态存储**: **Redis (with RedisJSON)**，用于存储所有用户的 `StudentProfile` 状态，替代原有的内存缓存。
    -   **持久化存储**: SQLite 数据库保持不变，作为状态快照和事件日志的最终持久化存储。

## 4. 核心设计变更

### 4.1 引入 Celery 和 Redis

-   **技术栈**:
    -   `celery`: 用于定义和执行分布式任务。
    -   `redis`: 同时作为 Celery 的 Broker, Backend，以及我们的中心化状态存储。
    -   `redis-py` (with JSON support): Python 客户端，用于与 Redis 交互。
-   **配置**:
    -   创建 `celery_app.py` 配置文件，定义 Celery 应用实例，并指定 Redis 的连接信息。
    -   定义至少两个专用队列，用于任务路由：
        -   `chat_queue`: 用于处理需要重量级AI依赖（如 `DynamicController`）的、计算密集型的任务。
        -   `db_writer_queue`: 用于处理所有轻量级的、快速的数据库写入任务，以确保主任务能尽快返回。
-   **Redis 客户端配置**:
    -   为了使用 RedisJSON，我们需要一个正确配置的 Redis 客户端。我们将在 `app/config/dependency_injection.py` 中创建一个工厂函数来提供这个客户端。
        ```python
        # backend/app/config/dependency_injection.py
        import redis
        from app.core.config import settings

        _redis_client_instance = None

        def get_redis_client() -> redis.Redis:
            """
            获取 Redis 客户端单例实例
            """
            global _redis_client_instance
            if _redis_client_instance is None:
                # 确保 decode_responses=False，以便 redis-py 返回字节
                # redis-py 的 JSON 命令需要字节作为输入
                _redis_client_instance = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=False
                )
            return _redis_client_instance
        ```
    -   **重要**: 需要在 `app/core/config.py` 的 `Settings` 类中添加 `REDIS_URL: str = "redis://localhost:6379/0"` 配置项。

### 4.2 改造 `UserStateService` (关键变更)

这是本次重构的核心，目标是将其从有状态的内存缓存服务改造为无状态的 Redis 访问代理。

**重要说明**：
- `UserStateService` 实例在 Worker 进程初始化时创建，但它只是一个 Redis 访问代理，不包含任何实际的用户数据。
- 真正的用户数据始终存储在 Redis 中，按需读取和写入。
- 每次任务需要处理用户数据时，都会从 Redis 获取最新数据，处理完成后立即写回。

-   **移除内存缓存**:
    -   删除 `UserStateService` 类中的 `self._state_cache: Dict[str, StudentProfile]` 成员变量。**这是强制性变更**。
    -   `UserStateService` 实例在 Worker 进程初始化时创建，但它只是一个 Redis 访问代理，不包含任何实际的用户数据。

-   **引入 RedisJSON 客户端**:
    -   修改 `UserStateService` 的 `__init__` 方法，使其接收一个 Redis 客户端实例，并通过依赖注入传入。
        ```python
        # backend/app/services/user_state_service.py

        # class UserStateService:
        #     def __init__(self):
        #         self._state_cache: Dict[str, StudentProfile] = {}
        
        # 修改为:
        class UserStateService:
            def __init__(self, redis_client: redis.Redis):
                self.redis_client = redis_client
        ```

-   **重写 `get_or_create_profile` 方法**:
    -   此方法将作为从 Redis 读取数据的主要入口。
    1.  **构造 Redis Key**: `key = f"user_profile:{participant_id}"`。
    2.  **查询 Redis**: 使用 `self.redis_client.json().get(key)` 尝试获取用户的 profile 数据。
    3.  **缓存命中 (Hit)**: 如果 Redis 返回数据，则调用 `StudentProfile.from_dict(participant_id, data)` 将 JSON 数据反序列化为一个**新的、临时的** `StudentProfile` 实例并返回。
    4.  **缓存未命中 (Miss)**:
        -   执行现有逻辑，调用 `_recover_from_history_with_snapshot(participant_id, db)` 从数据库恢复 `StudentProfile`。
        -   **关键一步**：将恢复的 `profile` 对象通过 `profile.to_dict()` 序列化后，使用 `self.redis_client.json().set(key, '.', profile_dict)` 将其**写入 Redis**。
        -   返回恢复的 `profile` 实例。

-   **实现 `save_profile` 方法**:
    -   创建一个新的公共方法 `save_profile(self, profile: StudentProfile)`。
    -   此方法负责将传入的 `profile` 对象序列化，并使用 `self.redis_client.json().set(...)` 更新或创建 Redis 中的对应记录。

-   **调整所有状态修改方法**:
    -   所有修改了 `profile` 的方法（如 `handle_event`, `handle_frustration_event`, `update_bkt_on_submission` 等）在逻辑结束时都**必须**调用 `self.save_profile(profile)` 来持久化更改。
        ```python
        # 示例：handle_frustration_event
        def handle_frustration_event(self, participant_id: str):
            profile, _ = self.get_or_create_profile(participant_id, db)
            profile.emotion_state['is_frustrated'] = True
            
            # 新增步骤：保存更改到Redis
            self.save_profile(profile)
            
            logger.info(f"UserStateService: 标记用户 {participant_id} 为挫败状态")
        ```

-   **`StudentProfile` 序列化**:
    -   `StudentProfile` 类中现有的 `to_dict` 和 `from_dict` 方法对于此重构至关重要。
    -   必须确保这两个方法能够正确地序列化和反序列化 `StudentProfile` 对象的所有状态，包括嵌套的 `BKTModel` 对象。

-   **并发处理**:
    -   **初期简化**: 初期我们可以接受"最后写入者获胜"(Last-Write-Wins) 的策略，这在大多数场景下是可接受的。
    -   **进阶方案 (可选)**: 未来如果需要更强的并发控制，可以引入**乐观锁**。在 `StudentProfile` 中增加一个 `version` 字段。`save_profile` 时使用 Redis 的 `WATCH`/`MULTI`/`EXEC` 事务，检查 `version` 是否匹配，如果匹配则更新并增加 `version`，否则操作失败并重试。

### 4.3 依赖注入系统调整

为了在 FastAPI 和 Celery Worker 之间共享服务（特别是无状态的服务），我们需要对现有的依赖注入系统进行改造。

1.  **改造 `get_user_state_service`**:
    -   修改 `get_user_state_service` 函数，使其能够接收一个 `redis.Redis` 客户端实例。这将允许我们在不同环境（FastAPI 应用、Celery Worker）中注入相同的 Redis 连接。
    -   移除原有的 `_user_state_service_instance` 单例，因为现在 `UserStateService` 是无状态的，我们可以在每个 Worker 进程中创建一个实例。
        ```python
        # backend/app/config/dependency_injection.py

        # ... (get_redis_client 定义) ...

        # 移除全局变量 _user_state_service_instance

        def get_user_state_service(redis_client: redis.Redis) -> UserStateService:
            """
            获取 UserStateService 实例
            """
            return UserStateService(redis_client=redis_client)
        ```

2.  **改造 `create_dynamic_controller`**:
    -   修改 `create_dynamic_controller` 函数，使其也接收 `redis.Redis` 客户端实例，并将其向下传递给 `get_user_state_service`。
        ```python
        # backend/app/config/dependency_injection.py

        def create_dynamic_controller(redis_client: redis.Redis):
            """
            创建动态控制器实例，注入所有依赖
            """
            from app.services.dynamic_controller import DynamicController

            return DynamicController(
                user_state_service=get_user_state_service(redis_client=redis_client),
                sentiment_service=get_sentiment_analysis_service(),
                rag_service=get_rag_service(),
                prompt_generator=get_prompt_generator(),
                llm_gateway=get_llm_gateway()
            )
        ```
    -   `get_dynamic_controller` 单例函数可以保持不变，但在 Celery Worker 中我们将不使用它。

### 4.4 Celery Worker 中的条件性依赖注入

为了优化资源使用并支持专门化的 Worker，我们必须实现一个**条件性依赖注入**机制。其核心思想是：只有在 Worker 明确需要处理重量级任务时，才为其加载昂贵的依赖（如 `DynamicController`）。

1.  **Worker 初始化逻辑 (基于队列)**:
    -   我们将重构 `celery_app.py` 中的 `worker_process_init` 信号处理函数。
    -   该函数会检查启动的 Worker 实例 (`sender`) 正在监听哪些队列。
    -   **只有当 Worker 监听 `chat_queue` 时**，才会执行 `DynamicController` 的初始化逻辑。
    -   其他 Worker（例如监听 `db_writer_queue` 的 Worker）将跳过此初始化，从而保持轻量级。

    ```python
    # backend/app/celery_app.py
    from celery import Celery, signals
    from app.config.dependency_injection import create_dynamic_controller, get_redis_client
    from app.core.config import settings

    # ... (Celery app definition) ...

    _dynamic_controller_instance = None

    @signals.worker_process_init.connect
    def init_worker_process(sender=None, **kwargs):
        """
        在 Worker 进程启动时，根据其监听的队列有条件地初始化依赖。
        """
        global _dynamic_controller_instance
        
        # 获取 Worker 实例正在监听的队列名称集合
        queues = {q.name for q in sender.options.get('queues', [])}
        
        # 只有当 Worker 明确服务于 'chat_queue' 时，才初始化重量级依赖
        if 'chat_queue' in queues:
            if _dynamic_controller_instance is None:
                print(f"Initializing DynamicController for Chat Worker (PID: {os.getpid()})...")
                redis_client = get_redis_client()
                _dynamic_controller_instance = create_dynamic_controller(redis_client=redis_client)
                print("DynamicController initialized.")
        else:
            print(f"Worker (PID: {os.getpid()}) is not serving 'chat_queue'. Skipping DynamicController initialization.")

    def get_dynamic_controller():
        """
        在 Celery 任务中获取 DynamicController 实例。
        
        重要: 此函数只应在路由到 'chat_queue' 的任务中调用。
        """
        global _dynamic_controller_instance
        if _dynamic_controller_instance is None:
            raise RuntimeError(
                "DynamicController not initialized. This function should only be called "
                "from tasks routed to the 'chat_queue'."
            )
        return _dynamic_controller_instance
    ```

2.  **创建专门的数据库写入任务**:
    -   为了将数据库操作与核心 AI 逻辑分离，我们将创建专门的、轻量级的数据库写入任务。
    -   这些任务将被放置在一个新文件中，例如 `backend/app/tasks/db_tasks.py`。
    -   这些任务**不会**调用 `get_dynamic_controller()`，因此它们可以在不加载 AI 依赖的轻量级 Worker 中安全运行。

    ```python
    # backend/app/tasks/db_tasks.py
    from app.celery_app import celery_app
    from app.db.database import SessionLocal
    # 假设的 CRUD 操作函数
    from app.crud.crud_submission import create_submission 

    @celery_app.task(name="tasks.save_submission")
    def save_submission_task(submission_data: dict):
        """一个专门用于保存 submission 数据的轻量级任务"""
        db = SessionLocal()
        try:
            # ... 执行数据库写入逻辑 ...
            create_submission(db, submission_data)
        finally:
            db.close()
    ```

3.  **数据库会话管理**:
    -   这一点保持不变：**必须**在每个任务函数（无论是重量级还是轻量级）的内部创建和关闭独立的数据库会话，以确保线程安全和连接管理。
        ```python
        # backend/app/tasks/chat_tasks.py
        from app.db.database import SessionLocal

        @celery_app.task
        def process_chat_request(request_data: dict):
            db = SessionLocal()
            try:
                # ... 任务逻辑 ...
                controller = get_dynamic_controller()
                # 将 db 会话传递给需要它的服务方法
                profile = controller.user_state_service.get_or_create_profile(
                    participant_id=request_data['participant_id'],
                    db=db
                )
                # ...
            finally:
                db.close()
        ```

### 4.5 API 端点异步化改造

所有需要执行潜在耗时操作的 API 端点都将被改造为异步模式。它们将不再直接执行业务逻辑，而是将任务分派到 Celery 队列中，并立即向客户端返回一个任务 ID。

-   **`/ai/chat2` (聊天 API)**
    -   **路径**: `POST /ai/chat2`
    -   **逻辑变更**:
        1.  执行输入验证。
        2.  调用 `process_chat_request.apply_async()` 将核心聊天任务分派到 `chat_queue`。
        3.  API 立即返回 `202 Accepted`，并在响应体中包含任务 ID。

-   **`/submit-test2` (代码提交 API)**
    -   **路径**: `POST /api/v1/submission/submit-test2`
    -   **逻辑变更**:
        1.  执行输入验证和代码评测。
        2.  将代码评测和BKT模型更新操作封装在新的、重量级的 Celery 任务中（例如 `process_submission_task`）。
        3.  API 将调用 `process_submission_task.apply_async()` 将任务分派到 `chat_queue`。
        4.  API 立即返回 `202 Accepted`，并在响应体中包含任务 ID。
        5.  保留原有的 `/submit-test` 端点以确保向后兼容性。

-   **`/log` (行为事件记录 API)**
    -   **路径**: `POST /api/v1/behavior/log`
    -   **逻辑变更**:
        1.  将原始事件持久化操作封装在轻量级的 Celery 任务中（例如 `save_behavior_task`）。
        2.  API 将调用 `save_behavior_task.apply_async()` 将任务分派到 `db_writer_queue`。
        3.  行为解释服务的调用保持同步执行，因为它需要立即处理事件。
        4.  API 立即返回 `202 Accepted`，表示事件已接收并开始处理。

-   **新增结果查询端点 (用于聊天和代码提交)**
    -   **路径**: `GET /ai/chat/result/{task_id}` 和 `GET /submission/result/{task_id}`
    -   **逻辑**: 用于轮询 `chat_queue` 中任务的结果。

## 5. 详细实现步骤 (Roadmap)

1.  **环境搭建 (Sprint 1)**:
    -   在 `pyproject.toml` 或 `requirements.txt` 中添加 `celery` 和 `redis` (`redis[hiredis,json]`)。
    -   配置并运行一个本地的 Redis 实例。
    -   创建 `celery_app.py` 并成功启动一个能连接到 Redis 的 Celery Worker。
2.  **`UserStateService` 改造 (Sprint 1)**:
    -   按照 4.2 中的描述，完全重构 `UserStateService`，移除 `_state_cache` 并集成 RedisJSON。
    -   编写单元测试，验证其能正确地从 Redis 读写 `StudentProfile`。
3.  **依赖注入系统调整 (Sprint 1)**:
    -   创建 `celery_app.py` 并实现 Worker 启动时的依赖注入配置。
    -   确保 Redis 客户端在 Worker 中正确共享。
4.  **创建 Celery 任务 (Sprint 2)**:
    -   创建 `app/tasks/chat_tasks.py`。
    -   定义 `process_chat_request` 任务。将 `DynamicController.generate_adaptive_response` 的核心逻辑迁移到此任务中。
    -   创建 `app/tasks/submission_tasks.py`。
    -   定义 `process_submission_task` 任务。将代码评测和BKT模型更新的核心逻辑迁移到此任务中。
    -   解决任务内部的依赖注入和数据库会话问题。
5.  **API 端点改造 (Sprint 2)**:
    -   添加 `/ai/chat2` 端点以分派任务。
    -   创建 `/ai/chat/result/{task_id}` 端点。
    -   添加 `/submit-test2` 端点以分派任务。
    -   创建 `/submission/result/{task_id}` 端点。
    -   修改 `/log` 端点以使用异步持久化。
6.  **前端适配 (Sprint 3)**:
    -   前端需要调整交互逻辑，在发送聊天请求和代码提交后，轮询结果查询端点，直到获得最终结果。(暂时不做)
7.  **部署与测试 (Sprint 4)**:
    -   更新 `Dockerfile` 和部署脚本，以包含 Redis 和 Celery Worker 服务。(暂时不做)
    -   进行压力测试，验证系统是否满足设定的成功指标。

## 6. 数据流和组件交互 (重构后)

新架构下存在三个主要的异步数据流：

**工作流 1: AI 聊天交互 (需要结果查询)**

1.  **Client** -> `POST /ai/chat2` -> **FastAPI**
2.  **FastAPI** -> (验证请求) -> `process_chat_request.apply_async(queue='chat_queue')` -> **Redis (Broker)**
3.  **FastAPI** -> `202 Accepted` with `task_id` -> **Client**
4.  **Redis (Broker)** -> (分派任务) -> **AI Worker (监听 chat_queue)**
5.  **AI Worker** -> (执行任务, 调用 `DynamicController`) -> `LLMGateway` -> **External LLM API**
6.  **AI Worker** -> (获取LLM结果) -> (可选) `save_snapshot_task.apply_async(queue='db_writer_queue')` -> **Redis (Broker)**
7.  **AI Worker** -> (任务完成) -> (存储结果) -> **Redis (Backend)**
8.  **Client** -> `GET /ai/chat/result/{task_id}` -> **FastAPI** -> (查询结果) -> **Redis (Backend)**
9.  **FastAPI** -> (返回结果) -> **Client**

**工作流 2: 代码提交处理 (需要结果查询)**

1.  **Client** -> `POST /api/v1/submission/submit-test2` -> **FastAPI**
2.  **FastAPI** -> (验证请求) -> `process_submission_task.apply_async(queue='chat_queue')` -> **Redis (Broker)**
3.  **FastAPI** -> `202 Accepted` with `task_id` -> **Client**
4.  **Redis (Broker)** -> (分派任务) -> **AI Worker (监听 chat_queue)**
5.  **AI Worker** -> (执行任务, 调用 `sandbox_service`) -> **Sandbox**
6.  **AI Worker** -> (获取评测结果) -> (更新BKT模型) -> (可选) `save_submission_task.apply_async(queue='db_writer_queue')` -> **Redis (Broker)**
7.  **AI Worker** -> (任务完成) -> (存储结果) -> **Redis (Backend)**
8.  **Client** -> `GET /submission/result/{task_id}` -> **FastAPI** -> (查询结果) -> **Redis (Backend)**
9.  **FastAPI** -> (返回结果) -> **Client**

**工作流 3: 后台数据写入 (即发即忘)**

1.  **Client** -> `POST /api/v1/behavior/log` -> **FastAPI**
2.  **FastAPI** -> (验证请求) -> `save_behavior_task.apply_async(queue='db_writer_queue')` -> **Redis (Broker)**
3.  **FastAPI** -> `202 Accepted` -> **Client** (操作立即完成，无需等待)
4.  **Redis (Broker)** -> (分派任务) -> **DB Worker (监听 db_writer_queue)**
5.  **DB Worker** -> (执行轻量级任务) -> **SQLite DB** (写入数据)
6.  **DB Worker** -> (任务完成) -> **Redis (Backend)** (仅记录任务状态)

## 7. 部署和运维考虑

-   **专门化 Worker**: 为了优化资源，应至少启动三种类型的 Worker：
    -   **AI Worker**: 处理计算密集型任务，只监听 `chat_queue`。
        ```bash
        # 从项目根目录运行
        celery -A backend.app.celery_app worker -l info -Q chat_queue -n ai_worker@%h
        ```
    -   **DB Worker**: 处理轻量级数据库写入任务，只监听 `db_writer_queue`。这种 Worker 不需要加载 AI 模型，内存占用极低。
        ```bash
        # 从项目根目录运行
        celery -A backend.app.celery_app worker -l info -Q db_writer_queue -n db_worker@%h
        ```
    -   **Beat Scheduler**: 用于调度定时任务（如唤醒 embedding 模型）。
        ```bash
        # 从项目根目录运行
        celery -A backend.app.celery_app beat -l info
        ```
-   **监控**: 需要引入对 Redis 和 Celery 的监控。Flower 是一个优秀的 Celery 监控工具。需要监控队列长度、任务执行时间、失败率等指标。
-   **日志**: Celery Worker 的日志需要集中管理，以便于调试。

## 8. 风险和缓解措施

-   **风险**: 前端改造工作量可能较大，需要适应异步交互模式。
    -   **缓解**: 与前端团队紧密沟通，提供清晰的 API 文档，并在早期提供可用的测试环境。
-   **风险**: Redis 成为单点故障。
    -   **缓解**: 在生产环境中，应部署高可用的 Redis 集群或使用云服务商提供的托管 Redis 服务。
-   **风险**: 任务失败处理。
    -   **缓解**: 为 Celery 任务配置合理的重试策略。对于关键任务，设计幂等性，确保重试不会产生副作用。建立失败任务的告警和手动重试机制。