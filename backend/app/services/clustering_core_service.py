#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聚类核心服务：从enhanced_cluster_analysis.py提取的核心功能
移动到 app/services/ 目录
"""

import os
import re
import hashlib
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize, StandardScaler

# 设置环境变量防止TensorFlow冲突
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TRANSFORMERS_NO_FLAX"] = "1"
os.environ["USE_TF"] = "0"

# sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
except Exception as e:
    raise RuntimeError(
        "无法导入 sentence-transformers，请先安装依赖并确保未加载 TensorFlow。\n"
        f"原始错误: {e}"
    )

# ---------------------------
# 文本/代码 预处理
# ---------------------------

CODE_FENCE = re.compile(r"```.*?```", re.S)
LONG_CODE = re.compile(r"^\s*([{}();/]|#include|using|class|def|public|private|if|for|while|import)\b", re.I)

def clean_for_semantics(t: str) -> str:
    """删除大段代码/典型代码行/超长行；仅供句向量编码使用"""
    if not isinstance(t, str):
        return ""
    s = CODE_FENCE.sub(" ", t)
    lines = []
    for ln in s.splitlines():
        if len(ln) > 160:    # 超长行去掉
            continue
        if LONG_CODE.search(ln):  # 明显代码行去掉
            continue
        lines.append(ln)
    s = " ".join(lines)
    return re.sub(r"\s+", " ", s).strip()

SUSPECT_CODE = re.compile(
    r"^\s*(#include|using\s+namespace|class\s+\w+|def\s+\w+|public\s+|private\s+|if\s*\(|for\s*\(|while\s*\(|"
    r"try\s*:|except\s*:|import\s+\w+|from\s+\w+|function\s+\w+|var\s+\w+|let\s+\w+|const\s+\w+)",
    re.I
)

def extract_code_blocks(raw: str) -> List[str]:
    """优先提取 ```...``` 块；没有的话用启发式取疑似代码行"""
    if not isinstance(raw, str):
        return []
    blocks = re.findall(r"```(.*?)(?:```)", raw, flags=re.S)
    if blocks:
        return blocks
    # 启发式逐行
    lines = []
    for ln in raw.splitlines():
        if SUSPECT_CODE.search(ln) or "{" in ln or "};" in ln or ln.strip().endswith(";"):
            lines.append(ln)
    return ["\n".join(lines)] if lines else []

COMMENT_LINE = re.compile(r"^\s*(//|#|--).*$")
COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.S)

def normalize_code(code: str) -> str:
    """去注释/空行/多余空白，统一小写，便于稳定哈希"""
    if not isinstance(code, str):
        return ""
    c = COMMENT_BLOCK.sub(" ", code)
    norm_lines = []
    for ln in c.splitlines():
        if COMMENT_LINE.match(ln):
            continue
        ln = re.sub(r"\s+", " ", ln).strip()
        if ln:
            norm_lines.append(ln.lower())
    return "\n".join(norm_lines)

def md5_hash(s: str) -> str:
    return hashlib.md5(s.encode("utf-8", errors="ignore")).hexdigest()

def preprocess_messages(raw_msgs: List[str]) -> Tuple[List[str], List[List[str]]]:
    """为每条消息：先抽代码→归一化→哈希；再清洗文本供语义通道"""
    clean_texts: List[str] = []
    code_hashes_per_msg: List[List[str]] = []
    for raw in raw_msgs:
        blocks = extract_code_blocks(raw)
        hashes = []
        for b in blocks:
            nb = normalize_code(b)
            if nb:
                hashes.append(md5_hash(nb))
        code_hashes_per_msg.append(hashes)
        clean_texts.append(clean_for_semantics(raw))
    return clean_texts, code_hashes_per_msg

# ---------------------------
# 滑动窗口
# ---------------------------

def create_windows(n_msgs: int, batch_size: int, overlap: int) -> List[List[int]]:
    """严格满窗：size=batch_size，步长=batch_size-overlap"""
    assert 0 <= overlap < batch_size
    stride = batch_size - overlap
    return [list(range(s, s + batch_size)) for s in range(0, n_msgs - batch_size + 1, stride)]

# ---------------------------
# 语义通道：句向量 + 窗口池化 + PCA/L2
# ---------------------------

def encode_messages(clean_texts: List[str],
                    model_name: str = "sentence-transformers/all-mpnet-base-v2",
                    device: str = "cpu",
                    batch_size: int = 64) -> np.ndarray:
    print(f"[encoder] Loading SentenceTransformer: {model_name}")
    model = SentenceTransformer(model_name, device=device)
    try:
        dim = model.get_sentence_embedding_dimension()
    except Exception:
        dim = None
    print(f"[encoder] embedding_dim = {dim}")
    embs = model.encode(clean_texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(embs, dtype=np.float32)

def pool_window_embeddings_with_padding(per_msg_embs: np.ndarray,
                                       windows: List[List[int]],
                                       pca_dim: int = 64,
                                       random_state: int = 42,
                                       target_size: int = 12) -> Tuple[np.ndarray, np.ndarray, PCA]:
    """
    对每个窗口：从消息嵌入中取出 → [mean ⊕ std] 池化（支持padding mask） → PCA→pca_dim → L2
    
    Args:
        per_msg_embs: 消息嵌入 (N, D)
        windows: 窗口索引列表
        pca_dim: PCA降维目标维度
        random_state: 随机种子
        target_size: 目标窗口大小（用于padding）
    
    Returns:
        window_vecs (M, pca_dim), pooled_raw (M, 2D_raw), pca_obj
    """
    pooled = []
    for idxs in windows:
        # 获取真实消息的嵌入
        valid_embs = per_msg_embs[idxs]  # (actual_size, D)
        
        # 如果窗口小于目标大小，需要考虑padding，但不实际pad向量
        # 只对真实消息做池化
        mu = valid_embs.mean(axis=0)  # 只对有效消息求均值
        sd = valid_embs.std(axis=0)   # 只对有效消息求标准差
        
        pooled.append(np.concatenate([mu, sd], axis=0))
    
    pooled_raw = np.vstack(pooled)  # (M, 2D_raw)
    
    # PCA→pca_dim（确保n_components不超过样本数量）
    n_samples = pooled_raw.shape[0]  # 窗口数量
    n_features = pooled_raw.shape[1]  # 特征维度
    
    # n_components必须 <= min(n_samples, n_features)
    max_components = min(n_samples, n_features)
    k = min(pca_dim, max_components)
    k = max(1, k)  # 至少1个成分
    
    if k >= max_components and max_components > 0:
        # 如果无需降维或无法降维，直接返回原始特征
        Z = normalize(pooled_raw)
        pca = None  # 无PCA对象
    else:
        pca = PCA(n_components=k, random_state=random_state)
        Z = pca.fit_transform(pooled_raw)
        Z = normalize(Z)  # 行向量单位化 → 余弦几何
    
    return Z.astype(np.float32), pooled_raw.astype(np.float32), pca

# ---------------------------
# 结构特征（窗口内/邻近）
# ---------------------------

def window_repeat_features(clean_texts: List[str],
                           per_msg_embs: np.ndarray,
                           windows: List[List[int]],
                           near_sim_thresh: float = 0.95) -> Tuple[np.ndarray, np.ndarray]:
    """窗口内重复：完全重复率 & 相邻高相似比例（余弦≥near_sim_thresh）"""
    repeat_eq = []
    repeat_sim = []

    for idxs in windows:
        # 只考虑有效消息，padding不参与计算
        valid_texts = [clean_texts[i].lower() for i in idxs if i < len(clean_texts) and clean_texts[i].strip()]
        total = len(valid_texts)
        uniq = len(set(valid_texts))
        repeat_eq.append(1.0 - (uniq / max(1, total)))

        sim_cnt = 0
        pair_cnt = 0
        valid_embs = per_msg_embs[idxs]  # 只取有效索引的嵌入
        if valid_embs.shape[0] >= 2:
            for a, b in zip(valid_embs[:-1], valid_embs[1:]):
                pair_cnt += 1
                if float(np.dot(a, b)) >= near_sim_thresh:
                    sim_cnt += 1
        repeat_sim.append((sim_cnt / pair_cnt) if pair_cnt else 0.0)

    return np.array(repeat_eq, dtype=np.float32), np.array(repeat_sim, dtype=np.float32)

def window_code_change(code_hashes_per_msg: List[List[str]],
                       windows: List[List[int]]) -> np.ndarray:
    """窗口内代码变化率：不同哈希/总哈希；无代码给 0.5 中性值；padding不参与计算"""
    rates = []
    for idxs in windows:
        # 只考虑有效消息的代码哈希
        hashes = [h for i in idxs if i < len(code_hashes_per_msg) for h in code_hashes_per_msg[i]]
        if not hashes:
            rates.append(0.5)
        else:
            rates.append(len(set(hashes)) / float(len(hashes)))
    return np.array(rates, dtype=np.float32)

# ---------------------------
# 仅用于"打标"的词典
# ---------------------------

ANY_ERROR_Q = re.compile(r"\b(any|is there|does.*have|are there)\b.*\b(error|bug|issue|problem)\b\??", re.I)
DONE = {"complete","completed","finish","finished","pass","passed","accept","accepted",
        "solved","resolve","resolved","fix","fixed","merge","merged","success","successfully","ok","ac"}
STUCK = {"error","errors","failed","fail","stuck","bug","exception","timeout","timed out","crash","cannot","not working"}

def done_stuck_counts(window_docs: List[str]) -> Tuple[np.ndarray, np.ndarray]:
    """计算窗口文档中的done和stuck关键词数量"""
    done_hits, stuck_hits = [], []
    for doc in window_docs:
        low = (doc or "").lower()
        d = sum(w in low for w in DONE)
        s = sum(w in low for w in STUCK)
        if ANY_ERROR_Q.search(low):
            s = max(0, s - 1)  # 探测式问题豁免
        done_hits.append(d)
        stuck_hits.append(s)
    return np.array(done_hits, dtype=np.float32), np.array(stuck_hits, dtype=np.float32)

def progress_score_from_proxies(repeat_eq: np.ndarray,
                                repeat_sim: np.ndarray,
                                code_change: np.ndarray,
                                done_hits: np.ndarray,
                                stuck_hits: np.ndarray,
                                cw_persist: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    返回：Z(6维代理的zscore)，progress_score（越大越"超进度"）
    这里计算的是窗口自己的进度分数，不是簇中心的分数
    """
    M = np.column_stack([repeat_eq, repeat_sim, code_change, done_hits, stuck_hits, cw_persist]).astype(np.float32)
    mu, sg = M.mean(axis=0), M.std(axis=0) + 1e-8
    Z = (M - mu) / sg
    ps = (+0.6 * Z[:, 3]      # done
          -0.4 * Z[:, 4]      # stuck
          -0.5 * Z[:, 1]      # repeat_sim
          -0.3 * Z[:, 0]      # repeat_eq
          +0.3 * Z[:, 2]      # code_change
          -0.4 * Z[:, 5])     # cw_persist
    return Z, ps.astype(np.float32)

