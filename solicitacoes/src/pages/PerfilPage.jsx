import { useEffect, useRef, useState } from "react";
import { Check, X, ShieldCheck } from "lucide-react";

// Dados demonstrativos. Não representam autenticação ou autorização real.
const PERFIL_EXEMPLO = {
  iniciais: "HS",
  organizacao: "Hospital Santa Clara",
  cidade: "Recife",
  estado: "PE",
  email: "contato@hospital.exemplo",
  perfil: "requester",
  ultimoAcesso: "Hoje, 12:31",
  senhaAlterada: "Alterada há 3 meses",
  duasEtapas: true,
  sessoes: 1,
};

const PERFIS = [
  { id: "requester", nome: "Solicitante" },
  { id: "clinical", nome: "Equipe clínica" },
  { id: "admin", nome: "Administrador" },
];

// Matriz somente visual: o backend deverá validar as permissões reais.
const PERMISSOES = [
  { nome: "Criar solicitações", perfis: ["requester"] },
  {
    nome: "Acompanhar o andamento dos pedidos",
    perfis: ["requester", "clinical", "admin"],
  },
  {
    nome: "Ver candidatos (somente por código)",
    perfis: ["requester", "clinical"],
  },
  { nome: "Aprovar candidatos na revisão clínica", perfis: ["clinical"] },
  {
    nome: "Ver dados pessoais de pacientes e doadores",
    perfis: ["clinical"],
  },
  { nome: "Consultar o registro de acessos", perfis: ["clinical", "admin"] },
  { nome: "Gerenciar perfis de acesso", perfis: ["admin"] },
];

function StatusPermissao({ permitido }) {
  return (
    <span
      className={`inline-flex min-w-14 items-center justify-center gap-1 rounded-full px-2 py-1 text-[11px] font-semibold ${
        permitido
          ? "bg-emerald-50 text-emerald-700"
          : "bg-zinc-100 text-zinc-600"
      }`}
    >
      {permitido ? (
        <Check size={12} aria-hidden="true" />
      ) : (
        <X size={12} aria-hidden="true" />
      )}
      {permitido ? "Sim" : "Não"}
    </span>
  );
}

