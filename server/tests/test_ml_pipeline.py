"""Testes do pipeline de Machine Learning, inferência, ausência de leakage e contratos FastAPI."""

import json

import pytest
from fastapi import HTTPException

from main import (
    AprovarPedidoInput,
    CreateSolicitacaoInput,
    RankRequest,
    app,
    aprovar_pedido,
    criar_solicitacao,
    health_check,
    listar_fila_revisao,
    listar_solicitacoes,
    obter_pedido_revisao,
    ranquear_doadores,
)
from ml.compatibility import is_blood_compatible
from ml.data_generator import generate_demo_donors, generate_training_dataset
from ml.features import ALL_FEATURES
from ml.predictor import matcher_service
from ml.train import METRICS_REPORT_PATH, MODEL_ARTIFACT_PATH


def test_training_dataset_has_no_pii_and_realistic_distribution():
    df = generate_training_dataset(n_requests=60, n_donors=150, seed=7)
    assert len(df) > 200
    for forbidden in ("nome", "cpf", "email", "celular", "senha"):
        assert forbidden not in df.columns
    for col in ALL_FEATURES:
        assert col in df.columns
    pos_rate = df["match_sucesso"].mean()
    assert 0.05 < pos_rate < 0.70, f"Taxa positiva fora da faixa realista: {pos_rate}"


def test_model_artifact_and_metrics_exist_and_beat_heuristic():
    assert MODEL_ARTIFACT_PATH.exists(), "Modelo treinado não encontrado!"
    assert METRICS_REPORT_PATH.exists(), "Relatório de métricas não encontrado!"

    report = json.loads(METRICS_REPORT_PATH.read_text(encoding="utf-8"))
    heur = report["test_metrics"]["Baseline Distância"]
    ml_cal = report["test_metrics"]["LightGBM Calibrado"]

    # O modelo de ML deve superar significativamente a heurística pura de distância
    assert ml_cal["roc_auc"] > heur["roc_auc"] + 0.12
    assert ml_cal["ndcg_at_5"] > heur["ndcg_at_5"] + 0.15
    assert ml_cal["brier_score"] < heur["brier_score"]
    # Garante realismo (não é uma fórmula trivial de 100%)
    assert 0.72 <= ml_cal["roc_auc"] <= 0.95


def test_predictor_enforces_safety_and_returns_ranked_scores():
    donors = generate_demo_donors()
    # Injeta propositalmente um doador incompatível (A+) muito próximo para pedido O-
    donors_with_invalid = [
        {
            "codigo": "D-INCOMPAT",
            "tipo_sanguineo": "A+",
            "estado": "PE",
            "cidade": "Recife - PE",
            "distancia_km": 0.2,
            "situacao": "disponivel_agora",
            "apto_clinicamente": True,
            "aceita_avisos": True,
        },
        *donors,
    ]
    req = {
        "tipo_sanguineo": "O-",
        "componente": "Concentrado de hemácias",
        "urgencia": "emergencia",
        "bolsas_total": 5,
        "bolsas_recebidas": 1,
        "estado": "PE",
        "cidade": "Recife",
        "hospital": "Hospital Santa Clara",
    }

    res = matcher_service.rank_donors(req, donors_with_invalid, top_k=5)
    cands = res["candidatos"]
    assert len(cands) > 0
    assert all(c["codigo"] != "D-INCOMPAT" for c in cands)
    assert all(
        is_blood_compatible(c["tipoSanguineo"], "O-", "Concentrado de hemácias")
        for c in cands
    )

    # Verifica ordenação decrescente de probabilidade calibrada
    probs = [c["probabilidadeCalibrada"] for c in cands]
    assert probs == sorted(probs, reverse=True)
    assert all(1 <= c["compatibilidade"] <= 99 for c in cands)
    assert all(len(c["fatoresPrincipais"]) >= 1 for c in cands)
    assert all(len(c["explicacaoShap"]) >= 1 for c in cands)


def test_fastapi_routes_and_frontend_contracts():
    registered_paths = {route.path for route in app.routes}
    for expected in (
        "/health",
        "/itens",
        "/api/ml/modelo",
        "/api/ml/ranquear",
        "/api/ml/feedback",
        "/api/solicitacoes",
        "/api/revisao/fila",
        "/api/revisao/pedidos/{pedido_id}",
        "/api/revisao/pedidos/{pedido_id}/aprovar",
    ):
        assert expected in registered_paths

    # Health check
    health = health_check()
    assert health["status"] == "ok"
    assert health["modelo_ml"] == "LightGBM Calibrado"

    # Fila de Revisão Clínica (RevisaoClinicaPage.jsx)
    fila = listar_fila_revisao()["itens"]
    assert len(fila) >= 1

    # Detalhe de pedido com candidatos sugeridos pela IA
    first_id = fila[0]["id"]
    detalhe = obter_pedido_revisao(first_id)
    assert "candidatos" in detalhe and len(detalhe["candidatos"]) >= 1
    first_cand = detalhe["candidatos"][0]
    for field in (
        "codigo",
        "cidade",
        "tipoSanguineo",
        "distanciaKm",
        "compatibilidade",
        "situacao",
        "selecionado",
    ):
        assert field in first_cand

    # Endpoint direto de ML (/api/ml/ranquear)
    ranked = ranquear_doadores(
        RankRequest(
            tipo_sanguineo="A+",
            componente="Concentrado de hemácias",
            urgencia="urgente",
            bolsas_total=3,
            estado="PE",
            cidade="Recife",
            hospital="Hospital Esperança",
            top_k=5,
        )
    )
    assert ranked["totalElegiveis"] >= 1
    assert len(ranked["candidatos"]) >= 1

    # Validação de tipo sanguíneo inválido
    with pytest.raises(HTTPException) as exc_info:
        ranquear_doadores(RankRequest(tipo_sanguineo="XYZ"))
    assert exc_info.value.status_code == 422

    # Fluxo Nova Solicitação -> Aprovação Clínica (feedback loop)
    created = criar_solicitacao(
        CreateSolicitacaoInput(
            tipo="O+",
            bolsas=2,
            urgencia="Emergência",
            componente="Concentrado de hemácias",
            estado="PE",
            cidade="Recife",
            hospital="Hemope — Recife",
            observacoes="Teste automatizado",
        )
    )
    assert created["tipoSanguineo"] == "O+"
    assert created["urgencia"] == "emergencia"
    assert len(created["candidatos"]) >= 1

    sols = listar_solicitacoes(urgencia="emergencia", ordem="urgentes")
    assert any(item["id"] == created["id"] for item in sols["itens"])

    approved = aprovar_pedido(
        created["id"],
        AprovarPedidoInput(
            selecionados=[created["candidatos"][0]["codigo"]],
            checklist={
                "compatibilidadeTransfusional": True,
                "elegibilidadeDoadores": True,
                "urgenciaPedido": True,
            },
        ),
    )
    assert approved["status"] == "aprovado"
