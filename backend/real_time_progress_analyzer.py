#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时学习进度分析器
解决当前聚类系统需要大量数据的问题
"""

import sys
import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, UTC
import numpy as np

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.user_state_service import UserStateService, StudentProfile


class RealTimeProgressAnalyzer:
    """实时学习进度分析器"""
    
    def __init__(self):
        # 关键词词典
        self.DONE_KEYWORDS = {
            "complete", "completed", "finish", "finished", "pass", "passed", 
            "accept", "accepted", "solved", "resolve", "resolved", "fix", "fixed", 
            "merge", "merged", "success", "successfully", "ok", "ac", "working", "works"
        }
        
        self.STUCK_KEYWORDS = {
            "error", "errors", "failed", "fail", "stuck", "bug", "exception", 
            "timeout", "timed out", "crash", "cannot", "not working", "confused", 
            "don't understand", "help", "lost", "difficult", "hard", "problem"
        }
        
        self.CONFIDENCE_KEYWORDS = {
            "confident", "understand", "clear", "got it", "makes sense", 
            "easy", "simple", "straightforward"
        }
        
        self.FRUSTRATION_KEYWORDS = {
            "frustrated", "frustrating", "annoying", "give up", "quit", 
            "impossible", "hate", "terrible", "awful"
        }

    def analyze_real_time_progress(self, 
                                   participant_id: str, 
                                   conversation_history: List[Dict[str, str]],
                                   current_message: str = None) -> Dict[str, Any]:
        """
        实时分析学习进度（无需等待大量数据）
        
        Args:
            participant_id: 参与者ID
            conversation_history: 对话历史
            current_message: 当前消息（可选）
            
        Returns:
            实时进度分析结果
        """
        # 提取用户消息
        user_messages = [msg['content'] for msg in conversation_history if msg.get('role') == 'user']
        if current_message:
            user_messages.append(current_message)
        
        if len(user_messages) == 0:
            return self._default_progress_result()
        
        # 分层分析策略
        if len(user_messages) < 5:
            return self._analyze_early_stage(user_messages, participant_id)
        elif len(user_messages) < 12:
            return self._analyze_mid_stage(user_messages, participant_id)
        else:
            return self._analyze_full_stage(user_messages, participant_id)

    def _analyze_early_stage(self, user_messages: List[str], participant_id: str) -> Dict[str, Any]:
        """早期阶段分析（1-4条消息）"""
        print(f"🌱 早期阶段分析: {len(user_messages)}条消息")
        
        # 基于关键词的快速分析
        done_count = sum(self._count_keywords(msg, self.DONE_KEYWORDS) for msg in user_messages)
        stuck_count = sum(self._count_keywords(msg, self.STUCK_KEYWORDS) for msg in user_messages)
        confidence_count = sum(self._count_keywords(msg, self.CONFIDENCE_KEYWORDS) for msg in user_messages)
        frustration_count = sum(self._count_keywords(msg, self.FRUSTRATION_KEYWORDS) for msg in user_messages)
        
        # 消息长度和复杂度分析
        avg_length = np.mean([len(msg) for msg in user_messages])
        
        # 简单的进度评估
        progress_indicators = {
            'done_ratio': done_count / len(user_messages),
            'stuck_ratio': stuck_count / len(user_messages),
            'confidence_ratio': confidence_count / len(user_messages),
            'frustration_ratio': frustration_count / len(user_messages),
            'avg_message_length': avg_length
        }
        
        # 早期进度分数
        progress_score = (
            progress_indicators['done_ratio'] * 0.4 +
            progress_indicators['confidence_ratio'] * 0.3 -
            progress_indicators['stuck_ratio'] * 0.3 -
            progress_indicators['frustration_ratio'] * 0.2
        )
        
        # 早期分类
        if progress_score > 0.2:
            cluster_name = "早期正面"
            teaching_strategy = "maintain_momentum"
        elif progress_score < -0.2:
            cluster_name = "早期困难"
            teaching_strategy = "provide_support"
        else:
            cluster_name = "早期探索"
            teaching_strategy = "gentle_guidance"
        
        return {
            'analysis_type': 'early_stage',
            'cluster_name': cluster_name,
            'progress_score': progress_score,
            'confidence': 0.6,  # 早期置信度较低
            'teaching_strategy': teaching_strategy,
            'indicators': progress_indicators,
            'message_count': len(user_messages),
            'stage': 'early'
        }

    def _analyze_mid_stage(self, user_messages: List[str], participant_id: str) -> Dict[str, Any]:
        """中期阶段分析（5-11条消息）"""
        print(f"🌿 中期阶段分析: {len(user_messages)}条消息")
        
        # 更复杂的模式分析
        recent_messages = user_messages[-5:]  # 最近5条
        
        # 计算各种指标
        indicators = self._calculate_detailed_indicators(user_messages)
        
        # 趋势分析
        early_score = self._calculate_period_score(user_messages[:len(user_messages)//2])
        recent_score = self._calculate_period_score(recent_messages)
        
        trend = recent_score - early_score
        
        # 中期进度分数（更复杂的计算）
        progress_score = (
            indicators['done_ratio'] * 0.3 +
            indicators['confidence_ratio'] * 0.2 -
            indicators['stuck_ratio'] * 0.3 -
            indicators['repetition_rate'] * 0.2 +
            trend * 0.3  # 趋势权重
        )
        
        # 中期分类
        if progress_score > 0.3:
            cluster_name = "中期进展"
            teaching_strategy = "increase_challenge"
        elif progress_score < -0.3:
            cluster_name = "中期困难"
            teaching_strategy = "provide_scaffolding"
        else:
            cluster_name = "中期稳定"
            teaching_strategy = "maintain_pace"
        
        return {
            'analysis_type': 'mid_stage',
            'cluster_name': cluster_name,
            'progress_score': progress_score,
            'confidence': 0.75,  # 中期置信度提高
            'teaching_strategy': teaching_strategy,
            'indicators': indicators,
            'trend': trend,
            'message_count': len(user_messages),
            'stage': 'mid'
        }

    def _analyze_full_stage(self, user_messages: List[str], participant_id: str) -> Dict[str, Any]:
        """完整阶段分析（≥12条消息）- 可以尝试完整聚类"""
        print(f"🌳 完整阶段分析: {len(user_messages)}条消息")
        
        # 首先尝试完整聚类
        try:
            from app.services.user_state_service import PROGRESS_CLUSTERING_AVAILABLE, progress_clustering_pipeline
            
            if PROGRESS_CLUSTERING_AVAILABLE:
                print("🔬 尝试完整聚类分析...")
                
                # 启用结构特征参与聚类
                clustering_result = progress_clustering_pipeline(
                    raw_msgs=user_messages,
                    batch_size=min(12, len(user_messages)),
                    overlap=min(4, len(user_messages)//3),
                    model_name="sentence-transformers/all-mpnet-base-v2",
                    pca_dim=min(64, len(user_messages)-1),
                    include_struct_in_clustering=True,  # 启用行为特征
                    lookback=2,
                    n_init=20,  # 减少计算量
                    max_iter=300,
                    random_state=42,
                    struct_weight=2.0,
                    near_sim_thresh=0.95
                )
                
                # 如果聚类成功，返回聚类结果
                if clustering_result:
                    latest_window_idx = len(clustering_result['windows']) - 1
                    return {
                        'analysis_type': 'full_clustering',
                        'cluster_name': clustering_result['named_labels'][latest_window_idx],
                        'progress_score': float(clustering_result['progress_score'][latest_window_idx]),
                        'confidence': float(clustering_result['sims'][latest_window_idx]),
                        'teaching_strategy': self._get_strategy_from_cluster(clustering_result['named_labels'][latest_window_idx]),
                        'silhouette_score': clustering_result.get('silhouette', 0.0),
                        'total_windows': len(clustering_result['windows']),
                        'message_count': len(user_messages),
                        'stage': 'full'
                    }
        except Exception as e:
            print(f"⚠️ 完整聚类失败，回退到高级分析: {e}")
        
        # 如果聚类失败，使用高级分析
        return self._advanced_analysis_fallback(user_messages, participant_id)

    def _advanced_analysis_fallback(self, user_messages: List[str], participant_id: str) -> Dict[str, Any]:
        """高级分析回退方案"""
        print("🔧 使用高级分析回退方案")
        
        # 复杂的指标计算
        indicators = self._calculate_detailed_indicators(user_messages)
        
        # 时间窗口分析
        window_size = 5
        windows = [user_messages[i:i+window_size] for i in range(0, len(user_messages)-window_size+1, 2)]
        window_scores = [self._calculate_period_score(window) for window in windows]
        
        # 整体趋势
        if len(window_scores) > 1:
            trend = window_scores[-1] - window_scores[0]
            stability = np.std(window_scores)
        else:
            trend = 0
            stability = 0
        
        # 高级进度分数
        progress_score = (
            indicators['done_ratio'] * 0.25 +
            indicators['confidence_ratio'] * 0.2 -
            indicators['stuck_ratio'] * 0.25 -
            indicators['repetition_rate'] * 0.15 +
            trend * 0.15 -
            stability * 0.1  # 稳定性也很重要
        )
        
        # 高级分类
        if progress_score > 0.4:
            cluster_name = "高级进展"
            teaching_strategy = "advanced_challenges"
        elif progress_score > 0.1:
            cluster_name = "稳定进展"
            teaching_strategy = "gradual_advancement"
        elif progress_score > -0.2:
            cluster_name = "需要支持"
            teaching_strategy = "targeted_help"
        else:
            cluster_name = "需要干预"
            teaching_strategy = "intensive_support"
        
        return {
            'analysis_type': 'advanced_fallback',
            'cluster_name': cluster_name,
            'progress_score': progress_score,
            'confidence': 0.8,
            'teaching_strategy': teaching_strategy,
            'indicators': indicators,
            'trend': trend,
            'stability': stability,
            'window_scores': window_scores,
            'message_count': len(user_messages),
            'stage': 'advanced'
        }

    def _calculate_detailed_indicators(self, messages: List[str]) -> Dict[str, float]:
        """计算详细指标"""
        total_msgs = len(messages)
        
        # 关键词计数
        done_count = sum(self._count_keywords(msg, self.DONE_KEYWORDS) for msg in messages)
        stuck_count = sum(self._count_keywords(msg, self.STUCK_KEYWORDS) for msg in messages)
        confidence_count = sum(self._count_keywords(msg, self.CONFIDENCE_KEYWORDS) for msg in messages)
        frustration_count = sum(self._count_keywords(msg, self.FRUSTRATION_KEYWORDS) for msg in messages)
        
        # 重复性分析
        unique_messages = len(set(msg.lower().strip() for msg in messages))
        repetition_rate = 1.0 - (unique_messages / total_msgs)
        
        # 长度变化
        lengths = [len(msg) for msg in messages]
        length_variance = np.var(lengths) if len(lengths) > 1 else 0
        
        # 问句比例
        question_count = sum(1 for msg in messages if '?' in msg)
        question_ratio = question_count / total_msgs
        
        return {
            'done_ratio': done_count / total_msgs,
            'stuck_ratio': stuck_count / total_msgs,
            'confidence_ratio': confidence_count / total_msgs,
            'frustration_ratio': frustration_count / total_msgs,
            'repetition_rate': repetition_rate,
            'question_ratio': question_ratio,
            'length_variance': length_variance,
            'avg_length': np.mean(lengths)
        }

    def _calculate_period_score(self, messages: List[str]) -> float:
        """计算时期分数"""
        if not messages:
            return 0.0
        
        indicators = self._calculate_detailed_indicators(messages)
        return (
            indicators['done_ratio'] * 0.4 +
            indicators['confidence_ratio'] * 0.3 -
            indicators['stuck_ratio'] * 0.3 -
            indicators['frustration_ratio'] * 0.2
        )

    def _count_keywords(self, message: str, keywords: set) -> int:
        """计算关键词出现次数"""
        message_lower = message.lower()
        return sum(1 for keyword in keywords if keyword in message_lower)

    def _get_strategy_from_cluster(self, cluster_name: str) -> str:
        """根据聚类名称获取教学策略"""
        strategy_map = {
            '低进度': 'provide_foundation',
            '正常': 'maintain_pace',
            '超进度': 'increase_challenge'
        }
        return strategy_map.get(cluster_name, 'adaptive_response')

    def _default_progress_result(self) -> Dict[str, Any]:
        """默认进度结果"""
        return {
            'analysis_type': 'insufficient_data',
            'cluster_name': '数据不足',
            'progress_score': 0.0,
            'confidence': 0.0,
            'teaching_strategy': 'collect_more_data',
            'message_count': 0,
            'stage': 'init'
        }


# 集成到UserStateService的新方法
def add_real_time_analysis_to_user_state_service():
    """为UserStateService添加实时分析方法"""
    
    def analyze_real_time_progress_enhanced(self, participant_id: str, conversation_history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """
        增强的实时进度分析（替代原有的analyze_learning_progress）
        """
        analyzer = RealTimeProgressAnalyzer()
        result = analyzer.analyze_real_time_progress(participant_id, conversation_history)
        
        if result['analysis_type'] != 'insufficient_data':
            # 更新用户档案
            try:
                profile, _ = self.get_or_create_profile(participant_id, None)
                current_time = datetime.now(UTC)
                
                clustering_data = {
                    'current_cluster': result['cluster_name'],
                    'cluster_confidence': result['confidence'],
                    'progress_score': result['progress_score'],
                    'last_analysis_timestamp': current_time.isoformat(),
                    'conversation_count_analyzed': result['message_count'],
                    'analysis_type': result['analysis_type'],
                    'teaching_strategy': result['teaching_strategy'],
                    'clustering_history': profile.behavior_patterns.get('progress_clustering', {}).get('clustering_history', [])
                }
                
                # 添加历史记录
                clustering_data['clustering_history'].append({
                    'timestamp': current_time.isoformat(),
                    'cluster_name': result['cluster_name'],
                    'confidence': result['confidence'],
                    'progress_score': result['progress_score'],
                    'message_count': result['message_count'],
                    'analysis_type': result['analysis_type']
                })
                
                # 保持历史记录数量限制
                if len(clustering_data['clustering_history']) > 20:
                    clustering_data['clustering_history'] = clustering_data['clustering_history'][-20:]
                
                # 更新Redis
                set_dict = {
                    'behavior_patterns.progress_clustering': clustering_data
                }
                self.set_profile(profile, set_dict)
                
                logger.info(f"实时进度分析完成: {participant_id} -> {result['cluster_name']} (置信度: {result['confidence']:.3f})")
                
            except Exception as e:
                logger.error(f"更新用户档案时出错: {e}")
        
        return result
    
    # 添加方法到UserStateService类
    UserStateService.analyze_real_time_progress_enhanced = analyze_real_time_progress_enhanced


if __name__ == "__main__":
    # 测试实时分析器
    analyzer = RealTimeProgressAnalyzer()
    
    # 测试不同阶段
    test_cases = [
        # 早期阶段
        [{"role": "user", "content": "I don't understand this"}],
        [{"role": "user", "content": "I don't understand this"}, 
         {"role": "user", "content": "Can you help me?"}],
        
        # 中期阶段
        [{"role": "user", "content": f"Message {i}"} for i in range(7)],
        
        # 完整阶段
        [{"role": "user", "content": f"I'm struggling with problem {i}"} for i in range(15)]
    ]
    
    for i, conversation in enumerate(test_cases):
        print(f"\n{'='*50}")
        print(f"测试用例 {i+1}: {len(conversation)}条消息")
        result = analyzer.analyze_real_time_progress(f"test_user_{i}", conversation)
        print(f"分析结果: {result['cluster_name']}")
        print(f"进度分数: {result['progress_score']:.3f}")
        print(f"置信度: {result['confidence']:.3f}")
        print(f"教学策略: {result['teaching_strategy']}")
        print(f"分析类型: {result['analysis_type']}")





