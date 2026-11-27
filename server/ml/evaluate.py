"""Métricas de classificação, calibração, ranking e gráficos de avaliação (incluindo SHAP)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "hemolink_mpl"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


def _dcg(relevances: np.ndarray, k: int) -> float:
    rel = np.asarray(relevances, dtype=float)[:k]
    if rel.size == 0:
        return 0.0
    discounts = np.log2(np.arange(2, rel.size + 2))
    return float(np.sum((2.0**rel - 1.0) / discounts))


def compute_ranking_metrics(
    df_eval: pd.DataFrame,
    scores: np.ndarray,
    group_col: str = "pedido_id",
    target_col: str = "match_sucesso",
    rel_col: str = "relevancia",
    k_ndcg: int = 5,
    k_prec: int = 3,
    k_rec: int = 5,
) -> Dict[str, float]:
    """Calcula NDCG@K, Precision@K, Recall@K e MRR agrupados por pedido_id."""
    work = df_eval[[group_col, target_col, rel_col]].copy()
    work["_score"] = np.asarray(scores, dtype=float)

    ndcg_list: List[float] = []
    prec_list: List[float] = []
    rec_list: List[float] = []
    mrr_list: List[float] = []

    for _, grp in work.groupby(group_col, sort=False):
        ordered = grp.sort_values("_score", ascending=False)
        rels = ordered[rel_col].to_numpy()
        y_bin = ordered[target_col].to_numpy()

        ideal_rels = np.sort(rels)[::-1]
        idcg = _dcg(ideal_rels, k_ndcg)
        if idcg > 0:
            ndcg_list.append(_dcg(rels, k_ndcg) / idcg)

        top_p = y_bin[:k_prec]
        prec_list.append(float(np.mean(top_p)) if len(top_p) > 0 else 0.0)

        total_pos = int(np.sum(y_bin))
        if total_pos > 0:
            rec_list.append(float(np.sum(y_bin[:k_rec]) / total_pos))
            pos_positions = np.where(y_bin == 1)[0]
            mrr_list.append(1.0 / (int(pos_positions[0]) + 1))

    return {
        f"ndcg_at_{k_ndcg}": round(float(np.mean(ndcg_list)) if ndcg_list else 0.0, 4),
        f"precision_at_{k_prec}": round(float(np.mean(prec_list)) if prec_list else 0.0, 4),
        f"recall_at_{k_rec}": round(float(np.mean(rec_list)) if rec_list else 0.0, 4),
        "mrr": round(float(np.mean(mrr_list)) if mrr_list else 0.0, 4),
    }


def evaluate_predictions(
    df_eval: pd.DataFrame,
    scores: np.ndarray,
    is_probability: bool = True,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """Avalia um conjunto de predições com métricas de classificação, calibração e ranking."""
    y_true = df_eval["match_sucesso"].to_numpy(dtype=int)
    scores_arr = np.asarray(scores, dtype=float)

    metrics: Dict[str, Any] = {
        "roc_auc": round(float(roc_auc_score(y_true, scores_arr)), 4),
        "pr_auc": round(float(average_precision_score(y_true, scores_arr)), 4),
    }

    if is_probability:
        probs = np.clip(scores_arr, 1e-6, 1.0 - 1e-6)
        preds = (probs >= threshold).astype(int)
        metrics.update(
            {
                "f1": round(float(f1_score(y_true, preds, zero_division=0)), 4),
                "precision": round(float(precision_score(y_true, preds, zero_division=0)), 4),
                "recall": round(float(recall_score(y_true, preds, zero_division=0)), 4),
                "brier_score": round(float(brier_score_loss(y_true, probs)), 4),
                "log_loss": round(float(log_loss(y_true, probs)), 4),
            }
        )
    else:
        metrics.update(
            {
                "f1": None,
                "precision": None,
                "recall": None,
                "brier_score": None,
                "log_loss": None,
            }
        )

    metrics.update(compute_ranking_metrics(df_eval, scores_arr))
    return metrics


def generate_evaluation_plots(
    df_test: pd.DataFrame,
    model_scores: Dict[str, np.ndarray],
    metrics_by_model: Dict[str, Dict[str, Any]],
    explainer_pipeline: Any,
    X_test: pd.DataFrame,
    output_dir: Path,
) -> Dict[str, str]:
    """Gera gráficos acadêmicos (Comparativo, ROC/PR, Calibração e SHAP) em PNG."""
    output_dir.mkdir(parents=True, exist_ok=True)
    y_test = df_test["match_sucesso"].to_numpy(dtype=int)
    saved_paths: Dict[str, str] = {}

    # 1. Comparação geral de modelos (Barras agrupadas)
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    model_names = list(metrics_by_model.keys())
    metric_keys = ["roc_auc", "pr_auc", "ndcg_at_5", "precision_at_3"]
    metric_labels = ["ROC-AUC", "PR-AUC", "NDCG@5", "Precision@3"]
    x = np.arange(len(model_names))
    width = 0.19
    colors = ["#C8102E", "#2B2B30", "#E07A5F", "#3D7EA6"]

    for i, (m_key, m_label, color) in enumerate(zip(metric_keys, metric_labels, colors)):
        vals = [metrics_by_model[m][m_key] for m in model_names]
        bars = ax.bar(x + (i - 1.5) * width, vals, width, label=m_label, color=color)
        for bar in bars:
            h = bar.get_height()
            ax.annotate(
                f"{h:.2f}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7.5,
            )

    ax.set_ylabel("Pontuação (0 a 1)")
    ax.set_title("HemoLink ML — Comparativo de Modelos no Conjunto de Teste (GroupSplit)")
    ax.set_xticks(x)
    ax.set_xticklabels(model_names, rotation=12, ha="right")
    ax.set_ylim(0, 1.08)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(frameon=False, ncol=4, loc="upper center")
    fig.tight_layout()
    p_comp = output_dir / "model_comparison.png"
    fig.savefig(p_comp, dpi=160)
    plt.close(fig)
    saved_paths["model_comparison"] = str(p_comp)

    # 2. Curvas ROC e Precision-Recall
    fig, (ax_roc, ax_pr) = plt.subplots(1, 2, figsize=(11.5, 4.8))
    for name, scores in model_scores.items():
        fpr, tpr, _ = roc_curve(y_test, scores)
        auc_v = roc_auc_score(y_test, scores)
        ax_roc.plot(fpr, tpr, linewidth=1.8, label=f"{name} (AUC={auc_v:.3f})")

        prec, rec, _ = precision_recall_curve(y_test, scores)
        ap_v = average_precision_score(y_test, scores)
        ax_pr.plot(rec, prec, linewidth=1.8, label=f"{name} (AP={ap_v:.3f})")

    ax_roc.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax_roc.set_title("Curva ROC")
    ax_roc.set_xlabel("Taxa de Falsos Positivos")
    ax_roc.set_ylabel("Taxa de Verdadeiros Positivos")
    ax_roc.legend(fontsize=8, loc="lower right")
    ax_roc.grid(alpha=0.3)

    ax_pr.axhline(y_test.mean(), color="k", linestyle="--", alpha=0.4, label="Aleatório")
    ax_pr.set_title("Curva Precision-Recall")
    ax_pr.set_xlabel("Recall")
    ax_pr.set_ylabel("Precision")
    ax_pr.legend(fontsize=8, loc="upper right")
    ax_pr.grid(alpha=0.3)

    fig.tight_layout()
    p_roc = output_dir / "roc_pr_curves.png"
    fig.savefig(p_roc, dpi=160)
    plt.close(fig)
    saved_paths["roc_pr_curves"] = str(p_roc)

    # 3. Curva de Calibração (apenas modelos probabilísticos)
    fig, ax = plt.subplots(figsize=(6.5, 5.2))
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Calibração perfeita")
    for name, scores in model_scores.items():
        if metrics_by_model[name]["brier_score"] is None:
            continue
        prob_true, prob_pred = calibration_curve(
            y_test, np.clip(scores, 0.0, 1.0), n_bins=10, strategy="quantile"
        )
        brier = metrics_by_model[name]["brier_score"]
        ax.plot(prob_pred, prob_true, marker="o", linewidth=1.6, label=f"{name} (Brier={brier:.3f})")

    ax.set_title("Curva de Calibração de Probabilidades (Score 0–100%)")
    ax.set_xlabel("Probabilidade média prevista")
    ax.set_ylabel("Frequência real observada")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    p_cal = output_dir / "calibration_curve.png"
    fig.savefig(p_cal, dpi=160)
    plt.close(fig)
    saved_paths["calibration_curve"] = str(p_cal)

    # 4. Explicabilidade SHAP (Global + Local)
    try:
        preprocessor = explainer_pipeline.named_steps["preprocessor"]
        estimator = explainer_pipeline.named_steps["model"]
        X_sample = X_test.iloc[: min(400, len(X_test))]
        X_trans = preprocessor.transform(X_sample)
        feature_names = list(preprocessor.get_feature_names_out())

        explainer = shap.TreeExplainer(estimator)
        shap_vals_raw = explainer.shap_values(X_trans)
        if isinstance(shap_vals_raw, list):
            shap_vals = shap_vals_raw[1]
            expected_val = explainer.expected_value[1]
        elif getattr(shap_vals_raw, "ndim", 2) == 3:
            shap_vals = shap_vals_raw[:, :, 1]
            expected_val = explainer.expected_value[1]
        else:
            shap_vals = shap_vals_raw
            expected_val = (
                float(explainer.expected_value[0])
                if isinstance(explainer.expected_value, (list, np.ndarray))
                else float(explainer.expected_value)
            )

        # Global Beeswarm
        plt.figure(figsize=(9.5, 6.0))
        shap.summary_plot(
            shap_vals,
            features=X_trans,
            feature_names=feature_names,
            max_display=14,
            show=False,
        )
        plt.title("SHAP — Impacto Global das Features no Score de Matching")
        plt.tight_layout()
        p_shap_global = output_dir / "shap_summary.png"
        plt.savefig(p_shap_global, dpi=160, bbox_inches="tight")
        plt.close()
        saved_paths["shap_summary"] = str(p_shap_global)

        # Local Waterfall para o candidato de maior score na amostra
        probs_sample = estimator.predict_proba(X_trans)[:, 1]
        best_idx = int(np.argmax(probs_sample))
        exp = shap.Explanation(
            values=shap_vals[best_idx],
            base_values=float(expected_val),
            data=X_trans[best_idx],
            feature_names=feature_names,
        )
        plt.figure(figsize=(9.0, 5.5))
        shap.plots.waterfall(exp, max_display=10, show=False)
        plt.title("SHAP Local — Por que este candidato ficou em 1º lugar?", pad=22)
        plt.tight_layout()
        p_shap_local = output_dir / "shap_waterfall_example.png"
        plt.savefig(p_shap_local, dpi=160, bbox_inches="tight")
        plt.close()
        saved_paths["shap_waterfall"] = str(p_shap_local)
    except Exception as exc:  # pragma: no cover - fallback defensivo
        saved_paths["shap_error"] = str(exc)

    return saved_paths
