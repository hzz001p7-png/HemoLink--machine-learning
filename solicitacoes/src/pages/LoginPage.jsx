import { useState } from "react";
import { supabase } from "../lib/supabase";

export default function LoginPage({ onLogin }) {
  const [userType, setUserType] = useState("donor");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");

  async function handleLogin(e) {
    e.preventDefault();
    setLoading(true);
    setErro("");

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    setLoading(false);

    if (error) {
      setErro("Erro ao entrar: " + error.message);
      return;
    }

    onLogin?.(data.user);
  }

  return (
    <main className="min-h-screen flex bg-white font-sans">
      <section className="hidden md:flex w-1/2 bg-gradient-to-br from-[#c8102e] to-[#a90827] text-white flex-col justify-between p-10 lg:p-14">
        <div>
          <div className="flex items-center gap-2 font-bold text-sm">
            <div className="bg-white text-[#c8102e] w-8 h-8 rounded-lg flex items-center justify-center">
              🩸
            </div>
            Gota Certa
          </div>

          <div className="mt-20 max-w-md">
            <h1 className="text-4xl font-bold leading-tight">
              Cada gota conecta vidas. Cada gesto faz a diferença.
            </h1>
            <p className="text-white/85 text-sm leading-6 mt-4">
              Um só lugar para doadores e pacientes se encontrarem.
              Encontre pedidos próximos e ajude a fazer a diferença.
            </p>
          </div>

          <div className="mt-8 space-y-4 max-w-md">
            <div className="bg-white text-gray-800 rounded-xl p-4 flex items-center gap-4">
              <div className="bg-rose-100 text-[#c8102e] rounded-lg p-3 text-xl">♡</div>
              <div>
                <h3 className="font-bold text-sm">Para quem doa</h3>
                <p className="text-xs text-gray-500 mt-1">
                  Veja pedidos próximos e ajude quem precisa.
                </p>
              </div>
            </div>

            <div className="bg-[#a50a25]/50 border border-white/10 text-white rounded-xl p-4 flex items-center gap-4">
              <div className="bg-white/10 rounded-lg p-3 text-xl">🩸</div>
              <div>
                <h3 className="font-bold text-sm">Para quem precisa</h3>
                <p className="text-xs text-white/70 mt-1">
                  Publique um pedido e encontre doadores compatíveis.
                </p>
              </div>
            </div>
          </div>
        </div>

        <p className="text-xs text-white/80">
          Uma doação pode ajudar a salvar até 4 vidas.
        </p>
      </section>

      <section className="w-full md:w-1/2 flex flex-col bg-white">
        <header className="flex justify-between items-center px-8 py-6 text-xs text-gray-500">
          <span>Gota Certa</span>
          <span>Ajuda</span>
        </header>

        <div className="flex flex-1 items-center justify-center px-6 py-10">
          <div className="w-full max-w-md">
            <h2 className="text-2xl font-bold text-gray-800">Boas-vindas!</h2>
            <p className="text-xs text-gray-400 mt-2">
              Acesse sua conta e acompanhe pedidos perto de você.
            </p>

            <div className="grid grid-cols-2 bg-gray-100 p-1 rounded-xl mt-5">
              <button
                type="button"
                onClick={() => setUserType("donor")}
                className={`py-3 rounded-lg text-xs font-medium ${
                  userType === "donor"
                    ? "bg-[#c8102e] text-white"
                    : "text-gray-500"
                }`}
              >
                🩸 Sou doador
              </button>

              <button
                type="button"
                onClick={() => setUserType("recipient")}
                className={`py-3 rounded-lg text-xs font-medium ${
                  userType === "recipient"
                    ? "bg-[#c8102e] text-white"
                    : "text-gray-500"
                }`}
              >
                ♡ Preciso de sangue
              </button>
            </div>

            <form onSubmit={handleLogin} className="mt-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  E-mail
                </label>
                <input
                  type="email"
                  placeholder="voce@gmail.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#c8102e]"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Senha
                </label>
                <input
                  type="password"
                  placeholder="Sua senha"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#c8102e]"
                />
              </div>

              {erro && (
                <p className="text-sm text-red-600" role="alert">{erro}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-[#e50936] to-[#bf0d2d] text-white font-semibold text-sm rounded-xl py-4 disabled:opacity-60"
              >
                {loading ? "Entrando..." : "Entrar →"}
              </button>
            </form>
          </div>
        </div>
      </section>
    </main>
  );
}