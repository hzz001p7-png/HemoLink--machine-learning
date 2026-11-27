"""Pipeline de treinamento, validação cruzada por grupo, calibração e exportação do modelo."""

from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRanker
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.pipeline import Pipeline

from .data_generator import (
    UCI_TRANSFUSION_REFERENCE_STATS,
    generate_training_dataset,
)
from .evaluate import evaluate_predictions, generate_evaluation_plots
from .features import ALL_FEATURES, create_preprocessor

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_ARTIFACT_PATH = ARTIFACTS_DIR / "donor_matcher_v1.joblib"
METRICS_REPORT_PATH = ARTIFACTS_DIR / "metrics_report.json"
DATASET_PATH = ARTIFACTS_DIR / "training_dataset.csv"
PLOTS_DIR = ARTIFACTS_DIR / "plots"


def _heuristic_distance_scores(df: pd.DataFrame) -> np.ndarray:
    """Baseline não-ML: ordena candidatos exclusivamente por proximidade geográfica."""
    return np.exp(-df["distancia_km"].to_numpy(dtype=float) / 25.0)


def _make_lgbm_classifier(seed: int = 42) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocessor", create_preprocessor(scale_numeric=False)),
            (
                "model",
                LGBMClassifier(
                    n_estimators=220,
                    learning_rate=0.04,
                    max_depth=5,
                    num_leaves=15,
                    min_child_samples=60,
                    subsample=0.82,
                    subsample_freq=1,
                    colsample_bytree=0.82,
                    reg_alpha=1.0,
                    reg_lambda=4.0,
                    random_state=seed,
                    n_jobs=1,
                    verbosity=-1,
                ),
            ),
        ]
    )


def _make_logistic_regression(seed: int = 42) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocessor", create_preprocessor(scale_numeric=True)),
            (
                "model",
                LogisticRegression(
                    C=1.0,
                    max_iter=1000,
                    random_state=seed,
                ),
            ),
        ]
    )


def _make_random_forest(seed: int = 42) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocessor", create_preprocessor(scale_numeric=False)),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=150,
                    max_depth=12,
                    min_samples_leaf=18,
                    random_state=seed,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def _group_sizes(series: pd.Series) -> List[int]:
    """Calcula tamanhos de grupo preservando a ordem contígua por pedido_id."""
    return [int(size) for _, size in series.groupby(series, sort=False).size().items()]


def _fit_and_predict_lgbm_ranker(
    df_train: pd.DataFrame,
    df_test: pd.DataFrame,
    seed: int = 42,
) -> Tuple[Any, np.ndarray]:
    """Treina um LGBMRanker (Learning-to-Rank com LambdaRank) agrupado por pedido_id."""
    train_sorted = df_train.sort_values("pedido_id", kind="mergesort")
    pre = create_preprocessor(scale_numeric=False)
    X_tr = pre.fit_transform(train_sorted[ALL_FEATURES])
    y_tr = train_sorted["relevancia"].to_numpy(dtype=int)
    groups = _group_sizes(train_sorted["pedido_id"])

    ranker = LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        n_estimators=220,
        learning_rate=0.04,
        max_depth=5,
        num_leaves=15,
        min_child_samples=60,
        subsample=0.82,
        subsample_freq=1,
        colsample_bytree=0.82,
        reg_alpha=1.0,
        reg_lambda=4.0,
        random_state=seed,
        n_jobs=1,
        verbosity=-1,
    )
    ranker.fit(X_tr, y_tr, group=groups)

    X_te = pre.transform(df_test[ALL_FEATURES])
    scores = ranker.predict(X_te)
    return (pre, ranker), scores


def _cross_validate_classifier(
    builder_fn: Any,
    df_train: pd.DataFrame,
    n_splits: int = 5,
    seed: int = 42,
) -> Dict[str, float]:
    """Executa GroupKFold CV rigoroso agrupado por pedido_id."""
    gkf = GroupKFold(n_splits=n_splits)
    X = df_train[ALL_FEATURES]
    y = df_train["match_sucesso"].to_numpy(dtype=int)
    groups = df_train["pedido_id"].to_numpy()

    fold_metrics: List[Dict[str, Any]] = []
    for tr_idx, va_idx in gkf.split(X, y, groups):
        model = builder_fn(seed)
        model.fit(X.iloc[tr_idx], y[tr_idx])
        probs = model.predict_proba(X.iloc[va_idx])[:, 1]
        fold_metrics.append(
            evaluate_predictions(df_train.iloc[va_idx], probs, is_probability=True)
        )

    keys = ["roc_auc", "pr_auc", "brier_score", "ndcg_at_5", "precision_at_3", "mrr"]
    return {
        f"cv_{k}_mean": round(float(np.mean([m[k] for m in fold_metrics])), 4)
        for k in keys
    }


