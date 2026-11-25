// AVISO: Kleber, presta atencao nos comentarios pfv
// Tipo sanguíneo selecionado pelo usuário.
// Backend:salvar no campo tipo_sanguineo do pedido. POR FAVOR
import { useState } from "react";

const tiposSanguineos = [
  "A+",
  "A-",
  "B+",
  "B-",
  "AB+",
  "AB-",
  "O+",
  "O-",
];

export default function NovaSolicitacaoPage() {
  const [tipo, setTipo] = useState("A+");
  // Quantidade de bolsas solicitadas
  const [bolsas, setBolsas] = useState(3);
  // Nível de urgência da solicitação.
  const [urgencia, setUrgencia] = useState("Urgente");
  // Tipo de hemocomponente solicitado.
  const [componente, setComponente] = useState("Concentrado de hemácias");
  // Mensagens de retorno para o usuário após ações no formulário.
  const [mensagem, setMensagem] = useState("");

  function enviarPedido(event) {
    event.preventDefault();
     /*
    Kleber:

    Dados esperados:
    - tipo
    - bolsas
    - urgencia
    - componente
    - estado
    - cidade
    - hospital
    - observacoes
    - usuario_id

    O código do pedido deve ser gerado pelo backend,
    tem que evitar os códigos duplicados.

    Kleber registrar o usuário responsável
    e cria a solicitação com status "Aguardando revisão clínica".
  */
    setMensagem("Pedido enviado para revisão clínica.");
  }

  return (
    <main className="min-h-screen flex-1 bg-[#f7f5f3] p-6 text-[#28282d] lg:p-10">
      <div className="mx-auto max-w-6xl">
        <header className="mb-7">
          <p className="text-xs font-bold uppercase tracking-widest text-[#c8102e]">
            Portal de hemoterapia
          </p>

          <h1 className="mt-2 text-4xl font-bold">
            Nova solicitação
          </h1>

          <p className="mt-2 text-sm text-[#79777a]">
            Informe os dados do pedido. O paciente é identificado apenas por
            código.
          </p>
        </header>

        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          <form
            onSubmit={enviarPedido}
            className="rounded-2xl bg-white p-6 shadow-sm"
          >
            <section className="border-b border-[#e6e2df] pb-6">
              <h2 className="mb-5 text-lg font-bold">
                <span className="mr-2 rounded-full bg-[#f8e4e8] px-2 py-1 text-sm text-[#c8102e]">
                  1
                </span>
                Sobre o pedido
              </h2>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="text-xs font-bold">
                  Código do pedido
                  <input
                    readOnly
                    value="#2042 · gerado automaticamente"
                    className="mt-2 h-10 w-full rounded-lg border bg-[#f5f3f2] px-3 text-sm font-normal"
                  />
                </label>

                <label className="text-xs font-bold">
                  Tipo de hemocomponente
                  <select
                    value={componente}
                    onChange={(event) => setComponente(event.target.value)}
                    className="mt-2 h-10 w-full rounded-lg border bg-white px-3 text-sm font-normal"
                  >
                    <option>Concentrado de hemácias</option>
                    <option>Concentrado de plaquetas</option>
                    <option>Plasma fresco congelado</option>
                    <option>Crioprecipitado</option>
                  </select>
                </label>
              </div>

              <div className="mt-5">
                <p className="mb-2 text-xs font-bold">
                  Tipo sanguíneo do paciente
                </p>

                <div className="flex flex-wrap gap-2">
                  {tiposSanguineos.map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => setTipo(item)}
                      className={`rounded-full border px-4 py-2 text-xs font-bold ${
                        tipo === item
                          ? "border-[#28282d] bg-[#28282d] text-white"
                          : "bg-white hover:border-[#c8102e] hover:text-[#c8102e]"
                      }`}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-5 flex items-center gap-4 text-xs font-bold">
                Bolsas necessárias

                <button
                  type="button"
                  onClick={() => setBolsas(Math.max(1, bolsas - 1))}
                  className="rounded-full bg-[#fae5e9] px-3 py-1 text-lg text-[#c8102e]"
                >
                  −
                </button>

                <span>{bolsas}</span>

                <button
                  type="button"
                  onClick={() => setBolsas(Math.min(99, bolsas + 1))}
                  className="rounded-full bg-[#fae5e9] px-3 py-1 text-lg text-[#c8102e]"
                >
                  +
                </button>
              </div>
            </section>

            <section className="border-b border-[#e6e2df] py-6">
              <h2 className="mb-5 text-lg font-bold">
                <span className="mr-2 rounded-full bg-[#f8e4e8] px-2 py-1 text-sm text-[#c8102e]">
                  2
                </span>
                Urgência
              </h2>

              <div className="grid gap-3 md:grid-cols-3">
                {[
                  ["Normal", "Até 1 semana"],
                  ["Urgente", "De 2 a 3 dias"],
                  ["Emergência", "Hoje"],
                ].map(([nome, descricao]) => (
                  <button
                    key={nome}
                    type="button"
                    onClick={() => setUrgencia(nome)}
                    className={`rounded-lg border p-4 text-left ${
                      urgencia === nome
                        ? "border-[#da6e85] bg-[#fff5f6]"
                        : "bg-white hover:border-[#df8295]"
                    }`}
                  >
                    <strong className="block text-sm">{nome}</strong>
                    <span className="text-xs text-gray-500">
                      {descricao}
                    </span>
                  </button>
                ))}
              </div>
            </section>

            <section className="border-b border-[#e6e2df] py-6">
              <h2 className="mb-5 text-lg font-bold">
                <span className="mr-2 rounded-full bg-[#f8e4e8] px-2 py-1 text-sm text-[#c8102e]">
                  3
                </span>
                Local
              </h2>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="text-xs font-bold">
                  Estado
                  <select className="mt-2 h-10 w-full rounded-lg border px-3 font-normal">
                    <option>PE</option>
                    <option>PB</option>
                    <option>AL</option>
                    <option>BA</option>
                  </select>
                </label>

                <label className="text-xs font-bold">
                  Cidade
                  <select className="mt-2 h-10 w-full rounded-lg border px-3 font-normal">
                    <option>Recife</option>
                    <option>Olinda</option>
                    <option>Joao Pessoa</option>
                    <option>Salvador</option>
                    <option>Alagoas</option>
                  </select>
                </label>
              </div>

              <label className="mt-4 block text-xs font-bold">
                Hospital ou ponto de coleta
                <select className="mt-2 h-10 w-full rounded-lg border px-3 font-normal">
                  <option>Hospital Santa Clara</option>
                  <option>Hospital Esperança</option>
                  <option>Hemope — Recife</option>
                  <option>Hospital de Emergência e Trauma Senador Humberto Lucena</option>
                  <option>Hospital Municipal de Salvador</option>
                  <option>Hospital Geral do Estado Professor Osvaldo Brandão Vilela</option>
                </select>
              </label>
            </section>

            <section className="pt-6">
              <h2 className="mb-5 text-lg font-bold">
                <span className="mr-2 rounded-full bg-[#f8e4e8] px-2 py-1 text-sm text-[#c8102e]">
                  4
                </span>
                Observações para a equipe clínica
              </h2>

              <textarea
                placeholder="Ex.: horário limite, orientações do hemocentro..."
                className="min-h-24 w-full rounded-lg border p-3 text-sm"
              />
            </section>

            <div className="mt-6 flex justify-end gap-3 border-t pt-5">
              <button
                type="button"
                onClick={() => setMensagem("Rascunho salvo nesta tela.")}
                className="rounded-lg border px-4 py-2 text-sm font-bold"
              >
                Salvar rascunho
              </button>

              <button
                type="submit"
                className="rounded-lg bg-[#c8102e] px-4 py-2 text-sm font-bold text-white"
              >
                Enviar para revisão clínica
              </button>
            </div>

            {mensagem && (
              <p className="mt-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">
                {mensagem}
              </p>
            )}
          </form>

          <aside className="h-fit rounded-2xl bg-white p-6 shadow-sm">
  <h2 className="mb-5 font-bold">Resumo do pedido</h2>

  <div className="space-y-4 text-sm">
    <div className="flex justify-between">
      <span className="text-gray-500">Pedido</span>
      <strong>#2042</strong>
    </div>
  </div>
          </aside>
        </div>
      </div>
    </main>
  );
}