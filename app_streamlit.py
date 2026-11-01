"""
TechFix Informática — Painel Administrativo (Streamlit)
CRUD completo de clientes e ordens de serviço no Supabase.

Executar:  streamlit run app_streamlit.py
"""
import os

import pandas as pd
import streamlit as st

from db import (
    STATUS_VALIDOS,
    criar_os,
    get_client,
    mensagem_erro_banco,
    normalizar_celular,
    obter_ou_criar_cliente,
    validar_cliente,
    validar_os,
)

st.set_page_config(page_title="TechFix — Painel", page_icon="🛠️", layout="wide")


# ----------------------------------------------------------------------
# Conexão (credenciais de .streamlit/secrets.toml OU variáveis de ambiente)
# ----------------------------------------------------------------------
def ler_credenciais():
    try:
        return st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    except Exception:  # noqa: BLE001 — sem secrets.toml, cai para o .env
        return os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY")


@st.cache_resource
def conectar():
    url, key = ler_credenciais()
    return get_client(url, key)


try:
    sb = conectar()
except Exception as e:  # noqa: BLE001
    st.error(f"❌ {e}")
    st.stop()


# ----------------------------------------------------------------------
# Leitura de dados
# ----------------------------------------------------------------------
@st.cache_data(ttl=30)
def carregar_ordens() -> pd.DataFrame:
    """Lista as OS já com os dados do cliente (join via relacionamento FK)."""
    resp = (
        sb.table("ordens_servico")
        .select("*, clientes(nome, email, celular_whatsapp, endereco)")
        .order("id", desc=True)
        .execute()
    )
    linhas = []
    for r in resp.data:
        c = r.get("clientes") or {}
        linhas.append(
            {
                "OS": r["id"],
                "Cliente": c.get("nome"),
                "E-mail": c.get("email"),
                "Celular": c.get("celular_whatsapp"),
                "Endereço": c.get("endereco"),
                "Modelo": r["modelo_computador"],
                "Problema": r["problema_relatado"],
                "Status": r["status"],
                "Abertura": r["data_abertura"],
                "Atualização": r["data_atualizacao"],
                "cliente_id": r["cliente_id"],
            }
        )
    df = pd.DataFrame(linhas)
    if not df.empty:
        for col in ["Abertura", "Atualização"]:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True).dt.tz_convert("America/Sao_Paulo").dt.strftime("%d/%m/%Y %H:%M")
    return df


@st.cache_data(ttl=30)
def carregar_clientes() -> pd.DataFrame:
    resp = sb.table("clientes").select("*").order("nome").execute()
    return pd.DataFrame(resp.data)


def recarregar():
    """Limpa o cache após qualquer alteração e redesenha a tela."""
    st.cache_data.clear()
    st.rerun()


try:
    df_os = carregar_ordens()
    df_cli = carregar_clientes()
except Exception as e:  # noqa: BLE001
    st.error(f"❌ {mensagem_erro_banco(e)}")
    st.stop()


# ----------------------------------------------------------------------
# Barra lateral — filtros
# ----------------------------------------------------------------------
st.sidebar.title("🔎 Filtros")
f_nome = st.sidebar.text_input("Nome do cliente")
f_email = st.sidebar.text_input("E-mail")
f_status = st.sidebar.multiselect("Status", STATUS_VALIDOS, default=[])
if st.sidebar.button("🔄 Atualizar dados"):
    recarregar()

df_filtrado = df_os.copy()
if not df_filtrado.empty:
    if f_nome:
        df_filtrado = df_filtrado[df_filtrado["Cliente"].str.contains(f_nome, case=False, na=False)]
    if f_email:
        df_filtrado = df_filtrado[df_filtrado["E-mail"].str.contains(f_email, case=False, na=False)]
    if f_status:
        df_filtrado = df_filtrado[df_filtrado["Status"].isin(f_status)]

st.title("🛠️ TechFix Informática — Painel Administrativo")

aba_consultar, aba_cadastrar, aba_editar, aba_ind = st.tabs(
    ["📋 Consultar", "➕ Cadastrar", "✏️ Editar/Excluir", "📊 Indicadores"]
)

# ======================================================================
# ABA 1 — CONSULTAR
# ======================================================================
with aba_consultar:
    st.subheader("Ordens de serviço")
    st.caption(f"{len(df_filtrado)} de {len(df_os)} registros (use os filtros na barra lateral).")

    if df_filtrado.empty:
        st.info("Nenhuma ordem de serviço encontrada.")
    else:
        st.dataframe(
            df_filtrado.drop(columns=["cliente_id"]),
            width="stretch",
            hide_index=True,
        )
        # Desafio opcional (+0,5): exportar os dados filtrados em CSV
        csv = df_filtrado.drop(columns=["cliente_id"]).to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button("⬇️ Exportar CSV (dados filtrados)", csv, "ordens_servico.csv", "text/csv")

