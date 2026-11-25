import { useCallback, useEffect, useState } from "react";
import { TriangleAlert, Clock, Inbox } from "lucide-react";

/* ============================================================
   CONTRATO DE DADOS — Revisão clínica

   GET  /api/revisao/fila                  -> { itens: Pedido[] }  (somente na_fila)
   GET  /api/revisao/pedidos/{id}          -> Pedido
   POST /api/revisao/pedidos/{id}/aprovar  { selecionados, checklist } -> Pedido
   POST /api/revisao/pedidos/{id}/devolver -> Pedido
   POST /api/revisao/pedidos/{id}/recusar  -> Pedido

   Pedido {
     id: string,
     numero: number,               // 2041
     tipoSanguineo: string,        // "O-"
     hospital: string,             // "Hospital Santa Clara"
     componente: string,           // "Concentrado de hemácias"
     bolsasRecebidas: number,
     bolsasTotal: number,
     regiao: string,               // "Recife - PE"
     urgencia: "emergencia" | "urgente" | "normal",
     status: "na_fila" | "aprovado" | "devolvido" | "recusado",
     etapaAtual: number,
     etapaTotal: number,
     etapaNome: string,
     checklist: { compatibilidadeTransfusional, elegibilidadeDoadores, urgenciaPedido },
     candidatos: [{
       codigo: string,             // "D-0301"
       cidade: string,             // "Olinda - PE"
       tipoSanguineo: string,
       distanciaKm: number,
       compatibilidade: number,    // 0-100
       situacao: "disponivel_agora" | "responde_1h",
       selecionado: boolean,
     }],
     criadoEm: string,             // ISO
   }
   ============================================================ */

const API_URL = `${import.meta.env.VITE_BACKEND_URL ?? ""}/api`;

const URGENCIA = {
  emergencia: {
    label: "Emergência",
    badge: "bg-[#B3122B] text-white",
    circulo: "bg-[#C8102E] text-white",
  },
  urgente: {
    label: "Urgente",
    badge: "bg-[#FDF1D8] text-[#8A5A00] border border-[#F0D9A8]",
    circulo: "bg-[#F6D976] text-[#5C4400]",
  },
  normal: {
    label: "Normal",
    badge: "bg-[#ECECEE] text-[#55555C]",
    circulo: "bg-[#F6D976] text-[#5C4400]",
  },
};

const SITUACAO = {
  disponivel_agora: { label: "Disponível agora", classe: "font-semibold text-[#2B2B30]" },
  responde_1h: { label: "Responde em 1h", classe: "text-[#6B6B73]" },
};

const CHECKLIST = [
  { chave: "compatibilidadeTransfusional", label: "Confirmei a compatibilidade transfusional" },
  { chave: "elegibilidadeDoadores", label: "Confirmei a elegibilidade dos doadores selecionados" },
  { chave: "urgenciaPedido", label: "Validei a urgência do pedido" },
];

const GRID_CANDIDATOS =
  "grid grid-cols-[24px_36px_minmax(130px,1.3fr)_44px_64px_minmax(140px,1.5fr)_110px] items-center gap-3";

function formatarTempo(iso) {
  if (!iso) return "";
  const min = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (min < 1) return "agora";
  if (min < 60) return `há ${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `há ${h} h`;
  return `há ${Math.floor(h / 24)} d`;
}

function formatarKm(valor) {
  return `${Number(valor ?? 0).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} km`;
}

/* ============================================================
   COMPONENTES BASE
   ============================================================ */

function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-md bg-black/10 ${className}`} />;
}

function Botao({ kind = "primary", className = "", ...props }) {
  const estilos = {
    primary: "bg-[#C8102E] text-white hover:bg-[#A80D26]",
    outline: "border border-[#C8102E] text-[#C8102E] bg-white hover:bg-[#FDECEE]",
    ghost: "border border-[#D9D9DD] text-[#2B2B30] bg-white hover:bg-[#F4F4F6]",
  };
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-[13px] font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#C8102E] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${estilos[kind]} ${className}`}
      {...props}
    />
  );
}

function Caixa({ checked, onChange, testid, ariaLabel }) {
  return (
    <input
      type="checkbox"
      checked={checked}
      onChange={onChange}
      aria-label={ariaLabel}
      data-testid={testid}
      className="h-4 w-4 cursor-pointer rounded accent-[#C8102E]"
    />
  );
}

