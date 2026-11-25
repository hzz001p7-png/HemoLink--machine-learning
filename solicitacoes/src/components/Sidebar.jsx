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

export default function Sidebar({ user, activePath, onNavigate }) {
  const items = MENUS[user?.role] ?? [];
  const perfilAtivo = activePath === "/perfil";

  return (
    <aside className="flex w-full shrink-0 flex-col bg-[#f6f4f2] px-4 py-5 text-zinc-800 lg:sticky lg:top-0 lg:h-screen lg:w-60">
      <div className="flex items-center gap-2.5 px-2 pb-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#c8102e] text-white">
          <Droplet size={16} fill="currentColor" aria-hidden="true" />
        </div>
        <span className="text-sm font-bold">Gota Certa</span>
      </div>

      <nav
        className="flex gap-1 overflow-x-auto pb-3 lg:flex-col lg:overflow-visible lg:pb-0"
        aria-label="Menu principal"
      >
        {items.map(({ id, label, icon: Icon, path }) => {
          const active = activePath === path;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onNavigate?.(path)}
              aria-current={active ? "page" : undefined}
              className={`flex shrink-0 items-center gap-3 whitespace-nowrap rounded-xl px-3 py-2.5 text-left text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#c8102e]/40 ${
                active
                  ? "bg-rose-100 text-[#c8102e]"
                  : "text-zinc-700 hover:bg-black/5"
              }`}
            >
              <Icon size={18} strokeWidth={1.75} aria-hidden="true" />
              {label}
            </button>
          );
        })}
      </nav>

      <button
        type="button"
        onClick={() => onNavigate?.("/perfil")}
        aria-label="Abrir perfil de acesso"
        aria-current={perfilAtivo ? "page" : undefined}
        className={`mt-3 rounded-xl border px-3 py-3 text-left transition hover:bg-rose-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#c8102e] lg:mt-auto ${
          perfilAtivo
            ? "border-[#c8102e] bg-rose-50"
            : "border-transparent bg-black/5"
        }`}
      >
        <span className="block text-[11px] text-zinc-500">Perfil de acesso</span>
        <span className="block text-sm font-bold">
          {ROLE_LABEL[user?.role] ?? "—"}
        </span>
        {(user?.organization || user?.name) && (
          <span className="block text-[11px] text-zinc-500">
            {user.organization ?? user.name}
          </span>
        )}
      </button>
    </aside>
  );
}
