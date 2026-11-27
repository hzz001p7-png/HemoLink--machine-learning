-- Schema sugerido para o Supabase (PostgreSQL) — HemoLink ML
-- Compatível com server/main.py e os contratos do frontend React (solicitacoes/).
-- Obs.: dados pessoais sensíveis (CPF, nome, telefone) ficam isolados em `perfis`
-- e NUNCA são enviados como features ao modelo de Machine Learning.

create table if not exists public.doadores (
    id uuid primary key default gen_random_uuid(),
    perfil_id uuid references public.perfis(id) on delete set null,
    codigo text unique not null, -- ex.: 'D-0301'
    tipo_sanguineo text not null check (tipo_sanguineo in ('A+','A-','B+','B-','AB+','AB-','O+','O-','Não sei')),
    estado char(2) not null,
    cidade text not null,
    latitude double precision,
    longitude double precision,
    sexo char(1) check (sexo in ('M','F')),
    idade integer check (idade between 16 and 99),
    peso_kg numeric(5,1),
    apto_clinicamente boolean not null default true,
    aceita_avisos boolean not null default true,
    situacao text not null default 'responde_1h'
        check (situacao in ('disponivel_agora','responde_1h','indisponivel_temporario')),
    total_doacoes_anteriores integer not null default 0,
    dias_desde_ultima_doacao integer,
    doacoes_ultimos_12m integer not null default 0,
    taxa_aceite_historico numeric(4,3),
    taxa_comparecimento numeric(4,3),
    tempo_medio_resposta_min numeric(6,1),
    horas_desde_ultimo_acesso numeric(7,1) default 24.0,
    turno_preferido text default 'flexivel'
        check (turno_preferido in ('manha','tarde','noite','flexivel')),
    atualizado_em timestamptz not null default now()
);

create table if not exists public.solicitacoes (
    id uuid primary key default gen_random_uuid(),
    numero serial unique not null, -- ex.: 2041, 2042
    usuario_id uuid,
    tipo_sanguineo text not null check (tipo_sanguineo in ('A+','A-','B+','B-','AB+','AB-','O+','O-')),
    componente text not null,
    bolsas_total integer not null check (bolsas_total between 1 and 99),
    bolsas_recebidas integer not null default 0,
    urgencia text not null check (urgencia in ('normal','urgente','emergencia')),
    estado char(2) not null,
    cidade text not null,
    hospital text not null,
    observacoes text default '',
    status text not null default 'na_fila'
        check (status in ('na_fila','aprovado','devolvido','recusado','concluido')),
    etapa_atual integer not null default 2,
    etapa_total integer not null default 5,
    etapa_nome text not null default 'Aguardando revisão clínica',
    checklist jsonb not null default '{"compatibilidadeTransfusional": false, "elegibilidadeDoadores": false, "urgenciaPedido": false}'::jsonb,
    criado_em timestamptz not null default now()
);

-- Tabela de Feedback Loop (Human-in-the-Loop) para retreinamento contínuo do modelo
create table if not exists public.recomendacoes_ml (
    id uuid primary key default gen_random_uuid(),
    solicitacao_id uuid references public.solicitacoes(id) on delete cascade,
    doador_codigo text not null,
    modelo_versao text not null,
    ranking integer not null,
    score_compatibilidade integer not null,
    probabilidade_calibrada numeric(5,4) not null,
    distancia_km numeric(6,2),
    fatores_principais jsonb default '[]'::jsonb,
    aprovado_equipe_clinica boolean default false,
    desfecho_real text check (desfecho_real in ('pendente','ignorou','recusou','respondeu_tarde','agendou','compareceu_doou')),
    match_sucesso boolean,
    criado_em timestamptz not null default now(),
    atualizado_em timestamptz not null default now()
);

create index if not exists idx_doadores_tipo_estado on public.doadores (tipo_sanguineo, estado);
create index if not exists idx_solicitacoes_status_urgencia on public.solicitacoes (status, urgencia);
create index if not exists idx_recomendacoes_solicitacao on public.recomendacoes_ml (solicitacao_id);
