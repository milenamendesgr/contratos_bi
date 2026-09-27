"""Alertas module with contract monitoring layout."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from components.cards import render_insights, render_kpi_cards
from components.charts import render_bar_chart
from components.filters import select_filter, text_filter
from components.tables import render_table_section
from config.settings import FILIAIS, DEMO_MODE
from utils.demo_data import carregar_demo
from utils import contratos_repository as repository
from utils.formatters import formatar_data, formatar_moeda, formatar_percentual, formatar_quantidade
from utils.insights import get_alertas_insights


QUERY_PATH = Path(__file__).resolve().parents[1] / "queries" / "alertas.sql"

ALERT_TABLE_COLUMNS = [
    "NIVEL_RISCO",
    "TIPO_ALERTA",
    "FILIAL_NOME",
    "CONTRATO",
    "FORNECEDOR",
    "CNPJ_FORNECEDOR",
    "TIPO",
    "STATUS",
    "DATA_FINAL",
    "VALOR_CONTRATO",
    "VALOR_MEDIDO",
    "SALDO_CONTRATO",
    "PERCENTUAL_CONSUMO",
]

ALERT_LABELS = {
    "CONTRATO_VENCIDO": "Contrato vencido",
    "PROXIMO_VENCIMENTO": "Proximo vencimento",
    "CONTRATO_PARALISADO": "Contrato paralisado",
    "ALTO_CONSUMO": "Alto consumo",
    "SEM_ALERTA": "Sem alerta",
}

RISK_ORDER = {
    "Critico": 0,
    "Atencao": 1,
    "Normal": 2,
}
STATUS_LABELS = {
    "01": "CANCELADO",
    "02": "ELABORACAO",
    "03": "EMITIDO",
    "04": "APROVACAO",
    "05": "VIGENTE",
    "06": "PARALISADO",
    "07": "SOLICITACAO_FINALIZACAO",
    "08": "FINALIZADO",
    "09": "REVISAO",
    "10": "REVISADO",
}


@st.cache_data(ttl=900, show_spinner=False)
def _load_alertas() -> pd.DataFrame:
    if DEMO_MODE:
        return carregar_demo("alertas")
    sql = QUERY_PATH.read_text(encoding="utf-8")
    return repository.run_sql(sql)


def _to_number(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0.0)

    normalized = (
        series.astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
        .replace({"": "0", "nan": "0", "None": "0"})
    )
    return pd.to_numeric(normalized, errors="coerce").fillna(0.0)


def _to_datetime(series: pd.Series) -> pd.Series:
    values = series.astype(str).str.strip().replace({"": None, "nan": None, "None": None})
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    protheus_mask = values.str.fullmatch(r"\d{8}", na=False)
    result.loc[protheus_mask] = pd.to_datetime(values.loc[protheus_mask], format="%Y%m%d", errors="coerce")
    result.loc[~protheus_mask] = pd.to_datetime(values.loc[~protheus_mask], dayfirst=True, errors="coerce")
    return result


def _risk_level(tipo_alerta: str) -> str:
    if tipo_alerta in {"CONTRATO_VENCIDO", "CONTRATO_PARALISADO"}:
        return "Critico"
    if tipo_alerta in {"PROXIMO_VENCIMENTO", "ALTO_CONSUMO"}:
        return "Atencao"
    return "Normal"


def _normalize_status(series: pd.Series) -> pd.Series:
    situacao = series.fillna("").astype(str).str.strip()
    return situacao.map(STATUS_LABELS).fillna(situacao).replace("", "Nao informado")


def _normalize_alertas(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()
    result.columns = [str(column).strip().upper() for column in result.columns]

    for column in ["FILIAL", "CONTRATO", "COD_FORNECEDOR", "LOJA_FORNECEDOR", "NOME_FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO_CONTRATO", "DESC_TIPO_CONTRATO", "SITUACAO", "TIPO_ALERTA"]:
        if column not in result.columns:
            result[column] = ""
        result[column] = result[column].fillna("").astype(str).str.strip()

    for column in ["DATA_INICIO", "DATA_FINAL"]:
        if column not in result.columns:
            result[column] = pd.NaT
        result[column] = _to_datetime(result[column])

    for column in ["VALOR_CONTRATO", "VALOR_MEDIDO", "SALDO_CONTRATO"]:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = _to_number(result[column])

    result["FILIAL_NOME"] = result["FILIAL"].map(FILIAIS).fillna(result["FILIAL"])
    result["FORNECEDOR"] = result["NOME_FORNECEDOR"]
    result["STATUS"] = _normalize_status(result["SITUACAO"])
    result["TIPO"] = result["DESC_TIPO_CONTRATO"].where(
        result["DESC_TIPO_CONTRATO"].ne(""),
        result["TIPO_CONTRATO"].replace("", "Nao informado"),
    )
    result["PERCENTUAL_CONSUMO"] = result.apply(
        lambda row: (row["VALOR_MEDIDO"] / row["VALOR_CONTRATO"] * 100) if row["VALOR_CONTRATO"] else 0.0,
        axis=1,
    )
    result["NIVEL_RISCO"] = result["TIPO_ALERTA"].apply(_risk_level)
    result["ALERTA"] = result["TIPO_ALERTA"].map(ALERT_LABELS).fillna(result["TIPO_ALERTA"])
    result["_ORDEM_RISCO"] = result["NIVEL_RISCO"].map(RISK_ORDER).fillna(9)

    return result.sort_values(["_ORDEM_RISCO", "DATA_FINAL", "PERCENTUAL_CONSUMO"], ascending=[True, True, False])


def _options(df: pd.DataFrame, column: str) -> list[str]:
    if df.empty or column not in df.columns:
        return ["Todos"]
    values = sorted(value for value in df[column].dropna().astype(str).unique() if value.strip())
    return ["Todos"] + values


def _filter_alertas(df: pd.DataFrame) -> pd.DataFrame:
    with st.expander("Filtros", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filial = select_filter("Filial", _options(df, "FILIAL_NOME"), key="alertas_filial")
            somente_alertas = st.checkbox("Somente contratos com alerta", value=True, key="alertas_somente")
        with col2:
            tipo_alerta = select_filter("Tipo de alerta", _options(df, "ALERTA"), key="alertas_tipo")
        with col3:
            nivel = select_filter("Nivel de risco", _options(df, "NIVEL_RISCO"), key="alertas_nivel")
        with col4:
            contrato = text_filter("Contrato", key="alertas_contrato", placeholder="Numero do contrato")

    result = df.copy()
    if somente_alertas and "TIPO_ALERTA" in result.columns:
        result = result[result["TIPO_ALERTA"].ne("SEM_ALERTA")]
    if filial != "Todos":
        result = result[result["FILIAL_NOME"].eq(filial)]
    if tipo_alerta != "Todos":
        result = result[result["ALERTA"].eq(tipo_alerta)]
    if nivel != "Todos":
        result = result[result["NIVEL_RISCO"].eq(nivel)]
    if contrato:
        result = result[result["CONTRATO"].astype(str).str.contains(str(contrato).strip(), case=False, na=False)]
    return result


def _alert_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["ALERTA", "QTD_CONTRATOS"])
    return (
        df.groupby("ALERTA", dropna=False)
        .size()
        .reset_index(name="QTD_CONTRATOS")
        .sort_values("QTD_CONTRATOS", ascending=False)
    )


def _branch_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["FILIAL_NOME", "QTD_ALERTAS"])
    return (
        df.groupby("FILIAL_NOME", dropna=False)
        .size()
        .reset_index(name="QTD_ALERTAS")
        .sort_values("QTD_ALERTAS", ascending=False)
        .head(10)
    )


def _display_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=ALERT_TABLE_COLUMNS)
    present = [column for column in ALERT_TABLE_COLUMNS if column in df.columns]
    result = df[present].copy()
    for column in ["DATA_INICIO", "DATA_FINAL"]:
        if column in result.columns:
            result[column] = result[column].apply(formatar_data)
    for column in ["VALOR_CONTRATO", "VALOR_MEDIDO", "SALDO_CONTRATO"]:
        if column in result.columns:
            result[column] = result[column].apply(formatar_moeda)
    if "PERCENTUAL_CONSUMO" in result.columns:
        result["PERCENTUAL_CONSUMO"] = result["PERCENTUAL_CONSUMO"].apply(formatar_percentual)
    return result


def _alert_card(title: str, color: str, items: list[str]) -> None:
    st.markdown(
        f"""
        <div style=\"border-left:6px solid {color};border:1px solid #E5E7EB;border-radius:10px;padding:12px 14px;margin-bottom:12px;background:#FFFFFF;\">
            <div style=\"font-weight:700;margin-bottom:8px;\">{title}</div>
            <div style=\"font-size:0.92rem;line-height:1.5;\">{'<br>'.join(items)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_alertas(
    df_contratos: Any = None,
    df_fornecedores: Any = None,
    df_medicoes: Any = None,
    df_financeiro: Any = None,
    df_itens: Any = None,
) -> None:
    st.header("Alertas")
    st.caption("Monitoramento dos contratos que precisam de atencao.")

    raw_alertas = _load_alertas()
    if raw_alertas.empty:
        st.warning("Nenhum contrato retornado pela consulta de alertas do Protheus.")
        if repository.LAST_ERROR:
            st.caption(f"Detalhe da consulta: {repository.LAST_ERROR}")
        return

    base = _normalize_alertas(raw_alertas)
    df = _filter_alertas(base)

    total_carteira = int(len(base))
    total_alertas = int(base["TIPO_ALERTA"].ne("SEM_ALERTA").sum())
    total_filtrado = int(len(df))
    valor_filtrado = float(df["VALOR_CONTRATO"].sum()) if not df.empty else 0.0
    saldo_filtrado = float(df["SALDO_CONTRATO"].sum()) if not df.empty else 0.0
    consumo_medio = float(df["PERCENTUAL_CONSUMO"].mean()) if not df.empty else 0.0

    cards = [
        {"title": "Contratos monitorados", "value": formatar_quantidade(total_carteira), "subtitle": "Contrato mais atual por filial"},
        {"title": "Com alerta", "value": formatar_quantidade(total_alertas), "subtitle": "Vencimento, paralisacao ou consumo"},
        {"title": "Exibidos", "value": formatar_quantidade(total_filtrado), "subtitle": "Carteira filtrada"},
        {"title": "Valor dos exibidos", "value": formatar_moeda(valor_filtrado), "subtitle": "Soma de VALOR_CONTRATO"},
        {"title": "Saldo dos exibidos", "value": formatar_moeda(saldo_filtrado), "subtitle": "Valor contrato menos medido"},
        {"title": "Consumo medio", "value": formatar_percentual(consumo_medio), "subtitle": "VALOR_MEDIDO / VALOR_CONTRATO"},
    ]
    render_kpi_cards(cards, columns=3)

    render_insights(
        get_alertas_insights(
            df,
            total_alertas,
            consumo_medio,
            percent_formatter=formatar_percentual,
            quantity_formatter=formatar_quantidade,
        )
    )

    st.markdown("### Nivel de risco")
    col1, col2, col3 = st.columns(3)
    with col1:
        _alert_card("Critico", "#DC2626", ["Contratos vencidos", "Contratos paralisados"])
    with col2:
        _alert_card("Atencao", "#D97706", ["Proximos do vencimento", "Consumo igual ou acima de 90%"])
    with col3:
        _alert_card("Normal", "#059669", ["Contratos sem alerta na regra atual"])

    if df.empty:
        st.warning("Nenhum contrato encontrado para os filtros selecionados.")
        return

    col1, col2 = st.columns(2)
    with col1:
        render_bar_chart(
            "Alertas por tipo",
            _alert_summary(df),
            x="QTD_CONTRATOS",
            y="ALERTA",
            orientation="h",
            empty_message="Sem alertas para exibir.",
        )
    with col2:
        render_bar_chart(
            "Filiais com mais alertas",
            _branch_summary(df),
            x="QTD_ALERTAS",
            y="FILIAL_NOME",
            orientation="h",
            empty_message="Sem filiais para exibir.",
        )

    render_table_section(
        title="Contratos que precisam de atencao",
        columns=ALERT_TABLE_COLUMNS,
        df=_display_table(df),
    )