function BadgeUrgencia({ urgencia }) {
  const u = URGENCIA[urgencia] ?? URGENCIA.normal;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${u.badge}`}>
      {urgencia === "emergencia" && <TriangleAlert size={11} />}
      {urgencia === "urgente" && <Clock size={11} />}
      {u.label}
    </span>
  );
}

/* ============================================================
   FILA (col esquerda)
   ============================================================ */

function ItemFila({ item, ativo, disabled, onClick }) {
  const u = URGENCIA[item.urgencia] ?? URGENCIA.normal;
  return (
    <button
      type="button"
      data-testid={`fila-item-${item.numero}`}
      onClick={onClick}
      disabled={disabled}
      className={`w-full rounded-xl border p-3 text-left transition-colors disabled:cursor-wait disabled:opacity-60 ${
        ativo
          ? "border-[#C8102E] bg-[#FDECEE]"
          : "border-[#E9E6E2] bg-white hover:border-[#C8102E]/50"
      }`}
    >
      <div className="flex items-start gap-3">
        <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[13px] font-bold ${u.circulo}`}>
          {item.tipoSanguineo}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-bold text-[#1D1D22]">#{item.numero}</p>
          <p className="truncate text-[12px] text-[#6B6B73]">{item.hospital}</p>
          <div className="mt-1.5 flex items-center justify-between gap-2">
            <BadgeUrgencia urgencia={item.urgencia} />
            <span className="text-[11px] text-[#6B6B73]">{formatarTempo(item.criadoEm)}</span>
          </div>
        </div>
      </div>
    </button>
  );
}

