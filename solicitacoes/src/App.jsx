import { useState } from "react";
import Sidebar from "./components/Sidebar";
import SolicitacoesPage from "./pages/SolicitacoesPage";
import NovaSolicitacaoPage from "./pages/NovaSolicitacaoPage";
import RevisaoClinicaPage from "./pages/RevisaoClinicaPage";
import PerfilPage from "./pages/PerfilPage";
import RegistroAcessosPage from "./pages/RegistroAcessosPage"; // NOVO

export default function App() {
  const [pagina, setPagina] = useState("/painel");
  const [pedidoInicial, setPedidoInicial] = useState(null);

  function abrirRevisao(pedidoOuNumero = null) {
    const numero =
      typeof pedidoOuNumero === "object" && pedidoOuNumero !== null
        ? pedidoOuNumero.numero ?? pedidoOuNumero.id ?? null
        : pedidoOuNumero;

    setPedidoInicial(numero);
    setPagina("/revisao");
  }

  function navegar(novaPagina) {
    if (novaPagina !== "/revisao") setPedidoInicial(null);
    setPagina(novaPagina);
  }

  let conteudo;

  if (pagina === "/perfil") {
    conteudo = <PerfilPage />;
  } else if (pagina === "/acessos") {            // NOVO
    conteudo = <RegistroAcessosPage />;          // NOVO
  } else if (pagina === "/revisao") {            // NOVO (else if)
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
