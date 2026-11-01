"""
TechFix Informática — Aplicação de Atendimento (Gradio)
Cadastro de cliente + abertura de Ordem de Serviço, gravando no Supabase.

Executar:  python app_gradio.py
"""
import gradio as gr

from db import (
    criar_os,
    get_client,
    mensagem_erro_banco,
    obter_ou_criar_cliente,
    validar_cliente,
    validar_os,
)

# Conexão criada uma única vez (credenciais lidas do .env)
try:
    supabase = get_client()
    ERRO_CONEXAO = None
except Exception as e:  # noqa: BLE001
    supabase = None
    ERRO_CONEXAO = str(e)


def cadastrar(nome, endereco, email, celular, modelo, problema):
    """Valida os campos, reaproveita/cria o cliente e abre a OS."""
    if supabase is None:
        return f"❌ {ERRO_CONEXAO}"

    # 1) Validação antes de enviar ao banco
    erros = validar_cliente(nome, endereco, email, celular) + validar_os(modelo, problema)
    if erros:
        return "❌ Corrija os campos abaixo:\n" + "\n".join(f"• {e}" for e in erros)

    # 2) Gravação no Supabase com tratamento de exceções
    try:
        cliente_id, novo = obter_ou_criar_cliente(supabase, nome, endereco, email, celular)
        os_id = criar_os(supabase, cliente_id, modelo, problema)
    except Exception as e:  # noqa: BLE001
        return f"❌ {mensagem_erro_banco(e)}"

    origem = "Novo cliente cadastrado" if novo else "Cliente já existente (reaproveitado pelo e-mail)"
    return (
        f"✅ Ordem de Serviço **nº {os_id}** aberta com sucesso!\n\n"
        f"{origem} — código do cliente: {cliente_id}.\n"
        f"Status inicial: **Aberto**."
    )


def limpar():
    """Esvazia todos os campos e a mensagem."""
    return "", "", "", "", "", "", ""


CSS = """
.gradio-container {max-width: 820px !important; margin: auto;}
#titulo h1 {margin-bottom: 0;}
"""

# Gradio 6 moveu css/theme do Blocks() para o launch(); mantemos compatibilidade com 4.x/5.x
ESTILO = {"css": CSS, "theme": gr.themes.Soft()}
GRADIO_6 = int(gr.__version__.split(".")[0]) >= 6

with gr.Blocks(title="TechFix — Atendimento", **({} if GRADIO_6 else ESTILO)) as demo:
    gr.Markdown(
        "# 🛠️ TechFix Informática\n"
        "### Abertura de Ordem de Serviço\n"
        "Preencha os dados do cliente e do equipamento e clique em **Cadastrar**. "
        "Se o e-mail já estiver cadastrado, o cliente é reaproveitado automaticamente.",
        elem_id="titulo",
    )

    with gr.Group():
        gr.Markdown("**👤 Dados do cliente**")
        with gr.Row():
            with gr.Column(min_width=260):
                nome = gr.Textbox(label="Nome do Cliente *", placeholder="Ex.: Maria da Silva")
            with gr.Column(min_width=260):
                email = gr.Textbox(label="E-mail *", placeholder="Ex.: maria@exemplo.com", type="email")
        with gr.Row():
            with gr.Column(min_width=260):
                celular = gr.Textbox(
                    label="Celular/WhatsApp *",
                    placeholder="Somente números com DDD — ex.: 11987654321",
                    max_lines=1,
                )
            with gr.Column(min_width=260):
                endereco = gr.Textbox(label="Endereço *", placeholder="Rua, número - bairro, cidade")

    with gr.Group():
        gr.Markdown("**💻 Equipamento**")
        modelo = gr.Textbox(label="Modelo do Computador *", placeholder="Ex.: Notebook Dell Inspiron 15 3520")
        problema = gr.Textbox(
            label="Problema Apresentado *",
            placeholder="Descreva o defeito relatado pelo cliente...",
            lines=4,
        )

    with gr.Row():
        btn_cadastrar = gr.Button("✅ Cadastrar", variant="primary")
        btn_limpar = gr.Button("🧹 Limpar", variant="secondary")

    resultado = gr.Markdown()

    entradas = [nome, endereco, email, celular, modelo, problema]
    btn_cadastrar.click(cadastrar, inputs=entradas, outputs=resultado)
    btn_limpar.click(limpar, inputs=None, outputs=entradas + [resultado])

    gr.Markdown("<small>* Campos obrigatórios. Use apenas dados fictícios nos testes (LGPD).</small>")


if __name__ == "__main__":
    # share=True gera um link público temporário para testar no celular
    demo.launch(share=True, **(ESTILO if GRADIO_6 else {}))
