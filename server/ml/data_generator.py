"""Gerador de dataset sintético realista e base de demonstração para o HemoLink.

Modela padrões realistas de doação de sangue no Nordeste brasileiro (PE, PB, AL, BA),
incorporando:
- Distribuição epidemiológica brasileira dos 8 tipos sanguíneos ABO/Rh;
- Padrões RFM (recência, frequência e retorno) inspirados no UCI Blood Transfusion Dataset;
- Relações não-lineares (interação distância x urgência, turno x histórico, preservação de O-);
- Cenários de cold start (~22% de doadores novos sem histórico prévio);
- Ruído estocástico (amostragem Bernoulli) para evitar acurácia artificial de 100%.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from .compatibility import (
    BLOOD_TYPE_PREVALENCE_BR,
    VALID_BLOOD_TYPES,
    check_donor_eligibility,
)
from .features import build_feature_row
from .geo import CITY_COORDINATES, HOSPITAL_COORDINATES, compute_distance_km

# Cidades por estado com pesos aproximados de densidade populacional na base
STATE_CITY_WEIGHTS: Dict[str, List[Tuple[str, float]]] = {
    "PE": [
        ("Recife", 0.38),
        ("Olinda", 0.16),
        ("Jaboatão dos Guararapes", 0.17),
        ("Paulista", 0.11),
        ("Camaragibe", 0.06),
        ("Cabo de Santo Agostinho", 0.05),
        ("Abreu e Lima", 0.04),
        ("Caruaru", 0.03),
    ],
    "PB": [
        ("João Pessoa", 0.60),
        ("Cabedelo", 0.16),
        ("Bayeux", 0.12),
        ("Santa Rita", 0.07),
        ("Campina Grande", 0.05),
    ],
    "AL": [
        ("Maceió", 0.72),
        ("Rio Largo", 0.13),
        ("Marechal Deodoro", 0.10),
        ("Arapiraca", 0.05),
    ],
    "BA": [
        ("Salvador", 0.65),
        ("Lauro de Freitas", 0.15),
        ("Camaçari", 0.12),
        ("Simões Filho", 0.05),
        ("Feira de Santana", 0.03),
    ],
}

STATE_WEIGHTS: List[Tuple[str, float]] = [
    ("PE", 0.52),
    ("BA", 0.22),
    ("PB", 0.14),
    ("AL", 0.12),
]

HOSPITALS_BY_STATE: Dict[str, List[Tuple[str, str]]] = {
    "PE": [
        ("Hospital Santa Clara", "Recife"),
        ("Hospital Esperança", "Recife"),
        ("Hemope — Recife", "Recife"),
        ("Maternidade Boa Vida", "Recife"),
        ("Hospital do Coração", "Recife"),
        ("Clínica São José", "Recife"),
        ("Hospital da Orla", "Recife"),
    ],
    "PB": [
        ("Hospital de Emergência e Trauma Senador Humberto Lucena", "João Pessoa"),
    ],
    "AL": [
        ("Hospital Geral do Estado Professor Osvaldo Brandão Vilela", "Maceió"),
    ],
    "BA": [
        ("Hospital Municipal de Salvador", "Salvador"),
    ],
}

COMPONENTS_PROBS: List[Tuple[str, float]] = [
    ("Concentrado de hemácias", 0.64),
    ("Concentrado de plaquetas", 0.18),
    ("Plasma fresco congelado", 0.12),
    ("Crioprecipitado", 0.06),
]

URGENCY_PROBS: List[Tuple[str, float]] = [
    ("normal", 0.42),
    ("urgente", 0.36),
    ("emergencia", 0.22),
]

# Estatísticas de referência do Blood Transfusion Service Center Dataset (UCI, Yeh et al. 2009)
# usadas na EDA para contextualizar recência/frequência de retorno de doadores
UCI_TRANSFUSION_REFERENCE_STATS: Dict[str, float] = {
    "n_donors": 748,
    "positive_return_rate": 0.238,
    "median_recency_months": 7.0,
    "median_frequency_donations": 4.0,
    "mean_frequency_donations": 5.51,
}


def _sigmoid(x: float) -> float:
    x_clamped = max(-25.0, min(25.0, x))
    return 1.0 / (1.0 + math.exp(-x_clamped))


def _weighted_choice(rng: np.random.Generator, items: List[Tuple[Any, float]]) -> Any:
    values = [item[0] for item in items]
    probs = np.array([item[1] for item in items], dtype=float)
    probs /= probs.sum()
    idx = int(rng.choice(len(values), p=probs))
    return values[idx]


def _city_coords_with_jitter(
    rng: np.random.Generator, city: str, state: str
) -> Tuple[float, float]:
    from .geo import normalize_place

    key = (normalize_place(city), state.upper())
    base_lat, base_lon = CITY_COORDINATES[key]
    # Jitter urbano de ~0 a 6 km ao redor do centro do município
    lat = base_lat + float(rng.normal(0.0, 0.025))
    lon = base_lon + float(rng.normal(0.0, 0.025))
    return round(lat, 5), round(lon, 5)


def generate_donor_pool(
    n_donors: int = 800,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Gera uma população sintética realista de doadores com perfis variados."""
    rng = np.random.default_rng(seed)
    blood_types = list(VALID_BLOOD_TYPES)
    blood_probs = np.array([BLOOD_TYPE_PREVALENCE_BR[bt] for bt in blood_types])
    blood_probs /= blood_probs.sum()

    donors: List[Dict[str, Any]] = []

    for i in range(1, n_donors + 1):
        state = _weighted_choice(rng, STATE_WEIGHTS)
        city = _weighted_choice(rng, STATE_CITY_WEIGHTS[state])
        lat, lon = _city_coords_with_jitter(rng, city, state)
        bt = str(rng.choice(blood_types, p=blood_probs))
        sexo = str(rng.choice(["M", "F"], p=[0.54, 0.46]))
        idade = int(np.clip(rng.normal(33, 10.5), 18, 67))
        peso_kg = round(float(np.clip(rng.normal(73 if sexo == "M" else 63, 11), 50, 118)), 1)

        # Perfil latente de engajamento do doador (0 = pouco ativo, 1 = doador fiel)
        engagement = float(rng.beta(2.2, 2.0))
        is_new_donor = bool(rng.random() < 0.22)

        if is_new_donor:
            total_doacoes = 0
            dias_ultima = None
            doacoes_12m = 0
            taxa_aceite = None
            taxa_comparecimento = None
            tempo_resposta = None
        else:
            # Frequência inspirada na distribuição skewed do UCI Blood Transfusion Dataset
            total_doacoes = int(np.clip(rng.exponential(scale=1.5 + 6.0 * engagement) + 1, 1, 32))
            min_gap = 60 if sexo == "M" else 90
            # ~10% em período de carência (serão barrados no Estágio 1!)
            if rng.random() < 0.10:
                dias_ultima = int(rng.integers(10, min_gap))
            else:
                dias_ultima = int(np.clip(rng.exponential(scale=130) + min_gap, min_gap, 900))
            max_12m = 4 if sexo == "M" else 3
            doacoes_12m = int(min(max_12m - 1, rng.poisson(lam=0.6 + 1.4 * engagement)))
            taxa_aceite = round(float(np.clip(rng.beta(2.5 + 5 * engagement, 2.5 + 4 * (1 - engagement)), 0.05, 0.99)), 3)
            taxa_comparecimento = round(float(np.clip(rng.beta(3.0 + 6 * engagement, 1.5 + 3.5 * (1 - engagement)), 0.15, 0.99)), 3)
            tempo_resposta = round(float(np.clip(rng.lognormal(mean=3.9 - 1.5 * engagement, sigma=0.55), 4, 240)), 1)

        # Disponibilidade correlacionada com engajamento
        p_agora = np.clip(0.18 + 0.52 * engagement, 0.1, 0.8)
        situacao = str(
            rng.choice(
                ["disponivel_agora", "responde_1h", "indisponivel_temporario"],
                p=[p_agora, 0.88 - p_agora, 0.12],
            )
        )
        horas_ultimo_acesso = round(
            float(np.clip(rng.exponential(scale=12 + 120 * (1 - engagement)), 0.1, 720)),
            1,
        )
        turno_preferido = str(
            rng.choice(["manha", "tarde", "noite", "flexivel"], p=[0.24, 0.28, 0.20, 0.28])
        )

        donors.append(
            {
                "codigo": f"D-{i:04d}",
                "tipo_sanguineo": bt,
                "estado": state,
                "cidade": f"{city} - {state}",
                "municipio": city,
                "latitude": lat,
                "longitude": lon,
                "sexo": sexo,
                "idade": idade,
                "peso_kg": peso_kg,
                "apto_clinicamente": bool(rng.random() > 0.04),
                "aceita_avisos": bool(rng.random() > 0.05),
                "situacao": situacao,
                "total_doacoes_anteriores": total_doacoes,
                "dias_desde_ultima_doacao": dias_ultima,
                "doacoes_ultimos_12m": doacoes_12m,
                "taxa_aceite_historico": taxa_aceite,
                "taxa_comparecimento": taxa_comparecimento,
                "tempo_medio_resposta_min": tempo_resposta,
                "horas_desde_ultimo_acesso": horas_ultimo_acesso,
                "turno_preferido": turno_preferido,
                "_latent_engagement": engagement,  # Usado apenas pelo simulador, nunca como feature!
            }
        )

    return donors


