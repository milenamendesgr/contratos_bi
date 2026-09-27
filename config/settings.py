"""
Configurações Globais do Dashboard de Contratos - CONTRATOS BI
"""

import os
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[1]

DATA_MODE = os.getenv("CONTRATOS_DATA_MODE", "demo").strip().lower()
if DATA_MODE not in {"demo", "api"}:
    raise ValueError("CONTRATOS_DATA_MODE deve ser demo ou api")
DEMO_MODE = DATA_MODE == "demo"
PROTHEUS_API_CONFIG = {}
if not DEMO_MODE:
    try:
        from config.local_settings import API_CONFIG as PROTHEUS_API_CONFIG
    except ModuleNotFoundError as exc:
        if exc.name != "config.local_settings":
            raise

# Cores da paleta CONTRATOS BI
CORES = {
    "verde_primario":   "#004B23",
    "verde_secundario": "#1B7A3E",
    "verde_destaque":   "#7FB77E",
    "fundo_principal":  "#FFFFFF",
    "fundo_secundario": "#F8F9FA",
    "texto_principal":  "#1C1C1C",
    "texto_secundario": "#555555",
    "borda_suave":      "#E0E0E0",
    # Cores de status de contrato
    "vigente":                 "#1B7A3E",
    "elaboracao":              "#E67E22",
    "emitido":                 "#2980B9",
    "aprovacao":               "#7FB77E",
    "paralisado":              "#8E44AD",
    "cancelado":               "#7F8C8D",
    "finalizado":              "#555555",
    "revisao":                 "#F39C12",
    "revisado":                "#0C5E42",
    "solicitacao_finalizacao": "#C0392B",
}

# Configuração da API TOTVS usada para executar SQL do Protheus.
# Pode ser sobrescrita por variáveis de ambiente no servidor Streamlit.
API_CONFIG = {
    "url": os.getenv(
        "CONTRATOS_API_URL",
        str(PROTHEUS_API_CONFIG.get("url", "")),
    ),
    "user": os.getenv("CONTRATOS_API_USER", str(PROTHEUS_API_CONFIG.get("user", ""))),
    "password": os.getenv("CONTRATOS_API_PASSWORD", str(PROTHEUS_API_CONFIG.get("password", ""))),
    "timeout": int(os.getenv("CONTRATOS_API_TIMEOUT", str(PROTHEUS_API_CONFIG.get("timeout", 120)))),
    "verify": os.getenv("CONTRATOS_API_VERIFY", str(PROTHEUS_API_CONFIG.get("verify", True))).lower() == "true",
}

# Banco SQLite exclusivo dos comentarios de contratos.
# O caminho pode ser sobrescrito no servidor sem alterar o codigo-fonte.
COMENTARIOS_DB_CONFIG = {
    "path": (PROJECT_ROOT / "data" / "demo_comentarios.db") if DEMO_MODE else Path(
        os.getenv("CONTRATOS_SQLITE_PATH", str(PROJECT_ROOT / "data" / "contratos_comentarios.db"))
    ),
    "busy_timeout_ms": int(os.getenv("CONTRATOS_SQLITE_BUSY_TIMEOUT_MS", "10000")),
}

# Unidades ficticias. Mapeamentos privados ficam em local_settings.
FILIAIS = {"D001": "Unidade Aurora", "D002": "Unidade Horizonte",
           "D003": "Unidade Primavera", "D004": "Unidade Vale Azul"}
if not DEMO_MODE:
    try:
        from config.local_settings import FILIAIS
    except ImportError:
        FILIAIS = {}

# Tipos de Contrato
TIPOS_CONTRATO = [
    "Prestação de Serviços",
    "Fornecimento",
    "Manutenção",
    "Locação",
    "Comodato",
    "Parceria",
    "Consultoria",
    "Outros",
]

# Status possíveis de um contrato
STATUS_CONTRATO = [
    "CANCELADO",
    "ELABORACAO",
    "EMITIDO",
    "APROVACAO",
    "VIGENTE",
    "PARALISADO",
    "SOLICITACAO_FINALIZACAO",
    "FINALIZADO",
    "REVISAO",
    "REVISADO",
]

# Mapeamento de colunas do arquivo importado → colunas internas do sistema
# Chave = nome que pode aparecer no Excel/CSV do usuário
# Valor = nome interno padronizado
COLUNAS_IMPORTACAO = {
    "Número do Contrato":  "NUMERO_CONTRATO",
    "Numero do Contrato":  "NUMERO_CONTRATO",
    "NUMERO_CONTRATO":     "NUMERO_CONTRATO",
    "Nº Contrato":         "NUMERO_CONTRATO",
    "No Contrato":         "NUMERO_CONTRATO",
    "Contrato":            "NUMERO_CONTRATO",
    "Cliente":             "CLIENTE",
    "CLIENTE":             "CLIENTE",
    "Contratante":         "CLIENTE",
    "Objeto":              "OBJETO",
    "OBJETO":              "OBJETO",
    "Descrição":           "OBJETO",
    "Descricao":           "OBJETO",
    "Filial":              "FILIAL",
    "FILIAL":              "FILIAL",
    "Unidade":             "FILIAL",
    "Tipo":                "TIPO",
    "TIPO":                "TIPO",
    "Tipo de Contrato":    "TIPO",
    "Data de Início":      "DATA_INICIO",
    "Data Início":         "DATA_INICIO",
    "Data Inicio":         "DATA_INICIO",
    "DATA_INICIO":         "DATA_INICIO",
    "Vigência Início":     "DATA_INICIO",
    "Vigencia Inicio":     "DATA_INICIO",
    "Data de Fim":         "DATA_FIM",
    "Data Fim":            "DATA_FIM",
    "DATA_FIM":            "DATA_FIM",
    "Data Vencimento":     "DATA_FIM",
    "Vencimento":          "DATA_FIM",
    "Vigência Fim":        "DATA_FIM",
    "Vigencia Fim":        "DATA_FIM",
    "Valor Mensal":        "VALOR_MENSAL",
    "VALOR_MENSAL":        "VALOR_MENSAL",
    "Valor Total":         "VALOR_TOTAL",
    "VALOR_TOTAL":         "VALOR_TOTAL",
    "Status":              "STATUS",
    "STATUS":              "STATUS",
    "Situação":            "STATUS",
    "Situacao":            "STATUS",
    "Responsável":         "RESPONSAVEL",
    "Responsavel":         "RESPONSAVEL",
    "RESPONSAVEL":         "RESPONSAVEL",
    "Observações":         "OBSERVACOES",
    "Observacoes":         "OBSERVACOES",
    "OBSERVACOES":         "OBSERVACOES",
    "Obs":                 "OBSERVACOES",
}

# Colunas internas que devem obrigatoriamente existir após importação
COLUNAS_OBRIGATORIAS = [
    "NUMERO_CONTRATO",
    "CLIENTE",
    "DATA_FIM",
    "STATUS",
]

# Configurações de layout
LAYOUT_CONFIG = {
    "page_title": "CONTRATOS BI - Contratos",
    "page_icon":  " ",
    "port":        8506,
}
