import { useEffect, useMemo, useState } from "react";
import {
  TriangleAlert,
  Clock,
  ArrowRight,
  ChevronDown,
} from "lucide-react";

/* ============================================================
   1. CONTRATO DE DADOS
   Quando o banco estiver pronto, a API só precisa devolver
   este formato. O front não muda.

   GET /api/solicitacoes?urgencia=todos|emergencia|urgente|normal&ordem=urgentes|recentes
   -> { itens: Solicitacao[], resumo: Resumo }

   Solicitacao {
     id: string,                // "2041"
     tipoSanguineo: string,     // "O-"
     hospital: string,          // "Hospital Santa Clara"
     componente: string,        // "Concentrado de hemácias"
     bolsasRecebidas: number,
     bolsasTotal: number,
     urgencia: "emergencia" | "urgente" | "normal",
     etapaAtual: number,        // 2
     etapaTotal: number,        // 5
     etapaNome: string,         // "Candidatos prontos"
   }

   Resumo { pedidosAbertos: number, aguardandoRevisao: number }

   ============================================================ */

const API_URL = ""; // ex.: "https://seu-backend.com/api"
const USE_MOCK = true; // coloque false quando a API estiver pronta

const MOCK = {
  itens: [
    { id: "2041", tipoSanguineo: "O-", hospital: "Hospital Santa Clara", componente: "Concentrado de hemácias", bolsasRecebidas: 1, bolsasTotal: 5, urgencia: "emergencia", etapaAtual: 2, etapaTotal: 5, etapaNome: "Candidatos prontos" },
    { id: "2040", tipoSanguineo: "A+", hospital: "Maternidade Boa Vida", componente: "Concentrado de hemácias", bolsasRecebidas: 1, bolsasTotal: 3, urgencia: "urgente", etapaAtual: 3, etapaTotal: 5, etapaNome: "Aguardando revisão clínica" },
    { id: "2038", tipoSanguineo: "B+", hospital: "Hospital do Coração", componente: "Plaquetas", bolsasRecebidas: 0, bolsasTotal: 2, urgencia: "normal", etapaAtual: 1, etapaTotal: 5, etapaNome: "Agente analisando" },
    { id: "2035", tipoSanguineo: "AB+", hospital: "Clínica São José", componente: "Plasma", bolsasRecebidas: 2, bolsasTotal: 4, urgencia: "urgente", etapaAtual: 4, etapaTotal: 5, etapaNome: "Contato em andamento" },
    { id: "2031", tipoSanguineo: "O+", hospital: "Hospital da Orla", componente: "Concentrado de hemácias", bolsasRecebidas: 6, bolsasTotal: 6, urgencia: "normal", etapaAtual: 5, etapaTotal: 5, etapaNome: "Concluído" },
  ],
  resumo: { pedidosAbertos: 4, aguardandoRevisao: 2 },
};

/* ============================================================
   2. HOOKS DE DADOS
   ============================================================ */

function useSolicitacoes({ urgencia, ordem }) {
  const [state, setState] = useState({ data: null, loading: true, error: null });

  useEffect(() => {
    let cancelado = false;
    setState((s) => ({ ...s, loading: true, error: null }));

    async function carregar() {
      try {
        if (USE_MOCK) {
          await new Promise((r) => setTimeout(r, 400));
          if (!cancelado) setState({ data: MOCK, loading: false, error: null });
          return;
        }
        const qs = new URLSearchParams({ urgencia, ordem }).toString();
        const res = await fetch(`${API_URL}/solicitacoes?${qs}`);
        if (!res.ok) throw new Error("Falha ao carregar solicitações");
        const json = await res.json();
        if (!cancelado) setState({ data: json, loading: false, error: null });
      } catch (e) {
        if (!cancelado) setState({ data: null, loading: false, error: e.message });
      }
    }
    carregar();
    return () => {
      cancelado = true;
    };
  }, [urgencia, ordem]);

  return state;
}

/* ============================================================
   3. CONFIG VISUAL
   ============================================================ */

const URGENCIA = {
  emergencia: { label: "Emergência", badge: "bg-[#B3122B] text-white", bar: "bg-[#C8102E]", row: "bg-[#FDECEE]", cta: "primary" },
  urgente: { label: "Urgente", badge: "bg-[#FDF1D8] text-[#8A5A00] border border-[#F0D9A8]", bar: "bg-[#C8102E]", row: "bg-white", cta: "primary" },
  normal: { label: "Normal", badge: "bg-[#ECECEE] text-[#55555C]", bar: "bg-[#C8102E]", row: "bg-white", cta: "outline" },
};

const FILTROS = [
  { value: "todos", label: "Todos" },
  { value: "emergencia", label: "Emergência" },
  { value: "urgente", label: "Urgente" },
  { value: "normal", label: "Normal" },
];