export default function PerfilPage() {
  const perfil = PERFIL_EXEMPLO;
  const nomePerfil = PERFIS.find((item) => item.id === perfil.perfil)?.nome;
  const [modal, setModal] = useState(null);
  const [mensagem, setMensagem] = useState("");
  const dialogRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (modal && !dialog.open) dialog.showModal();
    if (!modal && dialog.open) dialog.close();
  }, [modal]);

  function abrirModal(tipo, event) {
    triggerRef.current = event.currentTarget;
    setMensagem("");
    setModal(tipo);
  }

  function fecharModal() {
    setModal(null);
    setMensagem("");
    triggerRef.current?.focus();
  }

  function confirmar(event) {
    event.preventDefault();
    setMensagem(
      "Esta ação depende do backend. Nenhuma senha ou sessão foi alterada."
    );
  }

  const botaoSecundario =
    "shrink-0 rounded-lg border border-[#c8102e] px-3 py-2 text-xs font-semibold text-[#c8102e] transition hover:bg-rose-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#c8102e] focus-visible:ring-offset-2";

  return (
    <main className="min-h-screen min-w-0 flex-1 bg-[#f0eff1] p-5 text-[#28282d] lg:p-8">
      <header>
        <h1 className="text-[28px] font-bold leading-tight">Perfil de acesso</h1>
        <p className="mt-1 text-[13px] text-zinc-500">
          Veja o que o seu perfil pode fazer. Pedidos e doadores aparecem por
          código para proteger a privacidade.
        </p>
        <p className="mt-2 text-xs text-zinc-500">Dados de demonstração</p>
      </header>

      <div className="mt-6 grid items-start gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
        <div className="space-y-3">
          <section className="rounded-2xl bg-white p-6" aria-label="Dados do perfil">
            <div
              className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#c8102e] text-xl font-bold text-white"
              aria-hidden="true"
            >
              {perfil.iniciais}
            </div>
            <h2 className="text-sm font-bold">{perfil.organizacao}</h2>
            <p className="mt-1 text-xs text-zinc-500">
              {perfil.cidade} – {perfil.estado}
            </p>
            <span className="mt-3 inline-block rounded-full bg-rose-50 px-2 py-1 text-[11px] font-bold text-[#c8102e]">
              Perfil: {nomePerfil}
            </span>
            <dl className="mt-4 space-y-3 text-xs">
              <div className="border-t border-zinc-200 pt-3">
                <dt className="text-[11px] text-zinc-500">E-mail de acesso</dt>
                <dd className="mt-1 break-all font-bold">{perfil.email}</dd>
              </div>
              <div className="border-t border-zinc-200 pt-3">
                <dt className="text-[11px] text-zinc-500">Último acesso</dt>
                <dd className="mt-1 font-bold">{perfil.ultimoAcesso}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-2xl bg-white p-6" aria-labelledby="seguranca-titulo">
            <h2 id="seguranca-titulo" className="text-sm font-bold">Segurança</h2>

            <div className="flex items-center justify-between gap-3 border-b border-zinc-200 py-4">
              <div>
                <h3 className="text-xs font-bold">Senha</h3>
                <p className="mt-1 text-[11px] text-zinc-500">{perfil.senhaAlterada}</p>
              </div>
              <button
                type="button"
                className={botaoSecundario}
                onClick={(event) => abrirModal("senha", event)}
              >
                Alterar
              </button>
            </div>

            <div className="flex items-center justify-between gap-3 border-b border-zinc-200 py-4">
              <div>
                <h3 className="text-xs font-bold">Verificação em duas etapas</h3>
                <p className="mt-1 text-[11px] text-zinc-500">Pede um código ao entrar</p>
              </div>
              <span className="flex shrink-0 items-center gap-2 text-xs font-semibold">
                <ShieldCheck size={16} className="text-[#c8102e]" aria-hidden="true" />
                {perfil.duasEtapas ? "Ativada" : "Desativada"}
              </span>
            </div>

            <div className="flex items-center justify-between gap-3 pt-4">
              <div>
                <h3 className="text-xs font-bold">Sessões ativas</h3>
                <p className="mt-1 text-[11px] text-zinc-500">
                  {perfil.sessoes} {perfil.sessoes === 1 ? "dispositivo" : "dispositivos"}
                </p>
              </div>
              <button
                type="button"
                className={botaoSecundario}
                onClick={(event) => abrirModal("sessoes", event)}
              >
                Encerrar outras
              </button>
            </div>
          </section>
        </div>

        <section className="min-w-0 rounded-2xl bg-white p-5 lg:p-6" aria-labelledby="permissoes-titulo">
          <h2 id="permissoes-titulo" className="text-sm font-bold">
            O que cada perfil pode fazer
          </h2>
          <div
            className="mt-5 overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabela de permissões por perfil"
          >
            <table className="w-full min-w-[570px] border-collapse text-xs">
              <thead>
                <tr className="text-[10px] uppercase text-zinc-500">
                  <th scope="col" className="w-[41%] px-3 py-3 text-left">Permissão</th>
                  {PERFIS.map((item) => (
                    <th
                      key={item.id}
                      scope="col"
                      className={`px-3 py-3 text-center ${
                        perfil.perfil === item.id ? "bg-rose-50/70" : ""
                      }`}
                    >
                      {item.nome}
                      {perfil.perfil === item.id && <span className="block">(você)</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {PERMISSOES.map((permissao) => (
                  <tr key={permissao.nome} className="border-b border-zinc-100 last:border-0">
                    <th scope="row" className="px-3 py-4 text-left font-normal">
                      {permissao.nome}
                    </th>
                    {PERFIS.map((item) => (
                      <td
                        key={item.id}
                        className={`px-3 py-4 text-center ${
                          perfil.perfil === item.id ? "bg-rose-50/70" : ""
                        }`}
                      >
                        <StatusPermissao permitido={permissao.perfis.includes(item.id)} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <dialog
        ref={dialogRef}
        onCancel={(event) => {
          event.preventDefault();
          fecharModal();
        }}
        onClose={fecharModal}
        aria-labelledby="perfil-modal-titulo"
        aria-describedby="perfil-modal-descricao"
        className="fixed inset-0 m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-md overflow-y-auto rounded-xl border-0 bg-white p-6 text-[#28282d] shadow-xl backdrop:bg-black/40"
      >
        <h2 id="perfil-modal-titulo" className="text-lg font-bold">
          {modal === "senha" ? "Alterar senha" : "Encerrar outras sessões"}
        </h2>
        <p id="perfil-modal-descricao" className="mt-2 text-sm text-zinc-500">
          {modal === "senha"
            ? "A alteração de senha estará disponível quando a autenticação for conectada."
            : "O encerramento de sessões estará disponível quando a autenticação for conectada."}
        </p>
        <form onSubmit={confirmar} className="mt-5">
          {mensagem && (
            <p role="alert" className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-[#c8102e]">
              {mensagem}
            </p>
          )}
          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" className={botaoSecundario} onClick={fecharModal}>
              Fechar
            </button>
            <button
              type="submit"
              className="rounded-lg bg-[#c8102e] px-4 py-2 text-xs font-semibold text-white hover:bg-[#a80d26] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#c8102e] focus-visible:ring-offset-2"
            >
              Confirmar
            </button>
          </div>
        </form>
      </dialog>
    </main>
  );
}
