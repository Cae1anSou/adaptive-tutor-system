#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的聚类算法集成测试脚本
测试预训练模型的使用和簇的标注映射
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# 设置环境变量
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TRANSFORMERS_NO_FLAX"] = "1"
os.environ["USE_TF"] = "0"

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_conversation() -> List[Dict[str, str]]:
    """创建测试对话历史"""
    return [
        {"role": "user", "content": "I'm trying to implement a raycast system in Unity but I'm getting errors."},
        {"role": "assistant", "content": "Let me help you with Unity raycast implementation. What specific errors are you seeing?"},
        {"role": "user", "content": "The error says 'RaycastHit is not defined'."},
        {"role": "assistant", "content": "You need to import UnityEngine at the top of your script. Add 'using UnityEngine;' at the beginning."},
        {"role": "user", "content": "Thanks! That fixed it. Now I want to make the raycast detect only certain layers."},
        {"role": "assistant", "content": "You can use LayerMask to specify which layers the raycast should detect. Here's how to do it."},
        {"role": "user", "content": "Perfect! The raycast is working now. Can you show me how to visualize it in the scene view?"},
        {"role": "assistant", "content": "You can use Debug.DrawRay to visualize the raycast in the scene view. This is very useful for debugging."},
        {"role": "user", "content": "Great! Now I want to make it more efficient by using Physics.RaycastNonAlloc."},
        {"role": "assistant", "content": "Excellent choice! Physics.RaycastNonAlloc is more efficient as it reuses the RaycastHit array. Here's how to implement it."},
        {"role": "user", "content": "This is working much better! Can you show me how to handle multiple raycasts for different purposes?"},
        {"role": "assistant", "content": "You can create separate raycast methods for different purposes, or use a more sophisticated system with raycast layers and masks."},
        {"role": "user", "content": "I'm getting a performance issue when I have many objects to raycast against."},
        {"role": "assistant", "content": "For better performance with many objects, consider using spatial partitioning like quadtrees or octrees, or optimize your layer masks."},
        {"role": "user", "content": "That's a great suggestion! I'll implement a quadtree system to improve performance."},
        {"role": "assistant", "content": "That's an advanced optimization! Quadtrees are excellent for spatial queries. Would you like me to show you a basic quadtree implementation?"},
        {"role": "user", "content": "Yes, please! I want to learn how to implement spatial data structures."},
        {"role": "assistant", "content": "Here's a basic quadtree implementation for Unity. This will significantly improve your raycast performance."},
        {"role": "user", "content": "This is amazing! The performance improvement is incredible. Can you show me how to extend this to 3D with octrees?"},
        {"role": "assistant", "content": "Absolutely! Octrees are the 3D equivalent of quadtrees. Here's how to implement a basic octree system."},
        {"role": "user", "content": "This is exactly what I needed! The octree implementation is working perfectly."},
        {"role": "assistant", "content": "Excellent! You've successfully implemented a high-performance spatial partitioning system. This is a great foundation for complex 3D applications."},
        {"role": "user", "content": "Thank you so much! I've learned so much about optimization and spatial data structures."},
        {"role": "assistant", "content": "You're very welcome! You've shown great progress from basic raycasting to advanced spatial optimization. Keep up the excellent work!"},
        {"role": "user", "content": "I'm having trouble with the quadtree implementation. The performance isn't as good as expected."},
        {"role": "assistant", "content": "Let me help you debug the quadtree implementation. What specific performance issues are you seeing?"},
        {"role": "user", "content": "The insertion is taking too long when I have many objects."},
        {"role": "assistant", "content": "The issue might be with the subdivision logic. Let's optimize the insertion algorithm."},
        {"role": "user", "content": "I think I found the problem. The tree is getting too deep."},
        {"role": "assistant", "content": "Good catch! You should add a maximum depth limit to prevent the tree from becoming too unbalanced."},
        {"role": "user", "content": "That fixed it! The performance is much better now."},
        {"role": "assistant", "content": "Excellent! Depth limiting is crucial for quadtree performance. Great debugging work!"},
        {"role": "user", "content": "Now I want to add collision detection to the quadtree."},
        {"role": "assistant", "content": "Great idea! Quadtrees are perfect for broad-phase collision detection. Here's how to implement it."},
        {"role": "user", "content": "The collision detection is working, but it's missing some collisions."},
        {"role": "assistant", "content": "This is likely due to objects spanning multiple quadrants. You need to handle overlapping objects properly."},
        {"role": "user", "content": "I see the issue. Objects on quadrant boundaries aren't being checked."},
        {"role": "assistant", "content": "Exactly! You need to insert objects into all quadrants they overlap with, not just the center quadrant."},
        {"role": "user", "content": "That makes sense. Let me fix the insertion logic."},
        {"role": "assistant", "content": "Good approach! This will ensure no collisions are missed due to boundary issues."},
        {"role": "user", "content": "Perfect! Now the collision detection is working correctly."},
        {"role": "assistant", "content": "Excellent! You've successfully implemented a robust quadtree collision detection system."},
        {"role": "user", "content": "This has been a great learning experience. Thank you for all the help!"},
        {"role": "assistant", "content": "You're very welcome! You've shown excellent problem-solving skills and persistence. Keep up the great work!"}
    ]