const ORDENS = [
  { value: "urgentes", label: "Mais urgentes" },
  { value: "recentes", label: "Mais recentes" },
];


function acaoDoPedido(s) {
  if (s.etapaAtual >= s.etapaTotal) return { label: "Ver resumo", kind: "ghost" };
  if (s.etapaNome.toLowerCase().includes("candidatos") || s.etapaNome.toLowerCase().includes("revisão"))
    return { label: "Ver candidatos", kind: "primary" };
  return { label: "Abrir", kind: "outline" };
}

/* ============================================================
   4. COMPONENTES BASE
   ============================================================ */

function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-md bg-black/10 ${className}`} />;
}

/** Barra segmentada de andamento (etapas) */
function StepBar({ atual, total, concluido = false, onDark = false }) {
  const cor = concluido ? "bg-[#2E8B4A]" : onDark ? "bg-white" : "bg-[#C8102E]";
  const vazio = onDark ? "bg-white/30" : "bg-[#D9D9DD]";
  return (
    <div className="flex gap-1.5" role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={atual}>
      {Array.from({ length: total }).map((_, i) => (
        <span key={i} className={`h-[3px] flex-1 rounded-full ${i < atual ? cor : vazio}`} />
      ))}
    </div>
  );
}

/** Barra contínua de bolsas */
function BagBar({ recebidas, total, onDark = false }) {
  const pct = total > 0 ? Math.min(100, (recebidas / total) * 100) : 0;
  return (
    <div className={`h-[3px] w-full rounded-full ${onDark ? "bg-white/30" : "bg-[#D9D9DD]"}`}>
      <div className={`h-full rounded-full ${onDark ? "bg-white" : "bg-[#C8102E]"}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function Button({ kind = "primary", children, className = "", ...props }) {
  const styles = {
    primary: "bg-[#C8102E] text-white hover:bg-[#A80D26]",
    outline: "border border-[#C8102E] text-[#C8102E] bg-white hover:bg-[#FDECEE]",
    ghost: "border border-[#D9D9DD] text-[#2B2B30] bg-white hover:bg-[#F4F4F6]",
    onDark: "bg-white text-[#2B2B30] hover:bg-[#F4F4F6]",
  };
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-[13px] font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#C8102E] focus-visible:ring-offset-2 ${styles[kind]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

/* ============================================================
   6. CARD DE DESTAQUE (emergência)
   ============================================================ */

function DestaqueEmergencia({ pedido, loading, onVerCandidatos }) {
  const base = "relative overflow-hidden rounded-2xl bg-[#C8102E] p-5 text-white";

  if (loading) {
    return (
      <section className={`${base} min-h-[150px]`}>
        <Skeleton className="h-5 w-28 bg-white/30" />
        <Skeleton className="mt-6 h-12 w-72 bg-white/30" />
      </section>
    );
  }

  if (!pedido) {
    return (
      <section className={`${base} flex min-h-[150px] items-center bg-[#F1F1F3] text-[#55555C]`}>
        <div>
          <p className="text-[15px] font-semibold text-[#2B2B30]">Nenhuma emergência hoje</p>
          <p className="text-[13px]">Pedidos de emergência aparecem aqui assim que forem abertos.</p>
        </div>
      </section>
    );
  }

  const faltam = Math.max(0, pedido.bolsasTotal - pedido.bolsasRecebidas);

  return (
    <section className={`${base} flex min-h-[150px] flex-col justify-between`}>
      <span aria-hidden className="pointer-events-none absolute -right-10 -top-16 h-64 w-64 rounded-full bg-black/10" />
      <span aria-hidden className="pointer-events-none absolute right-16 top-10 h-40 w-40 rounded-full bg-black/10" />

      <div className="relative flex items-start justify-between gap-6">
        <div className="min-w-0 flex-1">
          <span className="inline-flex items-center gap-1.5 rounded-md bg-white px-2 py-0.5 text-[11px] font-semibold text-[#B3122B]">
            <TriangleAlert size={12} />
            Emergência hoje
          </span>

          <div className="mt-4 flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-white/15 text-[15px] font-bold">
              {pedido.tipoSanguineo}
            </span>
            <div className="min-w-0">
              <p className="truncate text-[16px] font-semibold">
                #{pedido.id} · {pedido.hospital}
              </p>
              <p className="text-[12px] text-white/80">{pedido.componente}</p>
            </div>
          </div>
        </div>

        <div className="w-[260px] shrink-0">
          <StepBar atual={pedido.etapaAtual} total={pedido.etapaTotal} onDark />
          <p className="mt-1.5 text-[11px] font-semibold">
            Etapa {pedido.etapaAtual} de {pedido.etapaTotal} · {pedido.etapaNome}
          </p>
          <Button kind="onDark" className="mt-3" onClick={() => onVerCandidatos?.(pedido)}>
            Ver candidatos <ArrowRight size={14} />
          </Button>
        </div>
      </div>

      <div className="relative mt-4">
        <div className="mb-1 flex justify-between text-[11px] font-semibold">
          <span>
            {pedido.bolsasRecebidas} de {pedido.bolsasTotal} bolsas
          </span>
          <span>Faltam {faltam}</span>
        </div>
        <BagBar recebidas={pedido.bolsasRecebidas} total={pedido.bolsasTotal} onDark />
      </div>
    </section>
  );
}

/* ============================================================
   7. CARDS DE RESUMO
   ============================================================ */

function ResumoCard({ titulo, valor, loading, acao, destaque }) {
  return (
    <div className="flex-1 rounded-2xl bg-white p-4">
      <p className="text-[12px] font-semibold text-[#2B2B30]">{titulo}</p>
      {loading ? (
        <Skeleton className="mt-2 h-8 w-10" />
      ) : (
        <p className="mt-1 text-[32px] font-bold leading-none text-[#1D1D22]">{valor ?? "–"}</p>
      )}
      {acao && !loading && (
        <a href="#" className={`mt-1.5 inline-block text-[12px] font-semibold ${destaque ? "text-[#C8102E]" : "text-[#2B2B30]"}`}>
          {acao}
        </a>
      )}
    </div>
  );
}

/* ============================================================
   8. LISTA DE PEDIDOS RECENTES
   ============================================================ */

const GRID = "grid grid-cols-[minmax(190px,1.4fr)_minmax(110px,0.9fr)_110px_minmax(200px,1.6fr)_130px] items-center gap-4";

function LinhaPedido({ pedido, onAcao }) {
  const u = URGENCIA[pedido.urgencia];
  const concluido = pedido.etapaAtual >= pedido.etapaTotal;
  const acao = acaoDoPedido(pedido);

  return (
    <li className={`${GRID} rounded-xl px-3 py-3 ${u.row}`}>
      <div className="flex items-center gap-3">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[#FDECEE] text-[14px] font-bold text-[#C8102E]">
          {pedido.tipoSanguineo}
        </span>
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-[#1D1D22]">#{pedido.id}</p>
          <p className="truncate text-[12px] text-[#2B2B30]">{pedido.hospital}</p>
          <p className="truncate text-[11px] text-[#6B6B73]">{pedido.componente}</p>
        </div>
      </div>

      <div>
        <p className="mb-1 text-[12px] text-[#2B2B30]">
          <span className="font-semibold">
            {pedido.bolsasRecebidas} de {pedido.bolsasTotal}
          </span>{" "}
          <span className="text-[#6B6B73]">bolsas</span>
        </p>
        <BagBar recebidas={pedido.bolsasRecebidas} total={pedido.bolsasTotal} />
      </div>

      <div>
        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${u.badge}`}>
          {pedido.urgencia === "emergencia" && <TriangleAlert size={11} />}
          {pedido.urgencia === "urgente" && <Clock size={11} />}
          {u.label}
        </span>
      </div>

      <div>
        <StepBar atual={pedido.etapaAtual} total={pedido.etapaTotal} concluido={concluido} />
        <p className={`mt-1.5 text-[11px] font-semibold ${concluido ? "text-[#2E8B4A]" : "text-[#2B2B30]"}`}>
          Etapa {pedido.etapaAtual} de {pedido.etapaTotal} · {pedido.etapaNome}
        </p>
      </div>

      <div className="flex justify-end">
        <Button kind={acao.kind} className="w-full" onClick={() => onAcao?.(pedido)}>
          {acao.label}
        </Button>
      </div>
    </li>
  );
}

function LinhaSkeleton() {
  return (
    <li className={`${GRID} rounded-xl bg-white px-3 py-3`}>
      <div className="flex items-center gap-3">
        <Skeleton className="h-11 w-11" />
        <div className="space-y-1.5">
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-3 w-28" />
        </div>
      </div>
      <Skeleton className="h-6 w-24" />
      <Skeleton className="h-6 w-20 rounded-full" />
      <Skeleton className="h-6 w-full" />
      <Skeleton className="h-8 w-full" />
    </li>
  );
}

function Seletor({ value, onChange, options }) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label="Ordenar pedidos"
        className="appearance-none rounded-full border border-[#E1E1E6] bg-white py-1.5 pl-4 pr-9 text-[12px] font-semibold text-[#2B2B30] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#C8102E]"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown size={14} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2" />
    </div>
  );
}

function PedidosRecentes({ itens, loading, error, filtro, onFiltro, ordem, onOrdem, onAcao }) {
  return (
    <section className="rounded-2xl bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-[16px] font-bold text-[#1D1D22]">Pedidos recentes</h2>
        <div className="flex items-center gap-3">
          <span className="text-[12px] font-semibold text-[#2B2B30]">Ordenar</span>
          <Seletor value={ordem} onChange={onOrdem} options={ORDENS} />
        </div>
      </div>

      <div className="mt-3 flex gap-2" role="tablist" aria-label="Filtrar por urgência">
        {FILTROS.map((f) => {
          const ativo = f.value === filtro;
          return (
            <button
              key={f.value}
              role="tab"
              aria-selected={ativo}
              onClick={() => onFiltro(f.value)}
              className={`rounded-full px-4 py-1.5 text-[12px] font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#C8102E] ${
                ativo ? "bg-[#1D1D22] text-white" : "border border-[#E1E1E6] bg-white text-[#2B2B30] hover:bg-[#F4F4F6]"
              }`}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      <div className={`${GRID} mt-4 px-3 text-[10px] font-semibold text-[#6B6B73]`}>
        <span>PEDIDO</span>
        <span>BOLSAS</span>
        <span>URGÊNCIA</span>
        <span>ANDAMENTO</span>
        <span />
      </div>

      <ul className="mt-1 flex flex-col gap-2">
        {loading && Array.from({ length: 4 }).map((_, i) => <LinhaSkeleton key={i} />)}

        {!loading && error && (
          <li className="rounded-xl bg-[#FDECEE] px-4 py-6 text-center text-[13px] text-[#B3122B]">
            Não foi possível carregar os pedidos. Verifique a conexão e tente de novo.
          </li>
        )}

        {!loading && !error && itens.length === 0 && (
          <li className="rounded-xl bg-[#F4F4F6] px-4 py-8 text-center">
            <p className="text-[13px] font-semibold text-[#2B2B30]">Nenhum pedido neste filtro</p>
            <p className="text-[12px] text-[#6B6B73]">Escolha outra urgência ou crie uma nova solicitação.</p>
          </li>
        )}

        {!loading && !error && itens.map((p) => <LinhaPedido key={p.id} pedido={p} onAcao={onAcao} />)}
      </ul>
    </section>
  );
}

/* ============================================================
   9. PÁGINA
   ============================================================ */

export default function SolicitacoesPage({ onVerCandidatos, onAbrirPedido }) {
  const [filtro, setFiltro] = useState("todos");
  const [ordem, setOrdem] = useState("urgentes");

  const { data, loading, error } = useSolicitacoes({ urgencia: filtro, ordem });

  const itens = data?.itens ?? [];
  const resumo = data?.resumo;

  // Destaque: primeiro pedido em emergência que ainda não foi concluído
  const destaque = useMemo(
    () => itens.find((p) => p.urgencia === "emergencia" && p.etapaAtual < p.etapaTotal) ?? null,
    [itens]
  );

  return (
    <main className="min-h-screen flex-1 bg-[#F0EFF1] px-8 py-8 font-sans text-[#2B2B30]">
        <header>
          <h1 className="text-[26px] font-bold text-[#1D1D22]">Solicitações</h1>
          <p className="text-[13px] text-[#6B6B73]">Acompanhe os pedidos de sangue do seu serviço.</p>
        </header>

        <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_260px]">
          <DestaqueEmergencia pedido={destaque} loading={loading} onVerCandidatos={onVerCandidatos} />

          <div className="flex gap-4 xl:flex-col">
            <ResumoCard titulo="Pedidos abertos" valor={resumo?.pedidosAbertos} loading={loading} />
            <ResumoCard
              titulo="Aguardando revisão clínica"
              valor={resumo?.aguardandoRevisao}
              loading={loading}
              acao="Ir para revisão"
              destaque
            />
          </div>
        </div>

        <div className="mt-4">
          <PedidosRecentes
            itens={itens}
            loading={loading}
            error={error}
            filtro={filtro}
            onFiltro={setFiltro}
            ordem={ordem}
            onOrdem={setOrdem}
            onAcao={onAbrirPedido}
          />
        </div>

        <footer className="mt-4 rounded-xl bg-[#E7E6E9] px-5 py-3 text-center text-[11px] leading-relaxed text-[#2B2B30]">
          <p>
            <strong>Privacidade:</strong> pacientes aparecem apenas por código de pedido. Os dados pessoais ficam restritos à equipe
            clínica autorizada.
          </p>
          <p>
            A IA ajuda a identificar possíveis compatibilidades. A elegibilidade para doação e a compatibilidade transfusional são
            confirmadas por profissionais de saúde.
          </p>
        </footer>
    </main>
  );
}
