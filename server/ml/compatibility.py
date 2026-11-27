"""Estágio 1 — Regras determinísticas de compatibilidade transfusional e elegibilidade clínica.

Baseado nas diretrizes de hemoterapia (ANVISA / Ministério da Saúde - Portaria de
Consolidação nº 5, Anexo IV). Nenhuma decisão de segurança biológica ABO/Rh ou
elegibilidade mínima é delegada ao modelo probabilístico de Machine Learning.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Dict, Optional, Set, Tuple

VALID_BLOOD_TYPES: Tuple[str, ...] = (
    "A+",
    "A-",
    "B+",
    "B-",
    "AB+",
    "AB-",
    "O+",
    "O-",
)

# Distribuição aproximada dos tipos sanguíneos na população brasileira (dados Ministério da Saúde)
BLOOD_TYPE_PREVALENCE_BR: Dict[str, float] = {
    "O+": 0.360,
    "A+": 0.340,
    "O-": 0.090,
    "B+": 0.080,
    "A-": 0.080,
    "AB+": 0.025,
    "B-": 0.020,
    "AB-": 0.005,
}

# Compatibilidade ABO/Rh para Concentrado de Hemácias (receptor -> conjunto de doadores compatíveis)
RBC_COMPATIBILITY: Dict[str, Set[str]] = {
    "O-": {"O-"},
    "O+": {"O-", "O+"},
    "A-": {"O-", "A-"},
    "A+": {"O-", "O+", "A-", "A+"},
    "B-": {"O-", "B-"},
    "B+": {"O-", "O+", "B-", "B+"},
    "AB-": {"O-", "A-", "B-", "AB-"},
    "AB+": {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"},
}

# Compatibilidade ABO para Plasma Fresco Congelado e Crioprecipitado (regra ABO inversa)
PLASMA_COMPATIBILITY: Dict[str, Set[str]] = {
    "O-": {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"},
    "O+": {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"},
    "A-": {"A-", "A+", "AB-", "AB+"},
    "A+": {"A-", "A+", "AB-", "AB+"},
    "B-": {"B-", "B+", "AB-", "AB+"},
    "B+": {"B-", "B+", "AB-", "AB+"},
    "AB-": {"AB-", "AB+"},
    "AB+": {"AB-", "AB+"},
}

# Compatibilidade conservadora para Concentrado de Plaquetas:
# ABO plasma-compatível + respeito estrito ao Rh- para evitar aloimunização anti-D
PLATELETS_COMPATIBILITY: Dict[str, Set[str]] = {
    "O-": {"O-", "A-", "B-", "AB-"},
    "O+": {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"},
    "A-": {"A-", "AB-"},
    "A+": {"A-", "A+", "AB-", "AB+"},
    "B-": {"B-", "AB-"},
    "B+": {"B-", "B+", "AB-", "AB+"},
    "AB-": {"AB-"},
    "AB+": {"AB-", "AB+"},
}

MAX_DISTANCE_KM_BY_URGENCY: Dict[str, float] = {
    "emergencia": 60.0,
    "urgente": 120.0,
    "normal": 250.0,
}

URGENCY_LEVEL_MAP: Dict[str, int] = {
    "normal": 1,
    "urgente": 2,
    "emergencia": 3,
}


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalize_blood_type(blood_type: Optional[str]) -> Optional[str]:
    """Normaliza representação de tipo sanguíneo (incluindo hífen Unicode '−' -> '-')."""
    if not blood_type:
        return None
    cleaned = (
        str(blood_type)
        .strip()
        .upper()
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace(" ", "")
    )
    return cleaned if cleaned in VALID_BLOOD_TYPES else None


def normalize_component(component: Optional[str]) -> str:
    """Normaliza o nome do hemocomponente para uma das 4 categorias canônicas."""
    if not component:
        return "concentrado_hemacias"
    norm = _strip_accents(str(component).strip().lower())
    if "plaqueta" in norm:
        return "concentrado_plaquetas"
    if "plasma" in norm:
        return "plasma_fresco_congelado"
    if "crio" in norm:
        return "crioprecipitado"
    return "concentrado_hemacias"


def normalize_urgency(urgency: Optional[str]) -> str:
    """Normaliza urgência para 'normal', 'urgente' ou 'emergencia'."""
    if not urgency:
        return "normal"
    norm = _strip_accents(str(urgency).strip().lower())
    if "emerg" in norm:
        return "emergencia"
    if "urgen" in norm:
        return "urgente"
    return "normal"


def compatible_donor_types(
    recipient_blood_type: str,
    component: str = "Concentrado de hemácias",
) -> Set[str]:
    """Retorna o conjunto de tipos sanguíneos de doadores compatíveis com o receptor e componente."""
    rec = normalize_blood_type(recipient_blood_type)
    if rec is None:
        return set()

    comp = normalize_component(component)
    if comp == "concentrado_hemacias":
        return set(RBC_COMPATIBILITY[rec])
    if comp in ("plasma_fresco_congelado", "crioprecipitado"):
        return set(PLASMA_COMPATIBILITY[rec])
    if comp == "concentrado_plaquetas":
        return set(PLATELETS_COMPATIBILITY[rec])
    return set(RBC_COMPATIBILITY[rec])


def is_blood_compatible(
    donor_blood_type: Optional[str],
    recipient_blood_type: Optional[str],
    component: str = "Concentrado de hemácias",
) -> bool:
    """Verifica se um doador é biologicamente compatível com o receptor para o hemocomponente."""
    donor = normalize_blood_type(donor_blood_type)
    recipient = normalize_blood_type(recipient_blood_type)
    if donor is None or recipient is None:
        return False
    return donor in compatible_donor_types(recipient, component)


def get_blood_prevalence(blood_type: Optional[str]) -> float:
    """Retorna a prevalência populacional brasileira do tipo sanguíneo."""
    bt = normalize_blood_type(blood_type)
    if bt is None:
        return 0.0
    return BLOOD_TYPE_PREVALENCE_BR[bt]


def get_universal_preservation_penalty(
    donor_blood_type: str,
    recipient_blood_type: str,
    component: str = "Concentrado de hemácias",
) -> float:
    """Mede o 'custo de oportunidade' de usar um doador universal em receptor não-universal.

    Retorna 0.0 para correspondência exata e valores maiores (até 1.0) quando um
    doador raro/universal (ex.: O- para hemácias ou AB para plasma) é alocado a um
    receptor que pode receber de vários outros tipos mais comuns.
    """
    donor = normalize_blood_type(donor_blood_type)
    recipient = normalize_blood_type(recipient_blood_type)
    if donor is None or recipient is None:
        return 1.0
    if donor == recipient:
        return 0.0

    comp = normalize_component(component)
    if comp == "concentrado_hemacias":
        if donor == "O-":
            return 1.0
        if donor == "O+" and recipient != "O+":
            return 0.35
        if donor.endswith("-") and recipient.endswith("+"):
            return 0.55
        return 0.25

    if comp in ("plasma_fresco_congelado", "crioprecipitado"):
        if donor.startswith("AB") and not recipient.startswith("AB"):
            return 0.85
        return 0.25

    return 0.30


@dataclass(frozen=True)
class EligibilityResult:
    """Resultado detalhado da triagem determinística (Estágio 1)."""

    eligible: bool
    reasons: Tuple[str, ...] = ()


def check_donor_eligibility(
    donor: Dict[str, object],
    recipient_blood_type: str,
    component: str = "Concentrado de hemácias",
    urgency: str = "normal",
    distance_km: Optional[float] = None,
    max_distance_km: Optional[float] = None,
) -> EligibilityResult:
    """Aplica todas as restrições rígidas de segurança clínica e operacional antes do ML."""
    reasons = []

    donor_bt = normalize_blood_type(donor.get("tipo_sanguineo"))
    if donor_bt is None:
        reasons.append("tipo_sanguineo_desconhecido")
    elif not is_blood_compatible(donor_bt, recipient_blood_type, component):
        reasons.append("incompativel_abo_rh_componente")

    if donor.get("apto_clinicamente", True) is False:
        reasons.append("inapto_clinicamente")

    if donor.get("aceita_avisos", True) is False:
        reasons.append("nao_aceita_notificacoes")

    idade = donor.get("idade")
    if idade is not None:
        if not (16 <= float(idade) <= 69):
            reasons.append("idade_fora_faixa_anvisa")

    peso_kg = donor.get("peso_kg")
    if peso_kg is not None:
        if float(peso_kg) < 50.0:
            reasons.append("peso_abaixo_50kg")

    sexo = str(donor.get("sexo", "F") or "F").strip().upper()
    min_interval_days = 60 if sexo == "M" else 90
    max_annual_donations = 4 if sexo == "M" else 3

    dias_ultima = donor.get("dias_desde_ultima_doacao")
    if dias_ultima is not None and float(dias_ultima) < min_interval_days:
        reasons.append(f"intervalo_minimo_nao_cumprido_{min_interval_days}d")

    doacoes_12m = donor.get("doacoes_ultimos_12m")
    if doacoes_12m is not None and int(doacoes_12m) >= max_annual_donations:
        reasons.append(f"limite_anual_doacoes_atingido_{max_annual_donations}")

    urg = normalize_urgency(urgency)
    radius_limit = (
        max_distance_km
        if max_distance_km is not None
        else MAX_DISTANCE_KM_BY_URGENCY[urg]
    )
    if distance_km is not None and float(distance_km) > radius_limit:
        reasons.append(f"fora_raio_maximo_{int(radius_limit)}km")

    return EligibilityResult(eligible=(len(reasons) == 0), reasons=tuple(reasons))
