# HemoLink — Backend FastAPI & Motor de Machine Learning

Módulo em Python responsável pela API do HemoLink e pelo motor de **Machine Learning** para encontrar e ranquear os doadores de sangue mais correspondentes para um pedido alvo.

## Arquitetura Híbrida em Dois Estágios

1. **Estágio 1 — Filtro Clínico Determinístico (`ml/compatibility.py`, `ml/geo.py`)**:
   - Garante compatibilidade biológica **ABO/Rh por hemocomponente** (Hemácias, Plasma fresco congelado com regra ABO inversa, Plaquetas e Crioprecipitado).
   - Aplica critérios mínimos da ANVISA / Ministério da Saúde (idade, peso, intervalo entre doações por sexo, limite anual, opt-in e raio máximo por urgência).
2. **Estágio 2 — Ranqueamento por Machine Learning (`ml/features.py`, `ml/train.py`, `ml/predictor.py`)**:
   - Avalia pares `(pedido_alvo, doador_elegível)` usando **LightGBM Calibrado** (comparado via `GroupKFold` contra Baseline por Distância, Regressão Logística, Random Forest e `LGBMRanker`).
   - Produz probabilidades calibradas (`0–100%`) e explicações locais via **SHAP** para apoiar a decisão da equipe clínica (*Human-in-the-Loop*).

## Como executar localmente (Windows / PowerShell)

```powershell
cd server

# 1. Ativar ambiente virtual (ou criar caso ainda não exista)
.\.venv\Scripts\Activate.ps1

# 2. (Se necessário) Instalar dependências
pip install -r requirements.txt

# 3. Treinar / retreinar modelos e gerar gráficos de avaliação + SHAP
python -m ml.train

# 4. Rodar testes automatizados (segurança transfusional, ML e contratos da API)
pytest -v

# 5. Iniciar a API FastAPI (Swagger disponível em http://localhost:8000/docs)
uvicorn main:app --reload --port 8000
```

## Integração com o Frontend (`solicitacoes/`)

Crie um arquivo `solicitacoes/.env` contendo:

```env
VITE_BACKEND_URL=http://localhost:8000
```

A tela de **Revisão Clínica** (`RevisaoClinicaPage.jsx`) passará a consumir os candidatos ranqueados em tempo real pelo modelo de Machine Learning.

## Integração com o Supabase

Configure `server/.env` com `SUPABASE_URL` e `SUPABASE_KEY` e execute o DDL de `server/supabase_schema.sql` no SQL Editor do Supabase. Enquanto o `.env` não estiver preenchido, a API opera automaticamente em modo de demonstração com o catálogo local de doadores..
