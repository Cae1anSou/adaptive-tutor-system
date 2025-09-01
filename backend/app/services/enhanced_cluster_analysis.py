# -*- coding: utf-8 -*-
"""
增强版进度三聚类核心（计算机学生英文技术对话）
- 语义通道：all-mpnet-base-v2 → mean+std → PCA→dim → L2
- 结构通道：窗口内重复/相邻高相似/代码变化 + 邻近窗口持续性
- 聚类：KMeans(k=3) in cosine space（L2后欧式≈余弦）
- 打标：仅用于命名的进度代理分（done/stuck/重复/变化/持续）
"""

import os
# 禁止 transformers 触发 TensorFlow/Flax
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TRANSFORMERS_NO_FLAX"] = "1"
os.environ["USE_TF"] = "0"

import re
import json
import glob
import hashlib
from typing import List, Tuple, Dict, Any, Optional

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize, StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
except Exception as e:
    raise RuntimeError(
        "无法导入 sentence-transformers，请先安装依赖并确保未加载 TensorFlow。\n"
        "pip install -U torch 'transformers==4.41.2' 'sentence-transformers==2.6.1' safetensors\n"
        f"原始错误: {e}"
    )

# ---------------------------
# JSON 加载（只取 data[*].translated_text）
# ---------------------------

def load_prompts_from_dir(path: str) -> List[str]:
    """
    从【目录 或 单个 .json 文件】加载要聚类的文本：
      - 仅提取 data[*].translated_text （按文件内顺序）
    """
    texts: List[str] = []

    def _ingest_file(fp: str):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                obj = json.load(f)
        except Exception as e:
            print(f"[WARN] 读取或解析失败，跳过：{fp} ({e})")
            return

        if isinstance(obj, dict) and isinstance(obj.get("data"), list):
            for item in obj["data"]:
                if isinstance(item, dict):
                    t = item.get("translated_text")
                    # if item.get("translation_status") != "success": continue
                    if isinstance(t, str) and t.strip():
                        texts.append(t.strip())
        else:
            print(f"[WARN] 文件结构不含 data[*].translated_text，跳过：{fp}")

    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "*.json")))
        for fp in files:
            _ingest_file(fp)
    elif os.path.isfile(path) and path.lower().endswith(".json"):
        _ingest_file(path)
    else:
        raise ValueError(f"路径既不是目录也不是 .json 文件：{path}")

    print(f"[loader] 从 {path} 解析得到 translated_text 共 {len(texts)} 条")
    return texts


# ---------------------------
# 文本/代码 预处理
# ---------------------------

CODE_FENCE = re.compile(r"```.*?```", re.S)
LONG_CODE  = re.compile(r"^\s*([{}();/]|#include|using|class|def|public|private|if|for|while|import)\b", re.I)

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


def pool_window_embeddings(per_msg_embs: np.ndarray,
                           windows: List[List[int]],
                           pca_dim: int = 64,
                           random_state: int = 42,
                           pca_obj: Optional[PCA] = None) -> Tuple[np.ndarray, np.ndarray, PCA]:
    """
    对每个窗口：从消息嵌入中取出 → [mean ⊕ std] 池化 → PCA→pca_dim → L2
    返回：window_vecs (M, pca_dim), pooled_raw (M, 2D_raw), pca_obj
    """
    pooled = []
    for idxs in windows:
        W = per_msg_embs[idxs]  # (batch, D)
        mu = W.mean(axis=0)
        sd = W.std(axis=0)
        pooled.append(np.concatenate([mu, sd], axis=0))
    pooled_raw = np.vstack(pooled)  # (M, 2D_raw)
    # PCA→pca_dim
    if pca_obj is not None:
        # 使用预训练的PCA模型
        pca = pca_obj
        Z = pca.transform(pooled_raw)
    else:
        # 训练新的PCA模型
        k = max(2, min(pca_dim, pooled_raw.shape[1], len(windows) - 1))
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
        texts = [clean_texts[i].lower() for i in idxs if clean_texts[i].strip()]
        total = len(texts)
        uniq = len(set(texts))
        repeat_eq.append(1.0 - (uniq / max(1, total)))

        sim_cnt = 0
        pair_cnt = 0
        W = per_msg_embs[idxs]
        if W.shape[0] >= 2:
            for a, b in zip(W[:-1], W[1:]):
                pair_cnt += 1
                if float(np.dot(a, b)) >= near_sim_thresh:
                    sim_cnt += 1
        repeat_sim.append((sim_cnt / pair_cnt) if pair_cnt else 0.0)

    return np.array(repeat_eq, dtype=np.float32), np.array(repeat_sim, dtype=np.float32)


