# backend/app/services/progress_clustering_service.py
"""
进度聚类分析服务
集成enhanced_cluster_analysis.py中的算法，提供实时聚类分析功能
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta

# 设置环境变量，避免TensorFlow相关警告
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TRANSFORMERS_NO_FLAX"] = "1"
os.environ["USE_TF"] = "0"

# 导入聚类算法相关模块
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import normalize, StandardScaler
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
except ImportError as e:
    logging.error(f"Failed to import clustering dependencies: {e}")
    raise

logger = logging.getLogger(__name__)


class ProgressClusteringService:
    """进度聚类分析服务"""
    
    def __init__(self, 
                 batch_size: int = 12,
                 overlap: int = 4,
                 model_name: str = "sentence-transformers/all-mpnet-base-v2",
                 pca_dim: int = 64,
                 lookback: int = 2,
                 near_sim_thresh: float = 0.92,
                 include_struct: bool = True,
                 struct_weight: float = 1.5,
                 n_init: int = 200,
                 max_iter: int = 1000,
                 use_pretrained_models: bool = True):
        """
        初始化聚类服务
        
        Args:
            batch_size: 滑动窗口大小
            overlap: 窗口重叠大小
            model_name: 句向量模型名称
            pca_dim: PCA降维维度
            lookback: 回看窗口数
            near_sim_thresh: 高相似度阈值
            include_struct: 是否包含结构特征
            struct_weight: 结构特征权重
            n_init: KMeans初始化次数
            max_iter: KMeans最大迭代次数
            use_pretrained_models: 是否使用预训练模型
        """
        self.batch_size = batch_size
        self.overlap = overlap
        self.model_name = model_name
        self.pca_dim = pca_dim
        self.lookback = lookback
        self.near_sim_thresh = near_sim_thresh
        self.include_struct = include_struct
        self.struct_weight = struct_weight
        self.n_init = n_init
        self.max_iter = max_iter
        self.use_pretrained_models = use_pretrained_models
        
        # 预训练模型路径
        self.pretrained_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'out_struct_dim48_w1p5_t0921')
        
        # 初始化句向量模型
        self._model = None
        self._model_loaded = False
        
        # 聚类结果缓存
        self._clustering_cache = {}
        
        logger.info(f"ProgressClusteringService initialized with batch_size={batch_size}, overlap={overlap}, include_struct={include_struct}, struct_weight={struct_weight}")
    
    def analyze_conversation_progress(self, 
                                    conversation_history: List[Dict[str, str]],
                                    participant_id: str) -> Dict[str, Any]:
        """
        分析对话进度
        
        Args:
            conversation_history: 对话历史，格式为 [{"role": "user/assistant", "content": "消息内容"}]
            participant_id: 参与者ID
            
        Returns:
            聚类分析结果
        """
        if not conversation_history or len(conversation_history) < self.batch_size:
            logger.info(f"Insufficient conversation history for clustering: {len(conversation_history)} messages")
            return self._get_default_result()
        
        try:
            # 提取消息内容
            messages = [msg["content"] for msg in conversation_history if msg.get("content", "").strip()]
            
            if len(messages) < self.batch_size:
                logger.info(f"Insufficient messages for clustering: {len(messages)} messages")
                return self._get_default_result()
            
            # 执行聚类分析
            result = self._perform_clustering(messages)
            
            # 添加元数据
            result.update({
                "participant_id": participant_id,
                "analysis_timestamp": datetime.now().isoformat(),
                "message_count": len(messages),
                "window_count": len(result.get("windows", []))
            })
            
            # 缓存结果
            self._clustering_cache[participant_id] = result
            
            logger.info(f"Clustering analysis completed for {participant_id}: {result.get('named_labels', [])}")
            return result
            
        except Exception as e:
            logger.error(f"Error in conversation progress analysis: {e}")
            return self._get_default_result()
    
    def _perform_clustering(self, messages: List[str]) -> Dict[str, Any]:
        """执行聚类分析"""
        try:
            # 导入聚类算法
            import sys
            import os
            from joblib import load
            
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            from app.services.enhanced_cluster_analysis import progress_clustering_pipeline
            
            # 检查是否使用预训练模型
            pca_obj = None
            scaler_obj = None
            
            if self.use_pretrained_models:
                pca_path = os.path.join(self.pretrained_dir, 'pca.joblib')
                scaler_path = os.path.join(self.pretrained_dir, 'struct_scaler.joblib')
                
                if os.path.exists(pca_path) and os.path.exists(scaler_path):
                    try:
                        pca_obj = load(pca_path)
                        scaler_obj = load(scaler_path)
                        logger.info("Loaded pretrained PCA and StandardScaler models")
                    except Exception as e:
                        logger.warning(f"Failed to load pretrained models: {e}")
                        pca_obj = None
                        scaler_obj = None
                else:
                    logger.warning(f"Pretrained model files not found: {pca_path}, {scaler_path}")
            
            # 调用聚类算法
            result = progress_clustering_pipeline(
                raw_msgs=messages,
                batch_size=self.batch_size,
                overlap=self.overlap,
                model_name=self.model_name,
                pca_dim=self.pca_dim,
                include_struct_in_clustering=self.include_struct,
                lookback=self.lookback,
                n_init=self.n_init,
                max_iter=self.max_iter,
                struct_weight=self.struct_weight,
                near_sim_thresh=self.near_sim_thresh,
                pca_obj=pca_obj,
                scaler_obj=scaler_obj
            )
            
            # 转换numpy数组为列表以便JSON序列化
            for key in ['labels', 'centers', 'sims', 'repeat_eq', 'repeat_sim', 'code_change', 
                       'cw_persist', 'done_hits', 'stuck_hits', 'Z_proxy', 'progress_score', 'named_labels']:
                if key in result and isinstance(result[key], np.ndarray):
                    result[key] = result[key].tolist()
            
            return result
            
        except Exception as e:
            logger.error(f"Error in clustering algorithm: {e}")
            return self._get_default_result()
    
    def get_current_progress_state(self, participant_id: str) -> Tuple[str, float]:
        """
        获取当前进度状态
        
        Args:
            participant_id: 参与者ID
            
        Returns:
            (进度状态, 置信度)
        """
        if participant_id not in self._clustering_cache:
            return "正常", 0.0
        
        result = self._clustering_cache[participant_id]
        named_labels = result.get("named_labels", [])
        progress_score = result.get("progress_score", [])
        
        if not named_labels or not progress_score:
            return "正常", 0.0
        
        # 获取最新的窗口状态
        current_state = named_labels[-1] if named_labels else "正常"
        current_score = progress_score[-1] if progress_score else 0.0
        
        # 计算置信度（基于进度分数的绝对值）
        confidence = min(1.0, abs(current_score) / 2.0)
        
        return current_state, confidence
    
    def get_progress_summary(self, participant_id: str) -> Dict[str, Any]:
        """
        获取进度摘要
        
        Args:
            participant_id: 参与者ID
            
        Returns:
            进度摘要信息
        """
        if participant_id not in self._clustering_cache:
            return {
                "current_state": "正常",
                "confidence": 0.0,
                "trend": "stable",
                "recommendations": []
            }
        
        result = self._clustering_cache[participant_id]
        named_labels = result.get("named_labels", [])
        progress_score = result.get("progress_score", [])
        
        if len(named_labels) < 2:
            return {
                "current_state": named_labels[-1] if named_labels else "正常",
                "confidence": 0.0,
                "trend": "stable",
                "recommendations": []
            }
        
        # 分析趋势
        recent_labels = named_labels[-3:]  # 最近3个窗口
        recent_scores = progress_score[-3:]  # 最近3个分数
        
        # 判断趋势
        if len(recent_scores) >= 2:
            score_trend = recent_scores[-1] - recent_scores[0]
            if score_trend > 0.5:
                trend = "improving"
            elif score_trend < -0.5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "current_state": named_labels[-1] if named_labels else "正常",
            "confidence": min(1.0, abs(progress_score[-1]) / 2.0) if progress_score else 0.0,
            "trend": trend,
            "recent_progress_scores": recent_scores,
            "window_count": len(named_labels)
        }
    
    def _get_default_result(self) -> Dict[str, Any]:
        """获取默认结果"""
        return {
            "participant_id": "",
            "analysis_timestamp": datetime.now().isoformat(),
            "message_count": 0,
            "window_count": 0,
            "labels": [],
            "named_labels": [],
            "progress_score": [],
            "names_map": {},
            "cluster_means": {},
            "current_progress_state": "正常",
            "confidence": 0.0
        }
    



# 创建单例实例
progress_clustering_service = ProgressClusteringService()