function CardFila({ fila, carregando, erro, selecionadoId, disabled, onSelect, onTentarDeNovo }) {
  return (
    <section data-testid="fila-card" className="h-fit rounded-2xl bg-white p-4">
      <h2 className="text-[14px] font-bold text-[#1D1D22]">
        Na fila{" "}
        <span data-testid="fila-count" className="font-semibold text-[#6B6B73]">
          ({carregando ? "…" : fila?.length ?? 0})
        </span>
      </h2>

      <div className="mt-3 flex flex-col gap-2">
        {carregando &&
          Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-[76px] w-full rounded-xl" />)}

        {!carregando && erro && (
          <div className="rounded-xl bg-[#FDECEE] p-4 text-center">
            <p className="text-[12px] font-semibold text-[#B3122B]">Não foi possível carregar a fila.</p>
            <Botao kind="ghost" className="mt-2" data-testid="fila-tentar-de-novo" onClick={onTentarDeNovo}>
              Tentar de novo
            </Botao>
          </div>
        )}

        {!carregando && !erro && (fila ?? []).length === 0 && (
          <p className="rounded-xl bg-[#F7F5F3] p-4 text-center text-[12px] text-[#6B6B73]">
            Nenhuma solicitação aguardando revisão.
          </p>
        )}

        {!carregando &&
          !erro &&
          (fila ?? []).map((item) => (
            <ItemFila
              key={item.id}
              item={item}
              ativo={item.id === selecionadoId}
              disabled={disabled}
              onClick={() => onSelect(item.id)}
            />
          ))}
      </div>
    </section>
  );
}

/* ============================================================
   DETALHE (coluna direita)
   ============================================================ */

function Estatistica({ rotulo, valor }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[#6B6B73]">{rotulo}</p>
      <p className="mt-0.5 text-[13px] font-bold text-[#1D1D22]">{valor}</p>
    </div>
  );
}

function LinhaCandidato({ candidato, ranking, enviando, onAlternar }) {
  const situacao = SITUACAO[candidato.situacao] ?? SITUACAO.responde_1h;
  return (
    <li className={`${GRID_CANDIDATOS} border-b border-[#F1EFEC] py-3 last:border-0`}>
      <Caixa
        checked={candidato.selecionado}
        onChange={() => onAlternar(candidato.codigo)}
        testid={`candidato-checkbox-${candidato.codigo}`}
        ariaLabel={`Selecionar candidato ${candidato.codigo}`}
      />
      <span className="text-[13px] font-bold text-[#1D1D22]">{ranking}º</span>
      <div className="min-w-0">
        <p className="text-[13px] font-bold text-[#1D1D22]">{candidato.codigo}</p>
        <p className="truncate text-[11px] text-[#6B6B73]">{candidato.cidade}</p>
      </div>
      <span className="text-[13px] text-[#6B6B73]">{candidato.tipoSanguineo}</span>
      <span className="text-[13px] text-[#6B6B73]">{formatarKm(candidato.distanciaKm)}</span>
      <div className="flex items-center gap-2">
        <div className="h-1.5 flex-1 rounded-full bg-[#F1EFEC]">
          <div className="h-full rounded-full bg-[#C8102E]" style={{ width: `${candidato.compatibilidade}%` }} />
        </div>
        <span className="w-10 text-right text-[13px] font-bold text-[#1D1D22]">{candidato.compatibilidade}%</span>
      </div>
      <span className={`text-[12px] ${situacao.classe}`}>{situacao.label}</span>
    </li>
  );
}

function DetalhePedido({ pedido, selecionados, checklist, enviando, onAlternarCandidato, onAlternarChecklist, onAprovar, onDevolver, onRecusar }) {
  const total = selecionados.length;

  return (
    <section data-testid="pedido-detalhe" className="rounded-2xl bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-[16px] font-bold text-[#1D1D22]">
          Pedido #{pedido.numero} · {pedido.hospital}
        </h2>
        <BadgeUrgencia urgencia={pedido.urgencia} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Estatistica rotulo="Tipo" valor={pedido.tipoSanguineo} />
        <Estatistica rotulo="Componente" valor={pedido.componente} />
        <Estatistica rotulo="Bolsas" valor={`${pedido.bolsasRecebidas} de ${pedido.bolsasTotal}`} />
        <Estatistica rotulo="Região" valor={pedido.regiao} />
      </div>

      <hr className="mt-5 border-[#F1EFEC]" />

      <h3 className="mt-5 text-[14px] font-bold text-[#1D1D22]">Candidatos pela IA</h3>
      <div className="mt-2 overflow-x-auto">
        <div className="min-w-[640px]">
          <div className={`${GRID_CANDIDATOS} border-b border-[#F1EFEC] pb-2 text-[10px] font-semibold uppercase tracking-wide text-[#6B6B73]`}>
            <span />
            <span>Ranking</span>
            <span>Código</span>
            <span>Tipo</span>
            <span>Distância</span>
            <span>Compatibilidade</span>
            <span>Situação</span>
          </div>
          <ul>
            {pedido.candidatos.map((candidato, indice) => (
              <LinhaCandidato
                key={candidato.codigo}
                candidato={candidato}
                ranking={indice + 1}
                enviando={enviando}
                onAlternar={onAlternarCandidato}
              />
            ))}
          </ul>
        </div>
      </div>

      <h3 className="mt-5 text-[14px] font-bold text-[#1D1D22]">Checklist da equipe</h3>
      <div className="mt-2 flex flex-col gap-2.5">
        {CHECKLIST.map(({ chave, label }) => (
          <label key={chave} className="flex cursor-pointer items-center gap-2.5 text-[13px] text-[#2B2B30]">
            <Caixa
              checked={Boolean(checklist[chave])}
              onChange={() => onAlternarChecklist(chave)}
              testid={`checklist-${chave}`}
              ariaLabel={label}
            />
            {label}
          </label>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap gap-3 border-t border-[#F1EFEC] pt-4">
        <Botao
          kind="primary"
          data-testid="aprovar-btn"
          disabled={enviando || total === 0}
          onClick={onAprovar}
        >
          {enviando
            ? "Enviando…"
            : `Aprovar ${total} selecionado${total === 1 ? "" : "s"}`}
        </Botao>
        <Botao kind="outline" data-testid="devolver-btn" disabled={enviando} onClick={onDevolver}>
          Devolver ao solicitante
        </Botao>
        <Botao kind="ghost" data-testid="recusar-btn" disabled={enviando} onClick={onRecusar}>
          Recusar pedido
        </Botao>
      </div>
    </section>
  );
}

/* ============================================================
   PÁGINA
   ============================================================ */

export default function RevisaoClinicaPage({ pedidoInicial }) {
  const [fila, setFila] = useState(null);
  const [carregandoFila, setCarregandoFila] = useState(true);
  const [erro, setErro] = useState(null);
  const [selecionadoId, setSelecionadoId] = useState(null);
  const [pedido, setPedido] = useState(null);
  const [carregandoPedido, setCarregandoPedido] = useState(false);
  const [selecionados, setSelecionados] = useState([]);
  const [checklist, setChecklist] = useState({});
  const [enviando, setEnviando] = useState(false);

  const carregarFila = useCallback(async (alvo) => {
    setCarregandoFila(true);
    setErro(null);
    try {
      const res = await fetch(`${API_URL}/revisao/fila?_=${Date.now()}`);
      if (!res.ok) throw new Error("Falha ao carregar a fila de revisão.");
      const json = await res.json();
      const itens = json.itens ?? [];
      setFila(itens);
      const alvoItem = itens.find((i) => String(i.numero) === String(alvo)) ?? itens[0] ?? null;
      setSelecionadoId(alvoItem?.id ?? null);
      if (!alvoItem) setPedido(null);
    } catch (e) {
      setErro(e.message);
      setFila([]);
      setSelecionadoId(null);
      setPedido(null);
    } finally {
      setCarregandoFila(false);
    }
  }, []);

  useEffect(() => {
    carregarFila(pedidoInicial);
  }, [carregarFila, pedidoInicial]);

  useEffect(() => {
    if (!selecionadoId) {
      setPedido(null);
      return;
    }
    let cancelado = false;
    setCarregandoPedido(true);
    fetch(`${API_URL}/revisao/pedidos/${selecionadoId}?_=${Date.now()}`)
      .then((res) => {
        if (!res.ok) throw new Error("Não foi possível carregar o pedido.");
        return res.json();
      })
      .then((detalhe) => {
        if (cancelado) return;
        setPedido(detalhe);
        setSelecionados((detalhe.candidatos ?? []).filter((c) => c.selecionado).map((c) => c.codigo));
        setChecklist(Object.fromEntries(CHECKLIST.map(({ chave }) => [chave, false])));
      })
      .catch(() => {
        if (!cancelado) {
          setPedido(null);
          setErro("Não foi possível carregar o pedido. Tente de novo.");
        }
      })
      .finally(() => {
        if (!cancelado) setCarregandoPedido(false);
      });
    return () => {
      cancelado = true;
    };
  }, [selecionadoId]);

  async function agir(acao, corpo) {
    if (!selecionadoId || enviando) return;
    setEnviando(true);
    try {
      const res = await fetch(`${API_URL}/revisao/pedidos/${selecionadoId}/${acao}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corpo ?? {}),
      });
      if (!res.ok) throw new Error();
      await carregarFila(null);
    } catch {
      setErro("Não foi possível concluir a ação. Tente de novo.");
    } finally {
      setEnviando(false);
    }
  }

  function alternarCandidato(codigo) {
    setSelecionados((atual) =>
      atual.includes(codigo) ? atual.filter((c) => c !== codigo) : [...atual, codigo]
    );
  }

  function alternarChecklist(chave) {
    setChecklist((atual) => ({ ...atual, [chave]: !atual[chave] }));
  }

  return (
    <main data-testid="revisao-page" className="min-h-screen flex-1 bg-[#F7F5F3] px-8 py-8 font-sans text-[#2B2B30]">
      <header>
        <h1 className="text-[26px] font-bold text-[#1D1D22]">Revisão clínica</h1>
        <p className="text-[13px] text-[#6B6B73]">
          A IA sugere candidatos. A equipe clínica confirma a elegibilidade e a compatibilidade.
        </p>
      </header>

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-[300px_1fr]">
        <CardFila
          fila={fila}
          carregando={carregandoFila}
          erro={erro}
          selecionadoId={selecionadoId}
          disabled={enviando}
          onSelect={setSelecionadoId}
          onTentarDeNovo={() => carregarFila(pedidoInicial)}
        />

        {carregandoFila || (!pedido && selecionadoId && carregandoPedido) ? (
          <section className="rounded-2xl bg-white p-5">
            <Skeleton className="h-6 w-64" />
            <Skeleton className="mt-4 h-4 w-full" />
            <Skeleton className="mt-8 h-4 w-40" />
            <Skeleton className="mt-3 h-24 w-full" />
          </section>
        ) : null}

        {!carregandoFila && !carregandoPedido && !pedido && !erro && (
          <section className="flex min-h-[300px] flex-col items-center justify-center rounded-2xl bg-white p-10 text-center">
            <Inbox size={28} className="text-[#6B6B73]" />
            <p className="mt-3 text-[14px] font-semibold text-[#2B2B30]">Nenhum pedido na fila</p>
            <p className="text-[12px] text-[#6B6B73]">
              Quando uma nova solicitação entrar, ela aparece aqui para revisão.
            </p>
          </section>
        )}

        {!carregandoFila && pedido && (
          <DetalhePedido
            pedido={pedido}
            selecionados={selecionados}
            checklist={checklist}
            enviando={enviando}
            onAlternarCandidato={alternarCandidato}
            onAlternarChecklist={alternarChecklist}
            onAprovar={() => agir("aprovar", { selecionados, checklist })}
            onDevolver={() => agir("devolver")}
            onRecusar={() => agir("recusar")}
          />
        )}
      </div>
    </main>
  );
}