# ---------------------------
# 辅助函数
# ---------------------------

def pad_messages_for_window(user_messages: List[str], target_size: int = 12, min_size: int = 1) -> Tuple[List[str], List[int], bool]:
    """
    为消息列表进行padding以达到目标窗口大小
    重要：必须严格保持窗口大小和预训练模型一致（12条消息）
    
    Args:
        user_messages: 原始用户消息列表
        target_size: 目标窗口大小（必须和预训练模型一致，默认12）
        min_size: 最小消息数量要求（至少1条才有意义）
    
    Returns:
        padded_messages: 总是target_size长度的消息列表
        valid_indices: 有效消息的索引列表
        is_padded: 是否进行了padding
    """
    if len(user_messages) < min_size:
        raise ValueError(f"消息数量不足最小要求：{len(user_messages)} < {min_size}")
    
    if len(user_messages) >= target_size:
        # 消息数量足够，取最近的target_size条
        recent_messages = user_messages[-target_size:]
        valid_indices = list(range(len(recent_messages)))
        return recent_messages, valid_indices, False
    
    # 总是padding到target_size，保持和预训练模型一致
    pad_count = target_size - len(user_messages)
    # 使用占位符进行padding（但在embedding时会被mask掉）
    padded_messages = user_messages + [f"[PAD_{i}]" for i in range(pad_count)]
    valid_indices = list(range(len(user_messages)))  # 只有原始消息是有效的
    
    return padded_messages, valid_indices, True

def create_single_window_from_messages(user_messages: List[str], 
                                     target_size: int = 12, 
                                     min_size: int = 1) -> Tuple[List[int], List[str], List[int], bool]:
    """
    从用户消息创建单个窗口
    重要：严格保持和预训练模型一致的窗口大小（12条消息）
    
    Args:
        user_messages: 用户消息列表
        target_size: 窗口大小（必须和预训练模型一致）
        min_size: 最小消息数量（至少1条）
    
    Returns:
        window_indices: 窗口索引（总是[0,1,2,...,11]）
        processed_messages: 处理后的消息（总是12条，可能包含padding）
        valid_indices: 有效消息索引（真实消息的索引）
        is_padded: 是否进行了padding
    """
    processed_messages, valid_indices, is_padded = pad_messages_for_window(user_messages, target_size, min_size)
    window_indices = list(range(len(processed_messages)))  # 总是[0,1,2,...,target_size-1]
    
    return window_indices, processed_messages, valid_indices, is_padded
