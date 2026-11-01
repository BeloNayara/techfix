-- =====================================================================
-- TechFix Informática — Sistema de Ordens de Serviço
-- Script DDL para Supabase (PostgreSQL)
-- Execute este arquivo inteiro no SQL Editor do Supabase.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0) Limpeza (permite reexecutar o script durante os testes)
--    A ordem importa: primeiro a tabela filha (ordens_servico).
-- ---------------------------------------------------------------------
drop table if exists public.ordens_servico cascade;
drop table if exists public.clientes cascade;
drop function if exists public.fn_atualiza_data_atualizacao() cascade;

-- ---------------------------------------------------------------------
-- 1) Tabela CLIENTES
--    Um cliente pode ter várias ordens de serviço (relação 1:N).
-- ---------------------------------------------------------------------
create table public.clientes (
    -- Chave primária gerada automaticamente
    id               bigint generated always as identity primary key,

    -- Campos essenciais (NOT NULL)
    nome             text        not null,
    endereco         text        not null,
    email            text        not null,
    celular_whatsapp text        not null,

    -- Data de cadastro preenchida automaticamente
    data_cadastro    timestamptz not null default now(),

    -- E-mail único: é a chave de reaproveitamento do cliente no Gradio
    constraint uq_clientes_email unique (email),

    -- Nome não pode ser vazio/só espaços
    constraint ck_clientes_nome check (length(trim(nome)) >= 2),

    -- Validação simples de formato de e-mail (algo@dominio.ext)
    constraint ck_clientes_email check (
        email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    ),

    -- Celular: somente dígitos, de 10 a 13 caracteres (ex.: 11987654321)
    constraint ck_clientes_celular check (celular_whatsapp ~ '^[0-9]{10,13}$')
);

comment on table public.clientes is 'Cadastro de clientes da TechFix Informática';

-- ---------------------------------------------------------------------
-- 2) Tabela ORDENS_SERVICO
--    Cada OS pertence a exatamente um cliente (FK obrigatória).
-- ---------------------------------------------------------------------
create table public.ordens_servico (
    -- Chave primária = número da OS
    id                bigint generated always as identity primary key,

    -- Chave estrangeira para clientes.
    -- ON DELETE CASCADE: ao excluir um cliente, suas OS também são excluídas
    -- (o painel Streamlit pede confirmação antes dessa operação).
    cliente_id        bigint not null
                      references public.clientes (id)
                      on update cascade
                      on delete cascade,

    modelo_computador text   not null,
    problema_relatado text   not null,

    -- Status com valor inicial 'Aberto'
    status            text   not null default 'Aberto',

    data_abertura     timestamptz not null default now(),
    data_atualizacao  timestamptz,

    -- Somente os status permitidos pelo fluxo da loja
    constraint ck_os_status check (
        status in ('Aberto', 'Em análise', 'Aguardando peça', 'Concluído', 'Entregue')
    ),

    -- Textos não podem ser vazios
    constraint ck_os_modelo   check (length(trim(modelo_computador)) > 0),
    constraint ck_os_problema check (length(trim(problema_relatado)) > 0)
);

comment on table public.ordens_servico is 'Ordens de serviço (reparos) abertas para os clientes';

-- ---------------------------------------------------------------------
-- 3) Índices
--    Aceleram os filtros usados no painel (cliente, status, nome).
-- ---------------------------------------------------------------------
create index idx_os_cliente_id    on public.ordens_servico (cliente_id);
create index idx_os_status        on public.ordens_servico (status);
create index idx_os_data_abertura on public.ordens_servico (data_abertura desc);
create index idx_clientes_nome    on public.clientes (lower(nome));

-- ---------------------------------------------------------------------
-- 4) Trigger: atualiza data_atualizacao a cada UPDATE em uma OS
-- ---------------------------------------------------------------------
create or replace function public.fn_atualiza_data_atualizacao()
returns trigger
language plpgsql
as $$
begin
    new.data_atualizacao := now();
    return new;
end;
$$;

create trigger trg_os_data_atualizacao
before update on public.ordens_servico
for each row
execute function public.fn_atualiza_data_atualizacao();

-- ---------------------------------------------------------------------
-- 5) Segurança: Row Level Security (RLS)
--    O Supabase expõe as tabelas via API REST. Com RLS ligado, nada é
--    acessível sem uma política explícita.
--    Para esta atividade acadêmica, as políticas abaixo liberam o CRUD
--    para a chave anon (usada pelos apps). Em produção, o ideal seria
--    exigir login (role "authenticated") ou usar a service_role apenas
--    no servidor.
-- ---------------------------------------------------------------------
alter table public.clientes       enable row level security;
alter table public.ordens_servico enable row level security;

-- Clientes
create policy "clientes_select" on public.clientes
    for select to anon, authenticated using (true);
create policy "clientes_insert" on public.clientes
    for insert to anon, authenticated with check (true);
create policy "clientes_update" on public.clientes
    for update to anon, authenticated using (true) with check (true);
create policy "clientes_delete" on public.clientes
    for delete to anon, authenticated using (true);

-- Ordens de serviço
create policy "os_select" on public.ordens_servico
    for select to anon, authenticated using (true);
create policy "os_insert" on public.ordens_servico
    for insert to anon, authenticated with check (true);
create policy "os_update" on public.ordens_servico
    for update to anon, authenticated using (true) with check (true);
create policy "os_delete" on public.ordens_servico
    for delete to anon, authenticated using (true);

-- ---------------------------------------------------------------------
-- 6) Dados fictícios para teste (LGPD: nenhum dado real)
-- ---------------------------------------------------------------------
insert into public.clientes (nome, endereco, email, celular_whatsapp) values
    ('Ana Teste',    'Rua Fictícia, 100 - Centro',      'ana.teste@exemplo.com',    '11900000001'),
    ('Bruno Exemplo','Av. Imaginária, 250 - Jardim',    'bruno.exemplo@exemplo.com','11900000002'),
    ('Carla Modelo', 'Travessa Demo, 7 - Vila Nova',    'carla.modelo@exemplo.com', '11900000003');

insert into public.ordens_servico (cliente_id, modelo_computador, problema_relatado, status) values
    (1, 'Notebook Dell Inspiron 15', 'Não liga, LED de energia apagado.',        'Aberto'),
    (1, 'Mouse Logitech M170',       'Clique esquerdo falhando.',                'Concluído'),
    (2, 'Desktop Positivo',          'Muito lento e com tela azul ao iniciar.',  'Em análise'),
    (3, 'Notebook Lenovo IdeaPad 3', 'Tela trincada, precisa troca do display.', 'Aguardando peça');

-- ---------------------------------------------------------------------
-- 7) Testes rápidos das restrições (descomente para verificar o erro)
-- ---------------------------------------------------------------------
-- insert into public.clientes (nome, endereco, email, celular_whatsapp)
--   values ('X', 'Rua', 'email-invalido', '119'); -- viola CHECKs
-- update public.ordens_servico set status = 'Cancelado' where id = 1; -- viola CHECK de status
