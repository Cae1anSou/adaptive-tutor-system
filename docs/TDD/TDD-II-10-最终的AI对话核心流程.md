### **详细技术设计文档 (TDD-II-10): 最终的AI对话核心流程**

**版本:** 1.2
**关联的顶层TDD:** V1.2 - 所有章节
**作者:** 曹欣卓
**日期:** 2025-7-29

#### **1. 功能概述 (Feature Overview)**

**目标:** 设计并实现一个能够处理核心AI对话请求 (`POST /api/v1/ai/chat`) 的、高度智能化的后端流程。该流程负责**编排（Orchestrate）** 多个后台服务，全面地、实时地理解学习者的**情境（Context）**和**状态（State）**，并据此动态生成能够驱动LLM产生个性化、自适应教学反馈的 Prompts。系统提示与消息层分离：系统提示仅包含稳定的身份与规则，动态上下文放入消息。

**核心原则:**

* **情境与状态的融合:** 成功的设计必须能将**外显的情境**（代码、对话历史、任务）和**内隐的状态**（认知、行为、情感）无缝融合，作为LLM决策的依据。
* **清晰的编排逻辑:** `DynamicController` 作为总指挥，其调用各个服务的顺序和逻辑必须清晰、合理。
* **Prompt工程是核心:** 系统的“智能”最终体现在`PromptGenerator`所产出的高质量、上下文感知的System Prompt中。

**范围:**

1.  详细设计`POST /ai/chat`端点背后的核心服务`DynamicController`的`generate_adaptive_response`方法。
2.  明确`DynamicController`调用`UserStateService`, `SentimentAnalysisService`, `RAGService`, `PromptGenerator`, `LLMGateway`的顺序和数据传递。
3.  详细设计`PromptGenerator`如何融合所有输入信息，构建最终的 System Prompt 与上下文消息（messages），并输出可存证的上下文快照。

#### **2. 设计与实现**

##### **2.1. AI对话核心流程时序图 (Orchestration Sequence Diagram)**

```mermaid
sequenceDiagram
    participant API as API Endpoint (/chat)
    participant Controller as DynamicController
    participant UserState as UserStateService
    participant Sentiment as SentimentService
    participant RAG as RAGService
    participant PromptGen as PromptGenerator
    participant LLM_GW as LLMGateway
    participant DB as SQLite DB
  
    API->>Controller: 1. generate_adaptive_response(request_body)
  
    Controller->>UserState: 2. 请求更新并获取用户状态<br>(传入participant_id, user_message)
  
    activate UserState
    UserState->>Sentiment: 3. analyze_sentiment(user_message)
    Sentiment-->>UserState: 4. 返回情感标签 (e.g., 'confused')
    UserState->>UserState: 5. **融合情感与行为，<br>更新内存中的状态向量**
    UserState-->>Controller: 6. 返回最新的用户状态摘要
    deactivate UserState
  
    Controller->>RAG: 7. retrieve(user_message)
    activate RAG
    RAG-->>Controller: 8. 返回相关的知识片段
    deactivate RAG

    Controller->>PromptGen: 9. create_prompts(状态摘要, 检索片段, 完整上下文)
    activate PromptGen
    PromptGen-->>Controller: 10. 返回构建好的 System Prompt、Messages 列表与 Context Snapshot
    deactivate PromptGen

    Controller->>LLM_GW: 11. get_completion(system_prompt, messages)
    activate LLM_GW
    LLM_GW-->>Controller: 12. 返回LLM生成的回答
    deactivate LLM_GW
  
    par "后台异步任务"
        Controller->>DB: 13a. (通过PersistenceService) 记录完整交互日志
    and
        Controller->>UserState: 13b. (可选) 根据AI的回答，再次更新用户状态
    end

    Controller-->>API: 14. 返回最终AI回答
```

##### **2.2. 核心服务实现 (`backend/services/dynamic_controller.py`)**

`DynamicController`是无状态的编排器，它的方法接收所有需要的信息。

```python
# backend/services/dynamic_controller.py
from app.schemas.chat import ChatRequest, ChatResponse
from . import user_state_service, rag_service, prompt_generator, llm_gateway, persistence_service


class DynamicController:
    async def generate_adaptive_response(self, request: ChatRequest, db) -> str:
        # 步骤 2-6: 获取全面的、最新的用户状态摘要
        # 这一步包含了情感分析和状态更新的内部逻辑
        state_summary = user_state_service.get_updated_summary(
            db=db,
            participant_id=request.participant_id,
            user_message=request.user_message
        )

        # 步骤 7-8: RAG检索
        retrieved_context = rag_service.retrieve(request.user_message)

        # 步骤 9-10: 动态生成Prompts
        system_prompt, messages = prompt_generator.create_prompts(
            user_state=state_summary,
            retrieved_context=retrieved_context,
            conversation_history=request.conversation_history,
            user_message=request.user_message,
            code_content=request.code_context,
            task_context=request.task_context
        )

        # 步骤 11-12: 调用LLM
        ai_response_content = await llm_gateway.get_completion(system_prompt, messages)

        # 步骤 13: 异步记录日志
        persistence_service.log_chat_interaction(
            db=db,
            request=request,
            system_prompt=system_prompt,
            context_snapshot=context_snapshot,
            ai_response=ai_response_content
        )

        # 步骤 14: 返回结果
        return ai_response_content


dynamic_controller = DynamicController()
```
**设计决策:** `user_state_service`暴露一个更高层次的方法`get_updated_summary`，该方法内部封装了调用`SentimentAnalysisService`和更新内存状态的逻辑，使`DynamicController`的调用更简洁。