# ======================================================================
# ABA 2 — CADASTRAR (nova OS manual)
# ======================================================================
with aba_cadastrar:
    st.subheader("Nova ordem de serviço")
    tipo = st.radio("Cliente", ["Cliente existente", "Novo cliente"], horizontal=True)

    with st.form("form_nova_os", clear_on_submit=True):
        if tipo == "Cliente existente":
            if df_cli.empty:
                st.warning("Nenhum cliente cadastrado ainda. Escolha 'Novo cliente'.")
                cliente_sel = None
            else:
                opcoes = {f"{r.nome} — {r.email}": r.id for r in df_cli.itertuples()}
                cliente_sel = opcoes[st.selectbox("Selecione o cliente", list(opcoes))]
        else:
            c1, c2 = st.columns(2)
            n_nome = c1.text_input("Nome *")
            n_email = c2.text_input("E-mail *")
            n_cel = c1.text_input("Celular/WhatsApp * (somente números)")
            n_end = c2.text_input("Endereço *")

        modelo = st.text_input("Modelo do computador *")
        problema = st.text_area("Problema apresentado *")
        status = st.selectbox("Status inicial", STATUS_VALIDOS, index=0)
        enviar = st.form_submit_button("Cadastrar OS", type="primary")

    if enviar:
        erros = validar_os(modelo, problema)
        if tipo == "Novo cliente":
            erros = validar_cliente(n_nome, n_end, n_email, n_cel) + erros
        elif cliente_sel is None:
            erros.append("Selecione um cliente.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            try:
                if tipo == "Novo cliente":
                    cliente_sel, _ = obter_ou_criar_cliente(sb, n_nome, n_end, n_email, n_cel)
                os_id = criar_os(sb, cliente_sel, modelo, problema, status)
                st.cache_data.clear()
                st.success(f"✅ OS nº {os_id} cadastrada com sucesso!")
            except Exception as e:  # noqa: BLE001
                st.error(f"❌ {mensagem_erro_banco(e)}")

# ======================================================================
# ABA 3 — EDITAR / EXCLUIR
# ======================================================================
with aba_editar:
    col_os, col_cli = st.columns(2)

    # ---------------- Ordens de serviço ----------------
    with col_os:
        st.subheader("Ordem de serviço")
        if df_os.empty:
            st.info("Nenhuma OS cadastrada.")
        else:
            mapa_os = {f"OS {r.OS} — {r.Cliente} — {r.Modelo}": r for r in df_os.itertuples()}
            sel = mapa_os[st.selectbox("Selecione a OS", list(mapa_os), key="sel_os")]
            st.caption(f"Problema: {sel.Problema}")

            novo_status = st.selectbox(
                "Status", STATUS_VALIDOS, index=STATUS_VALIDOS.index(sel.Status), key="novo_status"
            )
            if st.button("💾 Salvar status", key="btn_status"):
                try:
                    sb.table("ordens_servico").update({"status": novo_status}).eq("id", sel.OS).execute()
                    st.success(f"Status da OS {sel.OS} alterado para '{novo_status}'.")
                    recarregar()
                except Exception as e:  # noqa: BLE001
                    st.error(f"❌ {mensagem_erro_banco(e)}")

            st.divider()
            conf_os = st.checkbox(f"Confirmo a exclusão da OS {sel.OS}", key="conf_os")
            if st.button("🗑️ Excluir OS", disabled=not conf_os, key="btn_del_os"):
                try:
                    sb.table("ordens_servico").delete().eq("id", sel.OS).execute()
                    st.success(f"OS {sel.OS} excluída.")
                    recarregar()
                except Exception as e:  # noqa: BLE001
                    st.error(f"❌ {mensagem_erro_banco(e)}")

    # ---------------- Clientes ----------------
    with col_cli:
        st.subheader("Cliente")
        if df_cli.empty:
            st.info("Nenhum cliente cadastrado.")
        else:
            mapa_cli = {f"{r.nome} — {r.email}": r for r in df_cli.itertuples()}
            cli = mapa_cli[st.selectbox("Selecione o cliente", list(mapa_cli), key="sel_cli")]

            with st.form("form_edit_cli"):
                e_end = st.text_input("Endereço", value=cli.endereco)
                e_email = st.text_input("E-mail", value=cli.email)
                e_cel = st.text_input("Celular/WhatsApp", value=cli.celular_whatsapp)
                salvar_cli = st.form_submit_button("💾 Salvar cliente")

            if salvar_cli:
                erros = validar_cliente(cli.nome, e_end, e_email, e_cel)
                if erros:
                    for e in erros:
                        st.error(e)
                else:
                    try:
                        sb.table("clientes").update(
                            {
                                "endereco": e_end.strip(),
                                "email": e_email.strip().lower(),
                                "celular_whatsapp": normalizar_celular(e_cel),
                            }
                        ).eq("id", cli.id).execute()
                        st.success("Cliente atualizado.")
                        recarregar()
                    except Exception as e:  # noqa: BLE001
                        st.error(f"❌ {mensagem_erro_banco(e)}")

            st.divider()
            qtd_os = int((df_os["cliente_id"] == cli.id).sum()) if not df_os.empty else 0
            st.warning(
                f"Excluir este cliente também apagará suas {qtd_os} OS (ON DELETE CASCADE)."
            )
            conf_cli = st.checkbox(f"Confirmo a exclusão de {cli.nome}", key="conf_cli")
            if st.button("🗑️ Excluir cliente", disabled=not conf_cli, key="btn_del_cli"):
                try:
                    sb.table("clientes").delete().eq("id", cli.id).execute()
                    st.success("Cliente excluído.")
                    recarregar()
                except Exception as e:  # noqa: BLE001
                    st.error(f"❌ {mensagem_erro_banco(e)}")

# ======================================================================
# ABA 4 — INDICADORES
# ======================================================================
with aba_ind:
    st.subheader("Indicadores")
    contagem = (
        df_os["Status"].value_counts().reindex(STATUS_VALIDOS, fill_value=0)
        if not df_os.empty
        else pd.Series(0, index=STATUS_VALIDOS)
    )

    cols = st.columns(len(STATUS_VALIDOS) + 1)
    cols[0].metric("Total de OS", int(contagem.sum()))
    for col, (status, qtd) in zip(cols[1:], contagem.items()):
        col.metric(status, int(qtd))

    st.markdown("**OS por status**")
    st.bar_chart(contagem.rename("Quantidade"))

    st.metric("Clientes cadastrados", len(df_cli))