def _simulate_outcome(
    rng: np.random.Generator,
    feature_row: Dict[str, Any],
    latent_engagement: float,
) -> Tuple[int, int, float]:
    """Simula desfecho real de um convite (match_sucesso, relevancia 0-3, prob_latente).

    Combina efeitos não-lineares realistas (distância x urgência, confiabilidade
    multiplicativa, preservação de estoque raro, turno e recência) com ruído
    aleatório substancial, simulando imprevistos reais da vida do doador.
    """
    dist = float(feature_row["distancia_km"])
    urg = int(feature_row["urgencia_nivel"])
    exact = int(feature_row["is_exact_match"])
    univ_pen = float(feature_row["penalidade_universal"])
    situacao = str(feature_row["situacao_disponibilidade"])
    turno_af = float(feature_row["afinidade_turno_doador"])
    horas_acesso = float(feature_row["horas_desde_ultimo_acesso"])
    fim_semana = int(feature_row["fim_de_semana"])
    novo = int(feature_row["eh_doador_novo"])
    total_doacoes = int(feature_row["total_doacoes_anteriores"])

    taxa_aceite = feature_row["taxa_aceite_historico"]
    taxa_comp = feature_row["taxa_comparecimento"]
    tempo_resp = feature_row["tempo_medio_resposta_min"]

    # Decaimento não-linear da distância (muito mais severo em emergências!)
    dist_scale = {1: 32.0, 2: 18.0, 3: 8.5}[urg]
    dist_effect = 1.85 * math.exp(-dist / dist_scale) - 0.85

    # Efeito da situação em interação com urgência
    if situacao == "disponivel_agora":
        sit_effect = 0.65 + 0.32 * (urg - 1)
    elif situacao == "responde_1h":
        sit_effect = 0.05 - 0.25 * (urg == 3)
    else:
        sit_effect = -1.75

    # Confiabilidade histórica (efeito multiplicativo, penalidade de no-show crônico e cold start)
    componente = str(feature_row["componente"])
    if novo == 1 or pd.isna(taxa_aceite) or pd.isna(taxa_comp):
        # Doador novo: depende do perfil latente com maior incerteza; plaquetas por aférese convertem menos
        hist_effect = -0.18 + 0.85 * (latent_engagement - 0.5)
        if componente == "concentrado_plaquetas":
            hist_effect -= 0.75
        resp_effect = 0.0
    else:
        acc = float(taxa_aceite)
        comp = float(taxa_comp)
        reliability = acc * comp
        hist_effect = 2.60 * (reliability - 0.36) + 0.28 * math.log1p(total_doacoes)
        # Interação não-linear: "no-show crônico" (aceita muito, mas falta)
        if acc >= 0.65 and comp <= 0.45:
            hist_effect -= 1.35
        # Interação não-linear: doador recorrente confiável em plaquetas/emergência
        if componente == "concentrado_plaquetas" and total_doacoes >= 3:
            hist_effect += 0.65
        t_min = float(tempo_resp) if not pd.isna(tempo_resp) else 45.0
        resp_effect = -0.35 * (urg / 2.0) * math.log1p(t_min / 20.0)
        # Barreira logística abrupta em emergência: distância ou tempo alto inviabiliza chegada hoje
        if urg == 3 and (dist > 14.0 or t_min > 45.0):
            resp_effect -= 1.10
        if urg == 3 and dist <= 6.0 and situacao == "disponivel_agora" and comp >= 0.75:
            resp_effect += 0.95

    # Atividade recente no app
    recency_effect = -0.30 * math.log1p(horas_acesso / 12.0)

    # Preservação de estoque raro: equipe clínica e protocolo priorizam match exato
    # (exceto em emergências críticas onde compatibilidade imediata prevalece)
    stock_effect = 0.55 * exact - (0.85 if urg < 3 else 0.20) * univ_pen

    # Interação temporal (afinidade de turno + queda em fins de semana/madrugada)
    sin_h = float(feature_row["hora_sin"])
    is_late_night = 1.0 if sin_h > 0.0 and float(feature_row["hora_cos"]) > 0.7 else 0.0
    time_effect = 0.90 * (turno_af - 0.55) - 0.20 * fim_semana - 0.35 * is_late_night
    if fim_semana == 1 and situacao == "disponivel_agora" and dist <= 8.0:
        time_effect += 0.55

    # Ruído idiossincrático (imprevistos não observados: trânsito, trabalho, saúde)
    unobserved_shock = float(rng.normal(0.0, 0.72))

    logit = (
        -0.95
        + dist_effect
        + sit_effect
        + hist_effect
        + resp_effect
        + recency_effect
        + stock_effect
        + time_effect
        + unobserved_shock
    )
    prob_success = _sigmoid(logit)

    # Gera relevância graduada (0..3) consistente com a probabilidade latente
    u = float(rng.random())
    if u < prob_success:
        relevancia = 3  # Aceitou e compareceu à doação
        match_sucesso = 1
    elif u < min(0.98, prob_success + 0.14):
        relevancia = 2  # Aceitou / agendou, mas não concluiu
        match_sucesso = 0
    elif u < min(0.99, prob_success + 0.28):
        relevancia = 1  # Respondeu tarde / demonstrou interesse
        match_sucesso = 0
    else:
        relevancia = 0  # Ignorou ou recusou
        match_sucesso = 0

    return match_sucesso, relevancia, round(prob_success, 4)


