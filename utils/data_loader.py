"""
Carregamento, normalização e geração de dados de contratos - CONTRATOS BI
"""

import io
import random
from datetime import datetime

import pandas as pd

from config.settings import COLUNAS_IMPORTACAO, FILIAIS
from utils.data_normalization import limpar_string, calcular_status_vencimento


# ---------------------------------------------------------------------------
# NORMALIZAÇÃO
# ---------------------------------------------------------------------------

def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Renomeia colunas do arquivo para o padrão interno usando COLUNAS_IMPORTACAO."""
    rename_map = {}
    for col in df.columns:
        col_stripped = str(col).strip()
        if col_stripped in COLUNAS_IMPORTACAO:
            rename_map[col] = COLUNAS_IMPORTACAO[col_stripped]
    return df.rename(columns=rename_map)


def garantir_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Garante que todas as colunas internas existam (preenche com vazio se ausente)."""
    todas = [
        "NUMERO_CONTRATO", "CLIENTE", "OBJETO", "FILIAL", "TIPO",
        "DATA_INICIO", "DATA_FIM", "VALOR_MENSAL", "VALOR_TOTAL",
        "STATUS", "RESPONSAVEL", "OBSERVACOES",
    ]
    for col in todas:
        if col not in df.columns:
            df[col] = ""
    return df


def converter_datas(df: pd.DataFrame) -> pd.DataFrame:
    """Converte colunas de data para datetime (tenta inferir formato automaticamente)."""
    for col in ["DATA_INICIO", "DATA_FIM"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
    return df


def converter_valores(df: pd.DataFrame) -> pd.DataFrame:
    """Converte colunas de valor para float, tratando formatação brasileira."""
    for col in ["VALOR_MENSAL", "VALOR_TOTAL"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("R$", "", regex=False)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def normalizar_filial(df: pd.DataFrame) -> pd.DataFrame:
    """Mapeia código de filial para nome legível; mantém valor original se não mapeado."""
    if "FILIAL" in df.columns:
        df["FILIAL"] = df["FILIAL"].astype(str).str.strip()
        df["FILIAL_NOME"] = df["FILIAL"].map(FILIAIS).fillna(df["FILIAL"])
    else:
        df["FILIAL_NOME"] = ""
    return df


def adicionar_alertas(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona colunas DIAS_RESTANTES e ALERTA_VENCIMENTO ao DataFrame."""
    if "DATA_FIM" in df.columns:
        hoje = pd.Timestamp.now().normalize()
        df["DIAS_RESTANTES"] = df["DATA_FIM"].apply(
            lambda d: int((pd.Timestamp(d).normalize() - hoje).days)
            if pd.notna(d) else None
        )
        df["ALERTA_VENCIMENTO"] = df.apply(
            lambda row: calcular_status_vencimento(
                row["DATA_FIM"], str(row.get("STATUS", ""))
            ),
            axis=1,
        )
    else:
        df["DIAS_RESTANTES"] = None
        df["ALERTA_VENCIMENTO"] = "Sem Data"
    return df


# ---------------------------------------------------------------------------
# CARREGAMENTO DE ARQUIVO
# ---------------------------------------------------------------------------

def carregar_arquivo(arquivo) -> pd.DataFrame:
    """
    Carrega um arquivo Excel (.xlsx/.xls) ou CSV (.csv) e retorna
    o DataFrame completamente normalizado e pronto para uso.
    Lança ValueError com mensagem amigável em caso de erro.
    """
    nome = arquivo.name.lower()
    try:
        if nome.endswith(".csv"):
            try:
                df = pd.read_csv(arquivo, sep=None, engine="python", encoding="utf-8")
            except Exception:
                arquivo.seek(0)
                df = pd.read_csv(arquivo, sep=None, engine="python", encoding="latin-1")
        elif nome.endswith((".xlsx", ".xls")):
            df = pd.read_excel(arquivo)
        else:
            raise ValueError(
                f"Formato não suportado: '{arquivo.name}'. Use Excel (.xlsx) ou CSV (.csv)."
            )
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Erro ao ler '{arquivo.name}': {e}")

    if df.empty:
        raise ValueError("O arquivo importado está vazio.")

    df = normalizar_colunas(df)
    df = garantir_colunas(df)
    df = converter_datas(df)
    df = converter_valores(df)
    df = normalizar_filial(df)
    df = adicionar_alertas(df)

    # Limpeza de strings
    for col in ["NUMERO_CONTRATO", "CLIENTE", "OBJETO", "TIPO", "STATUS", "RESPONSAVEL", "OBSERVACOES"]:
        if col in df.columns:
            df[col] = df[col].apply(limpar_string)

    # Preencher valores ausentes
    df["NUMERO_CONTRATO"] = df["NUMERO_CONTRATO"].replace("", "N/I")
    df["CLIENTE"]         = df["CLIENTE"].replace("", "NÃO INFORMADO")
    df["STATUS"]          = df["STATUS"].replace("", "VIGENTE")
    df["TIPO"]            = df["TIPO"].replace("", "Não Classificado")

    return df


# ---------------------------------------------------------------------------
# DADOS DE EXEMPLO
# ---------------------------------------------------------------------------

def gerar_dados_exemplo() -> pd.DataFrame:
    """Adapta a mesma carteira sintetica para as telas legadas de importacao."""
    from utils.demo_data import carregar_demo
    from utils.contratos_service import preparar_carteira_contratos

    df = preparar_carteira_contratos(carregar_demo("contratos"))
    df["NUMERO_CONTRATO"] = df["CONTRATO"]
    df["CLIENTE"] = df["FORNECEDOR"]
    df["OBJETO"] = df["DESCRICAO"]
    df["VALOR_MENSAL"] = (df["VALOR_ATUAL"] / 12).round(2)
    df["RESPONSAVEL"] = "Equipe demonstracao"
    df["OBSERVACOES"] = "Dados inteiramente ficticios"
    return df
