/**
 * COLOQUEI COMENTARIOS COM A IA PARA TENTAR AJUDAR KLEBER (POR FAVOR TIRAR QUANDO TERMINAR O BACKEND)
 * CONTRATO DE DADOS — tela "Registro de acessos"
 *
 * O backend deve devolver exatamente estes campos.
 * Nada aqui fala com o banco: toda leitura passa por `service.listAccessLogs`.
 *
 * Endpoint sugerido:
 *   GET /api/acessos?search=&period=today|7d|30d|all&role=all|requester|clinical|admin|system&result=all|allowed|blocked|automatic
 *   -> { summary: { accessesToday, personalDataViewed, blockedAttempts },
 *        items: [{ id, occurredAt, actorName, actorRole, action, requestCode, result }] }
 */

export const ACESSO_ROLE_LABEL = {
  requester: "Solicitante",
  clinical: "Equipe clínica",
  admin: "Administrador",
  system: "Sistema",
};

export const ACESSO_RESULT_LABEL = {
  allowed: "Permitido",
  blocked: "Bloqueado",
  automatic: "Automático",
};

export const ACESSO_PERIOD_OPTIONS = [
  { value: "today", label: "Hoje" },
  { value: "7d", label: "Últimos 7 dias" },
  { value: "30d", label: "Últimos 30 dias" },
  { value: "all", label: "Todo o período" },
];

export const ACESSO_ROLE_OPTIONS = [
  { value: "all", label: "Todos os perfis" },
  { value: "requester", label: ACESSO_ROLE_LABEL.requester },
  { value: "clinical", label: ACESSO_ROLE_LABEL.clinical },
  { value: "admin", label: ACESSO_ROLE_LABEL.admin },
  { value: "system", label: ACESSO_ROLE_LABEL.system },
];

export const ACESSO_RESULT_OPTIONS = [
  { value: "all", label: "Todos os resultados" },
  { value: "allowed", label: ACESSO_RESULT_LABEL.allowed },
  { value: "blocked", label: ACESSO_RESULT_LABEL.blocked },
  { value: "automatic", label: ACESSO_RESULT_LABEL.automatic },
];

export const INITIAL_ACESSO_FILTERS = {
  search: "",
  period: "today",
  role: "all",
  result: "all",
};

/** Dados apenas de referência. O log real precisa ser gravado append-only pelo backend. */
export const DEMO_ACESSOS = {
  summary: { accessesToday: 38, personalDataViewed: 6, blockedAttempts: 1 },
  items: [
    { id: "log-1", occurredAt: "2026-11-21T12:42:00-03:00", actorName: "Dra. Helena M.", actorRole: "clinical", action: "Visualizou candidatos", requestCode: "#2041", result: "allowed" },
    { id: "log-2", occurredAt: "2026-11-21T12:31:00-03:00", actorName: "Hospital Santa Clara", actorRole: "requester", action: "Criou solicitação", requestCode: "#2042", result: "allowed" },
    { id: "log-3", occurredAt: "2026-11-21T11:58:00-03:00", actorName: "Hospital Santa Clara", actorRole: "requester", action: "Tentou abrir dados pessoais", requestCode: "#2040", result: "blocked" },
    { id: "log-4", occurredAt: "2026-11-21T11:20:00-03:00", actorName: "Agente de IA", actorRole: "system", action: "Gerou ranking de candidatos", requestCode: "#2038", result: "automatic" },
    { id: "log-5", occurredAt: "2026-11-21T10:47:00-03:00", actorName: "Dr. Marcos R.", actorRole: "clinical", action: "Aprovou candidatos", requestCode: "#2035", result: "allowed" },
    { id: "log-6", occurredAt: "2026-11-21T10:15:00-03:00", actorName: "Admin. Paula S.", actorRole: "admin", action: "Alterou perfil de acesso", requestCode: null, result: "allowed" },
    { id: "log-7", occurredAt: "2026-11-21T09:40:00-03:00", actorName: "Dra. Helena M.", actorRole: "clinical", action: "Exportou relatório de pedidos", requestCode: null, result: "allowed" },
  ],
};

