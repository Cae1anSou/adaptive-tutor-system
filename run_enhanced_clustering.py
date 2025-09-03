#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_enhanced_clustering.py

Entry script for tri-clustering over student–AI chat windows.
- Reads JSON with {"data":[{"translated_text": "..."}]} (falls back to "original_text" if needed).
- Produces:
  * window_features.csv
  * cluster_review.json  (per-cluster neighbors for manual audit)
  * cluster_scatter.png  (+ PCA components for the fig & X_pca.npy)
  * silhouette.json / silhouette_bar.png
  * label_map.template.json (sorted by cluster mean progress; YOU edit to '超进度/正常/低进度')
  * labels.csv (if --label_map provided, apply to all windows)
  * struct_scaler.joblib
  * (optional) clustering_pca.joblib (if --pca_dim/--pca_var used)
  * cluster_centers.joblib (if --export_assets, together with other assets)
"""

import os, json, argparse
from pathlib import Path
import numpy as np
import pandas as pd

from enhanced_cluster_analysis import (
    tri_cluster_pipeline,
    save_json, save_labels_csv,
    visualize_clusters_2d, compute_cluster_centers,
    freeze_assets
)

def load_texts(path: str):
    """Load translated_texts from a single JSON or a directory of JSONs."""
    texts = []
    p = Path(path)
    files = []
    if p.is_dir():
        files = sorted([f for f in p.glob("*.json")])
    elif p.is_file() and p.suffix.lower() == ".json":
        files = [p]
    else:
        raise ValueError(f"Invalid input path: {path}")
    for fp in files:
        try:
            obj = json.load(open(fp, "r", encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] skip {fp}: {e}")
            continue
        if isinstance(obj, dict) and isinstance(obj.get("data"), list):
            for item in obj["data"]:
                if not isinstance(item, dict): continue
                t = item.get("translated_text") or item.get("original_text")
                if isinstance(t, str) and t.strip():
                    texts.append(t.strip())
        else:
            print(f"[WARN] structure not matched in {fp}, expect dict->data[list]->translated_text")
    print(f"[loader] Parsed texts = {len(texts)}")
    return texts

def export_pca_visuals(X, labels, save_dir, medoid_indices=None):
    import numpy as np
    uniq = sorted(set(labels.tolist() if hasattr(labels, "tolist") else list(labels)))
    centers = np.vstack([X[labels == c].mean(axis=0) for c in uniq]).astype(np.float32)
    fig_path = str(Path(save_dir) / "cluster_scatter.png")
    visualize_clusters_2d(
        X=X, labels=labels, centers=centers,
        save_path=fig_path, title="Progress Clusters (PCA-2D)",
        medoid_indices=medoid_indices, show_2d_mean_centers=True, figsize=(9,7)
    )
    return fig_path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSON file or directory containing JSONs")
    ap.add_argument("--save_dir", required=True, help="Output directory")
    ap.add_argument("--semantic_mode", default="st", choices=["st","hash","none"])
    ap.add_argument("--embed_model", default="sentence-transformers/all-mpnet-base-v2")
    ap.add_argument("--semantic_weight", type=float, default=0.2)
    ap.add_argument("--structural_weight", type=float, default=0.8)
    ap.add_argument("--batch_size", type=int, default=12)
    ap.add_argument("--overlap", type=int, default=4)
    ap.add_argument("--near_k", type=int, default=12, help="Neighbors per cluster for review")
    ap.add_argument("--lexicon_json", default=None, help="Optional extra lexicon JSON")
    # PCA/L2 & quality
    ap.add_argument("--pca_dim", type=int, default=None, help="Pre-cluster PCA fixed dimension (exclusive with --pca_var)")
    ap.add_argument("--pca_var", type=float, default=None, help="Pre-cluster PCA cumulative variance threshold, e.g., 0.95")
    ap.add_argument("--no_l2_norm", action="store_true", help="Disable L2 normalization before clustering (default: enabled)")
    ap.add_argument("--silhouette_sample", type=int, default=0, help="Sampling size for silhouette (0 means all)")
    # labeling & export
    ap.add_argument("--label_map", default=None, help="Path to a JSON mapping {cluster_id: '超进度|正常|低进度'}")
    ap.add_argument("--export_assets", default=None, help="Directory to freeze online model assets")
    ap.add_argument("--use_fixed_mapping_for_debug", action="store_true", help="Quick draft naming by cluster mean progress")

    args = ap.parse_args()
    os.makedirs(args.save_dir, exist_ok=True)

    texts = load_texts(args.input)

    out = tri_cluster_pipeline(
        texts,
        batch_size=args.batch_size,
        overlap=args.overlap,
        semantic_mode=args.semantic_mode,
        embed_model_name=args.embed_model,
        semantic_weight=args.semantic_weight,
        structural_weight=args.structural_weight,
        topk_neighbors=args.near_k,
        lexicon_json=args.lexicon_json,
        use_fixed_mapping_for_debug=args.use_fixed_mapping_for_debug,
        pca_dim=args.pca_dim,
        pca_var=args.pca_var,
        l2_norm_before_cluster=(not args.no_l2_norm),
        silhouette_sample=args.silhouette_sample
    )

    # 1) window features csv
    feat = out["feat_df"].copy()
    feat.to_csv(str(Path(args.save_dir) / "window_features.csv"), index=False, encoding="utf-8")
    print(f"[save] window_features.csv -> {args.save_dir}")

    # 2) review bundle (for manual auditing)
    save_json(args.save_dir, "cluster_review.json", out["review"])

    # 3) silhouette
    save_json(args.save_dir, "silhouette.json", out["silhouette"])
    # small bar figure
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        pcs = out["silhouette"]["per_cluster"]
        xs = ["overall"] + [f"c{cid}" for cid in sorted(pcs.keys())]
        ys = [out["silhouette"]["overall"]] + [pcs[cid] for cid in sorted(pcs.keys())]
        plt.figure(figsize=(7.2, 4.2)); plt.bar(xs, ys); plt.ylim(-1,1); plt.ylabel("silhouette")
        plt.title("Silhouette (overall & per-cluster)"); plt.tight_layout()
        plt.savefig(str(Path(args.save_dir)/"silhouette_bar.png"), dpi=160); plt.close()
    except Exception as e:
        print(f"[warn] silhouette plot failed: {e}")

    # 4) PCA-2D visualization (use the clustering space 'X')
    meds = out["medoid_proto"]
    medoid_indices = [meds[int(c)]["medoid"] for c in sorted(set(out["labels"])) if meds[int(c)]["medoid"] is not None]
    export_pca_visuals(out["X"], out["labels"], args.save_dir, medoid_indices=medoid_indices)

    # 5) label map template (sorted by mean progress)
    means = out["means"]
    order = [c for c,_ in sorted(means.items(), key=lambda kv: kv[1])]
    template = {str(int(c)): "低进度" if i==0 else ("正常" if i==1 else "超进度") for i,c in enumerate(order[:3])}
    save_json(args.save_dir, "label_map.template.json", {
        "by_mean_progress_sorted": [{ "cluster_id": int(c), "mean_progress": float(means[c]) } for c in order],
        "template_mapping": template,
        "note": "请人工确认每个簇的标签，并另存为 label_map.json 后重跑本脚本加 --label_map 使用。"
    })

    # 6) if user supplies label_map, output labels.csv with names
    names_map = None
    if args.label_map and os.path.exists(args.label_map):
        try:
            lm = json.load(open(args.label_map, "r", encoding="utf-8"))
            names_map = {int(k): str(v) for k,v in lm.items()}
        except Exception as e:
            print(f"[WARN] load label_map failed: {e}")
    if names_map:
        named = [names_map.get(int(cid), f"Cluster-{int(cid)}") for cid in out["labels"]]
        save_labels_csv(args.save_dir,
                        starts=out["starts"], ends=out["ends"],
                        cluster_ids=out["labels"], cluster_names=named,
                        sim_to_center=out["sims"],
                        progress=out["feat_df"]["progress_score"].tolist(),
                        filename="labels.csv")

    # 7) Save struct scaler snapshot
    try:
        import joblib
        joblib.dump(out["struct_scaler"], str(Path(args.save_dir) / "struct_scaler.joblib"))
    except Exception:
        json.dump(out["struct_scaler"], open(str(Path(args.save_dir) / "struct_scaler.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 8) Save clustering PCA if used
    if out.get("clustering_pca"):
        try:
            import joblib
            joblib.dump(out["clustering_pca"], str(Path(args.save_dir) / "clustering_pca.joblib"))
        except Exception:
            json.dump(out["clustering_pca"], open(str(Path(args.save_dir) / "clustering_pca.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 9) Save cluster report summary
    save_json(args.save_dir, "cluster_report.json", {
        "semantic_mode_used": args.semantic_mode,
        "embed_model": args.embed_model,
        "silhouette_overall": float(out["silhouette"]["overall"]),
        "silhouette_per_cluster": {int(k): float(v) for k,v in out["silhouette"]["per_cluster"].items()},
        "cluster_mean_progress": {int(k): float(v) for k,v in out["means"].items()}
    })

    # 10) Export assets for online assignment (optional; requires label_map)
    if args.export_assets:
        if not names_map:
            print("[WARN] --export_assets supplied but no --label_map. Assets will be exported with empty label_map.json.")
            names_map = {}
        centers = out["centers"]  # mean-of-points in the clustering space
        freeze_assets(
            save_dir=args.save_dir,
            assets_dir=args.export_assets,
            centers=centers,
            label_map=names_map,
            semantic_mode=args.semantic_mode,
            embed_model=args.embed_model,
            semantic_weight=args.semantic_weight,
            structural_weight=args.structural_weight,
            struct_scaler=out["struct_scaler"],
            lexicon_snapshot=out["lexicon_snapshot"],
            window_cfg={"batch_size": args.batch_size, "overlap": args.overlap, "max_lines": 12},
            clustering_pca=out.get("clustering_pca"),
            l2_norm_before_cluster=(not args.no_l2_norm)
        )
        print(f"[save] assets exported -> {args.export_assets}")

if __name__ == "__main__":
    main()
