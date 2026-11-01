# TechFix Informática — Sistema de Ordens de Serviço

Duas aplicações Python que compartilham um banco PostgreSQL no **Supabase**:

| App | Arquivo | Uso |
|---|---|---|
| Atendimento | `app_gradio.py` | Balcão/celular: cadastra cliente + abre OS |
| Painel do gerente | `app_streamlit.py` | CRUD, filtros, indicadores, exportar CSV |
| Banco | `sql/schema.sql` | Tabelas, restrições, índices, trigger, RLS |
| Módulo comum | `db.py` | Conexão, validações e regras compartilhadas |

```
[Celular/Navegador]          [Navegador do Gerente]
        |                              |
   App Gradio                    App Streamlit
        |      supabase-py (REST)      |
        +----------> SUPABASE <--------+
```

## 1. Banco de dados

1. Crie um projeto em [supabase.com](https://supabase.com).
2. Abra **SQL Editor**, cole todo o conteúdo de `sql/schema.sql` e clique em **Run**.
   - Cria `clientes` e `ordens_servico` (1:N), com PK, FK `ON DELETE CASCADE`, `NOT NULL`,
     `UNIQUE(email)`, `CHECK` de status, e-mail e celular (10–13 dígitos).
   - Cria índices, trigger que atualiza `data_atualizacao` e políticas RLS.
   - Insere 3 clientes e 4 OS **fictícios** para teste.
3. Em **Project Settings → API**, copie a *Project URL* e a chave **anon (public)**.

## 2. Instalação

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

Crie o arquivo `.env` a partir do modelo e preencha:

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

> O `.env` (e o `.streamlit/secrets.toml`, se usado) está no `.gitignore`.
> **Nunca** use a chave `service_role` nos apps.

## 3. Execução

```bash
# Cadastro (gera também um link público *.gradio.live para abrir no celular)
python app_gradio.py

# Painel administrativo (abre em http://localhost:8501)
streamlit run app_streamlit.py
```

## 4. Funcionalidades

**Gradio** — `gr.Blocks` com `Row/Column` responsivos; validação de campos obrigatórios,
e-mail e celular; reaproveita cliente pelo e-mail; abre OS com status `Aberto`;
retorna o nº da OS; botão Limpar; `share=True`.

**Streamlit** — abas *Consultar*, *Cadastrar*, *Editar/Excluir*, *Indicadores*;
filtros por nome, e-mail e status na sidebar; edição de status da OS e de dados
do cliente; exclusão com checkbox de confirmação; `st.metric` por status e
`st.bar_chart`; **exportação CSV** dos dados filtrados (bônus).

**Boas práticas** — credenciais fora do código (`.env`/`secrets.toml`), `try/except`
em todas as operações com mensagens amigáveis, validação no app **e** no banco,
somente dados fictícios (LGPD).