def window_code_change(code_hashes_per_msg: List[List[str]],
                       windows: List[List[int]]) -> np.ndarray:
    """窗口内代码变化率：不同哈希/总哈希；无代码给 0.5 中性值"""
    rates = []
    for idxs in windows:
        hashes = [h for i in idxs for h in code_hashes_per_msg[i]]
        if not hashes:
            rates.append(0.5)
        else:
            rates.append(len(set(hashes)) / float(len(hashes)))
    return np.array(rates, dtype=np.float32)


def lookback_persist(window_vecs: np.ndarray,
                     code_hashes_per_msg: List[List[str]],
                     windows: List[List[int]],
                     lookback: int = 2) -> np.ndarray:
    """邻近窗口“持续停滞”：0.5*文本窗余弦 + 0.5*代码Jaccard 的最大值"""
    code_sets = [set([h for i in idxs for h in code_hashes_per_msg[i]]) for idxs in windows]
    out = []
    for i in range(len(windows)):
        best = 0.0
        for j in range(max(0, i - lookback), i):
            text_cos = float(np.dot(window_vecs[i], window_vecs[j]))  # 已 L2
            A, B = code_sets[i], code_sets[j]
            jac = (len(A & B) / len(A | B)) if (A or B) else 0.0
            best = max(best, 0.5 * text_cos + 0.5 * jac)
        out.append(best)
    return np.array(out, dtype=np.float32)


# ---------------------------
# 仅用于“打标”的词典（含探测式问句豁免）
# ---------------------------

ANY_ERROR_Q = re.compile(r"\b(any|is there|does.*have|are there)\b.*\b(error|bug|issue|problem)\b\??", re.I)
DONE  = {"complete","completed","finish","finished","pass","passed","accept","accepted",
         "solved","resolve","resolved","fix","fixed","merge","merged","success","successfully","ok","ac"}
STUCK = {"error","errors","failed","fail","stuck","bug","exception","timeout","timed out","crash","cannot","not working"}

def done_stuck_counts(window_docs: List[str]) -> Tuple[np.ndarray, np.ndarray]:
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


# ---------------------------
# 聚类 & 命名
# ---------------------------

def kmeans_cosine(X: np.ndarray, k: int = 3,
                  n_init: int = 50, max_iter: int = 500,
                  random_state: int = 42) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """
    L2 之后用欧式 KMeans ≈ 余弦；返回 labels, centers, sims(和中心的余弦), silhouette
    """
    Xn = normalize(X)
    km = KMeans(n_clusters=k, n_init=n_init, max_iter=max_iter, random_state=random_state)
    labels = km.fit_predict(Xn)
    centers = normalize(km.cluster_centers_)
    sims = np.sum(Xn * centers[labels], axis=1).astype(np.float32)  # 点积即余弦
    sil = -1.0
    if len(np.unique(labels)) > 1 and Xn.shape[0] > k:
        try:
            sil = float(silhouette_score(Xn, labels, metric="cosine"))
        except Exception:
            pass
    return labels, centers, sims, sil


