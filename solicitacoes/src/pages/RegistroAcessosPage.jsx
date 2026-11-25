import { useEffect, useMemo, useState } from "react";
import {
  Check,
  ChevronDown,
  Download,
  LoaderCircle,
  Settings,
  ShieldAlert,
} from "lucide-react";
import {
  ACESSO_PERIOD_OPTIONS,
  ACESSO_RESULT_LABEL,
  ACESSO_RESULT_OPTIONS,
  ACESSO_ROLE_LABEL,
  ACESSO_ROLE_OPTIONS,
  DEMO_ACESSOS,
  INITIAL_ACESSO_FILTERS,
  buildAccessLogsCsv,
  filterAccessLogs,
  formatAccessDateTime,
} from "../lib/acessos";

const RESULT_STYLE = {
  allowed: "bg-[#d4f3e6] text-[#1e7e53]",
  blocked: "bg-[#fde2e4] text-[#a32d3f]",
  automatic: "bg-[#edefef] text-[#4b5563]",
};

const RESULT_ICON = {
  allowed: Check,
  blocked: ShieldAlert,
  automatic: Settings,
};

function ResultBadge({ result }) {
  const Icon = RESULT_ICON[result] ?? Settings;
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-1 text-[11px] font-bold ${
        RESULT_STYLE[result] ?? RESULT_STYLE.automatic
      }`}
    >
      <Icon size={12} aria-hidden="true" />
      {ACESSO_RESULT_LABEL[result] ?? result}
    </span>
  );
}

function Select({ label, value, options, onChange }) {
  return (
    <span className="relative inline-flex w-full items-center sm:w-auto">
      <select
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full appearance-none rounded-xl border border-[#e1e1e6] bg-white py-0 pl-3.5 pr-9 text-[13px] text-[#28282d] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#c8102e]/40 sm:w-auto"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown
        size={15}
        aria-hidden="true"
        className="pointer-events-none absolute right-3 text-zinc-500"
      />
    </span>
  );
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Tela somente leitura. Quem decide o que o usuário pode ver é o backend.
 *
 * Props:
 *  - service: opcional, { listAccessLogs(filters), exportCsv?(filters) }.
 *    Sem service, a tela mostra DEMO_ACESSOS com o selo "Dados fictícios".
 */
export default function RegistroAcessosPage({ service }) {
  const [filters, setFilters] = useState(INITIAL_ACESSO_FILTERS);
  const [data, setData] = useState(DEMO_ACESSOS);
  const [loading, setLoading] = useState(Boolean(service));
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!service) return;
    let active = true;
    setLoading(true);
    setError("");
    service
      .listAccessLogs(filters)
      .then((response) => {
        if (active) setData(response);
      })
      .catch(() => {
        if (active)
          setError("Não foi possível carregar o registro de acessos. Tente novamente.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [service, filters]);

  const visibleItems = useMemo(
    () => (service ? data.items : filterAccessLogs(DEMO_ACESSOS.items, filters)),
    [service, data.items, filters]
  );

  async function handleExportCsv() {
    setError("");
    setExporting(true);
    try {
      const filename = `registro-de-acessos-${filters.period}.csv`;
      if (service?.exportCsv) {
        const exported = await service.exportCsv(filters);
        const blob =
          exported instanceof Blob
            ? exported
            : new Blob([exported], { type: "text/csv;charset=utf-8;" });
        downloadBlob(blob, filename);
      } else {
        downloadBlob(
          new Blob([buildAccessLogsCsv(visibleItems)], { type: "text/csv;charset=utf-8;" }),
          filename
        );
      }
    } catch {
      setError("Não foi possível exportar o arquivo CSV. Tente novamente.");
    } finally {
      setExporting(false);
    }
  }

  const summary = service ? data.summary : DEMO_ACESSOS.summary;
  const hasActiveFilters =
    filters.search.trim() !== "" ||
    filters.role !== "all" ||
    filters.result !== "all" ||
    filters.period !== "today";

  const kpiBase = "rounded-2xl p-5";

  return (
    <main className="min-h-screen min-w-0 flex-1 bg-[#f0eff1] p-5 text-[#28282d] lg:p-8">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-[28px] font-bold leading-tight">Registro de acessos</h1>
          <p className="mt-1 text-[13px] text-zinc-500">
            Quem acessou o quê, e quando. Os registros não podem ser editados nem apagados.
          </p>
        </div>
        <button
          type="button"
          onClick={handleExportCsv}
          disabled={exporting || loading}
          className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-[#e1e1e6] bg-white px-4 py-2.5 text-xs font-semibold text-[#28282d] transition hover:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#c8102e] disabled:opacity-60"
        >
          <Download size={14} aria-hidden="true" />
          {exporting ? "Exportando…" : "Exportar CSV"}
        </button>
      </header>

      <section
        className="mt-6 grid gap-4 md:grid-cols-3"
        aria-label="Resumo de acessos"
      >
        <article className={`${kpiBase} bg-[#f5f4f2]`}>
          <p className="text-xs font-semibold text-[#55555c]">Acessos hoje</p>
          <p className="mt-1.5 text-[32px] font-bold leading-none">{summary.accessesToday}</p>
        </article>
        <article className={`${kpiBase} bg-[#f5f4f2]`}>
          <p className="text-xs font-semibold text-[#55555c]">Dados pessoais visualizados</p>
          <p className="mt-1.5 text-[32px] font-bold leading-none">
            {summary.personalDataViewed}
          </p>
        </article>
        <article className={`${kpiBase} bg-[#fde8ec]`}>
          <p className="text-xs font-semibold text-[#55555c]">Tentativas bloqueadas</p>
          <p className="mt-1.5 text-[32px] font-bold leading-none text-[#7a1224]">
            {summary.blockedAttempts}
          </p>
        </article>
      </section>

      <section
        className="mt-5 rounded-2xl bg-[#f5f4f2] p-4 lg:p-6"
        aria-label="Lista de registros de acesso"
      >
        <div className="flex flex-wrap items-center gap-2.5">
          <input
            type="search"
            aria-label="Buscar por usuário ou pedido"
            placeholder="Buscar por usuário ou pedido"
            value={filters.search}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, search: event.target.value }))
            }
            className="h-10 w-full rounded-xl border border-[#e1e1e6] bg-white px-3.5 text-[13px] text-[#28282d] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#c8102e]/40 sm:w-60"
          />
          <Select
            label="Filtrar por período"
            value={filters.period}
            options={ACESSO_PERIOD_OPTIONS}
            onChange={(value) => setFilters((prev) => ({ ...prev, period: value }))}
          />
          <Select
            label="Filtrar por perfil"
            value={filters.role}
            options={ACESSO_ROLE_OPTIONS}
            onChange={(value) => setFilters((prev) => ({ ...prev, role: value }))}
          />
          <Select
            label="Filtrar por resultado"
            value={filters.result}
            options={ACESSO_RESULT_OPTIONS}
            onChange={(value) => setFilters((prev) => ({ ...prev, result: value }))}
          />
          {!service && (
            <span className="rounded-full bg-[#fdf1d8] px-3 py-1.5 text-[11px] font-bold text-[#8a5a00]">
              Dados fictícios
            </span>
          )}
        </div>

        {error && (
          <p role="alert" className="mt-4 text-sm text-[#a32d3f]">
            {error}
          </p>
        )}

        {loading ? (
          <p
            role="status"
            className="mt-6 flex items-center gap-2 rounded-xl bg-white px-5 py-8 text-sm text-zinc-500"
          >
            <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
            Carregando registros…
          </p>
        ) : (
          <div
            className="mt-4 overflow-x-auto rounded-xl bg-white"
            tabIndex={0}
            role="region"
            aria-label="Tabela de registros de acesso"
          >
            <table className="w-full min-w-[680px] border-collapse text-[13px]">
              <thead>
                <tr>
                  {["Data e hora", "Usuário", "Ação", "Pedido", "Resultado"].map((title) => (
                    <th
                      key={title}
                      scope="col"
                      className="px-4 pb-3 pt-4 text-left text-[10px] font-semibold uppercase tracking-wide text-zinc-500"
                    >
                      {title}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleItems.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-sm text-zinc-500">
                      Nenhum registro encontrado para os filtros aplicados.
                      {hasActiveFilters && (
                        <button
                          type="button"
                          onClick={() => setFilters(INITIAL_ACESSO_FILTERS)}
                          className="ml-2 font-semibold text-[#c8102e] underline underline-offset-2"
                        >
                          Limpar filtros
                        </button>
                      )}
                    </td>
                  </tr>
                ) : (
                  visibleItems.map((item) => {
                    const { time, date } = formatAccessDateTime(item);
                    return (
                      <tr
                        key={item.id}
                        className="border-b border-zinc-100 last:border-0"
                      >
                        <td className="px-4 py-3.5 align-middle">
                          <div className="font-bold text-[#1d1d22]">{time}</div>
                          <div className="text-[11px] text-zinc-500">{date}</div>
                        </td>
                        <td className="px-4 py-3.5 align-middle">
                          <div className="font-bold text-[#1d1d22]">{item.actorName}</div>
                          <div className="text-[11px] text-zinc-500">
                            {ACESSO_ROLE_LABEL[item.actorRole] ?? item.actorRole}
                          </div>
                        </td>
                        <td className="px-4 py-3.5 align-middle text-[#28282d]">
                          {item.action}
                        </td>
                        <td className="px-4 py-3.5 align-middle font-medium text-[#1d1d22]">
                          {item.requestCode ?? "—"}
                        </td>
                        <td className="px-4 py-3.5 align-middle">
                          <ResultBadge result={item.result} />
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
