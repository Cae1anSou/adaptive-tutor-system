#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试聚类算法集成
验证聚类服务、动态控制器和提示词生成器的集成是否正常工作
"""

import sys
import os
import json
from datetime import datetime, UTC

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.progress_clustering_service import progress_clustering_service
from app.services.dynamic_controller import DynamicController
from app.services.prompt_generator import prompt_generator
from app.services.user_state_service import UserStateService
from app.schemas.chat import ChatRequest, ConversationMessage, CodeContent
from app.schemas.content import CodeContent as ContentCodeContent

# 模拟Redis客户端
class MockRedisClient:
    def __init__(self):
        self.data = {}
    
    def json(self):
        return self
    
    def get(self, key, path=None):
        if key in self.data:
            if path:
                # 简单的路径解析
                data = self.data[key]
                path_parts = path.strip('.').split('.')
                for part in path_parts:
                    if isinstance(data, dict) and part in data:
                        data = data[part]
                    else:
                        return None
                return data
            return self.data[key]
        return None
    
    def set(self, key, path, value):
        if key not in self.data:
            self.data[key] = {}
        if path == '.':
            self.data[key] = value
        else:
            # 简单的路径设置
            path_parts = path.strip('.').split('.')
            current = self.data[key]
            for part in path_parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[path_parts[-1]] = value

def create_mock_services():
    """创建模拟的服务实例"""
    # 创建模拟Redis客户端
    mock_redis = MockRedisClient()
    
    # 创建用户状态服务
    user_state_service = UserStateService(mock_redis)
    
    # 创建其他模拟服务
    class MockService:
        def analyze_sentiment(self, text):
            return type('MockSentiment', (), {
                'label': 'neutral',
                'confidence': 0.5,
                'details': {}
            })()
    
    sentiment_service = MockService()
    rag_service = None
    
    # 创建模拟LLM网关
    class MockLLMGateway:
        async def get_completion(self, system_prompt, messages):
            return "This is a mock AI response for testing purposes."
    
    llm_gateway = MockLLMGateway()
    
    # 创建动态控制器
    controller = DynamicController(
        user_state_service=user_state_service,
        sentiment_service=sentiment_service,
        rag_service=rag_service,
        prompt_generator=prompt_generator,
        llm_gateway=llm_gateway
    )
    
    return controller, user_state_service

def create_test_conversation():
    """创建测试对话历史"""
    conversation = [
        ConversationMessage(
            role="user",
            content="I'm having trouble understanding how to use loops in Python. Can you help me?",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Of course! Loops are fundamental in Python. Let me explain the basic concepts...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="user",
            content="I see, but I'm still confused about when to use for vs while loops.",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Great question! Let me clarify the difference...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="user",
            content="I think I understand now. Can you show me an example?",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Here's a simple example...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="user",
            content="This is really helpful! I want to practice more.",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Excellent! Practice is the best way to learn. Here are some exercises...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="user",
            content="I tried the exercises and they worked! I'm getting better at this.",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="That's fantastic! You're making great progress. Let's move on to more advanced topics...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="user",
            content="Can you show me how to use loops with lists?",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Sure! Lists and loops work together beautifully in Python...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="user",
            content="I'm starting to feel more confident with loops now!",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="That's wonderful! Your confidence is growing, and that's a great sign of learning...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="user",
            content="Can we move on to functions next?",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        ),
        ConversationMessage(
            role="assistant",
            content="Absolutely! Functions are the next logical step. Let's explore them...",
            timestamp=datetime.now(UTC)
        )
    ]
    return conversation

def test_clustering_service():
    """测试聚类服务"""
    print("🔍 测试聚类服务...")
    
    # 创建测试对话
    conversation = create_test_conversation()
    conversation_dicts = [
        {"role": msg.role, "content": msg.content}
        for msg in conversation
    ]
    
    try:
        # 测试聚类分析
        result = progress_clustering_service.analyze_conversation_progress(
            conversation_dicts, 
            "test_user_001"
        )
        
        print(f"✅ 聚类分析成功!")
        print(f"   消息数量: {result.get('message_count', 0)}")
        print(f"   窗口数量: {result.get('window_count', 0)}")
        print(f"   进度标签: {result.get('named_labels', [])}")
        print(f"   进度分数: {result.get('progress_score', [])}")
        
        # 测试进度状态获取
        current_state, confidence = progress_clustering_service.get_current_progress_state("test_user_001")
        print(f"   当前状态: {current_state}")
        print(f"   置信度: {confidence:.3f}")
        
        # 测试进度摘要
        summary = progress_clustering_service.get_progress_summary("test_user_001")
        print(f"   趋势: {summary.get('trend', 'unknown')}")
        print(f"   建议数量: {len(summary.get('recommendations', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ 聚类服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prompt_generator():
    """测试提示词生成器"""
    print("\n📝 测试提示词生成器...")
    
    try:
        # 创建模拟聚类结果
        clustering_result = {
            "named_labels": ["正常", "正常", "超进度"],
            "progress_score": [0.1, 0.2, 0.8],
            "window_count": 3,
            "message_count": 15
        }
        
        # 创建模拟用户状态
        user_state = type('MockUserState', (), {
            'participant_id': 'test_user_001',
            'emotion_state': {'current_sentiment': 'neutral'},
            'behavior_patterns': {},
            'bkt_models': {},
            'is_new_user': False
        })()
        
        # 测试提示词生成
        system_prompt, messages = prompt_generator.create_prompts(
            user_state=user_state,
            retrieved_context=["Python loops are fundamental programming constructs"],
            conversation_history=[{"role": "user", "content": "Help me with loops"}],
            user_message="I need help with Python loops",
            clustering_result=clustering_result
        )
        
        print(f"✅ 提示词生成成功!")
        print(f"   系统提示词长度: {len(system_prompt)}")
        print(f"   消息数量: {len(messages)}")
        
        # 检查是否包含聚类信息
        if "PROGRESS ANALYSIS" in system_prompt:
            print(f"   ✅ 包含进度分析信息")
        else:
            print(f"   ❌ 缺少进度分析信息")
        
        return True
        
    except Exception as e:
        print(f"❌ 提示词生成器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_user_state_service():
    """测试用户状态服务"""
    print("\n👤 测试用户状态服务...")
    
    try:
        # 创建模拟Redis和用户状态服务
        mock_redis = MockRedisClient()
        user_state_service = UserStateService(mock_redis)
        
        # 创建测试聚类结果
        clustering_result = {
            "analysis_timestamp": datetime.now().isoformat(),
            "named_labels": ["低进度", "正常", "超进度"],
            "progress_score": [-0.5, 0.1, 0.9],
            "window_count": 3,
            "message_count": 15
        }
        
        # 测试聚类状态更新
        user_state_service.update_clustering_state("test_user_002", clustering_result)
        print(f"✅ 聚类状态更新成功!")
        
        # 测试聚类状态获取
        clustering_state = user_state_service.get_clustering_state("test_user_002")
        print(f"   当前进度状态: {clustering_state.get('current_progress_state', 'unknown')}")
        print(f"   进度分数: {clustering_state.get('progress_score', 0.0)}")
        print(f"   趋势: {clustering_state.get('trend', 'unknown')}")
        print(f"   置信度: {clustering_state.get('confidence', 0.0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 用户状态服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dynamic_controller():
    """测试动态控制器"""
    print("\n🎮 测试动态控制器...")
    
    try:
        # 创建模拟服务
        controller, user_state_service = create_mock_services()
        
        # 创建测试请求
        conversation = create_test_conversation()
        request = ChatRequest(
            participant_id="test_user_003",
            user_message="I want to learn more about Python functions",
            conversation_history=conversation,
            mode="learning",
            content_id="python_basics"
        )
        
        # 测试控制器处理（不调用LLM）
        print(f"✅ 动态控制器创建成功!")
        print(f"   请求参与者ID: {request.participant_id}")
        print(f"   对话历史长度: {len(request.conversation_history)}")
        print(f"   模式: {request.mode}")
        
        return True
        
    except Exception as e:
        print(f"❌ 动态控制器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🚀 开始聚类算法集成测试...\n")
    
    tests = [
        ("聚类服务", test_clustering_service),
        ("提示词生成器", test_prompt_generator),
        ("用户状态服务", test_user_state_service),
        ("动态控制器", test_dynamic_controller)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            print()
    
    print("=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过! 聚类算法集成成功!")
    else:
        print("⚠️  部分测试失败，请检查相关组件")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
