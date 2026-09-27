"""Data access for Protheus contract portfolio queries."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pandas as pd
import requests
import streamlit as st
from requests.auth import HTTPBasicAuth

from config.settings import API_CONFIG, DEMO_MODE
from utils.demo_data import carregar_demo
from utils.adiantamentos_service import preparar_adiantamentos
from utils.contratos_service import preparar_carteira_contratos
from utils.execucao_contratual_service import preparar_execucao_contratual
from utils.financeiro_service import preparar_financeiro, preparar_fluxo_financeiro
from utils.fornecedores_service import preparar_fornecedores
from utils.medicoes_service import preparar_medicoes


QUERY_DIR = Path(__file__).resolve().parents[1] / "queries"
LAST_ERROR: str | None = None


def _read_query(filename: str) -> str:
    return (QUERY_DIR / filename).read_text(encoding="utf-8")


def _read_query_with_base(filename: str) -> str:
    sql = _read_query(filename)
    if "{{BASE_CONTRATOS}}" not in sql:
        return sql
    return sql.replace("{{BASE_CONTRATOS}}", _read_query("base_contratos.sql"))


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("rows", "data", "result", "results", "items", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
        for value in payload.values():
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def _parse_response_text(text: str) -> pd.DataFrame:
    raw = (text or "").strip()
    if not raw:
        return pd.DataFrame()

    cleaned = raw.lstrip("\ufeff")
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    cleaned = re.sub(r"}\s*{", "},{", cleaned)

    try:
        payload = json.loads(cleaned)
        rows = _extract_rows(payload)
        if rows:
            return pd.DataFrame(rows)
        return pd.DataFrame(payload)
    except Exception:
        pass

    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    objects = []
    for chunk in cleaned.split("},{"):
        item = chunk
        if not item.startswith("{"):
            item = "{" + item
        if not item.endswith("}"):
            item += "}"
        try:
            objects.append(json.loads(item))
        except Exception:
            continue

    return pd.DataFrame(objects)


def run_sql(sql: str) -> pd.DataFrame:
    """Execute a SQL string through the configured Protheus REST endpoint."""
    global LAST_ERROR
    LAST_ERROR = None

    if DEMO_MODE:
        raise RuntimeError("SQL externo indisponivel no modo demo.")

    url = API_CONFIG.get("url")
    if not url:
        LAST_ERROR = "API_CONFIG.url nao configurado."
        return pd.DataFrame()

    try:
        endpoint = urlsplit(str(url))
        if (endpoint.scheme != "https" or not endpoint.hostname
                or endpoint.username is not None or endpoint.password is not None
                or endpoint.query or endpoint.fragment):
            raise ValueError
        if API_CONFIG.get("verify", True) is not True:
            raise ValueError
    except ValueError:
        LAST_ERROR = "Configure uma URL HTTPS sem credenciais, query ou fragmento e mantenha verify=True."
        return pd.DataFrame()

    auth = None
    if API_CONFIG.get("user") and API_CONFIG.get("password"):
        auth = HTTPBasicAuth(str(API_CONFIG["user"]), str(API_CONFIG["password"]))

    try:
        with requests.Session() as session:
            # Nao herdar proxies ou credenciais .netrc da maquina.
            session.trust_env = False
            response = session.get(
                str(url),
                auth=auth,
                data=sql.encode("utf-8"),
                headers={"Content-Type": "text/plain", "Accept": "application/json"},
                timeout=int(API_CONFIG.get("timeout", 120)),
                verify=True,
                allow_redirects=False,
            )
        if response.status_code != 200:
            LAST_ERROR = f"HTTP {response.status_code}: consulta recusada pela API."
            return pd.DataFrame()

        encoding = "cp1252"
        content_type = response.headers.get("content-type", "")
        if "charset=" in content_type:
            encoding = content_type.split("charset=")[-1].strip()
        try:
            text = response.content.decode(encoding)
        except Exception:
            text = response.text
        return _parse_response_text(text)
    except Exception:
        LAST_ERROR = "Falha na consulta. Verifique conectividade, certificado e configuracao da API."
        return pd.DataFrame()


@st.cache_data(ttl=900, show_spinner=False)
def get_base_contratos() -> pd.DataFrame:
    """Load the normalized one-row-per-contract base from Protheus."""
    if DEMO_MODE:
        return preparar_carteira_contratos(carregar_demo("contratos"))

    # Versao do cache alterada quando a regra SQL da carteira muda.
    cache_version = 2
    _ = cache_version
    sql = _read_query("base_contratos.sql") #abre o arquivo base_contratos.sql e le o conteudo
    df = run_sql(sql) #aqui executa a query sql e retorna um dataframe com os dados
    return preparar_carteira_contratos(df) #aqui prepara o dataframe para ser usado na carteira de contratos, chamando a funcao preparar_carteira_contratos do arquivo utils/contratos_service.py


def get_dashboard_executivo() -> pd.DataFrame:
    """Load and normalize the contract portfolio DataFrame used by executive views."""
    return get_base_contratos()


def get_carteira_contratos() -> pd.DataFrame:
    """Alias for future modules that consume the same contract portfolio."""
    return get_base_contratos()


@st.cache_data(ttl=900, show_spinner=False)
def get_execucao_contratual() -> pd.DataFrame:
    """Load and normalize contractual execution data from Protheus."""
    if DEMO_MODE:
        return preparar_execucao_contratual(carregar_demo("execucao"))

    sql = _read_query_with_base("execucao_contratual.sql")
    df = run_sql(sql)
    return preparar_execucao_contratual(df)


@st.cache_data(ttl=900, show_spinner=False)
def get_financeiro() -> pd.DataFrame:
    """Load and normalize financial contract data from Protheus."""
    if DEMO_MODE:
        return preparar_financeiro(carregar_demo("financeiro"))

    sql = _read_query_with_base("financeiro.sql")
    df = run_sql(sql)
    return preparar_financeiro(df)


@st.cache_data(ttl=900, show_spinner=False)
def get_fluxo_financeiro() -> pd.DataFrame:
    """Load and normalize financial flow data from Protheus."""
    if DEMO_MODE:
        return preparar_fluxo_financeiro(carregar_demo("fluxo"))

    sql = _read_query_with_base("fluxo_financeiro.sql")
    df = run_sql(sql)
    return preparar_fluxo_financeiro(df)


@st.cache_data(ttl=900, show_spinner=False)
def get_adiantamentos() -> pd.DataFrame:
    """Load and normalize contract advances from Protheus."""
    if DEMO_MODE:
        return preparar_adiantamentos(carregar_demo("adiantamentos"))

    sql = _read_query("adiantamentos.sql")
    df = run_sql(sql)
    return preparar_adiantamentos(df)


@st.cache_data(ttl=900, show_spinner=False)
def get_fornecedores() -> pd.DataFrame:
    """Load and normalize supplier contract data from Protheus."""
    if DEMO_MODE:
        return preparar_fornecedores(carregar_demo("fornecedores"))

    sql = _read_query_with_base("fornecedores.sql")
    df = run_sql(sql)
    return preparar_fornecedores(df)


@st.cache_data(ttl=900, show_spinner=False)
def get_validacoes_base_contratos() -> pd.DataFrame:
    """Load validation metrics for the normalized contract base."""
    if DEMO_MODE:
        return carregar_demo("validacoes")

    sql = _read_query_with_base("validacoes_base_contratos.sql")
    return run_sql(sql)


@st.cache_data(ttl=900, show_spinner=False)
def get_medicoes() -> pd.DataFrame:
    """Load and normalize contract measurement data (CND010/CNE010) from Protheus.

    A consulta foi dividida em duas partes porque o endpoint REST do Protheus
    retorna HTTP 500 quando a SQL unica com todos os subselects correlacionados
    e JOINs e enviada. O merge e realizado no Python pela chave composta
    FILIAL + CONTRATO + REVISAO_CONTRATO + NUMERO_MEDICAO.
    """
    if DEMO_MODE:
        return preparar_medicoes(carregar_demo("medicoes"))

    df_cabecalho = run_sql(_read_query("medicoes_cabecalho.sql"))
    df_itens = run_sql(_read_query("medicoes_itens.sql"))

    if df_cabecalho.empty:
        return preparar_medicoes(df_cabecalho)

    merge_keys = ["FILIAL", "CONTRATO", "REVISAO_CONTRATO", "NUMERO_MEDICAO"]
    for key in merge_keys:
        if key in df_cabecalho.columns:
            df_cabecalho[key] = df_cabecalho[key].astype(str).str.strip()
        if key in df_itens.columns:
            df_itens[key] = df_itens[key].astype(str).str.strip()

    if df_itens.empty:
        for column in [
            "QTD_ITENS",
            "QTD_PRODUTOS_DISTINTOS",
            "QTD_SOLICITADA",
            "QTD_MEDIDA",
            "TOTAL_ITENS",
            "TOTAL_LIQUIDO_ITENS",
            "TOTAL_MULTAS_ITENS",
            "TOTAL_BONIFICACOES_ITENS",
        ]:
            df_cabecalho[column] = 0
        return preparar_medicoes(df_cabecalho)

    df = df_cabecalho.merge(df_itens, on=merge_keys, how="left", suffixes=("", "_ITENS"))

    for column in [
        "QTD_ITENS",
        "QTD_PRODUTOS_DISTINTOS",
        "QTD_SOLICITADA",
        "QTD_MEDIDA",
        "TOTAL_ITENS",
        "TOTAL_LIQUIDO_ITENS",
        "TOTAL_MULTAS_ITENS",
        "TOTAL_BONIFICACOES_ITENS",
    ]:
        if column not in df.columns:
            df[column] = 0
        df[column] = df[column].fillna(0)

    return preparar_medicoes(df)


@st.cache_data(ttl=900, show_spinner=False)
def get_medicoes_itens_detalhe() -> pd.DataFrame:
    """Load CNE010 item rows used by the Medicoes drill-down."""
    if DEMO_MODE:
        return carregar_demo("medicoes_itens")

    return run_sql(_read_query("medicoes_itens_detalhe.sql"))
