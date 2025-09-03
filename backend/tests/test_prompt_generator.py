import os
import sys
import pytest


# 将 backend 目录添加到 sys.path 中，便于按项目方式导入
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.prompt_generator import PromptGenerator
from app.schemas.chat import UserStateSummary
from app.schemas.content import CodeContent


def make_user_state(
    *,
    is_new_user: bool,
    emotion: str = "NEUTRAL",
    bkt_models: dict | None = None,
    behavior_patterns: dict | None = None,
):
    patterns = behavior_patterns or {}
    return UserStateSummary(
        participant_id="u1",
        emotion_state={"current_sentiment": emotion},
        behavior_counters=patterns,
        behavior_patterns=patterns,
        bkt_models=bkt_models or {},
        is_new_user=is_new_user,
    )


def test_build_message_history_with_code_context():
    g = PromptGenerator()

    conversation_history = [
        {"role": "assistant", "content": "Hi"},
        {"role": "user", "content": "Show me"},
    ]
    code = CodeContent(
        html="<h1>Hello</h1>",
        css="h1 { color: red; }",
        js="console.log('x')",
    )

    messages = g._build_message_history(
        conversation_history=conversation_history,
        code_context=code,
        user_message="Why?",
    )

    # 历史消息保留
    assert messages[0] == {"role": "assistant", "content": "Hi"}
    assert messages[1] == {"role": "user", "content": "Show me"}

    # 追加的用户消息包含代码片段与问题
    last = messages[-1]
    assert last["role"] == "user"
    assert "Here is my current code:" in last["content"]
    assert "```html" in last["content"] and "```css" in last["content"] and "```javascript" in last["content"]
    assert "My question is: Why?" in last["content"]


def test_build_system_prompt_new_user_no_context():
    g = PromptGenerator()
    user_state = make_user_state(is_new_user=True, emotion="NEUTRAL")

    prompt = g._build_system_prompt(
        user_state=user_state,
        retrieved_context=[],
        task_context=None,
        topic_title=None,
    )

    # 含基础系统提示
    assert "You are 'Alex', a world-class AI programming tutor" in prompt
    # 情感策略（NEUTRAL）
    assert "The student seems neutral" in prompt
    # 新用户提示
    assert "This is a new student" in prompt
    # 无RAG上下文提示
    assert "No relevant knowledge was retrieved" in prompt


def test_build_system_prompt_existing_user_with_progress_behavior_and_context():
    g = PromptGenerator()
    bkt_models = {
        "topic1": {"mastery_prob": 0.9},    # advanced
        "topic2": {"mastery_prob": 0.6},    # intermediate
        "topic3": {"mastery_prob": 0.2},    # beginner
    }
    behavior_patterns = {
        "error_frequency": 0.75,
        "help_seeking_tendency": 0.3,
    }
    user_state = make_user_state(is_new_user=False, emotion="CONFUSED", bkt_models=bkt_models, behavior_patterns=behavior_patterns)

    retrieved = ["ctx1", "ctx2"]
    prompt = g._build_system_prompt(
        user_state=user_state,
        retrieved_context=retrieved,
        mode="learning",
        content_title="loops",
    )

    # 既有学生提示
    assert "existing student" in prompt
    # 掌握度概览
    assert "topic1: advanced" in prompt
    assert "topic2: intermediate" in prompt
    # 行为统计
    assert "BEHAVIOR METRICS: error frequency: 0.75, help-seeking tendency: 0.30" in prompt
    # RAG 上下文连接符与内容
    assert "REFERENCE KNOWLEDGE" in prompt and "ctx1" in prompt and "ctx2" in prompt
    assert "---" in prompt
    # 任务与主题
    assert "TOPIC: The current topic is 'loops'" in prompt


def test_create_prompts_integration():
    g = PromptGenerator()
    user_state = make_user_state(is_new_user=True, emotion="EXCITED")
    conversation_history = [
        {"role": "assistant", "content": "Welcome"},
    ]
    code = CodeContent(html="<p>Hi</p>")

    system_prompt, messages = g.create_prompts(
        user_state=user_state,
        retrieved_context=["Docs"],
        conversation_history=conversation_history,
        user_message="Explain closures",
        code_content=code,
        mode="learning",
        content_title="javascript",
    )

    # 系统提示含期待关键字
    assert "EXCITED" not in system_prompt  # 文本不一定直接包含标签，但会包含策略文字
    assert "excited and engaged" in system_prompt
    assert "Docs" in system_prompt

    # 消息历史正确拼装
    assert messages[0] == {"role": "assistant", "content": "Welcome"}
    assert messages[-1]["role"] == "user"
    assert "My question is: Explain closures" in messages[-1]["content"]