def progress_score_from_proxies(repeat_eq: np.ndarray,
                                repeat_sim: np.ndarray,
                                code_change: np.ndarray,
                                done_hits: np.ndarray,
                                stuck_hits: np.ndarray,
                                cw_persist: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    返回：Z(6维代理的zscore)，progress_score（越大越“超进度”）
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


def name_clusters_by_progress(labels: np.ndarray,
                              progress_score: np.ndarray,
                              use_fixed_mapping: bool = True) -> Tuple[Dict[int, str], np.ndarray, Dict[int, float]]:
    """
    用簇内 progress_score 的均值排序命名：低进度 / 正常 / 超进度
    
    Args:
        labels: 聚类标签
        progress_score: 进度分数
        use_fixed_mapping: 是否使用固定的簇ID映射 (0:超进度, 1:正常, 2:低进度)
    """
    k = len(np.unique(labels))
    means = {c: float(progress_score[labels == c].mean()) if np.any(labels == c) else -1e9
             for c in range(k)}
    
    if use_fixed_mapping and k == 3:
        # 使用固定的簇ID映射，与labels.labeled.csv保持一致
        # 根据人工审核后的标注：{1: '正常', 0: '超进度', 2: '低进度'}
        names = {1: "正常", 0: "超进度", 2: "低进度"}
    else:
        # 使用基于progress_score均值的动态映射
        order = [c for c, _ in sorted(means.items(), key=lambda kv: kv[1])]  # 低→高
        names = {order[0]: "低进度", order[1]: "正常", order[2]: "超进度"} if k == 3 else {order[i]: f"Cluster-{i}" for i in range(k)}
    
    named = np.array([names[c] for c in labels])
    return names, named, means


def export_prototypes(Xn: np.ndarray,
                      labels: np.ndarray,
                      centers: np.ndarray,
                      topk: int = 8) -> Dict[int, List[int]]:
    """每簇选与中心余弦最大的 top-k 样本索引"""
    ids: Dict[int, List[int]] = {}
    sims_to_center = np.sum(Xn * centers[labels], axis=1)
    for c in np.unique(labels):
        idx = np.where(labels == c)[0]
        if idx.size == 0:
            ids[int(c)] = []
            continue
        s = sims_to_center[idx]
        top = idx[np.argsort(-s)[:topk]]
        ids[int(c)] = [int(i) for i in top]
    return ids


# ---------------------------
# 主流程（供入口脚本调用）
# ---------------------------

def progress_clustering_pipeline(
    raw_msgs: List[str],
    batch_size: int = 12,
    overlap: int = 4,
    model_name: str = "sentence-transformers/all-mpnet-base-v2",
    pca_dim: int = 64,
    include_struct_in_clustering: bool = False,
    lookback: int = 2,
    n_init: int = 50,
    max_iter: int = 500,
    random_state: int = 42,
    struct_weight: float = 2.0,
    near_sim_thresh: float = 0.95,
    pca_obj: Optional[PCA] = None,
    scaler_obj: Optional[StandardScaler] = None,
) -> Dict[str, Any]:
    """
    返回一个 dict，含：
      - windows / docs / start_idx / end_idx
      - features for clustering (Xn), labels, centers, sims, silhouette
      - proxies & progress_score
      - names_map / named_labels / cluster_means
      - prototypes（索引）
      - pca_obj / scaler_obj（便于导出上线）
    """
    N = len(raw_msgs)
    clean_texts, code_hashes_per_msg = preprocess_messages(raw_msgs)
    windows = create_windows(N, batch_size, overlap)
    if not windows:
        raise ValueError("有效窗口数为 0，请检查 batch_size / overlap 或数据量。")

    # per-message 语义嵌入（clean_text）
    per_msg_embs = encode_messages(clean_texts, model_name=model_name)

    # 窗口向量（mean+std → PCA→pca_dim → L2）
    win_vecs, pooled_raw, pca_obj = pool_window_embeddings(per_msg_embs, windows, pca_dim=pca_dim, random_state=random_state, pca_obj=pca_obj)

    # 窗口文档（用于 done/stuck 与展示）
    docs = [" ".join([raw_msgs[i] for i in idxs]) for idxs in windows]

    # 结构特征（窗口内）
    repeat_eq, repeat_sim = window_repeat_features(clean_texts, per_msg_embs, windows,
                                                   near_sim_thresh=near_sim_thresh)
    code_change = window_code_change(code_hashes_per_msg, windows)

    # 邻近窗口持续停滞
    cw_persist = lookback_persist(win_vecs, code_hashes_per_msg, windows, lookback=lookback)

    # ------ 聚类（阶段 A） ------
    scaler = None
    if include_struct_in_clustering:
        if scaler_obj is not None:
            scaler = scaler_obj
            S = scaler.transform(np.column_stack([repeat_eq, repeat_sim, code_change]))
        else:
            scaler = StandardScaler()
            S = scaler.fit_transform(np.column_stack([repeat_eq, repeat_sim, code_change]))
        S *= float(struct_weight)   # 结构特征加权
        X = np.hstack([win_vecs, S])
    else:
        X = win_vecs
    Xn = normalize(X)

    labels, centers, sims, sil = kmeans_cosine(Xn, k=3, n_init=n_init, max_iter=max_iter, random_state=random_state)

    # 供人工审核的中心（未命名）
    centers_out = centers.copy()

    # ------ 后置打标（阶段 B） ------
    done_hits, stuck_hits = done_stuck_counts(docs)
    Z_proxy, progress_score = progress_score_from_proxies(repeat_eq, repeat_sim, code_change, done_hits, stuck_hits, cw_persist)

    names_map, named_labels, cluster_means = name_clusters_by_progress(labels, progress_score, use_fixed_mapping=True)

    # 原型样本（每簇 top-k）
    prototypes = export_prototypes(Xn, labels, centers, topk=8)

    # 起止索引
    starts = [w[0] for w in windows]
    ends   = [w[-1] for w in windows]

    return {
        "windows": windows,
        "docs": docs,
        "start_idx": starts,
        "end_idx": ends,
        "Xn": Xn,
        "labels": labels,
        "centers": centers_out,
        "sims": sims,
        "silhouette": sil,
        "repeat_eq": repeat_eq,
        "repeat_sim": repeat_sim,
        "code_change": code_change,
        "cw_persist": cw_persist,
        "done_hits": done_hits,
        "stuck_hits": stuck_hits,
        "Z_proxy": Z_proxy,
        "progress_score": progress_score,
        "names_map": names_map,
        "named_labels": named_labels,
        "cluster_means": cluster_means,
        "prototypes": prototypes,
        "pca_obj": pca_obj,
        "scaler_obj": scaler,
    }


# ====== 可读中心（medoid）与可视化 ======
from sklearn.feature_extraction.text import TfidfVectorizer
import matplotlib
matplotlib.use("Agg")  # 无GUI环境下安全保存图片
import matplotlib.pyplot as plt

def get_cluster_medoids(Xn: np.ndarray,
                        labels: np.ndarray,
                        centers: np.ndarray,
                        topk: int = 1):
    """
    返回：{cluster_id: {"indices":[...], "sims":[...]} }
    每个簇内按与簇中心的余弦相似度排序，选出 topk 个 medoid 索引
    """
    out: Dict[int, Dict[str, Any]] = {}
    for c in sorted(set(labels)):
        idx = np.where(labels == c)[0]
        if idx.size == 0:
            out[int(c)] = {"indices": [], "sims": []}
            continue
        sims = (Xn[idx] * centers[c]).sum(axis=1)
        order = np.argsort(-sims)[:topk]
        out[int(c)] = {
            "indices": [int(idx[i]) for i in order],
            "sims": [float(sims[i]) for i in order]
        }
    return out

def _tfidf_top_terms(docs, idx, topn=12):
    """给定文档列表docs，在第 idx 个文档上取 TF-IDF 最高的 topn 关键词（用于人工感知）"""
    vectorizer = TfidfVectorizer(lowercase=True, stop_words="english", max_features=20000,
                                 token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z_\-\.]{1,}\b")
    X = vectorizer.fit_transform(docs)
    row = X[idx]
    if row.nnz == 0:
        return []
    terms = np.array(vectorizer.get_feature_names_out())
    top_idx = row.indices[np.argsort(-row.data)[:topn]]
    return [str(t) for t in terms[top_idx]]

def build_center_summaries(raw_msgs,
                           windows,
                           docs,
                           medoids_dict,
                           msg_preview=6,
                           char_limit=1200,
                           topn_terms=12):
    """
    生成可读中心摘要：
      - 每簇取 medoid 窗口（与中心最接近），导出该窗口前若干条消息
      - 同时给出该窗口的 TF-IDF 关键词
    返回：{cluster_id: {...}}
    """
    summaries = {}
    for c, obj in medoids_dict.items():
        if not obj["indices"]:
            summaries[int(c)] = {"medoid_index": None, "similarity": None,
                                 "start_idx": None, "end_idx": None,
                                 "excerpt": "", "top_terms": []}
            continue
        m = obj["indices"][0]
        sim = obj["sims"][0]
        win = windows[m]
        start_idx, end_idx = win[0], win[-1]
        msgs = [raw_msgs[i] for i in win[:msg_preview]]
        excerpt = "\n---\n".join(msgs)
        if len(excerpt) > char_limit:
            excerpt = excerpt[:char_limit] + " …"
        try:
            terms = _tfidf_top_terms(docs, m, topn=topn_terms)
        except Exception:
            terms = []
        summaries[int(c)] = {
            "medoid_index": int(m),
            "similarity": float(sim),
            "start_idx": int(start_idx),
            "end_idx": int(end_idx),
            "excerpt": excerpt,
            "top_terms": terms,
        }
    return summaries

def visualize_clusters_2d(Xn: np.ndarray,
                          labels: np.ndarray,
                          centers: np.ndarray,
                          save_path: str,
                          title: str = "Progress Clusters (PCA-2D)",
                          medoid_indices: Optional[List[int]] = None,
                          show_2d_mean_centers: bool = True,
                          figsize=(9, 7)):
    """
    将特征（已L2）用 PCA 降到2维，画散点；
    - ⭐：算法中心（高维中心投影）
    - ✚：二维均值中心（视觉中心，更接近点云几何中点）
    - ◯：medoid（与中心最接近的真实样本）
    """
    pca = PCA(n_components=2, random_state=42)
    Z = pca.fit_transform(Xn)
    C_alg = pca.transform(centers)  # 算法中心（投影）
    C_vis = None
    if show_2d_mean_centers:
        C_vis = np.vstack([Z[labels == c].mean(axis=0) for c in sorted(set(labels))])

    plt.figure(figsize=figsize)
    for c in sorted(set(labels)):
        mask = (labels == c)
        plt.scatter(Z[mask, 0], Z[mask, 1], s=20, alpha=0.65, label=f"Cluster {c}")
    # ⭐ 算法中心
    plt.scatter(C_alg[:,0], C_alg[:,1], s=180, marker="*", edgecolors="k", linewidths=1.0, label="Centers (algo)")
    # ✚ 二维均值中心
    if C_vis is not None:
        plt.scatter(C_vis[:,0], C_vis[:,1], s=140, marker="+", linewidths=2.0, label="Centers (2D mean)")
    # ◯ medoid
    if medoid_indices:
        M = pca.transform(Xn[np.array(medoid_indices)])
        plt.scatter(M[:,0], M[:,1], s=120, marker="o", facecolors="none", edgecolors="k", linewidths=1.5, label="Medoids")
    plt.title(title)
    plt.xlabel("PC1"); plt.ylabel("PC2")
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path, dpi=180)
    plt.close()
    return save_path