##### **2.2.1. 数据存储与可追溯性**
- 将本轮用于生成回答的系统提示词与上下文快照同时存入 `chat_history`：
  - `raw_prompt_to_llm`: System Prompt（身份/规则/策略/模式/安全约束）
  - `raw_context_to_llm`: 上下文快照（RAG 文本、内容 JSON、测试结果、学生上下文等，按注入顺序拼接）
- 数据库新增列 `chat_history.raw_context_to_llm`（TEXT）。`init_db.py` 在 `create_all` 后执行轻量迁移：若列不存在，自动 `ALTER TABLE` 添加。

##### **2.3. 动态Prompt生成器实现 (`backend/services/prompt_generator.py`)**

这是将所有信息转化为prompt的地方。

```python
# backend/services/prompt_generator.py

class PromptGenerator:
    def create_prompts(self, user_state: dict, retrieved_context: list, ...) -> (str, list):
      
        # --- 1. 构建 System Prompt（精简） ---
        # 仅包含：身份/规则、简短情感策略、模式标志、安全约束。
        system_prompt = self._build_system_prompt(user_state, mode, content_title)

        # --- 2. 构建 Context Messages（动态上下文） ---
        # 包含：学生上下文摘要、RAG参考、内容数据（学习模式去除 sc_all；测试模式完整）、测试结果等。
        context_messages = self._build_context_messages(user_state, retrieved_context, mode, content_title, content_json, test_results)

        # --- 3. 构建 Conversation Messages（历史+当前用户） ---
        messages = context_messages + self._build_message_history(conversation_history, code_context, user_message)

        # --- 4. 生成 Context Snapshot（用于科研存证） ---
        context_snapshot = serialize(context_messages)
      
        return system_prompt, messages, context_snapshot

    def _build_system_prompt(self, user_state, retrieved_context, task_context) -> str:
        # --- 角色和总体目标 ---
        prompt_parts = [
            "You are 'Alex', a world-class AI programming tutor. Your goal is to help a student master a specific topic by providing personalized, empathetic, and insightful guidance. You must respond in Markdown."
        ]
      
        # --- 教学策略指令 (基于用户状态) ---
        emotion = user_state.get('emotion', {}).get('label', 'NEUTRAL').upper()
        if emotion == 'FRUSTRATED':
            prompt_parts.append("STRATEGY: The student seems frustrated. Your top priority is to be encouraging and empathetic. Acknowledge the difficulty before offering help. Use phrases like 'Don't worry, this is a tricky part' or 'Let's try a different approach'.")
        elif emotion == 'CONFUSED':
            prompt_parts.append("STRATEGY: The student seems confused. Break down concepts into smaller, simpler steps. Use analogies. Provide the simplest possible examples. Avoid jargon.")
      
        # ... 可以加入更多基于BKT模型和行为状态的策略 ...

        # 动态上下文（RAG/内容JSON/测试结果/学生行为等）不会放入 System Prompt，而是以 assistant 消息注入。

        return "\n\n".join(prompt_parts)

    def _build_message_history(self, history, code, user_message) -> list:
        # 构造一个符合OpenAI ChatCompletion格式的messages列表
        messages = [{"role": "system", "content": "..."}] # system prompt内容稍后注入
      
        # 添加历史对话
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
          
        # 将当前代码和用户最新问题组合成最后一条用户消息
        latest_user_content = f"""
Here is my current code:
---HTML---
{code.html}
---CSS---
{code.css}
---JS---
{code.js}
---
My question is: {user_message}
"""
        messages.append({"role": "user", "content": latest_user_content})
        return messages

prompt_generator = PromptGenerator()
```

***

**内容注入与保真规则:**
- 学习内容（learning_content）：仅在学习模式注入，去除 `sc_all` 字段后再格式化展示；其他字段不删减。
- 测试任务（test_tasks）：在测试模式注入，保持完整，不删减。

**总结:**
我们将 AI 对话的系统提示与动态上下文彻底分层：System Prompt 承载稳定且高优先级的规则，Messages 注入所有动态上下文。`PromptGenerator` 产出 `system_prompt + messages + context_snapshot`，`DynamicController` 负责编排并将 `context_snapshot` 与 `system_prompt` 一并存证到 `chat_history`。这样既优化了模型对指令的遵从性，也保证了科研数据的可追溯与完整性。
