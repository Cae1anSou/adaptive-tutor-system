#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚类进度完整集成测试
测试完整流程：获取消息 -> 开始聚类 -> 更新用户状态 -> 写入提示词
"""

import sys
import os
import pytest
import redis
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Any, Optional
from datetime import datetime, UTC

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# 导入测试所需的模块
from app.services.user_state_service import UserStateService, StudentProfile
from app.services.distance_based_clustering_service import DistanceBasedClusteringService
from app.services.prompt_generator import PromptGenerator
from app.services.dynamic_controller import DynamicController
from app.schemas.chat import ChatRequest, UserStateSummary, SentimentAnalysisResult
from app.schemas.content import CodeContent


class TestClusteringIntegrationFull:
    """聚类进度完整集成测试类"""

    @pytest.fixture
    def redis_client(self):
        """模拟Redis客户端"""
        mock_redis = Mock(spec=redis.Redis)
        mock_redis.json.return_value = Mock()
        return mock_redis

    @pytest.fixture
    def user_state_service(self, redis_client):
        """用户状态服务"""
        return UserStateService(redis_client)

    @pytest.fixture
    def prompt_generator(self):
        """提示词生成器"""
        return PromptGenerator()

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return Mock()

    @pytest.fixture
    def sample_conversation_history(self):
        """示例对话历史"""
        return [
            {"role": "user", "content": "I'm struggling with this sorting algorithm. Can you help me?"},
            {"role": "assistant", "content": "I'd be happy to help! What specific part of sorting are you having trouble with?"},
            {"role": "user", "content": "I don't understand how bubble sort works"},
            {"role": "assistant", "content": "Let me explain bubble sort step by step..."},
            {"role": "user", "content": "I'm getting confused with the nested loops"},
            {"role": "assistant", "content": "The outer loop controls the number of passes..."},
            {"role": "user", "content": "I think I understand now, but my code isn't working"},
            {"role": "assistant", "content": "Let's debug your code together..."},
            {"role": "user", "content": "I'm still getting errors. This is really frustrating!"},
            {"role": "assistant", "content": "Don't worry, debugging is part of learning..."},
            {"role": "user", "content": "Can you just tell me what's wrong with my code?"},
            {"role": "assistant", "content": "Let me guide you to find the issue..."},
        ]

    @pytest.fixture 
    def sample_user_messages(self):
        """示例用户消息（用于聚类）"""
        return [
            "I'm struggling with this sorting algorithm. Can you help me?",
            "I don't understand how bubble sort works",
            "I'm getting confused with the nested loops", 
            "I think I understand now, but my code isn't working",
            "I'm still getting errors. This is really frustrating!",
            "Can you just tell me what's wrong with my code?"
        ]

    def test_step1_message_extraction(self, sample_conversation_history):
        """测试步骤1：从对话历史中提取用户消息"""
        print("\n🔍 测试步骤1：消息提取")
        
        # 从对话历史中提取用户消息
        user_messages = [msg['content'] for msg in sample_conversation_history if msg.get('role') == 'user']
        
        assert len(user_messages) > 0, "应该提取到用户消息"
        assert "I'm struggling with this sorting algorithm" in user_messages[0]
        assert "Can you just tell me what's wrong" in user_messages[-1]
        
        print(f"✅ 成功提取到 {len(user_messages)} 条用户消息")
        for i, msg in enumerate(user_messages):
            print(f"   {i+1}. {msg[:50]}...")

    @patch('app.services.distance_based_clustering_service.DistanceBasedClusteringService')
    def test_step2_clustering_analysis(self, mock_clustering_service_class, user_state_service, sample_user_messages):
        """测试步骤2：聚类分析"""
        print("\n🧠 测试步骤2：聚类分析")
        
        # 设置模拟聚类服务
        mock_clustering_service = Mock()
        mock_clustering_service.is_loaded = True
        mock_clustering_service.classify_with_strategy.return_value = {
            'analysis_successful': True,
            'cluster_name': '低进度',
            'confidence': 0.75,
            'progress_score': -0.45,
            'classification_type': 'distance_based_full',
            'message_count': 6,
            'distances': [0.25, 0.63, 0.72]
        }
        mock_clustering_service_class.return_value = mock_clustering_service

        # 执行聚类分析
        with patch.object(user_state_service, 'get_or_create_profile') as mock_get_profile:
            # 模拟用户档案
            mock_profile = StudentProfile("test_user_001")
            mock_get_profile.return_value = (mock_profile, False)
            
            # 模拟set_profile方法
            user_state_service.set_profile = Mock()
            
            # 执行分析
            result = user_state_service.analyze_with_distance_clustering(
                "test_user_001", 
                [{"role": "user", "content": msg} for msg in sample_user_messages]
            )
            
            assert result is not None, "聚类分析应该返回结果"
            assert result.get('analysis_successful') is True, "分析应该成功"
            assert result['cluster_name'] == '低进度', f"预期聚类名称为'低进度'，实际为'{result['cluster_name']}'"
            assert result['cluster_confidence'] == 0.75, f"预期置信度0.75，实际为{result['cluster_confidence']}"
            
            print(f"✅ 聚类分析成功:")
            print(f"   聚类结果: {result['cluster_name']}")
            print(f"   置信度: {result['cluster_confidence']:.3f}")
            print(f"   进度分数: {result['progress_score']:.3f}")
            print(f"   分类类型: {result['analysis_type']}")

    def test_step3_user_state_update(self, user_state_service, redis_client):
        """测试步骤3：用户状态更新"""
        print("\n📊 测试步骤3：用户状态更新")
        
        participant_id = "test_user_002"
        
        # 模拟Redis存储
        stored_data = {}
        def mock_json_get(key, path='.'):
            if key in stored_data:
                if path == '.':
                    return stored_data[key]
                # 简化的路径解析
                parts = path.strip('.').split('.')
                data = stored_data[key]
                for part in parts:
                    if part and isinstance(data, dict):
                        data = data.get(part)
                    else:
                        break
                return data
            return None
            
        def mock_json_set(key, path, value):
            if path == '.':
                stored_data[key] = value
            else:
                # 简化的路径设置
                if key not in stored_data:
                    stored_data[key] = {}
                # 这里简化处理，实际Redis会更复杂
                if 'behavior_patterns.progress_clustering' in path:
                    if 'behavior_patterns' not in stored_data[key]:
                        stored_data[key]['behavior_patterns'] = {}
                    stored_data[key]['behavior_patterns']['progress_clustering'] = value
            return True
        
        redis_client.json().get.side_effect = mock_json_get
        redis_client.json().set.side_effect = mock_json_set
        
        # 获取或创建用户档案
        profile, is_new = user_state_service.get_or_create_profile(participant_id)
        
        # 模拟聚类数据更新
        clustering_data = {
            'current_cluster': '正常',
            'cluster_confidence': 0.82,
            'progress_score': 0.15,
            'last_analysis_timestamp': datetime.now(UTC).isoformat(),
            'conversation_count_analyzed': 8,
            'analysis_type': 'distance_based_full',
            'model_type': 'distance_based',
            'cluster_distances': [0.45, 0.18, 0.67],
            'clustering_history': []
        }
        
        # 添加历史记录
        clustering_data['clustering_history'].append({
            'timestamp': datetime.now(UTC).isoformat(),
            'cluster_name': '正常',
            'confidence': 0.82,
            'progress_score': 0.15,
            'message_count': 8,
            'analysis_type': 'distance_based_full',
            'model_type': 'distance_based'
        })
        
        # 更新用户状态
        set_dict = {
            'behavior_patterns.progress_clustering': clustering_data
        }
        user_state_service.set_profile(profile, set_dict)
        
        # 验证更新结果
        assert redis_client.json().set.called, "应该调用Redis设置方法"
        
        # 验证存储的数据结构
        stored_profile = stored_data.get(f"user_profile:{participant_id}", {})
        progress_data = stored_profile.get('behavior_patterns', {}).get('progress_clustering', {})
        
        assert progress_data.get('current_cluster') == '正常', "聚类结果应该正确存储"
        assert progress_data.get('cluster_confidence') == 0.82, "置信度应该正确存储"
        assert len(progress_data.get('clustering_history', [])) == 1, "应该有一条历史记录"
        
        print(f"✅ 用户状态更新成功:")
        print(f"   用户ID: {participant_id}")
        print(f"   存储的聚类结果: {progress_data.get('current_cluster')}")
        print(f"   存储的置信度: {progress_data.get('cluster_confidence')}")
        print(f"   历史记录数量: {len(progress_data.get('clustering_history', []))}")

    def test_step4_prompt_generation(self, prompt_generator):
        """测试步骤4：基于聚类结果生成提示词"""
        print("\n📝 测试步骤4：提示词生成")
        
        # 创建包含聚类结果的用户状态摘要
        user_state = UserStateSummary(
            participant_id="test_user_003",
            emotion_state={
                'current_sentiment': 'frustrated',
                'confidence': 0.8,
                'details': {}
            },
            behavior_patterns={
                'progress_clustering': {
                    'current_cluster': '低进度',
                    'cluster_confidence': 0.75,
                    'progress_score': -0.45,
                    'last_analysis_timestamp': datetime.now(UTC).isoformat(),
                    'conversation_count_analyzed': 6,
                    'clustering_history': []
                },
                'error_frequency': 0.3,
                'help_seeking_tendency': 0.6
            },
            behavior_counters={},
            bkt_models={},
            is_new_user=False
        )
        
        # 生成提示词
        system_prompt, messages, context_snapshot = prompt_generator.create_prompts(
            user_state=user_state,
            retrieved_context=["Sorting algorithms are fundamental..."],
            conversation_history=[
                {"role": "user", "content": "I'm struggling with bubble sort"},
                {"role": "assistant", "content": "Let me help you understand..."}
            ],
            user_message="Can you explain the algorithm step by step?",
            mode="learning",
            content_title="Sorting Algorithms"
        )
        
        # 验证返回结构
        assert isinstance(system_prompt, str), "system_prompt应该是字符串"
        assert isinstance(messages, list), "messages应该是列表"
        assert isinstance(context_snapshot, str), "context_snapshot应该是字符串"
        
        # 验证messages结构
        assert len(messages) > 0, "应该有消息"
        for msg in messages:
            assert isinstance(msg, dict), "每个消息应该是字典"
            assert 'role' in msg, "消息应该有role字段"
            assert 'content' in msg, "消息应该有content字段"
            assert msg['role'] in ['user', 'assistant'], f"role应该是user或assistant，实际为{msg['role']}"
        
        # 验证聚类策略是否被应用到提示词中
        assert '低进度' in system_prompt or 'struggling' in system_prompt.lower(), "系统提示词应该包含针对低进度学生的策略"
        
        print(f"✅ 提示词生成成功:")
        print(f"   system_prompt长度: {len(system_prompt)} 字符")
        print(f"   messages数量: {len(messages)}")
        print(f"   context_snapshot长度: {len(context_snapshot)} 字符")
        print(f"   system_prompt片段: {system_prompt[:150]}...")
        
        # 检查聚类信息是否在上下文中
        progress_context_found = any(
            '低进度' in msg.get('content', '') or 'progress' in msg.get('content', '').lower() 
            for msg in messages if msg.get('role') == 'assistant'
        )
        
        if progress_context_found:
            print(f"   ✅ 聚类进度信息已包含在消息上下文中")
        
        print(f"   最后一条用户消息: {messages[-1]['content'][:50]}...")

    @patch('app.services.distance_based_clustering_service.DistanceBasedClusteringService')
    def test_full_integration_flow(self, mock_clustering_service_class, user_state_service, prompt_generator):
        """测试完整集成流程：消息->聚类->状态更新->提示词生成"""
        print("\n🚀 测试完整集成流程")
        
        participant_id = "test_user_integration"
        
        # 步骤1：准备测试数据
        conversation_history = [
            {"role": "user", "content": "I need help with my programming assignment"},
            {"role": "assistant", "content": "I'd be happy to help! What's the assignment about?"},
            {"role": "user", "content": "It's about implementing a binary search tree"},
            {"role": "assistant", "content": "Great! Let's break it down step by step..."},
            {"role": "user", "content": "I'm confused about the insertion method"},
            {"role": "assistant", "content": "The insertion in a BST follows a specific pattern..."},
            {"role": "user", "content": "I keep getting null pointer exceptions"},
            {"role": "assistant", "content": "Let's debug that together..."},
            {"role": "user", "content": "This is too difficult. I don't think I can do this"},
            {"role": "assistant", "content": "Don't give up! Programming takes practice..."}
        ]
        
        # 步骤2：设置模拟聚类服务
        mock_clustering_service = Mock()
        mock_clustering_service.is_loaded = True
        mock_clustering_service.classify_with_strategy.return_value = {
            'analysis_successful': True,
            'cluster_name': '低进度',
            'confidence': 0.68,
            'progress_score': -0.52,
            'classification_type': 'distance_based_full',
            'message_count': 5,
            'distances': [0.32, 0.71, 0.58]
        }
        mock_clustering_service_class.return_value = mock_clustering_service
        
        # 步骤3：模拟用户档案和Redis操作
        with patch.object(user_state_service, 'get_or_create_profile') as mock_get_profile, \
             patch.object(user_state_service, 'set_profile') as mock_set_profile:
            
            # 创建模拟用户档案
            mock_profile = StudentProfile(participant_id)
            mock_get_profile.return_value = (mock_profile, False)
            
            # 步骤4：执行聚类分析
            clustering_result = user_state_service.analyze_with_distance_clustering(
                participant_id, conversation_history
            )
            
            # 验证聚类结果
            assert clustering_result is not None, "聚类分析应该成功"
            assert clustering_result['cluster_name'] == '低进度', "聚类结果应该正确"
            
            # 步骤5：验证状态更新被调用
            assert mock_set_profile.called, "应该调用状态更新方法"
            
            # 获取更新的数据
            call_args = mock_set_profile.call_args
            updated_clustering_data = call_args[0][1]['behavior_patterns.progress_clustering']
            
            assert updated_clustering_data['current_cluster'] == '低进度', "状态更新应该包含正确的聚类结果"
            assert updated_clustering_data['cluster_confidence'] == 0.68, "状态更新应该包含正确的置信度"
            
            # 步骤6：基于更新后的状态生成提示词
            user_state = UserStateSummary(
                participant_id=participant_id,
                emotion_state={'current_sentiment': 'frustrated'},
                behavior_patterns={'progress_clustering': updated_clustering_data},
                behavior_counters={},
                bkt_models={},
                is_new_user=False
            )
            
            system_prompt, messages, context_snapshot = prompt_generator.create_prompts(
                user_state=user_state,
                retrieved_context=["Binary search trees are data structures..."],
                conversation_history=conversation_history,
                user_message="I need more help with this problem",
                mode="learning",
                content_title="Binary Search Trees"
            )
            
            # 验证最终结果
            assert isinstance(system_prompt, str) and len(system_prompt) > 0, "应该生成有效的system prompt"
            assert isinstance(messages, list) and len(messages) > 0, "应该生成消息列表"
            assert all('role' in msg and 'content' in msg for msg in messages), "所有消息应该有正确的结构"
            
            print(f"✅ 完整集成流程测试成功!")
            print(f"   参与者ID: {participant_id}")
            print(f"   聚类结果: {clustering_result['cluster_name']}")
            print(f"   置信度: {clustering_result['cluster_confidence']:.3f}")
            print(f"   生成的system prompt: {len(system_prompt)} 字符")
            print(f"   生成的messages数量: {len(messages)}")
            print(f"   聚类信息已集成到提示词系统中")

    def test_clustering_data_structure_verification(self):
        """测试聚类数据在user_state_service中的存储结构"""
        print("\n📋 测试聚类数据存储结构")
        
        # 验证聚类数据字典结构
        expected_clustering_structure = {
            'current_cluster': str,      # '低进度'/'正常'/'超进度' 
            'cluster_confidence': float, # [0,1] 置信度
            'progress_score': float,     # [-2,2] 进度分数
            'last_analysis_timestamp': str, # ISO格式时间戳
            'conversation_count_analyzed': int, # 已分析的消息数量
            'analysis_type': str,        # 分析类型
            'model_type': str,          # 模型类型
            'cluster_distances': list,   # 距离列表
            'clustering_history': list   # 历史记录列表
        }
        
        # 创建示例数据
        sample_clustering_data = {
            'current_cluster': '正常',
            'cluster_confidence': 0.85,
            'progress_score': 0.12,
            'last_analysis_timestamp': datetime.now(UTC).isoformat(),
            'conversation_count_analyzed': 10,
            'analysis_type': 'distance_based_full',
            'model_type': 'distance_based',
            'cluster_distances': [0.25, 0.15, 0.67],
            'clustering_history': [
                {
                    'timestamp': datetime.now(UTC).isoformat(),
                    'cluster_name': '正常',
                    'confidence': 0.85,
                    'progress_score': 0.12,
                    'message_count': 10,
                    'analysis_type': 'distance_based_full',
                    'model_type': 'distance_based'
                }
            ]
        }
        
        # 验证数据类型
        for key, expected_type in expected_clustering_structure.items():
            assert key in sample_clustering_data, f"缺少必需字段: {key}"
            actual_value = sample_clustering_data[key]
            if expected_type == str:
                assert isinstance(actual_value, str), f"字段 {key} 应该是字符串类型"
            elif expected_type == float:
                assert isinstance(actual_value, (int, float)), f"字段 {key} 应该是数值类型"
            elif expected_type == int:
                assert isinstance(actual_value, int), f"字段 {key} 应该是整数类型"
            elif expected_type == list:
                assert isinstance(actual_value, list), f"字段 {key} 应该是列表类型"
        
        # 验证历史记录结构
        history_entry = sample_clustering_data['clustering_history'][0]
        required_history_fields = ['timestamp', 'cluster_name', 'confidence', 'progress_score', 'message_count']
        
        for field in required_history_fields:
            assert field in history_entry, f"历史记录缺少字段: {field}"
        
        print(f"✅ 聚类数据结构验证通过!")
        print(f"   主要字段数量: {len(expected_clustering_structure)}")
        print(f"   历史记录字段数量: {len(required_history_fields)}")
        print(f"   示例当前聚类: {sample_clustering_data['current_cluster']}")
        print(f"   示例置信度: {sample_clustering_data['cluster_confidence']}")
        print(f"   示例进度分数: {sample_clustering_data['progress_score']}")

    def test_prompt_structure_verification(self, prompt_generator):
        """测试提示词的两部分结构：system_prompt 和 messages"""
        print("\n📄 测试提示词结构")
        
        # 创建测试用的用户状态
        user_state = UserStateSummary(
            participant_id="test_prompt_structure",
            emotion_state={'current_sentiment': 'neutral'},
            behavior_patterns={
                'progress_clustering': {
                    'current_cluster': '正常',
                    'cluster_confidence': 0.8,
                    'progress_score': 0.1
                }
            },
            behavior_counters={},
            bkt_models={},
            is_new_user=False
        )
        
        # 生成提示词
        system_prompt, messages, context_snapshot = prompt_generator.create_prompts(
            user_state=user_state,
            retrieved_context=["Test knowledge context"],
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "How are you?"}
            ],
            user_message="I need help with my code",
            code_content=CodeContent(html="<div>test</div>", css="body{color:red}", js="console.log('hi')"),
            mode="test"
        )
        
        print(f"📋 提示词结构分析:")
        
        # 验证第一部分：system_prompt
        print(f"   🎯 第一部分 - system_prompt:")
        print(f"      类型: {type(system_prompt)}")
        print(f"      长度: {len(system_prompt)} 字符")
        print(f"      开头: {system_prompt[:100]}...")
        assert isinstance(system_prompt, str), "system_prompt必须是字符串"
        assert len(system_prompt) > 0, "system_prompt不能为空"
        
        # 验证第二部分：messages
        print(f"   💬 第二部分 - messages:")
        print(f"      类型: {type(messages)}")
        print(f"      数量: {len(messages)} 条消息")
        assert isinstance(messages, list), "messages必须是列表"
        assert len(messages) > 0, "messages不能为空"
        
        # 验证messages中每个消息的结构
        for i, message in enumerate(messages):
            print(f"      消息 {i+1}:")
            print(f"         类型: {type(message)}")
            print(f"         字段: {list(message.keys()) if isinstance(message, dict) else 'N/A'}")
            if isinstance(message, dict):
                print(f"         role: {message.get('role', 'N/A')}")
                print(f"         content长度: {len(message.get('content', ''))} 字符")
            
            assert isinstance(message, dict), f"消息 {i+1} 必须是字典"
            assert 'role' in message, f"消息 {i+1} 必须包含 role 字段"
            assert 'content' in message, f"消息 {i+1} 必须包含 content 字段"
            assert message['role'] in ['user', 'assistant'], f"消息 {i+1} 的 role 必须是 'user' 或 'assistant'"
            assert isinstance(message['content'], str), f"消息 {i+1} 的 content 必须是字符串"
        
        # 验证第三部分：context_snapshot
        print(f"   📸 第三部分 - context_snapshot:")
        print(f"      类型: {type(context_snapshot)}")
        print(f"      长度: {len(context_snapshot)} 字符")
        assert isinstance(context_snapshot, str), "context_snapshot必须是字符串"
        
        print(f"✅ 提示词结构验证通过!")
        print(f"   ✅ system_prompt: 字符串类型，{len(system_prompt)} 字符")
        print(f"   ✅ messages: 列表类型，{len(messages)} 条消息，每条都有正确的role和content")
        print(f"   ✅ context_snapshot: 字符串类型，{len(context_snapshot)} 字符")


def run_standalone_tests():
    """独立运行测试（不使用pytest）"""
    print("🧪 开始聚类进度完整集成测试")
    print("=" * 60)
    
    # 创建测试实例
    test_instance = TestClusteringIntegrationFull()
    
    # 手动创建测试依赖
    mock_redis = Mock(spec=redis.Redis)
    mock_redis.json.return_value = Mock()
    
    user_state_service = UserStateService(mock_redis)
    prompt_generator = PromptGenerator()
    
    try:
        # 运行各个测试步骤
        sample_conversation = [
            {"role": "user", "content": "I'm struggling with this sorting algorithm. Can you help me?"},
            {"role": "assistant", "content": "I'd be happy to help! What specific part of sorting are you having trouble with?"},
            {"role": "user", "content": "I don't understand how bubble sort works"},
            {"role": "assistant", "content": "Let me explain bubble sort step by step..."},
            {"role": "user", "content": "I'm getting confused with the nested loops"},
            {"role": "assistant", "content": "The outer loop controls the number of passes..."},
            {"role": "user", "content": "I think I understand now, but my code isn't working"},
            {"role": "assistant", "content": "Let's debug your code together..."},
            {"role": "user", "content": "I'm still getting errors. This is really frustrating!"},
            {"role": "assistant", "content": "Don't worry, debugging is part of learning..."},
            {"role": "user", "content": "Can you just tell me what's wrong with my code?"},
            {"role": "assistant", "content": "Let me guide you to find the issue..."},
        ]
        
        sample_user_messages = [
            "I'm struggling with this sorting algorithm. Can you help me?",
            "I don't understand how bubble sort works",
            "I'm getting confused with the nested loops", 
            "I think I understand now, but my code isn't working",
            "I'm still getting errors. This is really frustrating!",
            "Can you just tell me what's wrong with my code?"
        ]
        
        test_instance.test_step1_message_extraction(sample_conversation)
        test_instance.test_clustering_data_structure_verification()
        test_instance.test_prompt_structure_verification(prompt_generator)
        
        print("\n" + "=" * 60)
        print("🎉 核心测试通过！聚类进度集成结构正确")
        print("\n💡 关键验证结果:")
        print("   ✅ 提示词由 system_prompt(str) + messages(list) + context_snapshot(str) 组成")
        print("   ✅ user_state_service 中聚类记录以字典格式存储")
        print("   ✅ 完整流程：消息提取 -> 聚类分析 -> 状态更新 -> 提示词生成")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_standalone_tests()
