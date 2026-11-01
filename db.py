"""
Módulo compartilhado de acesso ao Supabase e de validações.
Usado pelos dois apps (Gradio e Streamlit) para não duplicar regras.
"""
import os
import re

from dotenv import load_dotenv
from supabase import Client, create_client

# Carrega variáveis do arquivo .env (se existir) — as chaves NUNCA ficam no código
load_dotenv()

STATUS_VALIDOS = ["Aberto", "Em análise", "Aguardando peça", "Concluído", "Entregue"]

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
CELULAR_REGEX = re.compile(r"^[0-9]{10,13}$")


def get_client(url: str | None = None, key: str | None = None) -> Client:
    """Cria o cliente Supabase a partir de parâmetros ou variáveis de ambiente."""
    url = url or os.environ.get("SUPABASE_URL")
    key = key or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "Credenciais ausentes. Defina SUPABASE_URL e SUPABASE_KEY no .env "
            "(ou em .streamlit/secrets.toml)."
        )
    return create_client(url, key)


# ----------------------------------------------------------------------
# Validações
# ----------------------------------------------------------------------
def normalizar_celular(celular: str) -> str:
    """Remove espaços, parênteses e traços digitados pelo usuário."""
    return re.sub(r"[\s()\-+]", "", celular or "")


def validar_cliente(nome, endereco, email, celular) -> list[str]:
    """Retorna a lista de erros encontrados (vazia = tudo certo)."""
    erros = []
    if not (nome or "").strip():
        erros.append("Nome do cliente é obrigatório.")
    if not (endereco or "").strip():
        erros.append("Endereço é obrigatório.")
    if not (email or "").strip():
        erros.append("E-mail é obrigatório.")
    elif not EMAIL_REGEX.match(email.strip()):
        erros.append("E-mail em formato inválido (ex.: nome@dominio.com).")
    cel = normalizar_celular(celular)
    if not cel:
        erros.append("Celular/WhatsApp é obrigatório.")
    elif not CELULAR_REGEX.match(cel):
        erros.append("Celular deve conter apenas números, com 10 a 13 dígitos (ex.: 11987654321).")
    return erros


def validar_os(modelo, problema) -> list[str]:
    erros = []
    if not (modelo or "").strip():
        erros.append("Modelo do computador é obrigatório.")
    if not (problema or "").strip():
        erros.append("Problema apresentado é obrigatório.")
    return erros


def mensagem_erro_banco(exc: Exception) -> str:
    """Traduz erros comuns do PostgreSQL/Supabase para mensagens amigáveis."""
    texto = str(exc)
    if "uq_clientes_email" in texto or "duplicate key" in texto:
        return "Já existe um cliente com este e-mail."
    if "ck_clientes_email" in texto:
        return "O banco rejeitou o e-mail: formato inválido."
    if "ck_clientes_celular" in texto:
        return "O banco rejeitou o celular: use apenas números (10 a 13 dígitos)."
    if "ck_os_status" in texto:
        return "Status inválido."
    if "row-level security" in texto:
        return "Acesso negado pelas políticas de segurança (RLS) do Supabase."
    if "Name or service not known" in texto or "ConnectError" in texto:
        return "Não foi possível conectar ao Supabase. Verifique a internet e a SUPABASE_URL."
    return f"Erro ao acessar o banco de dados: {texto}"


# ----------------------------------------------------------------------
# Operações de negócio
# ----------------------------------------------------------------------
def obter_ou_criar_cliente(sb: Client, nome, endereco, email, celular) -> tuple[int, bool]:
    """
    Se o e-mail já existir, reaproveita o cliente; senão cria um novo.
    Retorna (cliente_id, criado_agora).
    """
    email = email.strip().lower()
    existente = sb.table("clientes").select("id").eq("email", email).limit(1).execute()
    if existente.data:
        return existente.data[0]["id"], False

    novo = (
        sb.table("clientes")
        .insert(
            {
                "nome": nome.strip(),
                "endereco": endereco.strip(),
                "email": email,
                "celular_whatsapp": normalizar_celular(celular),
            }
        )
        .execute()
    )
    return novo.data[0]["id"], True


def criar_os(sb: Client, cliente_id: int, modelo: str, problema: str, status: str = "Aberto") -> int:
    """Cria a ordem de serviço e devolve o número (id) gerado."""
    resp = (
        sb.table("ordens_servico")
        .insert(
            {
                "cliente_id": cliente_id,
                "modelo_computador": modelo.strip(),
                "problema_relatado": problema.strip(),
                "status": status,
            }
        )
        .execute()
    )
    return resp.data[0]["id"]