def generate_training_dataset(
    n_requests: int = 1200,
    n_donors: int = 850,
    max_candidates_per_request: int = 30,
    seed: int = 42,
) -> pd.DataFrame:
    """Gera dataset tabular de pares (pedido_alvo, doador_elegivel) com desfechos."""
    rng = np.random.default_rng(seed)
    donors = generate_donor_pool(n_donors=n_donors, seed=seed)

    blood_types = list(VALID_BLOOD_TYPES)
    # Pedidos reais demandam um pouco mais de tipos negativos em emergências
    req_bt_probs = np.array([0.31, 0.10, 0.08, 0.03, 0.03, 0.01, 0.32, 0.12])
    req_bt_probs /= req_bt_probs.sum()

    base_time = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
    records: List[Dict[str, Any]] = []

    for req_idx in range(1, n_requests + 1):
        state = _weighted_choice(rng, STATE_WEIGHTS)
        hospital, city = HOSPITALS_BY_STATE[state][
            int(rng.integers(0, len(HOSPITALS_BY_STATE[state])))
        ]
        from .geo import normalize_place

        h_lat, h_lon, _, _ = HOSPITAL_COORDINATES[normalize_place(hospital)]

        req_bt = str(rng.choice(blood_types, p=req_bt_probs))
        component = str(_weighted_choice(rng, COMPONENTS_PROBS))
        urgency = str(_weighted_choice(rng, URGENCY_PROBS))
        bolsas_total = int(rng.integers(1, 7))
        bolsas_recebidas = int(rng.integers(0, bolsas_total))

        req_dt = base_time + timedelta(
            days=int(rng.integers(0, 60)),
            hours=int(rng.integers(0, 24)),
            minutes=int(rng.integers(0, 60)),
        )

        request = {
            "pedido_id": f"PED-{req_idx:05d}",
            "tipo_sanguineo": req_bt,
            "componente": component,
            "urgencia": urgency,
            "bolsas_total": bolsas_total,
            "bolsas_recebidas": bolsas_recebidas,
            "estado": state,
            "cidade": city,
            "hospital": hospital,
            "latitude": h_lat,
            "longitude": h_lon,
            "criado_em": req_dt.isoformat(),
        }

        eligible_candidates: List[Tuple[Dict[str, Any], float]] = []
        for donor in donors:
            dist = compute_distance_km(donor, request)
            elig = check_donor_eligibility(
                donor=donor,
                recipient_blood_type=req_bt,
                component=component,
                urgency=urgency,
                distance_km=dist,
            )
            if elig.eligible:
                eligible_candidates.append((donor, dist))

        if len(eligible_candidates) < 4:
            continue

        # Amostra até max_candidates_per_request priorizando raio regional sem ordenar exatamente
        if len(eligible_candidates) > max_candidates_per_request:
            chosen_idx = rng.choice(
                len(eligible_candidates),
                size=max_candidates_per_request,
                replace=False,
            )
            eligible_candidates = [eligible_candidates[int(k)] for k in chosen_idx]

        for donor, dist in eligible_candidates:
            feat_row = build_feature_row(donor, request, distance_km=dist)
            y_bin, y_rel, p_true = _simulate_outcome(
                rng, feat_row, float(donor["_latent_engagement"])
            )
            row = {
                "pedido_id": request["pedido_id"],
                "doador_codigo": donor["codigo"],
                "tipo_pedido": req_bt,
                "tipo_doador": donor["tipo_sanguineo"],
                "estado_pedido": state,
                **feat_row,
                "match_sucesso": y_bin,
                "relevancia": y_rel,
                "prob_latente_simulada": p_true,
            }
            records.append(row)

    return pd.DataFrame(records)


