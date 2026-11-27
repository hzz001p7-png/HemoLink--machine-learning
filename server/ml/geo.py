"""Utilitários de geolocalização e distância Haversine para o HemoLink."""

from __future__ import annotations

import math
import unicodedata
from typing import Dict, Optional, Tuple

EARTH_RADIUS_KM = 6371.0

# Coordenadas geográficas (lat, lon) de municípios presentes no fluxo do HemoLink
CITY_COORDINATES: Dict[Tuple[str, str], Tuple[float, float]] = {
    # Pernambuco (PE)
    ("recife", "PE"): (-8.0476, -34.8770),
    ("olinda", "PE"): (-8.0089, -34.8553),
    ("jaboatao", "PE"): (-8.1128, -35.0150),
    ("jaboatao dos guararapes", "PE"): (-8.1128, -35.0150),
    ("paulista", "PE"): (-7.9408, -34.8731),
    ("camaragibe", "PE"): (-8.0206, -34.9786),
    ("abreu e lima", "PE"): (-7.9007, -34.8984),
    ("igarassu", "PE"): (-7.8342, -34.9064),
    ("cabo de santo agostinho", "PE"): (-8.2833, -35.0333),
    ("sao lourenco da mata", "PE"): (-8.0022, -35.0183),
    ("caruaru", "PE"): (-8.2829, -35.9761),
    ("petrolina", "PE"): (-9.3891, -40.5027),
    # Paraíba (PB)
    ("joao pessoa", "PB"): (-7.1195, -34.8450),
    ("cabedelo", "PB"): (-6.9811, -34.8339),
    ("bayeux", "PB"): (-7.1250, -34.9322),
    ("santa rita", "PB"): (-7.1139, -34.9781),
    ("campina grande", "PB"): (-7.2306, -35.8811),
    # Alagoas (AL)
    ("maceio", "AL"): (-9.6498, -35.7089),
    ("alagoas", "AL"): (-9.6498, -35.7089),  # Alias presente no select atual do front
    ("marechal deodoro", "AL"): (-9.7103, -35.8950),
    ("rio largo", "AL"): (-9.4783, -35.8531),
    ("arapiraca", "AL"): (-9.7525, -36.6611),
    # Bahia (BA)
    ("salvador", "BA"): (-12.9714, -38.5014),
    ("lauro de freitas", "BA"): (-12.8944, -38.3272),
    ("camacari", "BA"): (-12.6975, -38.3242),
    ("simoes filho", "BA"): (-12.7850, -38.4042),
    ("feira de santana", "BA"): (-12.2664, -38.9663),
}

# Coordenadas aproximadas dos hospitais e hemocentros cadastrados no HemoLink
HOSPITAL_COORDINATES: Dict[str, Tuple[float, float, str, str]] = {
    "hospital santa clara": (-8.0320, -34.8825, "Recife", "PE"),
    "hospital esperanca": (-8.0631, -34.8961, "Recife", "PE"),
    "hemope - recife": (-8.0556, -34.8975, "Recife", "PE"),
    "hemope": (-8.0556, -34.8975, "Recife", "PE"),
    "maternidade boa vida": (-8.0510, -34.8910, "Recife", "PE"),
    "hospital do coracao": (-8.0462, -34.8895, "Recife", "PE"),
    "clinica sao jose": (-8.0680, -34.8830, "Recife", "PE"),
    "hospital da orla": (-8.1180, -34.8960, "Recife", "PE"),
    "hospital de emergencia e trauma senador humberto lucena": (
        -7.1153,
        -34.8610,
        "João Pessoa",
        "PB",
    ),
    "hospital municipal de salvador": (-12.9125, -38.4310, "Salvador", "BA"),
    "hospital geral do estado professor osvaldo brandao vilela": (
        -9.6606,
        -35.7522,
        "Maceió",
        "AL",
    ),
}


def normalize_place(text: Optional[str]) -> str:
    """Remove acentos, travessões e normaliza espaços para comparação de locais."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    ascii_text = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    cleaned = (
        ascii_text.lower()
        .replace("—", "-")
        .replace("–", "-")
        .replace("−", "-")
        .strip()
    )
    return " ".join(cleaned.split())


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula a distância geodésica em quilômetros entre duas coordenadas."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_KM * c


def resolve_coordinates(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    hospital: Optional[str] = None,
    cidade: Optional[str] = None,
    estado: Optional[str] = None,
) -> Optional[Tuple[float, float]]:
    """Resolve coordenadas a partir de lat/lon explícitos, hospital ou cidade/estado."""
    if latitude is not None and longitude is not None:
        return (float(latitude), float(longitude))

    if hospital:
        h_norm = normalize_place(hospital)
        if h_norm in HOSPITAL_COORDINATES:
            lat, lon, _, _ = HOSPITAL_COORDINATES[h_norm]
            return (lat, lon)
        for key, (lat, lon, _, _) in HOSPITAL_COORDINATES.items():
            if key in h_norm or h_norm in key:
                return (lat, lon)

    if cidade:
        c_norm = normalize_place(cidade)
        # Suporta formatos como "Olinda - PE" ou "Recife – PE"
        if " - " in c_norm:
            parts = [p.strip() for p in c_norm.split(" - ", 1)]
            c_norm = parts[0]
            if not estado and len(parts) > 1:
                estado = parts[1]

        uf = str(estado).strip().upper() if estado else ""
        if uf and (c_norm, uf) in CITY_COORDINATES:
            return CITY_COORDINATES[(c_norm, uf)]

        for (city_key, _), coords in CITY_COORDINATES.items():
            if city_key == c_norm:
                return coords

    return None


def compute_distance_km(
    donor: Dict[str, object],
    request: Dict[str, object],
    fallback_km: float = 15.0,
) -> float:
    """Calcula a distância em km entre doador e pedido alvo com fallback seguro."""
    if donor.get("distancia_km") is not None:
        return round(max(0.1, float(donor["distancia_km"])), 2)

    donor_coords = resolve_coordinates(
        latitude=donor.get("latitude"),
        longitude=donor.get("longitude"),
        cidade=donor.get("cidade"),
        estado=donor.get("estado"),
    )
    req_coords = resolve_coordinates(
        latitude=request.get("latitude"),
        longitude=request.get("longitude"),
        hospital=request.get("hospital"),
        cidade=request.get("cidade"),
        estado=request.get("estado"),
    )

    if donor_coords is not None and req_coords is not None:
        # Fator urbano aproximado (~1.22x linha reta) para distância viária realista
        straight_km = haversine_km(
            donor_coords[0], donor_coords[1], req_coords[0], req_coords[1]
        )
        road_km = max(0.5, straight_km * 1.22)
        return round(road_km, 2)

    return fallback_km


def extract_city_state(
    cidade: Optional[str], estado: Optional[str]
) -> Tuple[str, str]:
    """Extrai (cidade_normalizada, UF) tratando strings como 'Recife - PE'."""
    c_norm = normalize_place(cidade)
    uf = str(estado or "").strip().upper()
    if " - " in c_norm:
        parts = [p.strip() for p in c_norm.split(" - ", 1)]
        c_norm = parts[0]
        if not uf and len(parts) > 1:
            uf = parts[1].upper()
    return c_norm, uf
