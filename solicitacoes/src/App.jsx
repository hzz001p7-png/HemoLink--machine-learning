import { useEffect, useState } from "react";
import { supabase } from "./lib/supabase";
import LoginPage from "./pages/LoginPage";

import Sidebar from "./components/Sidebar";
import SolicitacoesPage from "./pages/SolicitacoesPage";
import NovaSolicitacaoPage from "./pages/NovaSolicitacaoPage";
import RevisaoClinicaPage from "./pages/RevisaoClinicaPage";
import DoadoresPage from "./pages/DoadoresPage";
import PerfilPage from "./pages/PerfilPage";
import RegistroAcessosPage from "./pages/RegistroAcessosPage";

export default function App() {
  const [sessao, setSessao] = useState(null);
  const [verificando, setVerificando] = useState(true);
  const [pagina, setPagina] = useState("/painel");
  const [pedidoInicial, setPedidoInicial] = useState(null);

  useEffect(() => {
    async function verificarSessao() {
      const { data, error } = await supabase.auth.getSession();

      if (!error) {
        setSessao(data.session);
      }

      setVerificando(false);
    }

    verificarSessao();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSessao(session);
      setVerificando(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  function abrirRevisao(pedidoOuNumero = null) {
    const numero =
      typeof pedidoOuNumero === "object" && pedidoOuNumero !== null
        ? pedidoOuNumero.numero ?? pedidoOuNumero.id ?? null
        : pedidoOuNumero;

    setPedidoInicial(numero);
    setPagina("/revisao");
  }

  function navegar(novaPagina) {
    if (novaPagina !== "/revisao") {
      setPedidoInicial(null);
    }

    setPagina(novaPagina);
  }

  if (verificando) {
    return <div className="p-8">Verificando acesso...</div>;
  }

  if (!sessao) {
    return <LoginPage />;
  }

  let conteudo;

  if (pagina === "/perfil") {
    conteudo = <PerfilPage />;
  } else if (pagina === "/acessos") {
    conteudo = <RegistroAcessosPage />;
  } else if (pagina === "/doadores") {
    conteudo = <DoadoresPage />;
  } else if (pagina === "/revisao") {
    conteudo = <RevisaoClinicaPage pedidoInicial={pedidoInicial} />;
  } else if (pagina === "/solicitacoes/nova") {
    conteudo = <NovaSolicitacaoPage />;
  } else {
    conteudo = (
      <SolicitacoesPage
        onVerCandidatos={abrirRevisao}
        onAbrirPedido={abrirRevisao}
      />
    );
  }

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <Sidebar
        user={{
          role: "requester",
          organization: "Hospital Santa Clara",
        }}
        activePath={pagina}
        onNavigate={navegar}
      />
      {conteudo}
    </div>
  );
}