def generate_demo_donors() -> List[Dict[str, Any]]:
    """Retorna uma base enxuta de doadores (incluindo códigos da tela de Revisão Clínica)
    para funcionamento imediato do MVP antes da carga completa no Supabase."""
    featured = [
        {
            "codigo": "D-0301",
            "tipo_sanguineo": "O-",
            "estado": "PE",
            "cidade": "Olinda - PE",
            "latitude": -8.0150,
            "longitude": -34.8680,
            "sexo": "M",
            "idade": 29,
            "peso_kg": 76.0,
            "apto_clinicamente": True,
            "aceita_avisos": True,
            "situacao": "disponivel_agora",
            "total_doacoes_anteriores": 9,
            "dias_desde_ultima_doacao": 95,
            "doacoes_ultimos_12m": 2,
            "taxa_aceite_historico": 0.91,
            "taxa_comparecimento": 0.94,
            "tempo_medio_resposta_min": 8.0,
            "horas_desde_ultimo_acesso": 1.5,
            "turno_preferido": "flexivel",
        },
        {
            "codigo": "D-0153",
            "tipo_sanguineo": "O-",
            "estado": "PE",
            "cidade": "Recife - PE",
            "latitude": -8.0510,
            "longitude": -34.8990,
            "sexo": "F",
            "idade": 34,
            "peso_kg": 64.0,
            "apto_clinicamente": True,
            "aceita_avisos": True,
            "situacao": "disponivel_agora",
            "total_doacoes_anteriores": 6,
            "dias_desde_ultima_doacao": 120,
            "doacoes_ultimos_12m": 1,
            "taxa_aceite_historico": 0.85,
            "taxa_comparecimento": 0.90,
            "tempo_medio_resposta_min": 14.0,
            "horas_desde_ultimo_acesso": 3.0,
            "turno_preferido": "tarde",
        },
        {
            "codigo": "D-0118",
            "tipo_sanguineo": "O-",
            "estado": "PE",
            "cidade": "Jaboatão - PE",
            "latitude": -8.0750,
            "longitude": -34.9180,
            "sexo": "M",
            "idade": 41,
            "peso_kg": 81.0,
            "apto_clinicamente": True,
            "aceita_avisos": True,
            "situacao": "disponivel_agora",
            "total_doacoes_anteriores": 5,
            "dias_desde_ultima_doacao": 140,
            "doacoes_ultimos_12m": 1,
            "taxa_aceite_historico": 0.78,
            "taxa_comparecimento": 0.86,
            "tempo_medio_resposta_min": 19.0,
            "horas_desde_ultimo_acesso": 5.5,
            "turno_preferido": "flexivel",
        },
        {
            "codigo": "D-0097",
            "tipo_sanguineo": "O-",
            "estado": "PE",
            "cidade": "Olinda - PE",
            "latitude": -8.0010,
            "longitude": -34.8590,
            "sexo": "F",
            "idade": 26,
            "peso_kg": 58.0,
            "apto_clinicamente": True,
            "aceita_avisos": True,
            "situacao": "responde_1h",
            "total_doacoes_anteriores": 3,
            "dias_desde_ultima_doacao": 180,
            "doacoes_ultimos_12m": 1,
            "taxa_aceite_historico": 0.70,
            "taxa_comparecimento": 0.82,
            "tempo_medio_resposta_min": 38.0,
            "horas_desde_ultimo_acesso": 18.0,
            "turno_preferido": "manha",
        },
        {
            "codigo": "D-0061",
            "tipo_sanguineo": "O-",
            "estado": "PE",
            "cidade": "Paulista - PE",
            "latitude": -7.9590,
            "longitude": -34.8750,
            "sexo": "M",
            "idade": 37,
            "peso_kg": 79.0,
            "apto_clinicamente": True,
            "aceita_avisos": True,
            "situacao": "responde_1h",
            "total_doacoes_anteriores": 2,
            "dias_desde_ultima_doacao": 210,
            "doacoes_ultimos_12m": 0,
            "taxa_aceite_historico": 0.62,
            "taxa_comparecimento": 0.78,
            "tempo_medio_resposta_min": 48.0,
            "horas_desde_ultimo_acesso": 36.0,
            "turno_preferido": "noite",
        },
        {
            "codigo": "D-0412",
            "tipo_sanguineo": "O+",
            "estado": "PE",
            "cidade": "Paulista - PE",
            "latitude": -7.9430,
            "longitude": -34.8720,
            "sexo": "M",
            "idade": 31,
            "peso_kg": 77.0,
            "apto_clinicamente": True,
            "aceita_avisos": True,
            "situacao": "disponivel_agora",
            "total_doacoes_anteriores": 7,
            "dias_desde_ultima_doacao": 100,
            "doacoes_ultimos_12m": 2,
            "taxa_aceite_historico": 0.88,
            "taxa_comparecimento": 0.92,
            "tempo_medio_resposta_min": 11.0,
            "horas_desde_ultimo_acesso": 2.0,
            "turno_preferido": "flexivel",
        },
        {
            "codigo": "D-0388",
            "tipo_sanguineo": "A+",
            "estado": "PE",
            "cidade": "Paulista - PE",
            "latitude": -7.9520,
            "longitude": -34.8810,
            "sexo": "F",
            "idade": 28,
            "peso_kg": 61.0,
            "apto_clinicamente": True,
            "aceita_avisos": True,
            "situacao": "responde_1h",
            "total_doacoes_anteriores": 4,
            "dias_desde_ultima_doacao": 135,
            "doacoes_ultimos_12m": 1,
            "taxa_aceite_historico": 0.80,
            "taxa_comparecimento": 0.88,
            "tempo_medio_resposta_min": 24.0,
            "horas_desde_ultimo_acesso": 6.0,
            "turno_preferido": "tarde",
        },
        {
            "codigo": "D-0275",
            "tipo_sanguineo": "O+",
            "estado": "PE",
            "cidade": "Recife - PE",
            "latitude": -8.0420,
            "longitude": -34.8920,
            "sexo": "M",
            "idade": 35,
            "peso_kg": 82.0,
            "apto_clinicamente": True,
            "aceita_avisos": True,
            "situacao": "disponivel_agora",
            "total_doacoes_anteriores": 8,
            "dias_desde_ultima_doacao": 85,
            "doacoes_ultimos_12m": 2,
            "taxa_aceite_historico": 0.86,
            "taxa_comparecimento": 0.91,
            "tempo_medio_resposta_min": 12.0,
            "horas_desde_ultimo_acesso": 4.0,
            "turno_preferido": "flexivel",
        },
        {
            "codigo": "D-0219",
            "tipo_sanguineo": "B+",
            "estado": "PE",
            "cidade": "Recife - PE",
            "latitude": -8.0610,
            "longitude": -34.9080,
            "sexo": "F",
            "idade": 24,
            "peso_kg": 59.0,
            "apto_clinicamente": True,
            "aceita_avisos": True,
            "situacao": "responde_1h",
            "total_doacoes_anteriores": 0,
            "dias_desde_ultima_doacao": None,
            "doacoes_ultimos_12m": 0,
            "taxa_aceite_historico": None,
            "taxa_comparecimento": None,
            "tempo_medio_resposta_min": None,
            "horas_desde_ultimo_acesso": 10.0,
            "turno_preferido": "tarde",
        },
        {
            "codigo": "D-0190",
            "tipo_sanguineo": "AB+",
            "estado": "PE",
            "cidade": "Jaboatão - PE",
            "latitude": -8.1050,
            "longitude": -34.9980,
            "sexo": "M",
            "idade": 45,
            "peso_kg": 85.0,
            "apto_clinicamente": True,
            "aceita_avisos": True,
            "situacao": "disponivel_agora",
            "total_doacoes_anteriores": 11,
            "dias_desde_ultima_doacao": 92,
            "doacoes_ultimos_12m": 2,
            "taxa_aceite_historico": 0.89,
            "taxa_comparecimento": 0.93,
            "tempo_medio_resposta_min": 15.0,
            "horas_desde_ultimo_acesso": 2.5,
            "turno_preferido": "manha",
        },
    ]

    # Complementa com doadores gerados nos 4 estados (PE, PB, AL, BA)
    extra = generate_donor_pool(n_donors=140, seed=101)
    for idx, d in enumerate(extra, start=500):
        d = {k: v for k, v in d.items() if not k.startswith("_")}
        d["codigo"] = f"D-{idx:04d}"
        featured.append(d)

    return featured
