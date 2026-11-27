"""Testes exaustivos do Estágio 1 — Segurança transfusional ABO/Rh e elegibilidade ANVISA."""

import pytest

from ml.compatibility import (
    VALID_BLOOD_TYPES,
    check_donor_eligibility,
    compatible_donor_types,
    is_blood_compatible,
    normalize_blood_type,
    normalize_component,
)


def test_rbc_universal_donor_and_recipient():
    # O- doa Concentrado de Hemácias para todos os 8 tipos
    for rec in VALID_BLOOD_TYPES:
        assert is_blood_compatible("O-", rec, "Concentrado de hemácias") is True

    # O- só recebe Concentrado de Hemácias de O-
    assert compatible_donor_types("O-", "Concentrado de hemácias") == {"O-"}

    # AB+ recebe Concentrado de Hemácias de todos os 8 tipos
    assert compatible_donor_types("AB+", "Concentrado de hemácias") == set(VALID_BLOOD_TYPES)


def test_rbc_never_allows_rh_positive_into_rh_negative():
    rh_pos = [bt for bt in VALID_BLOOD_TYPES if bt.endswith("+")]
    rh_neg = [bt for bt in VALID_BLOOD_TYPES if bt.endswith("-")]
    for donor in rh_pos:
        for rec in rh_neg:
            assert is_blood_compatible(donor, rec, "Concentrado de hemácias") is False


def test_plasma_inverse_abo_compatibility():
    # AB é doador universal de plasma
    for rec in VALID_BLOOD_TYPES:
        assert is_blood_compatible("AB+", rec, "Plasma fresco congelado") is True
        assert is_blood_compatible("AB-", rec, "Plasma fresco congelado") is True

    # O só doa plasma para O
    assert is_blood_compatible("O-", "A+", "Plasma fresco congelado") is False
    assert is_blood_compatible("O+", "AB+", "Plasma fresco congelado") is False
    assert is_blood_compatible("O-", "O+", "Plasma fresco congelado") is True


def test_platelets_protects_rh_negative_recipients():
    assert is_blood_compatible("A+", "A-", "Concentrado de plaquetas") is False
    assert is_blood_compatible("A-", "A-", "Concentrado de plaquetas") is True
    assert is_blood_compatible("AB-", "O-", "Concentrado de plaquetas") is True


def test_unknown_blood_type_and_unicode_minus():
    assert normalize_blood_type("O−") == "O-"  # U+2212
    assert normalize_blood_type("Não sei") is None
    assert is_blood_compatible("Não sei", "O+", "Concentrado de hemácias") is False
    assert normalize_component("Plaquetas") == "concentrado_plaquetas"
    assert normalize_component("Plasma") == "plasma_fresco_congelado"


@pytest.mark.parametrize(
    "overrides,expected_reason_prefix",
    [
        ({"tipo_sanguineo": "A+"}, "incompativel_abo_rh_componente"),
        ({"tipo_sanguineo": "Não sei"}, "tipo_sanguineo_desconhecido"),
        ({"apto_clinicamente": False}, "inapto_clinicamente"),
        ({"aceita_avisos": False}, "nao_aceita_notificacoes"),
        ({"idade": 15}, "idade_fora_faixa_anvisa"),
        ({"idade": 75}, "idade_fora_faixa_anvisa"),
        ({"peso_kg": 48.5}, "peso_abaixo_50kg"),
        ({"sexo": "M", "dias_desde_ultima_doacao": 45}, "intervalo_minimo_nao_cumprido_60d"),
        ({"sexo": "F", "dias_desde_ultima_doacao": 75}, "intervalo_minimo_nao_cumprido_90d"),
        ({"sexo": "F", "doacoes_ultimos_12m": 3}, "limite_anual_doacoes_atingido_3"),
    ],
)
def test_anvisa_eligibility_blocks_invalid_donors(overrides, expected_reason_prefix):
    base_donor = {
        "codigo": "D-TEST",
        "tipo_sanguineo": "O-",
        "sexo": "M",
        "idade": 30,
        "peso_kg": 72.0,
        "apto_clinicamente": True,
        "aceita_avisos": True,
        "dias_desde_ultima_doacao": 120,
        "doacoes_ultimos_12m": 1,
    }
    donor = {**base_donor, **overrides}
    res = check_donor_eligibility(
        donor=donor,
        recipient_blood_type="O-",
        component="Concentrado de hemácias",
        urgency="emergencia",
        distance_km=5.0,
    )
    assert res.eligible is False
    assert any(r.startswith(expected_reason_prefix) for r in res.reasons)
