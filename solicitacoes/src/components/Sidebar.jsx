import {
  LayoutGrid,
  Plus,
  ShieldCheck,
  Users,
  FileText,
  Droplet,
  Heart,
  History,
  UserRound,
} from "lucide-react";

/**
 * MENUS POR PERFIL
 * Cada perfil ("requester" | "donor") tem seus próprios itens.
 * Para adicionar um item, basta incluir uma linha
 */
const MENUS = {
  requester: [
    { id: "painel", label: "Painel", icon: LayoutGrid, path: "/painel" },
    { id: "nova", label: "Nova solicitação", icon: Plus, path: "/solicitacoes/nova" },
    { id: "revisao", label: "Revisão clínica", icon: ShieldCheck, path: "/revisao" },
    { id: "doadores", label: "Doadores", icon: Users, path: "/doadores" },
    { id: "acessos", label: "Registro de acessos", icon: FileText, path: "/acessos" },
  ],
  donor: [
    { id: "painel", label: "Painel", icon: LayoutGrid, path: "/painel" },
    { id: "pedidos", label: "Pedidos próximos", icon: Droplet, path: "/pedidos" },
    { id: "doacoes", label: "Minhas doações", icon: Heart, path: "/doacoes" },
    { id: "historico", label: "Histórico", icon: History, path: "/historico" },
    { id: "perfil", label: "Meu perfil", icon: UserRound, path: "/perfil" },
  ],
};

const ROLE_LABEL = {
  requester: "Solicitante",
  donor: "Doador",
};

/**
 * Props:
 *  - user:        { role: "requester" | "donor", organization?: string, name?: string }
 *  - activePath:  caminho atual (ex.: "/acessos") para destacar o item ativo
 *  - onNavigate:  (path) => void  — use com react-router: navigate(path)
 */
export default function Sidebar({ user, activePath, onNavigate }) {
  const items = MENUS[user?.role] ?? [];

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col bg-[#f6f4f2] px-4 py-5 text-gray-800">
      {/* LOGO */}
      <div className="flex items-center gap-2.5 px-2 pb-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#c8102e] text-white">
          <Droplet size={16} fill="currentColor" />
        </div>
        <span className="text-sm font-bold">Gota Certa</span>
      </div>

      {/* NAVEGAÇÃO */}
      <nav className="flex flex-col gap-1" aria-label="Menu principal">
        {items.map(({ id, label, icon: Icon, path }) => {
          const active = activePath === path;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onNavigate?.(path)}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-[#c8102e]/40 ${
                active
                  ? "bg-rose-100 text-[#c8102e]"
                  : "text-gray-700 hover:bg-black/5"
              }`}
            >
              <Icon size={18} strokeWidth={1.75} />
              {label}
            </button>
          );
        })}
      </nav>

      {/* PERFIL DE ACESSO (rodapé) */}
      <div className="mt-auto rounded-xl bg-black/5 px-3 py-3">
        <p className="text-[11px] text-gray-500">Perfil de acesso</p>
        <p className="text-sm font-bold">{ROLE_LABEL[user?.role] ?? "—"}</p>
        {(user?.organization || user?.name) && (
          <p className="text-[11px] text-gray-500">
            {user.organization ?? user.name}
          </p>
        )}
      </div>
    </aside>
  );
}
