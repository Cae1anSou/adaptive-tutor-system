# backend/app/services/progress_clustering_service.py
"""
进度聚类分析服务（在线分配版）
- 使用预训练资产进行在线簇分配：struct_scaler.joblib、clustering_pca.joblib、(可选) cluster_centers.joblib、label_map.json
- 流程：消息 → 滑动窗口缓冲 → 结构特征+语义向量 → 标准化/加权 → L2 → 预训练PCA → L2 → 最近簇/阈值 → 输出
- 不进行重新聚类。
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from datetime import datetime

# 设置环境变量，避免TensorFlow相关警告
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TRANSFORMERS_NO_FLAX"] = "1"
os.environ["USE_TF"] = "0"

logger = logging.getLogger(__name__)


class ProgressClusteringService:
    """进度聚类分析服务（在线分配）"""

    def __init__(
        self,
        batch_size: int = 12,
        overlap: int = 10,  # 步长=2，更及时
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        semantic_weight: float = 0.2,
        structural_weight: float = 0.8,
        lookback: int = 3,
        use_pretrained_models: bool = True,
        assets_dir: Optional[str] = r"e:\adaptive-tutor-system\cluster_output_try1",
    ):
        self.batch_size = batch_size
        self.overlap = overlap
        self.model_name = model_name
        self.semantic_weight = semantic_weight
        self.structural_weight = structural_weight
        self.lookback = lookback
        self.use_pretrained_models = use_pretrained_models
        # 预训练资产路径
        self.assets_dir = assets_dir

        # 运行期缓存
        self._asset_loaded = False
        self._struct_scaler: Optional[Dict[str, Any]] = None
        self._pca: Optional[Dict[str, Any]] = None
        self._centers: Optional[np.ndarray] = None
        self._label_map: Dict[int, str] = {}
        self._cluster_order_by_progress: Optional[List[int]] = None

        # 句嵌入后端
        self._sem_backend = None

        # 结果缓存
        self._clustering_cache: Dict[str, Dict[str, Any]] = {}

        logger.info(
            f"ProgressClusteringService online initialized: batch_size={batch_size}, overlap={overlap}, weights(s={semantic_weight}, t={structural_weight}), assets={assets_dir}"
        )

    def _ensure_assets(self):
        if self._asset_loaded or not self.use_pretrained_models:
            return
        if not self.assets_dir:
            logger.warning("No assets_dir configured; will run without pretrained assets")
            self._asset_loaded = True
            return
        try:
            from joblib import load
        except Exception as e:
            logger.error(f"joblib import failed: {e}")
            raise

        # struct scaler
        scaler_path = os.path.join(self.assets_dir, "struct_scaler.joblib")
        if os.path.exists(scaler_path):
            try:
                self._struct_scaler = load(scaler_path)
                logger.info(f"Loaded struct_scaler from {scaler_path}")
            except Exception as e:
                logger.warning(f"Load struct_scaler failed: {e}")
                self._struct_scaler = None
        else:
            logger.warning(f"struct_scaler.joblib not found in {self.assets_dir}")

        # clustering PCA
        pca_path = os.path.join(self.assets_dir, "clustering_pca.joblib")
        if os.path.exists(pca_path):
            try:
                self._pca = load(pca_path)
                logger.info(f"Loaded clustering_pca from {pca_path}")
            except Exception as e:
                logger.warning(f"Load clustering_pca failed: {e}")
                self._pca = None
        else:
            logger.warning(f"clustering_pca.joblib not found in {self.assets_dir}")

        # optional centers
        centers_path = os.path.join(self.assets_dir, "cluster_centers.joblib")
        if os.path.exists(centers_path):
            try:
                self._centers = load(centers_path)
                logger.info(f"Loaded cluster_centers from {centers_path}")
            except Exception as e:
                logger.warning(f"Load cluster_centers failed: {e}")
                self._centers = None
        else:
            # 允许无中心：将采用进度分数阈值法
            logger.warning(f"cluster_centers.joblib not found in {self.assets_dir}; fallback to progress-threshold assignment")

        # label map (优先)，否则基于cluster_report.json均值推断顺序
        lm_path = os.path.join(self.assets_dir, "label_map.json")
        if os.path.exists(lm_path):
            try:
                lm = json.load(open(lm_path, "r", encoding="utf-8"))
                self._label_map = {int(k): str(v) for k, v in lm.items()}
                logger.info(f"Loaded label_map from {lm_path}: {self._label_map}")
            except Exception as e:
                logger.warning(f"Load label_map.json failed: {e}")
                self._label_map = {}
        else:
            # 从报告中读取簇均值，按升序推断 低进度/正常/超进度
            report_path = os.path.join(self.assets_dir, "cluster_report.json")
            means_order = None
            try:
                if os.path.exists(report_path):
                    rep = json.load(open(report_path, "r", encoding="utf-8"))
                    means: Dict[str, float] = rep.get("cluster_mean_progress") or {}
                    if means:
                        pairs = sorted(((int(k), float(v)) for k, v in means.items()), key=lambda kv: kv[1])
                        means_order = [cid for cid, _ in pairs]
                        # 默认中文命名
                        default_names = ["低进度", "正常", "超进度"]
                        self._label_map = {cid: (default_names[i] if i < len(default_names) else f"Cluster-{cid}") for i, cid in enumerate(means_order)}
                        logger.info(f"Inferred label_map from cluster_report means: {self._label_map}")
                        self._cluster_order_by_progress = means_order
            except Exception as e:
                logger.warning(f"Failed to infer label map from cluster_report.json: {e}")

        # 语义后端延迟加载
        self._asset_loaded = True

    def _get_sem_backend(self):
        if self._sem_backend is not None:
            return self._sem_backend
        # 直接复用增强版脚本中的后端，若不可用自动回退哈希
        try:
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
            from enhanced_cluster_analysis import SemanticBackend
            self._sem_backend = SemanticBackend(mode="st", model_name=self.model_name)
        except Exception as e:
            logger.warning(f"Semantic backend init failed: {e}; fallback to hash backend")
            from types import SimpleNamespace
            class _HashOnly:
                def __init__(self):
                    pass
                def encode(self, texts: List[str]) -> np.ndarray:
                    # 简单回退（与脚本一致的hash_features实现略过，直接零向量占位避免引入重复代码）
                    return np.zeros((len(texts), 1), dtype=np.float32)
            self._sem_backend = _HashOnly()
        return self._sem_backend

    def _windowing(self, n: int) -> List[List[int]]:
        # 与增强脚本一致的窗口策略
        step = max(1, self.batch_size - self.overlap)
        starts = list(range(0, max(1, n - self.batch_size + 1), step))
        windows = [list(range(s, min(n, s + self.batch_size))) for s in starts]
        if windows:
            last_end = windows[-1][-1]
            if last_end < n - 1:
                tail = list(range(max(0, n - self.batch_size), n))
                if windows[-1] != tail:
                    windows.append(tail)
        else:
            windows = [list(range(0, n))]
        return windows

    def _extract_features(self, messages: List[str]) -> Tuple[Dict[str, Any], np.ndarray, List[List[int]]]:
        """返回: feat_df(dict-like), sem_emb(np.ndarray), windows"""
        # 复用增强脚本的特征计算，避免重写
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
        from enhanced_cluster_analysis import (
            default_lexicon, build_regexes, FeatureConfig,
            features_for_windows, build_semantic_matrix
        )
        windows = self._windowing(len(messages))
        lex = default_lexicon()
        regexes = build_regexes(lex)
        cfg = FeatureConfig(max_lines=12, semantic_weight=self.semantic_weight, structural_weight=self.structural_weight)
        feat_df, excerpts = features_for_windows(messages, windows, regexes, cfg)
        sem = build_semantic_matrix(excerpts, self._get_sem_backend())
        # 将DataFrame转换为dict-列访问友好的形式（保持列顺序）
        feat_dict = {col: feat_df[col].tolist() for col in feat_df.columns}
        return feat_dict, sem.astype(np.float32), windows

    def _combine_apply_pca(self, sem: np.ndarray, feat: Dict[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
        """按训练时scaler列做标准化+加权，L2+PCA+L2，返回聚类空间X_for。"""
        if not self._struct_scaler or "feature_names" not in self._struct_scaler:
            raise RuntimeError("struct_scaler missing or invalid; cannot proceed online assignment")
        struct_cols: List[str] = list(self._struct_scaler["feature_names"])  # 训练时顺序
        Smu = np.asarray(self._struct_scaler.get("mean"), dtype=np.float32)
        Ssig = np.asarray(self._struct_scaler.get("std"), dtype=np.float32)
        # 构造 S 按列
        S = np.stack([np.asarray(feat[c], dtype=np.float32) for c in struct_cols], axis=1)
        Szn = (S - Smu) / (Ssig + 1e-6)
        # 组合并加权
        X_raw = np.hstack([sem * float(self.semantic_weight), Szn * float(self.structural_weight)]).astype(np.float32)
        # L2
        Xn = self._l2_rows(X_raw)
        # PCA 变换（若存在）
        if self._pca and isinstance(self._pca, dict) and "components" in self._pca and "mean" in self._pca:
            W = np.asarray(self._pca["components"], dtype=np.float32)  # shape: D x k
            mu = np.asarray(self._pca["mean"], dtype=np.float32)       # shape: D
            # 在训练保存的是 W = VT[:k].T (D x k)
            Xc = Xn - mu.reshape(1, -1)
            Z = Xc @ W
            X_for = self._l2_rows(Z)
        else:
            X_for = Xn
        return X_for, {"struct_cols": struct_cols}

    @staticmethod
    def _l2_rows(A: np.ndarray, eps: float = 1e-9) -> np.ndarray:
        n = np.linalg.norm(A, axis=1, keepdims=True)
        return A / np.maximum(n, eps)

    def _assign_labels(self, X_for: np.ndarray, feat: Dict[str, Any]) -> Tuple[np.ndarray, List[str], List[float]]:
        """返回: labels(np.ndarray[int]), named_labels(List[str]), confidences(List[float])"""
        n = X_for.shape[0]
        if self._centers is not None and isinstance(self._centers, np.ndarray) and self._centers.size > 0:
            # 最近中心
            C = self._centers.astype(np.float32)
            d2 = ((X_for[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
            labels = d2.argmin(axis=1).astype(int)
            sims = (1.0 / (1.0 + d2.min(axis=1))).astype(float).tolist()
            # 命名
            named = [self._label_map.get(int(cid), f"Cluster-{int(cid)}") for cid in labels]
            return labels, named, sims
        else:
            # 进度阈值法：使用训练的簇均值排序确定三段阈值
            prog = np.asarray(feat.get("progress_score", [0.0] * n), dtype=np.float32)
            order = self._cluster_order_by_progress
            if not order or len(order) < 3:
                # 若不可用，按固定分段
                thresholds = [-0.15, 0.15]
                cluster_ids = [0, 1, 2]
            else:
                # 读取训练均值作为锚点
                # 从 cluster_report.json 已经设置了 order
                # 我们取三段中值作为边界（简单法）：(-inf, t1], (t1, t2], (t2, +inf)
                # 由于我们没有具体数值，这里采用经验边界
                thresholds = [-0.15, 0.15]
                cluster_ids = order  # 保持排序后的ID映射
            labels_arr = np.zeros(n, dtype=int)
            labels_arr[prog <= thresholds[0]] = cluster_ids[0]
            labels_arr[(prog > thresholds[0]) & (prog <= thresholds[1])] = cluster_ids[1]
            labels_arr[prog > thresholds[1]] = cluster_ids[2]
            # 置信度：距离最近边界的归一化值
            d_to_edges = np.minimum(np.abs(prog - thresholds[0]), np.abs(prog - thresholds[1]))
            conf = np.clip((d_to_edges / 0.6), 0.0, 1.0).astype(float).tolist()
            named = [self._label_map.get(int(cid), f"Cluster-{int(cid)}") for cid in labels_arr]
            return labels_arr, named, conf

    def analyze_conversation_progress(self, conversation_history: List[Dict[str, str]], participant_id: str) -> Dict[str, Any]:
        """对话进度分析（在线分配）"""
        try:
            self._ensure_assets()
            messages = [m.get("content", "") for m in conversation_history if isinstance(m, dict) and m.get("content")]
            if len(messages) < self.batch_size:
                logger.info(f"Insufficient messages for online assignment: {len(messages)} < batch_size={self.batch_size}")
                return self._get_default_result()

            feat, sem, windows = self._extract_features(messages)
            X_for, meta = self._combine_apply_pca(sem, feat)
            labels, named, confidences = self._assign_labels(X_for, feat)

            # 聚合输出
            result = {
                "participant_id": participant_id,
                "analysis_timestamp": datetime.now().isoformat(),
                "message_count": len(messages),
                "window_count": len(windows),
                "windows": windows,
                "labels": labels.tolist() if hasattr(labels, "tolist") else list(map(int, labels)),
                "named_labels": named,
                "progress_score": feat.get("progress_score", []),
                "starts": feat.get("start_idx", []),
                "ends": feat.get("end_idx", []),
                "confidence": confidences,
            }
            # 缓存
            self._clustering_cache[participant_id] = result
            return result
        except Exception as e:
            logger.error(f"Error in online progress assignment: {e}")
            return self._get_default_result()

    def get_current_progress_state(self, participant_id: str) -> Tuple[str, float]:
        """获取当前窗口的状态及置信度"""
        if participant_id not in self._clustering_cache:
            return "正常", 0.0
        res = self._clustering_cache[participant_id]
        named = res.get("named_labels", [])
        confs = res.get("confidence", [])
        if not named:
            return "正常", 0.0
        return named[-1], (confs[-1] if confs else 0.0)

    def get_progress_summary(self, participant_id: str) -> Dict[str, Any]:
        if participant_id not in self._clustering_cache:
            return {"current_state": "正常", "confidence": 0.0, "trend": "stable", "recommendations": []}
        res = self._clustering_cache[participant_id]
        named = res.get("named_labels", [])
        prog = res.get("progress_score", [])
        if len(named) < 2:
            return {"current_state": (named[-1] if named else "正常"), "confidence": 0.0, "trend": "stable", "recommendations": []}
        recent_scores = prog[-3:] if prog else []
        if len(recent_scores) >= 2:
            delta = recent_scores[-1] - recent_scores[0]
            if delta > 0.5:
                trend = "improving"
            elif delta < -0.5:
                trend = "worsening"
            else:
                trend = "stable"
        else:
            trend = "stable"
        return {"current_state": named[-1], "confidence": 0.0, "trend": trend, "recommendations": []}

    def _get_default_result(self) -> Dict[str, Any]:
        return {
            "participant_id": None,
            "analysis_timestamp": datetime.now().isoformat(),
            "message_count": 0,
            "window_count": 0,
            "windows": [],
            "labels": [],
            "named_labels": [],
            "progress_score": [],
            "starts": [],
            "ends": [],
            "confidence": []
        }


# 单例
progress_clustering_service = ProgressClusteringService()
