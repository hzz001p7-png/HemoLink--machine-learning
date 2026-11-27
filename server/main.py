"""Backend FastAPI do HemoLink — API de Solicitações, Revisão Clínica e Motor de ML."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ml.compatibility import (
    normalize_blood_type,
    normalize_component,
    normalize_urgency,
)
from ml.data_generator import generate_demo_donors
from ml.predictor import matcher_service

load_dotenv()


def _init_supabase_client() -> Optional[Any]:
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_KEY") or "").strip()
    if not url or not key:
        return None
    try:
        from supabase import create_client

        return create_client(url, key)
    except Exception:
        return None


supabase = _init_supabase_client()

app = FastAPI(
    title="HemoLink API & Motor de Machine Learning",
    version=matcher_service.metadata.get("model_version", "1.0.0"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Schemas Pydantic
# ============================================================


class RankRequest(BaseModel):
    tipo_sanguineo: str = Field(..., description="Tipo sanguíneo do pedido alvo (ex.: O-, A+)")
    componente: str = Field(default="Concentrado de hemácias")
    urgencia: str = Field(default="normal")
    bolsas_total: int = Field(default=1, ge=1, le=99)
    bolsas_recebidas: int = Field(default=0, ge=0, le=99)
    estado: str = Field(default="PE")
    cidade: str = Field(default="Recife")
    hospital: str = Field(default="")
    top_k: int = Field(default=10, ge=1, le=100)
    max_distance_km: Optional[float] = Field(default=None, gt=0)
    include_shap: bool = Field(default=True)
    include_temporarily_unavailable: bool = Field(default=False)
    doadores: Optional[List[Dict[str, Any]]] = Field(default=None)


class FeedbackInput(BaseModel):
    pedido_id: str
    doador_codigo: str
    desfecho_real: str = Field(
        default="pendente",
        description="pendente | ignorou | recusou | respondeu_tarde | agendou | compareceu_doou",
    )
    aprovado_equipe_clinica: Optional[bool] = None
    observacoes: str = ""


class CreateSolicitacaoInput(BaseModel):
    tipo: str
    bolsas: int = Field(default=1, ge=1, le=99)
    urgencia: str = Field(default="normal")
    componente: str = Field(default="Concentrado de hemácias")
    estado: str = Field(default="PE")
    cidade: str = Field(default="Recife")
    hospital: str = Field(default="Hospital Santa Clara")
    observacoes: str = Field(default="")


class AprovarPedidoInput(BaseModel):
    selecionados: List[str] = Field(default_factory=list)
    checklist: Dict[str, bool] = Field(default_factory=dict)


# ============================================================
# Catálogo de Doadores e Estado em Memória (Fallback / Demo)
# ============================================================

_DEMO_DONORS: List[Dict[str, Any]] = generate_demo_donors()
_FEEDBACK_LOG: List[Dict[str, Any]] = []
_URGENCIA_ORDER = {"emergencia": 0, "urgente": 1, "normal": 2}


def _get_donor_pool(override_donors: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    if override_donors is not None:
        return override_donors
    if supabase is not None:
        try:
            resp = supabase.table("doadores").select("*").execute()
            if resp.data:
                return resp.data
        except Exception:
            pass
    return _DEMO_DONORS


def _rank_for_pedido(pedido: Dict[str, Any], top_k: int = 8) -> List[Dict[str, Any]]:
    req = {
        "tipo_sanguineo": pedido["tipoSanguineo"],
        "componente": pedido["componente"],
        "urgencia": pedido["urgencia"],
        "bolsas_total": pedido["bolsasTotal"],
        "bolsas_recebidas": pedido["bolsasRecebidas"],
        "estado": pedido.get("estado", "PE"),
        "cidade": pedido.get("cidade", "Recife"),
        "hospital": pedido.get("hospital", ""),
    }
    res = matcher_service.rank_donors(req, _get_donor_pool(), top_k=top_k)
    return res["candidatos"]


def _build_initial_pedidos() -> Dict[str, Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    seeds = [
        {
            "numero": 2041,
            "tipoSanguineo": "O-",
            "hospital": "Hospital Santa Clara",
            "componente": "Concentrado de hemácias",
            "bolsasRecebidas": 1,
            "bolsasTotal": 5,
            "estado": "PE",
            "cidade": "Recife",
            "urgencia": "emergencia",
            "status": "na_fila",
            "etapaAtual": 2,
            "etapaTotal": 5,
            "etapaNome": "Candidatos prontos",
            "observacoes": "Cirurgia de emergência em andamento.",
            "criadoEm": (now - timedelta(minutes=18)).isoformat(),
        },
        {
            "numero": 2040,
            "tipoSanguineo": "A+",
            "hospital": "Maternidade Boa Vida",
            "componente": "Concentrado de hemácias",
            "bolsasRecebidas": 1,
            "bolsasTotal": 3,
            "estado": "PE",
            "cidade": "Recife",
            "urgencia": "urgente",
            "status": "na_fila",
            "etapaAtual": 3,
            "etapaTotal": 5,
            "etapaNome": "Aguardando revisão clínica",
            "observacoes": "Reserva cirúrgica obstétrica.",
            "criadoEm": (now - timedelta(hours=1, minutes=12)).isoformat(),
        },
        {
            "numero": 2038,
            "tipoSanguineo": "B+",
            "hospital": "Hospital do Coração",
            "componente": "Plaquetas",
            "bolsasRecebidas": 0,
            "bolsasTotal": 2,
            "estado": "PE",
            "cidade": "Olinda",
            "urgencia": "normal",
            "status": "na_fila",
            "etapaAtual": 2,
            "etapaTotal": 5,
            "etapaNome": "Candidatos prontos",
            "observacoes": "Reposição plaquetária programada.",
            "criadoEm": (now - timedelta(hours=3)).isoformat(),
        },
        {
            "numero": 2035,
            "tipoSanguineo": "AB+",
            "hospital": "Clínica São José",
            "componente": "Plasma",
            "bolsasRecebidas": 2,
            "bolsasTotal": 4,
            "estado": "PE",
            "cidade": "Recife",
            "urgencia": "urgente",
            "status": "aprovado",
            "etapaAtual": 4,
            "etapaTotal": 5,
            "etapaNome": "Contato em andamento",
            "observacoes": "",
            "criadoEm": (now - timedelta(hours=5)).isoformat(),
        },
    ]

    store: Dict[str, Dict[str, Any]] = {}
    for item in seeds:
        pid = str(item["numero"])
        pedido = {
            "id": pid,
            "numero": item["numero"],
            "tipoSanguineo": item["tipoSanguineo"],
            "hospital": item["hospital"],
            "componente": item["componente"],
            "bolsasRecebidas": item["bolsasRecebidas"],
            "bolsasTotal": item["bolsasTotal"],
            "estado": item["estado"],
            "cidade": item["cidade"],
            "regiao": f"{item['cidade']} - {item['estado']}",
            "urgencia": item["urgencia"],
            "status": item["status"],
            "etapaAtual": item["etapaAtual"],
            "etapaTotal": item["etapaTotal"],
            "etapaNome": item["etapaNome"],
            "observacoes": item["observacoes"],
            "checklist": {
                "compatibilidadeTransfusional": item["status"] == "aprovado",
                "elegibilidadeDoadores": item["status"] == "aprovado",
                "urgenciaPedido": item["status"] == "aprovado",
            },
            "candidatos": [],
            "criadoEm": item["criadoEm"],
        }
        pedido["candidatos"] = _rank_for_pedido(pedido)
        store[pid] = pedido
    return store


_PEDIDOS_STORE: Dict[str, Dict[str, Any]] = _build_initial_pedidos()
_NEXT_NUMERO: int = max(p["numero"] for p in _PEDIDOS_STORE.values()) + 1


# ============================================================
# Rotas Gerais e Supabase
# ============================================================


@app.get("/health")
def health_check() -> Dict[str, Any]:
    meta = matcher_service.metadata
    return {
        "status": "ok",
        "modelo_ml": meta["selected_model_name"],
        "versao_modelo": meta["model_version"],
        "treinado_em": meta.get("trained_at"),
        "supabase_conectado": supabase is not None,
    }


@app.get("/itens")
def listar_itens() -> Any:
    if supabase is None:
        return []
    response = supabase.table("perfis").select("*").execute()
    return response.data


# ============================================================
# Rotas de Machine Learning
# ============================================================


@app.get("/api/ml/modelo")
def obter_modelo_ml() -> Dict[str, Any]:
    return matcher_service.metadata


@app.post("/api/ml/ranquear")
def ranquear_doadores(payload: RankRequest) -> Dict[str, Any]:
    bt = normalize_blood_type(payload.tipo_sanguineo)
    if bt is None:
        raise HTTPException(
            status_code=422,
            detail=f"Tipo sanguíneo inválido: '{payload.tipo_sanguineo}'. Use um valor ABO/Rh válido (ex.: O-, A+).",
        )

    request_dict = {
        "tipo_sanguineo": bt,
        "componente": normalize_component(payload.componente),
        "urgencia": normalize_urgency(payload.urgencia),
        "bolsas_total": payload.bolsas_total,
        "bolsas_recebidas": payload.bolsas_recebidas,
        "estado": payload.estado.upper(),
        "cidade": payload.cidade,
        "hospital": payload.hospital,
    }
    donors = _get_donor_pool(payload.doadores)
    return matcher_service.rank_donors(
        request=request_dict,
        donors=donors,
        top_k=payload.top_k,
        max_distance_km=payload.max_distance_km,
        include_shap=payload.include_shap,
        include_temporarily_unavailable=payload.include_temporarily_unavailable,
    )


@app.post("/api/ml/feedback")
def registrar_feedback(payload: FeedbackInput) -> Dict[str, Any]:
    valid_outcomes = {
        "pendente",
        "ignorou",
        "recusou",
        "respondeu_tarde",
        "agendou",
        "compareceu_doou",
    }
    if payload.desfecho_real not in valid_outcomes:
        raise HTTPException(
            status_code=422,
            detail=f"Desfecho inválido: '{payload.desfecho_real}'.",
        )

    entry = {
        "pedido_id": payload.pedido_id,
        "doador_codigo": payload.doador_codigo,
        "desfecho_real": payload.desfecho_real,
        "aprovado_equipe_clinica": payload.aprovado_equipe_clinica,
        "match_sucesso": payload.desfecho_real == "compareceu_doou",
        "observacoes": payload.observacoes,
        "registrado_em": datetime.now(timezone.utc).isoformat(),
    }
    _FEEDBACK_LOG.append(entry)
    return {"status": "registrado", "feedback": entry}


# ============================================================
# Rotas de Solicitações e Revisão Clínica (Frontend React)
# ============================================================


@app.get("/api/solicitacoes")
def listar_solicitacoes(
    urgencia: str = Query(default="todos"),
    ordem: str = Query(default="urgentes"),
) -> Dict[str, Any]:
    pedidos = list(_PEDIDOS_STORE.values())
    urg_filter = urgencia.strip().lower()
    if urg_filter and urg_filter != "todos":
        urg_norm = normalize_urgency(urg_filter)
        filtered = [p for p in pedidos if p["urgencia"] == urg_norm]
    else:
        filtered = pedidos

    if ordem == "recentes":
        filtered.sort(key=lambda p: p["criadoEm"], reverse=True)
    else:
        filtered.sort(
            key=lambda p: (_URGENCIA_ORDER.get(p["urgencia"], 99), -p["numero"])
        )

    abertos = sum(1 for p in pedidos if p["status"] not in ("concluido", "recusado"))
    aguardando = sum(1 for p in pedidos if p["status"] == "na_fila")
    return {
        "itens": filtered,
        "resumo": {
            "pedidosAbertos": abertos,
            "aguardandoRevisao": aguardando,
        },
    }


@app.post("/api/solicitacoes")
def criar_solicitacao(payload: CreateSolicitacaoInput) -> Dict[str, Any]:
    global _NEXT_NUMERO

    bt = normalize_blood_type(payload.tipo)
    if bt is None:
        raise HTTPException(
            status_code=422,
            detail=f"Tipo sanguíneo inválido: '{payload.tipo}'.",
        )

    numero = _NEXT_NUMERO
    _NEXT_NUMERO += 1
    pid = str(numero)
    estado = payload.estado.strip().upper()
    cidade = payload.cidade.strip()
    urgencia = normalize_urgency(payload.urgencia)

    pedido: Dict[str, Any] = {
        "id": pid,
        "numero": numero,
        "tipoSanguineo": bt,
        "hospital": payload.hospital.strip(),
        "componente": payload.componente.strip() or "Concentrado de hemácias",
        "bolsasRecebidas": 0,
        "bolsasTotal": payload.bolsas,
        "estado": estado,
        "cidade": cidade,
        "regiao": f"{cidade} - {estado}" if cidade and estado else cidade or estado,
        "urgencia": urgencia,
        "status": "na_fila",
        "etapaAtual": 2,
        "etapaTotal": 5,
        "etapaNome": "Candidatos prontos",
        "observacoes": payload.observacoes,
        "checklist": {
            "compatibilidadeTransfusional": False,
            "elegibilidadeDoadores": False,
            "urgenciaPedido": False,
        },
        "candidatos": [],
        "criadoEm": datetime.now(timezone.utc).isoformat(),
    }
    pedido["candidatos"] = _rank_for_pedido(pedido)
    _PEDIDOS_STORE[pid] = pedido
    return pedido


@app.get("/api/revisao/fila")
def listar_fila_revisao() -> Dict[str, Any]:
    itens = [p for p in _PEDIDOS_STORE.values() if p["status"] == "na_fila"]
    itens.sort(key=lambda p: (_URGENCIA_ORDER.get(p["urgencia"], 99), -p["numero"]))
    return {"itens": itens}


@app.get("/api/revisao/pedidos/{pedido_id}")
def obter_pedido_revisao(pedido_id: str) -> Dict[str, Any]:
    pedido = _PEDIDOS_STORE.get(str(pedido_id))
    if pedido is None:
        raise HTTPException(status_code=404, detail=f"Pedido '{pedido_id}' não encontrado.")
    if not pedido.get("candidatos"):
        pedido["candidatos"] = _rank_for_pedido(pedido)
    return pedido


@app.post("/api/revisao/pedidos/{pedido_id}/aprovar")
def aprovar_pedido(pedido_id: str, payload: AprovarPedidoInput) -> Dict[str, Any]:
    pedido = _PEDIDOS_STORE.get(str(pedido_id))
    if pedido is None:
        raise HTTPException(status_code=404, detail=f"Pedido '{pedido_id}' não encontrado.")

    selecionados_set = set(payload.selecionados)
    for cand in pedido.get("candidatos", []):
        cand["selecionado"] = cand["codigo"] in selecionados_set
        _FEEDBACK_LOG.append(
            {
                "pedido_id": pedido["id"],
                "doador_codigo": cand["codigo"],
                "aprovado_equipe_clinica": cand["selecionado"],
                "desfecho_real": "pendente",
                "registrado_em": datetime.now(timezone.utc).isoformat(),
            }
        )

    pedido["checklist"] = {**pedido.get("checklist", {}), **payload.checklist}
    pedido["status"] = "aprovado"
    pedido["etapaAtual"] = 4
    pedido["etapaNome"] = "Contato em andamento"
    return pedido


@app.post("/api/revisao/pedidos/{pedido_id}/devolver")
def devolver_pedido(pedido_id: str) -> Dict[str, Any]:
    pedido = _PEDIDOS_STORE.get(str(pedido_id))
    if pedido is None:
        raise HTTPException(status_code=404, detail=f"Pedido '{pedido_id}' não encontrado.")

    pedido["status"] = "devolvido"
    pedido["etapaAtual"] = 1
    pedido["etapaNome"] = "Devolvido para ajustes"
    return pedido


@app.post("/api/revisao/pedidos/{pedido_id}/recusar")
def recusar_pedido(pedido_id: str) -> Dict[str, Any]:
    pedido = _PEDIDOS_STORE.get(str(pedido_id))
    if pedido is None:
        raise HTTPException(status_code=404, detail=f"Pedido '{pedido_id}' não encontrado.")

    pedido["status"] = "recusado"
    pedido["etapaNome"] = "Recusado na revisão clínica"
    return pedido
