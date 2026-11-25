import { useState } from "react";
import Sidebar from "./components/Sidebar";
import SolicitacoesPage from "./pages/SolicitacoesPage";
import NovaSolicitacaoPage from "./pages/NovaSolicitacaoPage";
import RevisaoClinicaPage from "./pages/RevisaoClinicaPage";

export default function App() {
  const [pagina, setPagina] = useState("/painel");
  const [pedidoInicial, setPedidoInicial] = useState(null);

  function abrirRevisao(pedidoOuNumero = null) {
    // Caso `pedido` seja um objeto (ex.: { numero: 2041 }) ou já seja o número/id
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

      {pagina === "/revisao" ? (
        <RevisaoClinicaPage pedidoInicial={pedidoInicial} />
      ) : pagina === "/solicitacoes/nova" ? (
        <NovaSolicitacaoPage />
      ) : (
        <SolicitacoesPage
          onVerCandidatos={(pedido) => abrirRevisao(pedido)}
          onAbrirPedido={(pedido) => abrirRevisao(pedido)}
        />
      )}
    </div>
  );
}