def test_build_system_prompt_edge_cases():
    g = PromptGenerator()
    
    # 测试空的bkt_models和behavior_counters
    user_state = make_user_state(
        is_new_user=False, 
        emotion="NEUTRAL",
        bkt_models={},
        behavior_counters={}
    )
    
    prompt = g._build_system_prompt(
        user_state=user_state,
        retrieved_context=[],
        task_context=None,
        topic_title=None,
    )
    
    assert "existing student" in prompt
    assert "No relevant knowledge was retrieved" in prompt
    
    # 测试空值的bkt_models和behavior_counters（使用空字典而不是None）
    user_state_empty = UserStateSummary(
        participant_id="u1",
        emotion_state={"current_sentiment": "NEUTRAL"},
        behavior_counters={},
        bkt_models={},
        is_new_user=False,
    )
    
    prompt_empty = g._build_system_prompt(
        user_state=user_state_empty,
        retrieved_context=[],
        task_context=None,
        topic_title=None,
    )
    
    assert "existing student" in prompt_empty


def test_build_message_history_edge_cases():
    g = PromptGenerator()
    
    # 测试空对话历史
    messages = g._build_message_history(
        conversation_history=[],
        code_context=None,
        user_message="Hello"
    )
    
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    
    # 测试空用户消息
    messages_empty = g._build_message_history(
        conversation_history=[],
        code_context=None,
        user_message=""
    )
    
    assert len(messages_empty) == 0
    
    # 测试只有代码上下文，没有用户消息
    code = CodeContent(html="<h1>Test</h1>")
    messages_code_only = g._build_message_history(
        conversation_history=[],
        code_context=code,
        user_message=""
    )
    
    assert len(messages_code_only) == 1
    assert "Here is my current code:" in messages_code_only[0]["content"]


def test_create_prompts_edge_cases():
    g = PromptGenerator()
    
    # 测试所有可选参数为None的情况
    user_state = make_user_state(is_new_user=True, emotion="NEUTRAL")
    
    system_prompt, messages = g.create_prompts(
        user_state=user_state,
        retrieved_context=[],
        conversation_history=[],
        user_message="Test",
        code_content=None,
        task_context=None,
        topic_title=None,
    )
    
    assert "You are 'Alex'" in system_prompt
    assert len(messages) == 1
    assert messages[0]["content"] == "Test"


def test_error_handling():
    g = PromptGenerator()
    
    # 测试无效的情感状态
    user_state_invalid_emotion = make_user_state(
        is_new_user=True, 
        emotion="INVALID_EMOTION"
    )
    
    # 应该回退到NEUTRAL策略
    prompt = g._build_system_prompt(
        user_state=user_state_invalid_emotion,
        retrieved_context=[],
        task_context=None,
        topic_title=None,
    )
    
    assert "The student seems neutral" in prompt
    
    # 测试空用户消息处理
    messages = g._build_message_history(
        conversation_history=[],
        code_context=None,
        user_message=""
    )
    
    # 应该返回空列表，因为没有消息内容
    assert len(messages) == 0


def test_get_emotion_strategy_all():
    # 测试所有情感策略
    # FRUSTRATED
    text = PromptGenerator._get_emotion_strategy("FRUSTRATED")
    assert "The student seems frustrated" in text
    assert "validate their feelings" in text
    
    # CONFUSED
    text = PromptGenerator._get_emotion_strategy("CONFUSED")
    assert "The student seems confused" in text
    assert "pinpoint the source of confusion" in text
    
    # EXCITED
    text = PromptGenerator._get_emotion_strategy("EXCITED")
    assert "The student seems excited" in text
    assert "Challenge them with deeper explanations" in text
    
    # NEUTRAL
    text = PromptGenerator._get_emotion_strategy("NEUTRAL")
    assert "The student seems neutral" in text
    assert "spark interest" in text
    
    # 大小写不敏感测试
    text = PromptGenerator._get_emotion_strategy("frustrated")
    assert "The student seems frustrated" in text


def test_get_emotion_strategy_fallback():
    # 静态方法：未知情感走 NEUTRAL 策略
    text = PromptGenerator._get_emotion_strategy("unknown")
    assert "The student seems neutral" in text


def test_format_code_context():
    g = PromptGenerator()
    
    # 测试完整的代码内容
    code = CodeContent(
        html="<h1>Hello</h1>",
        css="h1 { color: red; }",
        js="console.log('x')"
    )
    formatted = g._format_code_context(code)
    assert "Here is my current code:" in formatted
    assert "```html" in formatted and "<h1>Hello</h1>" in formatted
    assert "```css" in formatted and "h1 { color: red; }" in formatted
    assert "```javascript" in formatted and "console.log('x')" in formatted
    
    # 测试只有部分代码内容
    code_partial = CodeContent(
        html="<h1>Hello</h1>",
        css="",
        js=""
    )
    formatted_partial = g._format_code_context(code_partial)
    assert "Here is my current code:" in formatted_partial
    assert "```html" in formatted_partial and "<h1>Hello</h1>" in formatted_partial
    assert "```css" not in formatted_partial
    assert "```javascript" not in formatted_partial
    
    # 测试空代码内容
    code_empty = CodeContent(html="", css="", js="")
    formatted_empty = g._format_code_context(code_empty)
    assert formatted_empty == ""

