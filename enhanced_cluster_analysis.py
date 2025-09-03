#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enhanced_cluster_analysis.py

Tri-clustering pipeline for student–AI chat windows with **cluster-level labeling**.
- Unifies naming at the cluster level (no per-window naming).
- Exports a review bundle: for each cluster, shows center-nearest windows with excerpts & metrics.
- Uses **semantic + structural** features:
    * Semantic: Sentence-Transformers (all-mpnet-base-v2) if available; otherwise fall back to hashed-TF.
    * Structural: cross-window repetition, in-window repetition, code-change, refined done/stuck/AI-wrong cues.
- Optional pre-cluster PCA ('--pca_dim' or '--pca_var') then **L2 → KMeans** (Euclidean ≈ Cosine).
- Provides Silhouette score (overall / per-cluster) with optional sampling.
- Visualizes clusters in PCA-2D with ⭐ algo centers, ✚ 2D means, ◯ medoids (real samples).
- Freezes assets for online assignment: centers, label_map, struct_scaler, clustering_pca(+L2 flag), lexicon snapshot, feature_config.

Author: ChatGPT (GPT-5 Thinking)
"""

from __future__ import annotations
import os, re, json, math, difflib, string, logging, random, hashlib
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
from collections import deque
import numpy as np
import pandas as pd

# hard-disable TF/Flax in transformers contexts
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TRANSFORMERS_NO_FLAX"] = "1"
os.environ["USE_TF"] = "0"

# -----------------------------
# Logging
# -----------------------------
logger = logging.getLogger("tri_cluster")
if not logger.handlers:
    h = logging.StreamHandler()
    fmt = logging.Formatter("[%(levelname)s] %(message)s")
    h.setFormatter(fmt)
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# -----------------------------
# Windowing
# -----------------------------
def make_windows(n: int, batch_size: int = 12, overlap: int = 4) -> List[List[int]]:
    """Fixed-size windows with overlap; ensure tail coverage."""
    if n <= 0:
        return []
    assert 0 <= overlap < batch_size, "overlap must be in [0, batch_size)"
    step = max(1, batch_size - overlap)
    starts = list(range(0, max(1, n - batch_size + 1), step))
    windows = [list(range(s, min(n, s + batch_size))) for s in starts]
    # tail
    if windows:
        last_end = windows[-1][-1]
        if last_end < n - 1:
            tail = list(range(max(0, n - batch_size), n))
            if windows[-1] != tail:
                windows.append(tail)
    else:
        windows = [list(range(0, n))]
    return windows

def window_text(all_texts: List[str], win_idx: List[int], max_lines: int = 12) -> str:
    msgs = [all_texts[i] for i in win_idx[:max_lines]]
    return "\n---\n".join(msgs)

# -----------------------------
# Phrase lexicon (refined)
# -----------------------------
def default_lexicon() -> Dict[str, List[str]]:
    """Refined English/Chinese patterns; avoid generic 'error/problem' false positives."""
    return {
        "done": [
            r"it\s+works", r"works\s+now", r"\bfixed\b", r"pass(?:ed|es)?",
            r"\bsuccess(?:ful(ly)?)?\b", r"\bsolved\b", r"resolve(?:d)?",
            r"running", r"ran\s+successfully", r"tests?\s+pass(?:ed)?",
            r"\bvalidated\b", r"\bverification\s+passed\b", r"通过了", r"成功了", r"现在可以了"
        ],
        "stuck": [
            r"still\s+(not\s+working|doesn['’]?t\s+work|fail(?:s|ing)?)",
            r"same\s+(issue|error|result)\s+(again|still)?",
            r"didn['’]?t\s+work", r"doesn['’]?t\s+solve",
            r"\bno\s+effect\b", r"\bunchanged\b", r"\bnot\s+fixed\b",
            r"keeps?\s+fail(?:ing)?", r"\bno\s+improvement\b",
            r"\bno\s+progress\b", r"\bresult\s+did\s+not\s+change\b",
            r"还是不行", r"没有效果", r"结果没有变化", r"不工作", r"失败了"
        ],
        "ai_wrong": [
            r"(your|this)\s+(answer|code|solution)\s+is\s+(wrong|incorrect)",
            r"(your|this)\s+(answer|code|solution)\s+(doesn['’]?t|didn['’]?t)\s+work",
            r"(that|this)\s+is\s+not\s+(helpful|useful|relevant)",
            r"(doesn['’]?t|didn['’]?t)\s+help",
            r"\birrelevant\b|\bnot\s+relevant\b",
            r"\byou\s+are\s+wrong\b", r"你给的(答案|代码)不对", r"不(相关|适用)"
        ]
    }

def build_regexes(lexicon: Dict[str, List[str]]) -> Dict[str, re.Pattern]:
    return {k: re.compile("|".join(v), re.I) if v else re.compile(r"$a") for k, v in lexicon.items()}

# -----------------------------
# Tokenization & helpers
# -----------------------------
_punct_tbl = str.maketrans("", "", string.punctuation)
_code_kw = re.compile(r"\b(def|class|import|from|function|const|let|var|public|private|static|return|if|for|while|try|catch)\b", re.I)
_fence = re.compile(r"```")

def word_tokens(s: str) -> List[str]:
    s = s.lower().replace("`", " ")
    s = s.translate(_punct_tbl)
    return [t for t in s.split() if len(t) > 1]

def codeish_tokens(s: str) -> List[str]:
    toks: List[str] = []
    for tok in re.split(r"[^A-Za-z0-9_]+", s):
        if not tok: continue
        parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", tok)
        for p in parts:
            if len(p) > 1:
                toks.append(p.lower())
    return toks

def char_ngrams(s: str, n: int = 3) -> List[str]:
    s = re.sub(r"\s+", " ", s.lower())
    return [s[i:i+n] for i in range(0, max(0, len(s)-n+1))]

def hash_features(tokens: List[str], dim: int = 2048) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    for t in tokens:
        h = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16) % dim
        vec[h] += 1.0
    n = np.linalg.norm(vec)
    if n > 0: vec /= n
    return vec

def extract_code(s: str) -> str:
    """Prefer fenced blocks; else heuristic code-like lines."""
    blocks = []
    for m in re.finditer(r"```(?:[a-zA-Z0-9_-]+)?\n(.*?)```", s, re.S):
        blocks.append(m.group(1))
    if blocks:
        return "\n".join(blocks)
    lines = [ln for ln in s.splitlines()
             if _code_kw.search(ln) or ln.strip().endswith(("{",";","}","</","/>",")"))]
    return "\n".join(lines[:2000])

def remove_code_text(s: str) -> str:
    """Remove fenced code and code-like lines to get 'pure text'."""
    s = re.sub(r"```(?:[a-zA-Z0-9_-]+)?\n.*?```", " ", s, flags=re.S)
    kept = []
    for ln in s.splitlines():
        if _code_kw.search(ln) or ln.strip().endswith(("{",";","}","</","/>",")")):
            continue
        kept.append(ln)
    return "\n".join(kept)

def jaccard(a: set, b: set) -> float:
    if not a and not b: return 1.0
    if not a or not b: return 0.0
    inter = len(a & b); union = len(a | b)
    return inter / union if union else 0.0

def ngram_repetition(s: str, n: int = 4) -> float:
    toks = word_tokens(s)
    ngrams = [" ".join(toks[i:i+n]) for i in range(0, max(0, len(toks)-n+1))]
    if not ngrams:
        return 0.0
    uniq = len(set(ngrams))
    return float(1.0 - (uniq / len(ngrams)))

def line_repetition(s: str) -> float:
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    if not lines: return 0.0
    return float(1.0 - (len(set(lines)) / len(lines)))

def strip_comments(code: str) -> str:
    code = re.sub(r"/\*.*?\*/", " ", code, flags=re.S)
    out = []
    for ln in code.splitlines():
        ln = re.sub(r"^\s*(//|#|--).*$", " ", ln).strip()
        if ln:
            out.append(re.sub(r"\s+", " ", ln).lower())
    return "\n".join(out)

def md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8", errors="ignore")).hexdigest()

# -----------------------------
# Embedding backend
# -----------------------------
class SemanticBackend:
    def __init__(self, mode: str = "st", model_name: str = "sentence-transformers/all-mpnet-base-v2", hash_dim: int = 2048):
        self.mode = mode
        self.model_name = model_name
        self.hash_dim = hash_dim
        self._st_model = None
        if mode == "st":
            try:
                from sentence_transformers import SentenceTransformer
                self._st_model = SentenceTransformer(model_name)
                logger.info(f"Loaded SentenceTransformer: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load {model_name}: {e}. Falling back to 'hash'.")
                self.mode = "hash"

    def encode(self, texts: List[str]) -> np.ndarray:
        if self.mode == "none":
            return np.zeros((len(texts), 1), dtype=np.float32)
        if self.mode == "st" and self._st_model is not None:
            try:
                embs = self._st_model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
                return np.asarray(embs, dtype=np.float32)
            except Exception as e:
                logger.warning(f"ST encode failed: {e}. Switching to 'hash'.")
                self.mode = "hash"
        # hash fallback
        vecs = []
        for s in texts:
            toks = word_tokens(s) + codeish_tokens(s) + char_ngrams(s, 3)
            vecs.append(hash_features(toks, dim=self.hash_dim))
        return np.vstack(vecs).astype(np.float32)

# -----------------------------
# Feature extraction
# -----------------------------
@dataclass
class FeatureConfig:
    max_lines: int = 12
    semantic_weight: float = 0.2
    structural_weight: float = 0.8
    # 重复与门控参数
    dup_lookback: int = 3               # 消息级代码复用回看窗口数
    high_dup_thresh: float = 0.70       # 单窗重复阈值（≥视为明显重复）
    high_dup_weight: float = 0.80       # 单窗高重复的强惩罚权重
    code_repeat_alpha: float = 1.0      # (1 - code_change)^alpha 的 α

def progress_score_from_proxies(f: Dict[str, float]) -> float:
    """Heuristic score ~[-1,1]. Higher ⇒ more '超进度'."""
    return (
        + 0.38 * f["done_hits"]
        + 0.34 * f["code_change"]
        - 0.22 * f["repeat_sim"]
        - 0.18 * f["repeat_eq"]
        - 0.26 * f["stuck_hits"]
        - 0.18 * f["cw_persist"]
        - 0.22 * f["inrep_line"]
        - 0.15 * f.get("inrep_ng4_text", 0.0)
        - 0.28 * f.get("code_dup_msg_inwin", 0.0)
        - 0.22 * f.get("code_dup_msg_lookback", 0.0)
        - 1.00 * f.get("code_repeat_penalty", 0.0)     # 推进门控后的含代码重复惩罚
        - 1.00 * f.get("high_dup_penalty_w", 0.0)      # 单窗高重复强惩罚（阈值触发）
        - 0.32 * f["ai_wrong_hits"]
    )

def features_for_windows(all_texts: List[str],
                         windows: List[List[int]],
                         lexicon_regex: Dict[str, re.Pattern],
                         cfg: FeatureConfig) -> Tuple[pd.DataFrame, List[str]]:
    feats: List[Dict[str, float]] = []
    excerpts: List[str] = []

    # 历史（跨窗）消息级代码集合
    prev_msg_code_sets: deque = deque(maxlen=cfg.dup_lookback)
    prev_code_concat = ""   # 用于 difflib 近似“代码变化”
    prev_tokset: set = set()
    prev2_tokset: set = set()

    for wj, win in enumerate(windows):
        s = window_text(all_texts, win, max_lines=cfg.max_lines)
        excerpts.append(s[:1200])

        # --- 代码抽取与“变化程度”(change=1-sim) ---
        code_concat = extract_code(s)
        if prev_code_concat:
            sim = difflib.SequenceMatcher(a=prev_code_concat, b=code_concat).quick_ratio()
            code_change = max(0.0, min(1.0, 1.0 - sim))  # 0..1（越大越“变动/推进”）
        else:
            code_change = 0.5 if code_concat else 0.0  # 无对照时给中性值
        prev_code_concat = code_concat

        # --- 语义相似/等值重复（与上一窗） ---
        tokset = set(word_tokens(s))
        jac_prev = jaccard(tokset, prev_tokset)
        jac_prev2 = jaccard(tokset, prev2_tokset)
        cw_persist = (jac_prev + jac_prev2) / 2.0 if (prev_tokset or prev2_tokset) else jac_prev
        prev2_tokset = prev_tokset
        prev_tokset = tokset

        # 与上一窗的行级等值
        prev_lines = set(window_text(all_texts, windows[wj-1], max_lines=cfg.max_lines).splitlines()) if wj>0 else set()
        cur_lines = set(s.splitlines())
        repeat_eq = len(cur_lines & prev_lines) / max(1, len(cur_lines | prev_lines))

        # --- 单窗内部重复 ---
        inrep_line_all = line_repetition(s)           # 行级重复（含代码）
        inrep_ng_all   = ngram_repetition(s, n=4)     # 含代码
        s_text_only    = remove_code_text(s)
        inrep_ng_text  = ngram_repetition(s_text_only, n=4)  # 去代码

        # --- 消息级代码哈希：同窗/跨窗复用 ---
        msg_code_hashes: List[str] = []
        for mi in win:
            blocks = extract_code(all_texts[mi])
            if blocks:
                merged = strip_comments("\n".join(blocks))
                if merged:
                    msg_code_hashes.append(md5(merged))
        if msg_code_hashes:
            code_dup_msg_inwin = 1.0 - (len(set(msg_code_hashes)) / float(len(msg_code_hashes)))
        else:
            code_dup_msg_inwin = 0.0

        cur_msg_set = set(msg_code_hashes)
        if cur_msg_set and len(prev_msg_code_sets) > 0:
            hist_union = set().union(*list(prev_msg_code_sets))
            inter = len(cur_msg_set & hist_union)
            code_dup_msg_lookback = inter / float(len(cur_msg_set))
        else:
            code_dup_msg_lookback = 0.0

        # --- 含代码 vs 去代码 n-gram 的“过量重复” + 推进门控 ---
        code_repeat_excess = max(0.0, inrep_ng_all - inrep_ng_text)
        num_code_lines = sum(1 for ln in s.splitlines() if _code_kw.search(ln))
        code_line_rate = min(1.0, num_code_lines / float(cfg.max_lines if cfg.max_lines > 0 else 12))
        code_repeat_penalty = code_repeat_excess * ((1.0 - code_change) ** cfg.code_repeat_alpha) * (0.5 + 0.5 * code_line_rate)

        # --- 单窗高重复（强信号：连续大段重复→低进度） ---
        # 取三种重复的最大值：行级、消息级代码复用、含代码 4-gram
        dup_max_inwin = max(float(inrep_line_all), float(code_dup_msg_inwin), float(inrep_ng_all))
        if dup_max_inwin >= cfg.high_dup_thresh:
            high_dup_penalty = (dup_max_inwin - cfg.high_dup_thresh) / (1.0 - cfg.high_dup_thresh)
            high_dup_flag = 1.0
        else:
            high_dup_penalty = 0.0
            high_dup_flag = 0.0
        high_dup_penalty_w = high_dup_penalty * cfg.high_dup_weight

        # --- 词典信号 ---
        done_hits = len(lexicon_regex["done"].findall(s))
        stuck_hits = len(lexicon_regex["stuck"].findall(s))
        ai_wrong_hits = len(lexicon_regex["ai_wrong"].findall(s))
        num_q = s.count("?")
        num_fences = len(_fence.findall(s))

        f = {
            "window_index": wj,
            "start_idx": win[0],
            "end_idx": win[-1],
            # 基础结构
            "repeat_sim": jac_prev,
            "repeat_eq": repeat_eq,
            "cw_persist": cw_persist,
            "code_change": code_change,
            "inrep_line": inrep_line_all,
            "inrep_ng4_text": inrep_ng_text,
            "inrep_ng4_all": inrep_ng_all,
            # 消息级代码复用
            "code_dup_msg_inwin": code_dup_msg_inwin,
            "code_dup_msg_lookback": code_dup_msg_lookback,
            # 含代码过量重复 + 门控
            "code_repeat_excess": code_repeat_excess,
            "code_repeat_penalty": code_repeat_penalty,
            # 单窗高重复（强惩罚）
            "dup_max_inwin": dup_max_inwin,
            "high_dup_penalty": high_dup_penalty,
            "high_dup_penalty_w": high_dup_penalty_w,
            "high_dup_flag": high_dup_flag,
            # 词典/统计
            "done_hits": min(1.0, done_hits/3.0),
            "stuck_hits": min(1.0, stuck_hits/3.0),
            "ai_wrong_hits": min(1.0, ai_wrong_hits/2.0),
            "q_density": min(1.0, num_q/12.0),
            "code_line_rate": code_line_rate,
            "fenced_blocks": min(1.0, num_fences/3.0),
        }
        f["progress_score"] = progress_score_from_proxies(f)
        feats.append(f)

        # 更新跨窗历史
        prev_msg_code_sets.append(cur_msg_set)

    df = pd.DataFrame(feats)
    # 为了兼容旧可视化/脚本，保留一个 inrep_ng4 别名（用“去代码”的版本更稳定）
    if "inrep_ng4" not in df.columns:
        df["inrep_ng4"] = df["inrep_ng4_text"]
    return df, excerpts

def build_semantic_matrix(excerpts: List[str], backend: SemanticBackend) -> np.ndarray:
    return backend.encode(excerpts)

def combine_semantic_structural(sem: np.ndarray,
                                struct_df: pd.DataFrame,
                                cfg: FeatureConfig) -> Tuple[np.ndarray, List[str], Dict[str, np.ndarray]]:
    struct_cols = [
        "done_hits","code_change","repeat_sim","repeat_eq","stuck_hits",
        "cw_persist","inrep_line","inrep_ng4_text",
        "code_dup_msg_inwin","code_dup_msg_lookback",
        "inrep_ng4_all","code_repeat_excess","code_repeat_penalty",
        "dup_max_inwin","high_dup_penalty","high_dup_penalty_w","high_dup_flag",
        "ai_wrong_hits","q_density","code_line_rate","fenced_blocks","progress_score"
    ]
    S = struct_df[struct_cols].to_numpy(dtype=np.float32)
    Smu = S.mean(axis=0); Ssig = S.std(axis=0) + 1e-6
    Szn = (S - Smu) / Ssig
    X = np.hstack([sem * cfg.semantic_weight, Szn * cfg.structural_weight]).astype(np.float32)
    scaler = {"feature_names": struct_cols, "mean": Smu.tolist(), "std": Ssig.tolist()}
    return X, struct_cols, scaler

# -----------------------------
# Pre-cluster L2 + PCA (NumPy/SVD)
# -----------------------------
def l2_normalize_rows(A: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    n = np.linalg.norm(A, axis=1, keepdims=True)
    return A / np.maximum(n, eps)

def fit_pca_for_clustering(X: np.ndarray,
                           pca_dim: Optional[int] = None,
                           pca_var: Optional[float] = None) -> Tuple[np.ndarray, Dict[str, object]]:
    """Zero-mean + SVD PCA; choose by fixed dim or cumulative variance (0<var<=1)."""
    assert (pca_dim is not None) ^ (pca_var is not None), "Choose exactly one of pca_dim / pca_var"
    X = X.astype(np.float32)
    mu = X.mean(axis=0, keepdims=True)
    Xc = X - mu
    U, S, VT = np.linalg.svd(Xc, full_matrices=False)
    var = (S ** 2)
    var_ratio = var / (var.sum() + 1e-12)
    if pca_dim is not None:
        k = int(max(1, min(pca_dim, VT.shape[0])))
    else:
        cum = np.cumsum(var_ratio)
        k = int(np.searchsorted(cum, float(pca_var)) + 1)
    W = VT[:k].T
    Z = Xc @ W
    model = {
        "components": W.astype(np.float32),
        "mean": mu.squeeze().astype(np.float32),
        "n_components": int(k),
        "explained": float(var_ratio[:k].sum())
    }
    return Z.astype(np.float32), model

# -----------------------------
# KMeans (NumPy; k-means++ init)
# -----------------------------
def kmeans(X: np.ndarray, k: int = 3, n_init: int = 100, iters: int = 800, seed: int = 23):
    best = None
    rng = random.Random(seed)
    for _ in range(n_init):
        centers = [X[rng.randrange(0, len(X))]]
        for _ in range(1, k):
            d2 = np.min(((X[:,None,:]-np.array(centers)[None,:,:])**2).sum(axis=2), axis=1)
            probs = d2 / (d2.sum() + 1e-9)
            idx = np.searchsorted(np.cumsum(probs), rng.random())
            centers.append(X[min(idx, len(X)-1)])
        centers = np.array(centers, dtype=np.float32)
        for _ in range(iters):
            d2 = ((X[:,None,:]-centers[None,:,:])**2).sum(axis=2)
            labels = d2.argmin(axis=1)
            new_centers = np.vstack([
                X[labels==j].mean(axis=0) if np.any(labels==j) else centers[j] for j in range(k)
            ]).astype(np.float32)
            if np.allclose(new_centers, centers):
                break
            centers = new_centers
        inertia = float(((X - centers[labels])**2).sum())
        if (best is None) or (inertia < best[0]):
            best = (inertia, centers, labels)
    return best[1], best[2]

# -----------------------------
# Silhouette (NumPy; optional sampling)
# -----------------------------
def compute_silhouette_scores(X: np.ndarray, labels: np.ndarray,
                              sample_size: int = 0, random_state: int = 42, chunk: int = 512) -> Dict:
    rng = np.random.RandomState(random_state)
    n = len(X)
    idx_all = np.arange(n, dtype=int)
    if sample_size and n > sample_size:
        idx_used = np.sort(rng.choice(idx_all, size=sample_size, replace=False))
    else:
        idx_used = idx_all
    clusters = sorted(set(map(int, labels)))
    by_c = {c: np.where(labels == c)[0] for c in clusters}
    ss = []
    for st in range(0, len(idx_used), chunk):
        ed = min(len(idx_used), st + chunk)
        I = idx_used[st:ed]
        A = X[I]
        D2 = ((A[:, None, :] - X[None, :, :]) ** 2).sum(axis=2)
        D = np.sqrt(D2 + 1e-12)
        for j, gi in enumerate(I):
            c = int(labels[gi])
            same = by_c[c]
            if same.size <= 1:
                a = 0.0
            else:
                d_same = D[j, same]
                a = float(d_same.mean())
            b = float("inf")
            for c2 in clusters:
                if c2 == c or by_c[c2].size == 0:
                    continue
                b = min(b, float(D[j, by_c[c2]].mean()))
            if not np.isfinite(b):
                s = 0.0
            else:
                m = max(a, b)
                s = 0.0 if m <= 1e-12 else (b - a) / m
            ss.append((int(gi), float(s)))
    overall = float(np.mean([s for _, s in ss])) if ss else 0.0
    per_cluster = {}
    for c in clusters:
        sc = [s for i, s in ss if labels[i] == c]
        per_cluster[int(c)] = float(np.mean(sc)) if sc else 0.0
    return {"overall": overall, "per_cluster": per_cluster, "per_sample": ss, "n_used": int(len(idx_used))}

# -----------------------------
# Cluster review & naming
# -----------------------------
def build_cluster_review(raw_msgs: List[str],
                         windows: List[List[int]],
                         X: np.ndarray,
                         labels: np.ndarray,
                         topk_neighbors: int,
                         df_metrics: pd.DataFrame,
                         msg_preview: int = 6,
                         char_limit: int = 1200) -> Dict[int, Dict]:
    review: Dict[int, Dict] = {}
    # 想在面板里看到的关键指标（若存在即导出）
    prefer_cols = [
        "progress_score","done_hits","code_change",
        "dup_max_inwin","high_dup_penalty","code_dup_msg_inwin","code_dup_msg_lookback",
        "inrep_line","inrep_ng4_text","inrep_ng4_all",
        "code_repeat_excess","code_repeat_penalty",
        "repeat_sim","repeat_eq","stuck_hits","cw_persist",
        "ai_wrong_hits","q_density","code_line_rate","fenced_blocks"
    ]
    cols = [c for c in prefer_cols if c in df_metrics.columns]

    for cid in sorted(set(labels)):
        idx = np.where(labels == cid)[0]
        if idx.size == 0:
            review[int(cid)] = {"neighbors": []}
            continue
        C = X[idx].mean(axis=0, keepdims=True)
        d2 = ((X[idx] - C)**2).sum(axis=1)
        order = [int(idx[i]) for i in np.argsort(d2)[:topk_neighbors]]
        items = []
        for row_idx in order:
            win = windows[row_idx]
            msgs = [raw_msgs[i] for i in win[:msg_preview]]
            excerpt = "\n---\n".join(msgs)
            if len(excerpt) > char_limit:
                excerpt = excerpt[:char_limit] + " …"
            metrics = df_metrics.loc[row_idx, cols].to_dict()
            items.append({
                "window_index": int(row_idx),
                "sim_to_center": float(1.0 / (1.0 + float(((X[row_idx]-C[0])**2).sum()))),
                "start_idx": int(win[0]),
                "end_idx": int(win[-1]),
                "excerpt": excerpt,
                "metrics": {k: float(v) for k,v in metrics.items()}
            })
        review[int(cid)] = {"neighbors": items}
    return review

def name_clusters_by_progress(labels: np.ndarray,
                              progress_scores: np.ndarray,
                              use_fixed_mapping: bool = False) -> Tuple[Dict[int,str], Dict[int,float]]:
    """Return (names_map, cluster_mean_progress). For fixed mapping, sort means asc → ['低进度','正常','超进度'].""" 
    means: Dict[int,float] = {}
    for c in sorted(set(labels)):
        means[int(c)] = float(progress_scores[labels==c].mean()) if np.any(labels==c) else 0.0
    if not use_fixed_mapping:
        return {}, means
    order = [c for c,_ in sorted(means.items(), key=lambda kv: kv[1])]
    fixed = ["低进度", "正常", "超进度"]
    names = {int(c): fixed[i] for i,c in enumerate(order[:3])}
    return names, means

# -----------------------------
# Medoid / prototypes
# -----------------------------
def compute_medoid_and_prototypes(X: np.ndarray, labels: np.ndarray, k: int = 3, topk: int = 12):
    out = {}
    for cid in sorted(set(labels)):
        idx = np.where(labels == cid)[0]
        if idx.size == 0:
            out[int(cid)] = {"medoid": None, "prototypes": []}
            continue
        C = X[idx].mean(axis=0, keepdims=True)
        d2 = ((X[idx] - C)**2).sum(axis=1)
        order_local = np.argsort(d2)
        proto_idx = [int(idx[i]) for i in order_local[:topk]]
        medoid = int(idx[order_local[0]])
        out[int(cid)] = {"medoid": medoid, "prototypes": proto_idx}
    return out

# -----------------------------
# Visualization (PCA-2D, ⭐✚◯)
# -----------------------------
def visualize_clusters_2d(
    X: np.ndarray,
    labels: np.ndarray,
    centers: np.ndarray,
    save_path: str,
    title: str = "Progress Clusters (PCA-2D)",
    medoid_indices: Optional[List[int]] = None,
    show_2d_mean_centers: bool = True,
    figsize=(9, 7)
):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    Xn = l2_normalize_rows(X.astype(np.float32))
    Cn = l2_normalize_rows(centers.astype(np.float32))
    Xmu = Xn.mean(axis=0, keepdims=True)
    Xc = Xn - Xmu
    U, S, VT = np.linalg.svd(Xc, full_matrices=False)
    W = VT[:2].T
    Z = Xc @ W
    C_alg = (Cn - Xmu) @ W
    uniq = sorted(set(labels.tolist() if hasattr(labels, "tolist") else list(labels)))
    C_vis = None
    if show_2d_mean_centers:
        C_vis = np.vstack([Z[labels == c].mean(axis=0) for c in uniq])

    plt.figure(figsize=figsize)
    for c in uniq:
        m = (labels == c)
        plt.scatter(Z[m,0], Z[m,1], s=20, alpha=0.65, label=f"Cluster {c}")
    plt.scatter(C_alg[:,0], C_alg[:,1], s=180, marker="*", edgecolors="k", linewidths=1.0, label="Centers (algo)")
    if C_vis is not None:
        plt.scatter(C_vis[:,0], C_vis[:,1], s=140, marker="+", linewidths=2.0, label="Centers (2D mean)")
    if medoid_indices:
        M = Z[np.array(medoid_indices, dtype=int)]
        plt.scatter(M[:,0], M[:,1], s=120, marker="o", facecolors="none", edgecolors="k", linewidths=1.5, label="Medoids")
    plt.title(title); plt.xlabel("PC1"); plt.ylabel("PC2"); plt.legend(); plt.tight_layout()
    plt.savefig(save_path, dpi=180); plt.close()

    # export PCA used for the fig + 2D embedding for debugging
    try:
        import joblib, os as _os
        joblib.dump({"components": W.T, "mean": Xmu.squeeze()}, os.path.splitext(save_path)[0]+".pca.joblib")
    except Exception:
        np.savez(os.path.splitext(save_path)[0]+".pca_fallback.npz", components=W.T, mean=Xmu.squeeze())
    np.save(os.path.splitext(save_path)[0]+".X_pca.npy", Z)
    return save_path

# -----------------------------
# Centers & asset freezing
# -----------------------------
def compute_cluster_centers(X: np.ndarray, labels: np.ndarray) -> np.ndarray:
    ids = sorted(set(map(int, labels)))
    centers = []
    for cid in ids:
        sel = (labels == cid)
        if np.any(sel):
            centers.append(X[sel].mean(axis=0))
        else:
            centers.append(np.zeros(X.shape[1], dtype=np.float32))
    return np.vstack(centers).astype(np.float32)

def freeze_assets(save_dir: str,
                  assets_dir: str,
                  centers: np.ndarray,
                  label_map: Dict[int, str],
                  semantic_mode: str,
                  embed_model: str,
                  semantic_weight: float,
                  structural_weight: float,
                  struct_scaler: Dict[str, object],
                  lexicon_snapshot: Dict[str, list],
                  window_cfg: Dict[str, int],
                  clustering_pca: Optional[Dict[str, object]] = None,
                  l2_norm_before_cluster: bool = True):
    """Persist everything needed for stable online assignment."""
    os.makedirs(assets_dir, exist_ok=True)
    # centers
    try:
        import joblib
        joblib.dump(centers, os.path.join(assets_dir, "cluster_centers.joblib"))
    except Exception:
        np.save(os.path.join(assets_dir, "cluster_centers.npy"), centers)
    # label map
    with open(os.path.join(assets_dir, "label_map.json"), "w", encoding="utf-8") as f:
        json.dump({str(int(k)): str(v) for k,v in label_map.items()}, f, ensure_ascii=False, indent=2)
    # embed meta
    with open(os.path.join(assets_dir, "embed_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"semantic_mode": semantic_mode, "embed_model": embed_model}, f, ensure_ascii=False, indent=2)
    # feature config (weights, window, L2)
    with open(os.path.join(assets_dir, "feature_config.json"), "w", encoding="utf-8") as f:
        json.dump({"semantic_weight": float(semantic_weight),
                   "structural_weight": float(structural_weight),
                   "window": window_cfg,
                   "l2_norm": bool(l2_norm_before_cluster)}, f, ensure_ascii=False, indent=2)
    # struct scaler
    try:
        import joblib
        joblib.dump(struct_scaler, os.path.join(assets_dir, "struct_scaler.joblib"))
    except Exception:
        with open(os.path.join(assets_dir, "struct_scaler.json"), "w", encoding="utf-8") as f:
            json.dump(struct_scaler, f, ensure_ascii=False, indent=2)
    # clustering PCA (optional)
    if clustering_pca:
        try:
            import joblib
            joblib.dump(clustering_pca, os.path.join(assets_dir, "clustering_pca.joblib"))
        except Exception:
            with open(os.path.join(assets_dir, "clustering_pca.json"), "w", encoding="utf-8") as f:
                json.dump(clustering_pca, f, ensure_ascii=False, indent=2)
    # lexicon snapshot
    with open(os.path.join(assets_dir, "lexicon_snapshot.json"), "w", encoding="utf-8") as f:
        json.dump(lexicon_snapshot, f, ensure_ascii=False, indent=2)

# -----------------------------
# I/O helpers
# -----------------------------
def save_json(save_dir: str, name: str, obj):
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {name} -> {path}")

def save_labels_csv(save_dir: str,
                    starts: List[int],
                    ends: List[int],
                    cluster_ids: np.ndarray,
                    cluster_names: List[str],
                    sim_to_center: Optional[List[float]] = None,
                    progress: Optional[List[float]] = None,
                    filename: str = "labels.csv"):
    os.makedirs(save_dir, exist_ok=True)
    df = pd.DataFrame({
        "start_idx": starts,
        "end_idx": ends,
        "cluster_id": cluster_ids.astype(int),
        "cluster_name": cluster_names
    })
    if sim_to_center is not None:
        df["sim_to_center"] = sim_to_center
    if progress is not None:
        df["progress_score"] = progress
    path = os.path.join(save_dir, filename)
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info(f"Saved {filename} -> {path}")

# -----------------------------
# Public pipeline
# -----------------------------
def tri_cluster_pipeline(all_texts: List[str],
                         batch_size: int = 12,
                         overlap: int = 4,
                         semantic_mode: str = "st",
                         embed_model_name: str = "sentence-transformers/all-mpnet-base-v2",
                         semantic_weight: float = 0.2,
                         structural_weight: float = 0.8,
                         topk_neighbors: int = 12,
                         lexicon_json: Optional[str] = None,
                         use_fixed_mapping_for_debug: bool = False,
                         pca_dim: Optional[int] = None,
                         pca_var: Optional[float] = None,
                         l2_norm_before_cluster: bool = True,
                         silhouette_sample: int = 0
                         ) -> Dict[str, Any]:
    """
    Returns a dict with:
      - windows, excerpts, features dataframe
      - X_raw (concat space), X (after optional L2 + PCA used for clustering), labels
      - cluster centers (mean of X per label), review bundle, medoids/prototypes
      - silhouette metrics, sims to center, progress means, default name map (optional)
      - struct scaler, lexicon snapshot, clustering PCA (if used), L2 flag
    """
    # 1) windows
    windows = make_windows(len(all_texts), batch_size=batch_size, overlap=overlap)

    # 2) lexicon
    lex = default_lexicon()
    if lexicon_json and os.path.exists(lexicon_json):
        try:
            ext = json.load(open(lexicon_json, "r", encoding="utf-8"))
            for k in ("done","stuck","ai_wrong"):
                if k in ext and isinstance(ext[k], list):
                    lex[k].extend(ext[k])
        except Exception as e:
            logger.warning(f"Failed to load lexicon {lexicon_json}: {e}")
    regexes = build_regexes(lex); lexicon_snapshot = lex

    # 3) structural features
    cfg = FeatureConfig(max_lines=12, semantic_weight=semantic_weight, structural_weight=structural_weight)
    feat_df, excerpts = features_for_windows(all_texts, windows, regexes, cfg)

    # 4) semantics
    backend = SemanticBackend(mode=semantic_mode, model_name=embed_model_name)
    sem = build_semantic_matrix(excerpts, backend)

    # 5) combine
    X_raw, struct_cols, struct_scaler = combine_semantic_structural(sem, feat_df, cfg)

    # 6) optional L2 + PCA for clustering space
    X_for = X_raw
    if l2_norm_before_cluster:
        X_for = l2_normalize_rows(X_for)
    clustering_pca = None
    if (pca_dim is not None) ^ (pca_var is not None):
        X_for, clustering_pca = fit_pca_for_clustering(X_for, pca_dim=pca_dim, pca_var=pca_var)
        # L2 again after PCA to align with cosine KMeans
        if l2_norm_before_cluster:
            X_for = l2_normalize_rows(X_for)

    # 7) KMeans (Euclidean; with L2 equals Cosine space)
    centers, labels = kmeans(X_for, k=3, n_init=100, iters=800, seed=23)
    feat_df["cluster"] = labels

    # 8) similarity to center (for each window)
    sims = []
    for i in range(len(feat_df)):
        cid = labels[i]
        C = X_for[labels==cid].mean(axis=0, keepdims=True)
        sims.append(float(1.0 / (1.0 + float(((X_for[i]-C[0])**2).sum()))))

    # 9) review bundle (use X_for for neighbor ranking)
    review = build_cluster_review(all_texts, windows, X_for, labels, topk_neighbors, feat_df, msg_preview=6, char_limit=1200)

    # 10) medoids / prototypes
    mp = compute_medoid_and_prototypes(X_for, labels, k=3, topk=min(topk_neighbors, 12))

    # 11) silhouette (on X_for)
    sil = compute_silhouette_scores(X_for, labels, sample_size=silhouette_sample)

    # 12) default naming map (OPTIONAL: quick draft; final mapping按你人工审核)
    names_map, means = name_clusters_by_progress(labels, feat_df["progress_score"].to_numpy(), use_fixed_mapping=use_fixed_mapping_for_debug)

    # 13) centers (mean-of-points in X_for)
    centers_mean = compute_cluster_centers(X_for, labels)

    # 14) starts/ends
    starts = feat_df["start_idx"].tolist()
    ends = feat_df["end_idx"].tolist()

    return {
        "windows": windows,
        "excerpts": excerpts,
        "feat_df": feat_df,
        "X_raw": X_raw,
        "X": X_for,
        "labels": labels,
        "centers": centers_mean,
        "sims": sims,
        "review": review,
        "medoid_proto": mp,
        "silhouette": sil,
        "means": means,
        "names_map_default": names_map,
        "starts": starts,
        "ends": ends,
        "struct_scaler": struct_scaler,
        "lexicon_snapshot": lexicon_snapshot,
        "clustering_pca": clustering_pca,
        "used_l2_norm": bool(l2_norm_before_cluster)
    }
