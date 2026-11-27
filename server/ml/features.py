"""Engenharia de atributos compartilhada entre treino offline e inferência online.

Garante ausência de train-serve skew: toda transformação aplicada durante o
treinamento é reproduzida exatamente igual na API FastAPI.
Nenhuma PII (nome, CPF, e-mail, celular) é utilizada como feature.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .compatibility import (
    URGENCY_LEVEL_MAP,
    get_blood_prevalence,
    get_universal_preservation_penalty,
    normalize_blood_type,
    normalize_component,
    normalize_urgency,
)
from .geo import compute_distance_km, extract_city_state

NUMERIC_FEATURES: List[str] = [
    "distancia_km",
    "log_distancia_km",
    "interacao_dist_urgencia",
    "raridade_tipo_doador",
    "penalidade_universal",
    "urgencia_nivel",
    "bolsas_faltantes",
    "taxa_aceite_historico",
    "taxa_comparecimento",
    "tempo_medio_resposta_min",
    "dias_desde_ultima_doacao",
    "total_doacoes_anteriores",
    "horas_desde_ultimo_acesso",
    "hora_sin",
    "hora_cos",
    "afinidade_turno_doador",
    "is_exact_match",
    "mesma_cidade",
    "mesmo_estado",
    "fim_de_semana",
    "eh_doador_novo",
]

CATEGORICAL_FEATURES: List[str] = [
    "componente",
    "situacao_disponibilidade",
]

ALL_FEATURES: List[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES

VALID_SITUATIONS = {"disponivel_agora", "responde_1h", "indisponivel_temporario"}


def normalize_situation(value: Optional[str]) -> str:
    """Normaliza a situação de disponibilidade do doador."""
    if not value:
        return "responde_1h"
    v = str(value).strip().lower()
    if v in VALID_SITUATIONS:
        return v
    if "agora" in v or "imediat" in v:
        return "disponivel_agora"
    if "indisp" in v:
        return "indisponivel_temporario"
    return "responde_1h"


def _parse_request_datetime(request: Dict[str, Any]) -> datetime:
    raw = request.get("criado_em") or request.get("criadoEm")
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            iso = raw.strip().replace("Z", "+00:00")
            return datetime.fromisoformat(iso)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _get_shift_from_hour(hour: int) -> str:
    if 6 <= hour < 12:
        return "manha"
    if 12 <= hour < 18:
        return "tarde"
    if 18 <= hour < 23:
        return "noite"
    return "madrugada"


def _compute_shift_affinity(donor: Dict[str, Any], req_hour: int) -> float:
    """Calcula afinidade (0 a 1) entre o turno do pedido e o turno preferido do doador."""
    explicit = donor.get("afinidade_turno_doador")
    if explicit is not None and not pd.isna(explicit):
        return float(np.clip(float(explicit), 0.0, 1.0))

    preferred = str(donor.get("turno_preferido", "flexivel") or "flexivel").strip().lower()
    req_shift = _get_shift_from_hour(req_hour)

    if preferred in ("flexivel", "qualquer", ""):
        return 0.78 if req_shift != "madrugada" else 0.45
    if preferred == req_shift:
        return 0.95
    adjacent = {
        ("manha", "tarde"),
        ("tarde", "manha"),
        ("tarde", "noite"),
        ("noite", "tarde"),
    }
    if (preferred, req_shift) in adjacent:
        return 0.55
    return 0.25


def _safe_float(value: Any, default: float = np.nan) -> float:
    if value is None:
        return default
    try:
        val = float(value)
        return default if math.isnan(val) else val
    except (TypeError, ValueError):
        return default


def build_feature_row(
    donor: Dict[str, Any],
    request: Dict[str, Any],
    distance_km: Optional[float] = None,
) -> Dict[str, Any]:
    """Constrói o dicionário de features para um par (doador, pedido_alvo)."""
    donor_bt = normalize_blood_type(
        donor.get("tipo_sanguineo") or donor.get("tipoSanguineo")
    )
    req_bt = normalize_blood_type(
        request.get("tipo_sanguineo") or request.get("tipoSanguineo")
    )
    component = normalize_component(request.get("componente"))
    urgency = normalize_urgency(request.get("urgencia"))
    urgency_level = URGENCY_LEVEL_MAP[urgency]

    dist = (
        round(max(0.1, float(distance_km)), 2)
        if distance_km is not None
        else compute_distance_km(donor, request)
    )

    donor_city, donor_state = extract_city_state(
        donor.get("cidade"), donor.get("estado")
    )
    req_city, req_state = extract_city_state(
        request.get("cidade") or request.get("regiao"), request.get("estado")
    )

    same_city = int(bool(donor_city and req_city and donor_city == req_city))
    same_state = int(bool(donor_state and req_state and donor_state == req_state))

    bolsas_total = int(request.get("bolsas_total") or request.get("bolsasTotal") or request.get("bolsas") or 1)
    bolsas_recebidas = int(
        request.get("bolsas_recebidas") or request.get("bolsasRecebidas") or 0
    )
    bolsas_faltantes = max(1, bolsas_total - bolsas_recebidas)

    total_doacoes = int(donor.get("total_doacoes_anteriores") or 0)
    taxa_aceite = _safe_float(donor.get("taxa_aceite_historico"), np.nan)
    taxa_comparecimento = _safe_float(donor.get("taxa_comparecimento"), np.nan)
    tempo_resposta = _safe_float(donor.get("tempo_medio_resposta_min"), np.nan)
    dias_ultima = _safe_float(donor.get("dias_desde_ultima_doacao"), np.nan)

    eh_doador_novo = int(
        total_doacoes == 0
        or (math.isnan(taxa_aceite) and math.isnan(taxa_comparecimento))
    )

    horas_acesso = _safe_float(donor.get("horas_desde_ultimo_acesso"), 48.0)
    horas_acesso = max(0.0, horas_acesso)

    req_dt = _parse_request_datetime(request)
    req_hour = int(request.get("hora_pedido")) if request.get("hora_pedido") is not None else req_dt.hour
    fim_de_semana = (
        int(bool(request.get("fim_de_semana")))
        if request.get("fim_de_semana") is not None
        else int(req_dt.weekday() >= 5)
    )

    angle = 2.0 * math.pi * (req_hour % 24) / 24.0

    is_exact = int(bool(donor_bt and req_bt and donor_bt == req_bt))
    prevalence = get_blood_prevalence(donor_bt)
    univ_penalty = (
        get_universal_preservation_penalty(donor_bt, req_bt, component)
        if donor_bt and req_bt
        else 1.0
    )

    return {
        "distancia_km": dist,
        "log_distancia_km": math.log1p(dist),
        "interacao_dist_urgencia": dist * urgency_level,
        "raridade_tipo_doador": prevalence,
        "penalidade_universal": univ_penalty,
        "urgencia_nivel": urgency_level,
        "bolsas_faltantes": bolsas_faltantes,
        "taxa_aceite_historico": taxa_aceite,
        "taxa_comparecimento": taxa_comparecimento,
        "tempo_medio_resposta_min": tempo_resposta,
        "dias_desde_ultima_doacao": dias_ultima,
        "total_doacoes_anteriores": total_doacoes,
        "horas_desde_ultimo_acesso": horas_acesso,
        "hora_sin": math.sin(angle),
        "hora_cos": math.cos(angle),
        "afinidade_turno_doador": _compute_shift_affinity(donor, req_hour),
        "is_exact_match": is_exact,
        "mesma_cidade": same_city,
        "mesmo_estado": same_state,
        "fim_de_semana": fim_de_semana,
        "eh_doador_novo": eh_doador_novo,
        "componente": component,
        "situacao_disponibilidade": normalize_situation(
            donor.get("situacao") or donor.get("situacao_disponibilidade")
        ),
    }


def build_feature_dataframe(
    pairs: Iterable[Tuple[Dict[str, Any], Dict[str, Any], Optional[float]]],
) -> pd.DataFrame:
    """Constrói um DataFrame alinhado com ALL_FEATURES a partir de pares (doador, pedido, dist)."""
    rows = [
        build_feature_row(donor, req, distance_km=dist)
        for donor, req, dist in pairs
    ]
    if not rows:
        return pd.DataFrame(columns=ALL_FEATURES)
    return pd.DataFrame(rows, columns=ALL_FEATURES)


def create_preprocessor(scale_numeric: bool = False) -> ColumnTransformer:
    """Cria o pré-processador sklearn para uso seguro dentro de Pipeline (sem data leakage)."""
    num_steps: List[Tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        num_steps.append(("scaler", StandardScaler()))

    cat_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", Pipeline(steps=num_steps), NUMERIC_FEATURES),
            ("cat", cat_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def summarize_candidate_factors(
    feature_row: Dict[str, Any],
    donor_bt: str,
    shap_contributions: Optional[Dict[str, float]] = None,
    max_factors: int = 3,
) -> List[str]:
    """Gera explicações curtas em português para a equipe clínica sobre o score do candidato."""
    labels: List[Tuple[float, str]] = []

    if feature_row.get("is_exact_match") == 1:
        weight = (shap_contributions or {}).get("is_exact_match", 0.35)
        labels.append((weight + 0.3, f"Tipo sanguíneo idêntico ({donor_bt})"))
    elif feature_row.get("penalidade_universal", 0.0) >= 0.8:
        labels.append((0.1, f"Doador universal ({donor_bt}) — preservar se houver exato"))

    dist = float(feature_row.get("distancia_km", 0.0))
    dist_weight = abs((shap_contributions or {}).get("distancia_km", 0.25))
    if dist <= 5.0:
        labels.append((dist_weight + 0.35, f"Muito próximo ({dist:.1f} km)".replace(".", ",")))
    elif dist <= 15.0:
        labels.append((dist_weight + 0.2, f"Raio urbano ({dist:.1f} km)".replace(".", ",")))
    else:
        labels.append((dist_weight, f"Distância de {dist:.1f} km".replace(".", ",")))

    situacao = feature_row.get("situacao_disponibilidade")
    if situacao == "disponivel_agora":
        sit_w = abs((shap_contributions or {}).get("situacao_disponibilidade_disponivel_agora", 0.25))
        labels.append((sit_w + 0.3, "Disponível agora"))

    taxa_comp = feature_row.get("taxa_comparecimento")
    if taxa_comp is not None and not pd.isna(taxa_comp):
        comp_pct = int(round(float(taxa_comp) * 100))
        if comp_pct >= 80:
            labels.append((0.28, f"Histórico confiável ({comp_pct}% comparecimento)"))
    elif feature_row.get("eh_doador_novo") == 1:
        labels.append((0.15, "Novo doador elegível"))

    tempo_resp = feature_row.get("tempo_medio_resposta_min")
    if tempo_resp is not None and not pd.isna(tempo_resp) and float(tempo_resp) <= 25:
        labels.append((0.22, f"Resposta rápida (~{int(round(float(tempo_resp)))} min)"))

    labels.sort(key=lambda item: item[0], reverse=True)
    return [text for _, text in labels[:max_factors]]
