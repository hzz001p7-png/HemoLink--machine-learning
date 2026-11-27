"""Serviço de inferência online (Estágio 1: Regras Clínicas + Estágio 2: ML Calibrado + SHAP)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import warnings

import joblib
import numpy as np
import shap

from .compatibility import (
    check_donor_eligibility,
    normalize_blood_type,
    normalize_component,
    normalize_urgency,
)
from .features import (
    ALL_FEATURES,
    build_feature_dataframe,
    build_feature_row,
    normalize_situation,
    summarize_candidate_factors,
)
from .geo import compute_distance_km
from .train import MODEL_ARTIFACT_PATH, run_training_pipeline


class DonorMatcherService:
    """Orquestra o pipeline híbrido de matching de doadores de sangue."""

    def __init__(self, model_path: Path = MODEL_ARTIFACT_PATH) -> None:
        self.model_path = Path(model_path)
        self._bundle: Optional[Dict[str, Any]] = None
        self._tree_explainer: Optional[Any] = None

    def ensure_loaded(self, auto_train_if_missing: bool = True) -> Dict[str, Any]:
        """Carrega o modelo serializado em disco (treina automaticamente se ausente)."""
        if self._bundle is not None:
            return self._bundle

        if not self.model_path.exists():
            if not auto_train_if_missing:
                raise FileNotFoundError(
                    f"Artefato do modelo não encontrado em {self.model_path}. "
                    "Execute `python -m ml.train` para gerar o modelo."
                )
            run_training_pipeline(save_artifacts=True)

        self._bundle = joblib.load(self.model_path)
        # Garante inferência single-thread (evita deadlock de OpenMP do LightGBM em threadpools FastAPI no Windows)
        calibrated = self._bundle.get("calibrated_model")
        if calibrated is not None and hasattr(calibrated, "calibrated_classifiers_"):
            for cc in calibrated.calibrated_classifiers_:
                est = getattr(cc, "estimator", None)
                if est is not None and hasattr(est, "named_steps") and "model" in est.named_steps:
                    mdl = est.named_steps["model"]
                    if hasattr(mdl, "set_params"):
                        mdl.set_params(n_jobs=1)

        explainer_pipe = self._bundle.get("explainer_pipeline")
        if explainer_pipe is not None:
            mdl = explainer_pipe.named_steps.get("model")
            if mdl is not None and hasattr(mdl, "set_params"):
                mdl.set_params(n_jobs=1)
            try:
                self._tree_explainer = shap.TreeExplainer(
                    explainer_pipe.named_steps["model"]
                )
            except Exception:
                self._tree_explainer = None
        return self._bundle

    @property
    def metadata(self) -> Dict[str, Any]:
        bundle = self.ensure_loaded()
        return {
            "model_version": bundle.get("model_version", "1.0.0"),
            "selected_model_name": bundle.get("selected_model_name", "LightGBM Calibrado"),
            "trained_at": bundle.get("trained_at"),
            "feature_columns": bundle.get("feature_columns", ALL_FEATURES),
            "metrics_summary": bundle.get("metrics_summary", {}),
        }

    def _compute_local_shap(
        self, X_df: Any
    ) -> Tuple[List[Dict[str, float]], Optional[List[str]]]:
        """Calcula contribuições SHAP por candidato usando o TreeExplainer."""
        bundle = self.ensure_loaded()
        explainer_pipe = bundle.get("explainer_pipeline")
        if self._tree_explainer is None or explainer_pipe is None or len(X_df) == 0:
            return [{} for _ in range(len(X_df))], None

        preprocessor = explainer_pipe.named_steps["preprocessor"]
        X_trans = preprocessor.transform(X_df)
        feature_names = list(preprocessor.get_feature_names_out())

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            raw_vals = self._tree_explainer.shap_values(X_trans)
        if isinstance(raw_vals, list):
            vals = raw_vals[1]
        elif getattr(raw_vals, "ndim", 2) == 3:
            vals = raw_vals[:, :, 1]
        else:
            vals = raw_vals

        per_row: List[Dict[str, float]] = []
        for i in range(len(X_df)):
            contrib = {
                name: round(float(vals[i, j]), 4)
                for j, name in enumerate(feature_names)
            }
            per_row.append(contrib)
        return per_row, feature_names

    def rank_donors(
        self,
        request: Dict[str, Any],
        donors: List[Dict[str, Any]],
        top_k: int = 10,
        max_distance_km: Optional[float] = None,
        include_shap: bool = True,
        include_temporarily_unavailable: bool = False,
    ) -> Dict[str, Any]:
        """Executa Estágio 1 (triagem clínica) + Estágio 2 (scoring ML calibrado + SHAP)."""
        bundle = self.ensure_loaded()
        calibrated_model = bundle["calibrated_model"]

        req_bt = normalize_blood_type(
            request.get("tipo_sanguineo") or request.get("tipoSanguineo")
        )
        if req_bt is None:
            raise ValueError("Tipo sanguíneo do pedido alvo é obrigatório e deve ser válido (ex.: O-, A+).")

        component = normalize_component(request.get("componente"))
        urgency = normalize_urgency(request.get("urgencia"))
        bolsas_total = int(
            request.get("bolsas_total")
            or request.get("bolsasTotal")
            or request.get("bolsas")
            or 1
        )
        bolsas_recebidas = int(
            request.get("bolsas_recebidas") or request.get("bolsasRecebidas") or 0
        )
        bolsas_faltantes = max(1, bolsas_total - bolsas_recebidas)

        eligible_items: List[Tuple[Dict[str, Any], float, Dict[str, Any]]] = []
        filtered_reasons: Dict[str, int] = {}

        for donor in donors:
            dist = compute_distance_km(donor, request)
            elig = check_donor_eligibility(
                donor=donor,
                recipient_blood_type=req_bt,
                component=component,
                urgency=urgency,
                distance_km=dist,
                max_distance_km=max_distance_km,
            )
            if not elig.eligible:
                for reason in elig.reasons:
                    filtered_reasons[reason] = filtered_reasons.get(reason, 0) + 1
                continue

            sit = normalize_situation(
                donor.get("situacao") or donor.get("situacao_disponibilidade")
            )
            if sit == "indisponivel_temporario" and not include_temporarily_unavailable:
                filtered_reasons["indisponivel_temporario"] = (
                    filtered_reasons.get("indisponivel_temporario", 0) + 1
                )
                continue

            feat_row = build_feature_row(donor, request, distance_km=dist)
            eligible_items.append((donor, dist, feat_row))

        if not eligible_items:
            return {
                "modelo": self.metadata["selected_model_name"],
                "versaoModelo": self.metadata["model_version"],
                "totalAvaliados": len(donors),
                "totalElegiveis": 0,
                "descartadosPorMotivo": filtered_reasons,
                "candidatos": [],
            }

        X_df = build_feature_dataframe(
            [(d, request, dist) for d, dist, _ in eligible_items]
        )
        probs = np.clip(calibrated_model.predict_proba(X_df)[:, 1], 0.0, 1.0)

        shap_rows: List[Dict[str, float]] = [{} for _ in range(len(eligible_items))]
        if include_shap:
            shap_rows, _ = self._compute_local_shap(X_df)

        scored: List[Tuple[float, int, float, Dict[str, Any]]] = []
        for idx, (donor, dist, feat_row) in enumerate(eligible_items):
            prob = float(probs[idx])
            score_pct = int(round(prob * 100))
            score_pct = max(1, min(99, score_pct))
            donor_bt = normalize_blood_type(
                donor.get("tipo_sanguineo") or donor.get("tipoSanguineo")
            ) or ""

            cidade_fmt = str(donor.get("cidade") or "")
            estado_fmt = str(donor.get("estado") or "").upper()
            if cidade_fmt and estado_fmt and f"- {estado_fmt}" not in cidade_fmt.upper():
                cidade_fmt = f"{cidade_fmt} - {estado_fmt}"

            sit_norm = normalize_situation(
                donor.get("situacao") or donor.get("situacao_disponibilidade")
            )
            ui_situacao = (
                "disponivel_agora"
                if sit_norm == "disponivel_agora"
                else "responde_1h"
            )

            factors = summarize_candidate_factors(
                feature_row=feat_row,
                donor_bt=donor_bt,
                shap_contributions=shap_rows[idx],
            )

            top_shap: Dict[str, float] = {}
            if include_shap and shap_rows[idx]:
                ordered_shap = sorted(
                    shap_rows[idx].items(),
                    key=lambda kv: abs(kv[1]),
                    reverse=True,
                )[:5]
                top_shap = dict(ordered_shap)

            candidate_obj: Dict[str, Any] = {
                "codigo": str(donor.get("codigo") or f"D-{idx + 1:04d}"),
                "cidade": cidade_fmt or "Recife - PE",
                "tipoSanguineo": donor_bt,
                "distanciaKm": round(float(dist), 1),
                "compatibilidade": score_pct,
                "probabilidadeCalibrada": round(prob, 4),
                "situacao": ui_situacao,
                "selecionado": False,
                "fatoresPrincipais": factors,
                "explicacaoShap": top_shap,
            }
            scored.append((prob, int(feat_row["is_exact_match"]), -dist, candidate_obj))

        # Ordena por probabilidade calibrada (desempate: match exato e menor distância)
        scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)

        ranked_candidates = [item[3] for item in scored[: max(1, int(top_k))]]
        auto_select_n = min(max(1, min(bolsas_faltantes, 3)), len(ranked_candidates))
        for i, cand in enumerate(ranked_candidates):
            cand["ranking"] = i + 1
            cand["selecionado"] = i < auto_select_n

        return {
            "modelo": self.metadata["selected_model_name"],
            "versaoModelo": self.metadata["model_version"],
            "totalAvaliados": len(donors),
            "totalElegiveis": len(eligible_items),
            "descartadosPorMotivo": filtered_reasons,
            "candidatos": ranked_candidates,
        }


# Instância singleton reutilizada pela API FastAPI
matcher_service = DonorMatcherService()