def test_clustering_service():
    """测试聚类服务"""
    try:
        from app.services.progress_clustering_service import ProgressClusteringService
        
        # 创建测试对话
        conversation = create_test_conversation()
        
        # 测试不同的配置
        test_configs = [
            {
                "name": "使用预训练模型",
                "use_pretrained": True,
                "include_struct": True,
                "struct_weight": 1.5
            },
            {
                "name": "不使用预训练模型",
                "use_pretrained": False,
                "include_struct": True,
                "struct_weight": 1.5
            },
            {
                "name": "仅语义特征",
                "use_pretrained": True,
                "include_struct": False,
                "struct_weight": 1.5
            }
        ]
        
        for config in test_configs:
            logger.info(f"\n=== 测试配置: {config['name']} ===")
            
            # 创建服务实例
            service = ProgressClusteringService(
                batch_size=12,
                overlap=4,
                model_name="sentence-transformers/all-mpnet-base-v2",
                pca_dim=64,
                lookback=2,
                near_sim_thresh=0.92,
                include_struct=config['include_struct'],
                struct_weight=config['struct_weight'],
                n_init=200,
                max_iter=1000,
                use_pretrained_models=config['use_pretrained']
            )
            
            # 执行聚类分析
            result = service.analyze_conversation_progress(conversation, "test_user_001")
            
            # 验证结果
            logger.info(f"消息数量: {result.get('message_count', 0)}")
            logger.info(f"窗口数量: {result.get('window_count', 0)}")
            logger.info(f"聚类标签: {result.get('named_labels', [])}")
            logger.info(f"进度分数: {result.get('progress_score', [])}")
            logger.info(f"簇映射: {result.get('names_map', {})}")
            
            # 验证簇的标注映射
            names_map = result.get('names_map', {})
            if names_map:
                logger.info("簇标注映射验证:")
                for cluster_id, label in names_map.items():
                    logger.info(f"  簇 {cluster_id} -> {label}")
                
                # 检查是否符合用户指定的映射 (1: 正常, 0: 超进度, 2: 低进度)
                expected_mapping = {1: "正常", 0: "超进度", 2: "低进度"}
                mapping_correct = True
                for cluster_id, expected_label in expected_mapping.items():
                    if cluster_id in names_map:
                        actual_label = names_map[cluster_id]
                        if actual_label != expected_label:
                            logger.warning(f"簇 {cluster_id} 的标注不匹配: 期望 '{expected_label}', 实际 '{actual_label}'")
                            mapping_correct = False
                
                if mapping_correct:
                    logger.info("✅ 簇标注映射正确")
                else:
                    logger.warning("⚠️ 簇标注映射与期望不符")
            
            # 获取进度摘要
            summary = service.get_progress_summary("test_user_001")
            logger.info(f"当前状态: {summary.get('current_state', '未知')}")
            logger.info(f"置信度: {summary.get('confidence', 0.0):.3f}")
            logger.info(f"趋势: {summary.get('trend', '未知')}")
            logger.info(f"建议数量: {len(summary.get('recommendations', []))}")
            
            # 清理缓存
            service._clustering_cache.clear()
        
        logger.info("\n=== 所有测试完成 ===")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_enhanced_cluster_analysis():
    """直接测试enhanced_cluster_analysis模块"""
    try:
        logger.info("\n=== 直接测试 enhanced_cluster_analysis ===")
        
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from app.services.enhanced_cluster_analysis import progress_clustering_pipeline
        
        # 创建测试消息
        messages = [msg["content"] for msg in create_test_conversation()]
        
        # 测试使用预训练模型
        logger.info("测试使用预训练模型...")
        result_with_pretrained = progress_clustering_pipeline(
            raw_msgs=messages,
            batch_size=12,
            overlap=4,
            model_name="sentence-transformers/all-mpnet-base-v2",
                             pca_dim=64,
            include_struct_in_clustering=True,
            lookback=2,
            n_init=200,
            max_iter=1000,
            struct_weight=1.5,
            near_sim_thresh=0.92
        )
        
        logger.info(f"使用预训练模型的结果:")
        logger.info(f"  簇映射: {result_with_pretrained.get('names_map', {})}")
        logger.info(f"  命名标签: {result_with_pretrained.get('named_labels', [])}")
        logger.info(f"  进度分数: {result_with_pretrained.get('progress_score', [])}")
        
        # 验证簇的标注映射
        names_map = result_with_pretrained.get('names_map', {})
        if names_map:
            logger.info("簇标注映射验证:")
            for cluster_id, label in names_map.items():
                logger.info(f"  簇 {cluster_id} -> {label}")
        
        logger.info("✅ enhanced_cluster_analysis 测试完成")
        
    except Exception as e:
        logger.error(f"enhanced_cluster_analysis 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_pretrained_models():
    """测试预训练模型文件"""
    try:
        logger.info("\n=== 测试预训练模型文件 ===")
        
        from joblib import load
        import os
        
        # 检查预训练模型文件
        pretrained_dir = os.path.join(os.path.dirname(__file__), '..', 'out_struct_dim48_w1p5_t0921')
        pca_path = os.path.join(pretrained_dir, 'pca.joblib')
        scaler_path = os.path.join(pretrained_dir, 'struct_scaler.joblib')
        
        logger.info(f"预训练模型目录: {pretrained_dir}")
        logger.info(f"PCA模型文件: {pca_path} (存在: {os.path.exists(pca_path)})")
        logger.info(f"Scaler模型文件: {scaler_path} (存在: {os.path.exists(scaler_path)})")
        
        if os.path.exists(pca_path) and os.path.exists(scaler_path):
            # 加载预训练模型
            pca_model = load(pca_path)
            scaler_model = load(scaler_path)
            
            logger.info(f"PCA模型组件数: {pca_model.n_components_}")
            logger.info(f"Scaler模型特征数: {scaler_model.n_features_in_}")
            
            logger.info("✅ 预训练模型加载成功")
        else:
            logger.warning("⚠️ 预训练模型文件不存在")
        
    except Exception as e:
        logger.error(f"预训练模型测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    logger.info("开始聚类算法集成测试...")
    
    # 测试预训练模型文件
    test_pretrained_models()
    
    # 直接测试enhanced_cluster_analysis
    test_enhanced_cluster_analysis()
    
    # 测试聚类服务
    test_clustering_service()
    
    logger.info("所有测试完成!")
