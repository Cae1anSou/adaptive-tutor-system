#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于距离的聚类服务：直接使用预训练模型文件进行聚类
移动到 app/services/ 目录
"""

import os
import json
import numpy as np
from joblib import load
from typing import List, Dict, Any, Optional
import logging

# 设置环境变量防止TensorFlow冲突
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TRANSFORMERS_NO_FLAX"] = "1"
os.environ["USE_TF"] = "0"

logger = logging.getLogger(__name__)

class DistanceBasedClusteringService:
    """基于距离的聚类服务：直接使用预训练模型文件"""
    
    def __init__(self, model_dir: str = None):
        if model_dir is None:
            # 默认使用models目录下的预训练模型
            current_dir = os.path.dirname(__file__)
            model_dir = os.path.join(current_dir, "..", "..", "models", "progress_clustering")
        
        self.model_dir = model_dir
        self.is_loaded = False
        
        try:
            # 加载所有预训练文件
            self.config = self._load_config()
            self.cluster_centers = self._load_cluster_centers()  # shape: (3, 51)
            self.pca_model = self._load_pca_model()
            self.struct_scaler = self._load_struct_scaler()
            self.names_map = self._load_names_map()
            self.cluster_means_progress = self._load_cluster_means_progress()
            
            # 检查文件完整性
            assert self.cluster_centers.shape[0] == 3, f"应该有3个聚类中心，实际: {self.cluster_centers.shape[0]}"
            assert self.cluster_centers.shape[1] == 51, f"特征维度应该是51，实际: {self.cluster_centers.shape[1]}"
            
            self.is_loaded = True
            
            print("✅ 距离聚类服务初始化成功")
            print(f"聚类中心形状: {self.cluster_centers.shape}")
            print(f"聚类名称: {self.names_map}")
            print(f"进度分数: {self.cluster_means_progress}")
            print(f"配置: {self.config}")
            
        except Exception as e:
            logger.error(f"距离聚类服务初始化失败: {e}")
            self.is_loaded = False

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = os.path.join(self.model_dir, "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_cluster_centers(self) -> np.ndarray:
        """加载聚类中心"""
        centers_path = os.path.join(self.model_dir, "cluster_centers.npy")
        return np.load(centers_path)

    def _load_pca_model(self):
        """加载PCA模型"""
        pca_path = os.path.join(self.model_dir, "pca.joblib")
        return load(pca_path)

    def _load_struct_scaler(self):
        """加载结构特征标准化器"""
        scaler_path = os.path.join(self.model_dir, "struct_scaler.joblib")
        return load(scaler_path)

    def _load_names_map(self) -> Dict[int, str]:
        """加载聚类名称映射"""
        report_path = os.path.join(self.model_dir, "cluster_report.json")
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
            return {int(k): v for k, v in report["names_map"].items()}

    def _load_cluster_means_progress(self) -> Dict[int, float]:
        """加载聚类进度分数"""
        report_path = os.path.join(self.model_dir, "cluster_report.json")
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
            return {int(k): v for k, v in report["cluster_means_progress"].items()}

    def classify_with_strategy(self, user_messages: List[str]) -> Dict[str, Any]:
        """
        通过计算与聚类中心的距离进行分类
        
        Args:
            user_messages: 用户消息列表
            
        Returns:
            聚类结果
        """
        if not self.is_loaded:
            return {"analysis_successful": False, "error": "模型未加载"}
        
        if len(user_messages) == 0:
            return {"analysis_successful": False, "error": "无用户消息"}
        
        try:
            # 导入聚类核心服务进行特征提取
            from .clustering_core_service import (
                preprocess_messages, 
                encode_messages, 
                create_single_window_from_messages
            )
            
            # 提取特征
            feature_vector = self._extract_features_with_core_service(user_messages)
            
            if feature_vector is None:
                return self._fallback_classification(user_messages)
            
            # 计算与每个聚类中心的余弦距离
            distances = self._calculate_cosine_distances(feature_vector)
            
            # 找到最近的聚类中心
            closest_cluster_id = np.argmin(distances)
            confidence = max(0.1, 1.0 - distances[closest_cluster_id])  # 距离越小，置信度越高
            
            # 获取聚类信息
            cluster_name = self.names_map.get(closest_cluster_id, f"聚类-{closest_cluster_id}")
            progress_score = self.cluster_means_progress.get(closest_cluster_id, 0.0)
            
            return {
                "cluster_id": int(closest_cluster_id),
                "cluster_name": cluster_name,
                "progress_score": float(progress_score),
                "confidence": float(confidence),
                "distances": distances.tolist(),
                "classification_type": "distance_based_full",
                "message_count": len(user_messages),
                "analysis_successful": True
            }
            
        except Exception as e:
            logger.error(f"距离分类失败: {e}")
            return self._fallback_classification(user_messages)

    def _extract_features_with_core_service(self, user_messages: List[str]) -> Optional[np.ndarray]:
        """
        使用核心聚类服务提取特征向量（支持padding和mask）
        
        Args:
            user_messages: 用户消息
            
        Returns:
            51维特征向量 [语义48维 + 结构3维]
        """
        try:
            from .clustering_core_service import (
                preprocess_messages, 
                encode_messages, 
                pool_window_embeddings_with_padding,
                window_repeat_features, 
                window_code_change,
                create_single_window_from_messages
            )
            
            # 创建单个窗口（支持padding）
            window_indices, processed_messages, valid_indices, is_padded = create_single_window_from_messages(
                user_messages, target_size=12, min_size=1
            )
            
            # 预处理消息
            clean_texts, code_hashes_per_msg = preprocess_messages(processed_messages)
            
            # 语义编码（只对有效消息编码）
            valid_clean_texts = [clean_texts[i] for i in valid_indices]
            per_msg_embs = encode_messages(valid_clean_texts, model_name=self.config['model_name'])
            
            # 为padding位置创建零向量
            if is_padded:
                emb_dim = per_msg_embs.shape[1]
                full_embs = np.zeros((len(processed_messages), emb_dim), dtype=np.float32)
                full_embs[valid_indices] = per_msg_embs
                per_msg_embs = full_embs
            
            # 窗口池化（不降维，后面用预训练PCA）
            win_vecs, pooled_raw, pca_obj = pool_window_embeddings_with_padding(
                per_msg_embs, [window_indices], pca_dim=99999, random_state=42, target_size=12  # 设置大数避免降维
            )
            
            # 使用预训练的PCA模型降维到48维
            pooled_features = pooled_raw[0]  # 取第一个（也是唯一的）窗口的pooled特征
            semantic_features = self.pca_model.transform([pooled_features])[0]
            
            # 确保语义特征是48维
            if len(semantic_features) != 48:
                logger.warning(f"PCA降维后维度异常: {len(semantic_features)}, 期望48维")
                if len(semantic_features) < 48:
                    semantic_features = np.pad(semantic_features, (0, 48 - len(semantic_features)))
                else:
                    semantic_features = semantic_features[:48]
            
            # 结构特征提取
            repeat_eq, repeat_sim = window_repeat_features(
                clean_texts, per_msg_embs, [window_indices], near_sim_thresh=self.config['near_sim_thresh']
            )
            code_change = window_code_change(code_hashes_per_msg, [window_indices])
            
            # 构建原始结构特征
            struct_raw = np.array([repeat_eq[0], repeat_sim[0], code_change[0]])
            
            # 使用预训练的标准化器
            struct_scaled = self.struct_scaler.transform([struct_raw])[0]
            
            # 应用结构权重
            struct_features = struct_scaled * self.config['struct_weight']
            
            # 合并特征：语义特征 (48维) + 结构特征 (3维) = 51维
            feature_vector = np.concatenate([semantic_features, struct_features])
            
            if len(feature_vector) != 51:
                logger.error(f"特征向量维度错误: {len(feature_vector)}, 期望51维")
                return None
            
            # L2标准化（与训练时保持一致）
            norm = np.linalg.norm(feature_vector)
            if norm > 0:
                feature_vector = feature_vector / norm
            
            return feature_vector
            
        except Exception as e:
            logger.error(f"核心服务特征提取失败: {e}")
            return None
    
    def _extract_features_legacy(self, user_messages: List[str], cluster_module) -> Optional[np.ndarray]:
        """
        提取消息的特征向量（简化版，与训练时保持一致）
        
        Args:
            user_messages: 用户消息
            cluster_module: 聚类分析模块
            
        Returns:
            51维特征向量 [语义48维 + 结构3维]
        """
        try:
            # 1. 语义特征提取（简化版）
            # 合并所有用户消息
            combined_text = " ".join(user_messages)
            
            # 使用sentence-transformer编码
            per_msg_embs = cluster_module.encode_messages(
                [combined_text], 
                model_name=self.config['model_name']
            )
            
            # PCA降维到48维
            semantic_features = self.pca_model.transform([per_msg_embs[0]])[0]
            
            # 确保语义特征是48维
            if len(semantic_features) != 48:
                logger.warning(f"语义特征维度异常: {len(semantic_features)}, 期望48维")
                # 如果维度不对，用零填充或截断
                if len(semantic_features) < 48:
                    semantic_features = np.pad(semantic_features, (0, 48 - len(semantic_features)))
                else:
                    semantic_features = semantic_features[:48]
            
            # 2. 结构特征提取（简化版）
            struct_features = self._extract_structural_features_simple(user_messages)
            
            # 3. 合并特征
            # 语义特征 (48维) + 结构特征 (3维) = 51维
            feature_vector = np.concatenate([semantic_features, struct_features])
            
            if len(feature_vector) != 51:
                logger.error(f"特征向量维度错误: {len(feature_vector)}, 期望51维")
                return None
            
            # L2标准化（与训练时保持一致）
            norm = np.linalg.norm(feature_vector)
            if norm > 0:
                feature_vector = feature_vector / norm
            
            return feature_vector
            
        except Exception as e:
            logger.error(f"特征提取失败: {e}")
            return None



    def _calculate_cosine_distances(self, feature_vector: np.ndarray) -> np.ndarray:
        """
        计算特征向量与各聚类中心的余弦距离
        
        Args:
            feature_vector: 51维特征向量
            
        Returns:
            与3个聚类中心的距离数组
        """
        # 计算余弦相似度
        similarities = np.dot(self.cluster_centers, feature_vector)
        
        # 转换为距离（距离 = 1 - 相似度）
        distances = 1.0 - similarities
        
        return distances

    def _fallback_classification(self, user_messages: List[str]) -> Dict[str, Any]:
        """回退分类方法"""
        logger.info("使用回退分类方法")
        
        # 简单规则：根据消息数量和内容长度判断
        total_length = sum(len(msg) for msg in user_messages)
        avg_length = total_length / len(user_messages) if user_messages else 0
        
        if avg_length > 100:
            cluster_id = 1  # 长消息可能是超进度
        elif avg_length < 30:
            cluster_id = 2  # 短消息可能是低进度
        else:
            cluster_id = 0  # 正常
        
        return {
            "cluster_id": cluster_id,
            "cluster_name": self.names_map.get(cluster_id, "未知"),
            "progress_score": self.cluster_means_progress.get(cluster_id, 0.0),
            "confidence": 0.3,  # 回退方法置信度较低
            "classification_type": "fallback",
            "message_count": len(user_messages),
            "analysis_successful": True
        }