def run_training_pipeline(
    n_requests: int = 1200,
    n_donors: int = 850,
    seed: int = 42,
    save_artifacts: bool = True,
) -> Dict[str, Any]:
    """Executa o ciclo completo: dados -> split por grupo -> CV -> calibração -> SHAP -> artefatos."""
    warnings.filterwarnings("ignore", category=UserWarning)

    df = generate_training_dataset(
        n_requests=n_requests,
        n_donors=n_donors,
        seed=seed,
    )

    # Split rigoroso por grupo (pedido_id nunca aparece simultaneamente em treino e teste)
    gss = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=seed)
    train_idx, test_idx = next(
        gss.split(df, df["match_sucesso"], groups=df["pedido_id"])
    )
    df_train = df.iloc[train_idx].reset_index(drop=True)
    df_test = df.iloc[test_idx].reset_index(drop=True)

    # Garantia explícita anti-vazamento
    overlap = set(df_train["pedido_id"]).intersection(set(df_test["pedido_id"]))
    assert len(overlap) == 0, f"Vazamento de dados detectado: {len(overlap)} pedidos repetidos!"

    X_train = df_train[ALL_FEATURES]
    y_train = df_train["match_sucesso"].to_numpy(dtype=int)
    groups_train = df_train["pedido_id"].to_numpy()
    X_test = df_test[ALL_FEATURES]

    model_scores: Dict[str, np.ndarray] = {}
    metrics_by_model: Dict[str, Dict[str, Any]] = {}
    cv_summary: Dict[str, Dict[str, float]] = {}

    # 1. Baseline Heurístico (apenas distância)
    heur_scores = _heuristic_distance_scores(df_test)
    model_scores["Baseline Distância"] = heur_scores
    metrics_by_model["Baseline Distância"] = evaluate_predictions(
        df_test, heur_scores, is_probability=True
    )

    # 2. Regressão Logística
    cv_summary["Regressão Logística"] = _cross_validate_classifier(
        _make_logistic_regression, df_train, n_splits=5, seed=seed
    )
    lr_pipe = _make_logistic_regression(seed)
    lr_pipe.fit(X_train, y_train)
    lr_probs = lr_pipe.predict_proba(X_test)[:, 1]
    model_scores["Regressão Logística"] = lr_probs
    metrics_by_model["Regressão Logística"] = evaluate_predictions(
        df_test, lr_probs, is_probability=True
    )

    # 3. Random Forest
    cv_summary["Random Forest"] = _cross_validate_classifier(
        _make_random_forest, df_train, n_splits=5, seed=seed
    )
    rf_pipe = _make_random_forest(seed)
    rf_pipe.fit(X_train, y_train)
    rf_probs = rf_pipe.predict_proba(X_test)[:, 1]
    model_scores["Random Forest"] = rf_probs
    metrics_by_model["Random Forest"] = evaluate_predictions(
        df_test, rf_probs, is_probability=True
    )

    # 4. LightGBM (Classifier)
    cv_summary["LightGBM"] = _cross_validate_classifier(
        _make_lgbm_classifier, df_train, n_splits=5, seed=seed
    )
    lgbm_pipe = _make_lgbm_classifier(seed)
    lgbm_pipe.fit(X_train, y_train)
    lgbm_probs = lgbm_pipe.predict_proba(X_test)[:, 1]
    model_scores["LightGBM"] = lgbm_probs
    metrics_by_model["LightGBM"] = evaluate_predictions(
        df_test, lgbm_probs, is_probability=True
    )

    # 5. LightGBM Calibrado (Isotônico com splits GroupKFold pré-computados -> zero leakage)
    gkf_splits = list(GroupKFold(n_splits=5).split(X_train, y_train, groups_train))
    calibrated_lgbm = CalibratedClassifierCV(
        estimator=_make_lgbm_classifier(seed),
        method="isotonic",
        cv=gkf_splits,
    )
    calibrated_lgbm.fit(X_train, y_train)
    cal_probs = calibrated_lgbm.predict_proba(X_test)[:, 1]
    model_scores["LightGBM Calibrado"] = cal_probs
    metrics_by_model["LightGBM Calibrado"] = evaluate_predictions(
        df_test, cal_probs, is_probability=True
    )

    # 6. LightGBM Ranker (Learning-to-Rank com LambdaRank)
    _, ranker_scores = _fit_and_predict_lgbm_ranker(df_train, df_test, seed=seed)
    model_scores["LGBMRanker (LambdaRank)"] = ranker_scores
    metrics_by_model["LGBMRanker (LambdaRank)"] = evaluate_predictions(
        df_test, ranker_scores, is_probability=False
    )

    report: Dict[str, Any] = {
        "model_version": "1.0.0",
        "selected_production_model": "LightGBM Calibrado",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "dataset_summary": {
            "total_pairs": int(len(df)),
            "train_pairs": int(len(df_train)),
            "test_pairs": int(len(df_test)),
            "total_requests": int(df["pedido_id"].nunique()),
            "train_requests": int(df_train["pedido_id"].nunique()),
            "test_requests": int(df_test["pedido_id"].nunique()),
            "positive_rate_total": round(float(df["match_sucesso"].mean()), 4),
            "positive_rate_test": round(float(df_test["match_sucesso"].mean()), 4),
            "cold_start_donor_rate": round(float(df["eh_doador_novo"].mean()), 4),
            "uci_reference": UCI_TRANSFUSION_REFERENCE_STATS,
        },
        "cv_5fold_group_metrics": cv_summary,
        "test_metrics": metrics_by_model,
    }

    if save_artifacts:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(DATASET_PATH, index=False)

        plots = generate_evaluation_plots(
            df_test=df_test,
            model_scores=model_scores,
            metrics_by_model=metrics_by_model,
            explainer_pipeline=lgbm_pipe,
            X_test=X_test,
            output_dir=PLOTS_DIR,
        )
        report["plots"] = plots

        feature_names_out = list(
            lgbm_pipe.named_steps["preprocessor"].get_feature_names_out()
        )
        artifact_bundle = {
            "model_version": report["model_version"],
            "selected_model_name": report["selected_production_model"],
            "trained_at": report["trained_at"],
            "calibrated_model": calibrated_lgbm,
            "explainer_pipeline": lgbm_pipe,
            "feature_columns": ALL_FEATURES,
            "feature_names_out": feature_names_out,
            "metrics_summary": report["test_metrics"]["LightGBM Calibrado"],
        }
        joblib.dump(artifact_bundle, MODEL_ARTIFACT_PATH)
        METRICS_REPORT_PATH.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return report