/**
 * "2026-11-21T12:42:00-03:00" -> { time: "12:42", date: "21/11/2026" }
 * O fuso vem do backend (TIMESTAMPTZ); aqui fixamos o horário de Brasília para
 * que o log mostre sempre a mesma hora, independentemente do navegador.
 */
export function formatAccessDateTime(item, { timeZone = "America/Sao_Paulo" } = {}) {
  const parsed = new Date(item.occurredAt);
  if (Number.isNaN(parsed.getTime())) return { time: "—", date: "—" };
  return {
    time: new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone }).format(parsed),
    date: new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", timeZone }).format(parsed),
  };
}

/** Filtro local usado apenas enquanto o backend não responde. */
export function filterAccessLogs(items, filters) {
  const term = filters.search.trim().toLowerCase();
  return items.filter((item) => {
    if (filters.role !== "all" && item.actorRole !== filters.role) return false;
    if (filters.result !== "all" && item.result !== filters.result) return false;
    if (!term) return true;
    const haystack = [
      item.actorName,
      ACESSO_ROLE_LABEL[item.actorRole] ?? "",
      item.action,
      item.requestCode ?? "",
    ].join(" ").toLowerCase();
    return haystack.includes(term);
  });
}

function escapeCsvCell(value) {
  const safe = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
  return `"${safe.replace(/"/g, '""')}"`;
}

/** CSV com BOM UTF-8, separador ";" e proteção contra injeção de fórmula no Excel. */
export function buildAccessLogsCsv(items) {
  const header = ["Data", "Hora", "Usuário", "Perfil", "Ação", "Pedido", "Resultado"];
  const rows = items.map((item) => {
    const { time, date } = formatAccessDateTime(item);
    return [
      date,
      time,
      item.actorName,
      ACESSO_ROLE_LABEL[item.actorRole] ?? item.actorRole,
      item.action,
      item.requestCode ?? "—",
      ACESSO_RESULT_LABEL[item.result] ?? item.result,
    ].map(escapeCsvCell).join(";");
  });
  return `\uFEFF${[header.map(escapeCsvCell).join(";"), ...rows].join("\n")}`;
}

/** Query string enviada ao backend: search, period, role, result. */
export function buildAccessLogsQuery(filters) {
  const params = new URLSearchParams();
  if (filters.search.trim()) params.set("search", filters.search.trim());
  params.set("period", filters.period);
  params.set("role", filters.role);
  params.set("result", filters.result);
  return params.toString();
}

/** URL de leitura: /api/acessos?period=today&role=all&result=all */
export function buildAccessLogsUrl(filters, baseUrl = "/api/acessos") {
  return `${baseUrl}?${buildAccessLogsQuery(filters)}`;
}

/** URL de exportação: /api/acessos/export.csv?period=today&role=all&result=all */
export function buildAccessLogsExportUrl(filters, baseUrl = "/api/acessos") {
  return `${baseUrl}/export.csv?${buildAccessLogsQuery(filters)}`;
}

/**
 * Adaptador pronto para o backend. Troque a URL/autenticação aqui e a página
 * passa a ler dados reais sem nenhuma outra mudança.
 *
 *   import { createAcessosService } from "../lib/acessos";
 *   const service = createAcessosService({ baseUrl: "/api/acessos" });
 *   <RegistroAcessosPage service={service} />
 */
export function createAcessosService({
  baseUrl = "/api/acessos",
  fetchImpl = fetch,
  headers = {},
} = {}) {
  async function request(url) {
    const response = await fetchImpl(url, { headers: { Accept: "application/json", ...headers } });
    if (!response.ok) throw new Error(`Falha ao consultar ${url}: ${response.status}`);
    return response;
  }

  return {
    async listAccessLogs(filters) {
      const response = await request(buildAccessLogsUrl(filters, baseUrl));
      const data = await response.json();
      return {
        summary: data.summary ?? { accessesToday: 0, personalDataViewed: 0, blockedAttempts: 0 },
        items: Array.isArray(data.items) ? data.items : [],
      };
    },

    async exportCsv(filters) {
      const response = await request(buildAccessLogsExportUrl(filters, baseUrl));
      return response.blob();
    },
  };
}
