
import { useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";

/* ============================================================
   Página Doadores — protótipo visual (dados fictícios)
   Só mostra código, cidade e distância: dados pessoais ficam
   restritos à equipe (LGPD).
   ============================================================ */

const TIPOS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

const SITUACAO = {
  disponivel_agora: "Disponível agora",
  responde_1h: "Responde em 1h",
  indisponivel: "Indisponível",
};

const doadoresMock = [
  { id: "D-0412", tipo: "O+", cidade: "Paulista", uf: "PE", distanciaKm: 1.2, situacao: "disponivel_agora", pos: { x: 14.8, y: 23 } },
  { id: "D-0388", tipo: "A+", cidade: "Paulista", uf: "PE", distanciaKm: 2.0, situacao: "responde_1h", pos: { x: 21.6, y: 49.7 } },
  { id: "D-0301", tipo: "O-", cidade: "Olinda", uf: "PE", distanciaKm: 2.5, situacao: "disponivel_agora", pos: { x: 50, y: 32 } },
  { id: "D-0275", tipo: "O+", cidade: "Recife", uf: "PE", distanciaKm: 3.1, situacao: "disponivel_agora", pos: { x: 73, y: 30 } },
  { id: "D-0219", tipo: "B+", cidade: "Recife", uf: "PE", distanciaKm: 4.4, situacao: "responde_1h", pos: { x: 79.7, y: 49.7 } },
  { id: "D-0190", tipo: "AB+", cidade: "Jaboatão", uf: "PE", distanciaKm: 7.8, situacao: "disponivel_agora", pos: { x: 44.5, y: 61 } },
];

const MUNICIPIOS = ["Todos", ...new Set(doadoresMock.map((d) => d.cidade))];

const rotuloTipo = (tipo) => tipo.replace("-", "−");
const formatarKm = (v) => `${v.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} km`;
const estaDisponivel = (d) => d.situacao !== "indisponivel";


function Seletor({ rotulo, valor, onChange, opcoes, largura }) {
  return (
    <label className={`block ${largura}`}>
      <span className="mb-1.5 block text-[13px] font-bold text-[#1D1D22]">{rotulo}</span>
      <span className="relative block">
        <select
          value={valor}
          onChange={(e) => onChange(e.target.value)}
          className="w-full appearance-none rounded-xl border border-[#E1DEDA] bg-white py-2.5 pl-3.5 pr-9 text-[14px] text-[#2B2B30] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#C8102E]"
        >
          {opcoes.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
        <ChevronDown
          size={16}
          aria-hidden="true"
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[#2B2B30]"
        />
      </span>
    </label>
  );
}

function ChipTipo({ tipo, ativo, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={ativo}
      className={`rounded-full border px-4 py-1.5 text-[13px] font-bold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#C8102E] focus-visible:ring-offset-2 ${
        ativo
          ? "border-[#C8102E] bg-[#C8102E] text-white"
          : "border-[#E1DEDA] bg-white text-[#2B2B30] hover:bg-[#FDF1F2]"
      }`}
    >
      {rotuloTipo(tipo)}
    </button>
  );
}

function AvatarTipo({ tipo, grande = false }) {
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-xl bg-[#FBDDE1] font-bold text-[#B3122B] ${
        grande ? "h-12 w-12 text-[16px]" : "h-11 w-11 text-[14px]"
      }`}
    >
      {rotuloTipo(tipo)}
    </span>
  );
}

function BotaoContato({ doador, onContato }) {
  return (
    <button
      type="button"
      disabled={!estaDisponivel(doador)}
      onClick={() => onContato(doador)}
      className="shrink-0 rounded-lg border border-[#C8102E] bg-white px-4 py-2 text-[13px] font-bold text-[#C8102E] transition-colors hover:bg-[#FDECEE] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#C8102E] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:border-[#D9D9DD] disabled:text-[#9A9AA2] disabled:hover:bg-white"
    >
      Solicitar contato
    </button>
  );
}

function TextoDoador({ doador }) {
  return (
    <div className="min-w-0">
      <p className="text-[15px] font-bold text-[#1D1D22]">{doador.id}</p>
      <p className="truncate text-[13px] text-[#2B2B30]">
        {doador.cidade} – {doador.uf} · {formatarKm(doador.distanciaKm)}
      </p>
      <p className="text-[12px] text-[#6B6B73]">{SITUACAO[doador.situacao]}</p>
    </div>
  );
}

function FundoMapa() {
  return (
    <svg viewBox="0 0 690 521" className="absolute inset-0 h-full w-full" aria-hidden="true">
      <rect width="690" height="521" fill="#E2DFDB" />
      <rect x="46" y="70" width="130" height="90" rx="14" fill="#E9E7E4" />
      <rect x="252" y="210" width="110" height="70" rx="14" fill="#EAE8E5" />
      <rect x="438" y="98" width="120" height="56" rx="14" fill="#E9E7E4" />
      <path d="M0 365 Q150 378 300 420 T690 485 L690 521 L0 521 Z" fill="#CFD9DF" />
      <g stroke="#F6F5F3" strokeLinecap="round" fill="none">
        <path d="M0 72 L690 90" strokeWidth="10" />
        <path d="M0 182 L690 205" strokeWidth="14" />
        <path d="M0 322 L535 280" strokeWidth="12" />
        <path d="M210 0 L275 521" strokeWidth="16" />
        <path d="M505 0 L450 521" strokeWidth="14" />
        <path d="M610 0 L600 380" strokeWidth="9" />
      </g>
    </svg>
  );
}

function Pino({ doador, ativo, onSelecionar }) {
  return (
    <button
      type="button"
      onClick={() => onSelecionar(doador.id)}
      aria-label={`Doador ${doador.id}, tipo ${doador.tipo}, ${doador.cidade}`}
      aria-pressed={ativo}
      style={{ left: `${doador.pos.x}%`, top: `${doador.pos.y}%`, zIndex: ativo ? 20 : 10 }}
      className={`absolute origin-bottom -translate-x-1/2 -translate-y-full rounded-lg transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-[#C8102E] ${
        ativo ? "scale-125" : "hover:scale-110"
      }`}
    >
      <svg width="40" height="50" viewBox="0 0 36 46" aria-hidden="true">
        <path
          d="M18 44C18 44 3 28 3 17a15 15 0 0 1 30 0c0 11-15 27-15 27Z"
          fill={ativo ? "#A3081F" : "#C8102E"}
          stroke="#fff"
          strokeWidth="2.5"
        />
        <text x="18" y="21" textAnchor="middle" fontSize="11" fontWeight="700" fill="#fff" fontFamily="inherit">
          {rotuloTipo(doador.tipo)}
        </text>
      </svg>
    </button>
  );
}

/* ============================================================
   PÁGINA
   ============================================================ */

export default function DoadoresPage() {
  const [estado, setEstado] = useState("PE");
  const [municipio, setMunicipio] = useState("Todos");
  const [tiposSelecionados, setTiposSelecionados] = useState([]);
  const [apenasDisponiveis, setApenasDisponiveis] = useState(true);
  const [selecionadoId, setSelecionadoId] = useState("D-0301");
  const [aviso, setAviso] = useState("");

  const doadores = useMemo(
    () =>
      doadoresMock
        .filter((d) => d.uf === estado)
        .filter((d) => municipio === "Todos" || d.cidade === municipio)
        .filter((d) => tiposSelecionados.length === 0 || tiposSelecionados.includes(d.tipo))
        .filter((d) => !apenasDisponiveis || estaDisponivel(d))
        .sort((a, b) => a.distanciaKm - b.distanciaKm),
    [estado, municipio, tiposSelecionados, apenasDisponiveis]
  );

  const ativo = doadores.find((d) => d.id === selecionadoId) ?? doadores[0] ?? null;

  function alternarTipo(tipo) {
    setTiposSelecionados((atual) =>
      atual.includes(tipo) ? atual.filter((t) => t !== tipo) : [...atual, tipo]
    );
  }

  function limparFiltros() {
    setMunicipio("Todos");
    setTiposSelecionados([]);
    setApenasDisponiveis(false);
  }

  function solicitarContato(doador) {
    setAviso(`Protótipo: o contato com ${doador.id} será integrado ao backend.`);
    setTimeout(() => setAviso(""), 3500);
  }

  return (
    <main className="min-h-screen flex-1 bg-[#ECEAE7] px-8 py-8 font-sans text-[#2B2B30]">
      <header>
        <h1 className="text-[28px] font-bold text-[#1D1D22]">Doadores</h1>
        <p className="text-[14px] text-[#6B6B73]">
          Encontre doadores compatíveis por tipo sanguíneo e região. Dados pessoais ficam restritos à equipe.
        </p>
      </header>

      <section className="mt-4 rounded-2xl bg-[#F4F2F0] p-5">
        <div className="flex flex-wrap items-end gap-x-4 gap-y-4">
          <Seletor rotulo="Estado" valor={estado} onChange={setEstado} opcoes={["PE"]} largura="w-[170px]" />
          <Seletor
            rotulo="Município"
            valor={municipio}
            onChange={setMunicipio}
            opcoes={MUNICIPIOS}
            largura="w-[170px]"
          />

          <div>
            <span className="mb-1.5 block text-[13px] font-bold text-[#1D1D22]">Tipo sanguíneo</span>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por tipo sanguíneo">
              {TIPOS.map((tipo) => (
                <ChipTipo
                  key={tipo}
                  tipo={tipo}
                  ativo={tiposSelecionados.includes(tipo)}
                  onClick={() => alternarTipo(tipo)}
                />
              ))}
            </div>
          </div>

          <label className="ml-auto flex cursor-pointer items-center gap-2 pb-2 text-[14px] font-bold text-[#1D1D22]">
            <input
              type="checkbox"
              checked={apenasDisponiveis}
              onChange={(e) => setApenasDisponiveis(e.target.checked)}
              className="h-[18px] w-[18px] cursor-pointer rounded accent-[#C8102E]"
            />
            Só disponíveis agora
          </label>
        </div>
      </section>

      {aviso && (
        <p role="status" className="mt-3 rounded-xl bg-[#DCE8F8] px-4 py-2 text-[13px] font-medium text-[#1F4E9C]">
          {aviso}
        </p>
      )}

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_406px]">
        <section
          aria-label="Mapa dos doadores"
          className="relative aspect-[690/521] w-full overflow-hidden rounded-3xl"
        >
          <FundoMapa />

          <p className="absolute left-4 top-4 z-30 rounded-full bg-white px-3.5 py-1.5 text-[13px] font-bold text-[#1D1D22]">
            <span className="text-[#C8102E]">{doadores.length}</span>{" "}
            {doadores.length === 1 ? "doador" : "doadores"} no mapa
          </p>

          {doadores.map((d) => (
            <Pino key={d.id} doador={d} ativo={ativo?.id === d.id} onSelecionar={setSelecionadoId} />
          ))}

          {doadores.length === 0 && (
            <p className="absolute inset-0 flex items-center justify-center text-[14px] text-[#6B6B73]">
              Nenhum doador para mostrar no mapa.
            </p>
          )}

          {ativo && (
            <div className="absolute bottom-4 left-4 z-30 flex w-[min(488px,calc(100%-32px))] items-center gap-3 rounded-2xl bg-white p-3.5">
              <AvatarTipo tipo={ativo.tipo} grande />
              <div className="min-w-0 flex-1">
                <TextoDoador doador={ativo} />
              </div>
              <BotaoContato doador={ativo} onContato={solicitarContato} />
            </div>
          )}
        </section>

        <section aria-label="Lista de doadores">
          {doadores.length === 0 ? (
            <div className="rounded-2xl bg-white p-8 text-center">
              <p className="text-[14px] font-bold text-[#2B2B30]">Nenhum doador com esses filtros</p>
              <p className="mt-1 text-[13px] text-[#6B6B73]">Tente outro tipo sanguíneo ou outra região.</p>
              <button
                type="button"
                onClick={limparFiltros}
                className="mt-3 rounded-lg border border-[#D9D9DD] bg-white px-4 py-2 text-[13px] font-bold hover:bg-[#F4F4F6]"
              >
                Limpar filtros
              </button>
            </div>
          ) : (
            <ul className="flex flex-col gap-2.5">
              {doadores.map((d) => {
                const marcado = ativo?.id === d.id;
                return (
                  <li
                    key={d.id}
                    className={`flex items-center gap-3 rounded-2xl bg-white p-3.5 ${
                      marcado ? "border-2 border-[#C8102E]" : "border-2 border-transparent"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => setSelecionadoId(d.id)}
                      aria-pressed={marcado}
                      className="flex min-w-0 flex-1 items-center gap-3 rounded-lg text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-[#C8102E]"
                    >
                      <AvatarTipo tipo={d.tipo} />
                      <TextoDoador doador={d} />
                    </button>
                    <BotaoContato doador={d} onContato={solicitarContato} />
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>

      <p className="mt-5 text-[12px] text-[#9A9AA2]">
        Protótipo visual: todos os dados exibidos são fictícios e não representam doadores reais ou
        disponibilidade clínica confirmada.
      </p>
    </main>
  );
}