def main() -> None:
    report = run_training_pipeline()
    ds = report["dataset_summary"]
    print("=== HemoLink ML — Relatório de Treinamento ===")
    print(
        f"Pares totais: {ds['total_pairs']} | Pedidos: {ds['total_requests']} "
        f"| Taxa de sucesso: {ds['positive_rate_total']:.1%}"
    )
    print("\nMétricas no conjunto de teste isolado (GroupSplit por pedido_id):")
    header = f"{'Modelo':<26} {'ROC-AUC':>8} {'PR-AUC':>8} {'Brier':>8} {'NDCG@5':>8} {'P@3':>8} {'MRR':>8}"
    print(header)
    print("-" * len(header))
    for name, m in report["test_metrics"].items():
        brier_str = f"{m['brier_score']:.4f}" if m["brier_score"] is not None else "   n/a"
        print(
            f"{name:<26} {m['roc_auc']:>8.4f} {m['pr_auc']:>8.4f} {brier_str:>8} "
            f"{m['ndcg_at_5']:>8.4f} {m['precision_at_3']:>8.4f} {m['mrr']:>8.4f}"
        )
    print(f"\nModelo salvo em: {MODEL_ARTIFACT_PATH}")
    print(f"Relatório salvo em: {METRICS_REPORT_PATH}")


if __name__ == "__main__":
    main()
