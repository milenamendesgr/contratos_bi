"""Vigencia e prazos module."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.cards import render_kpi_cards
from components.charts import render_bar_chart
from components.filters import select_filter
from components.tables import render_table_section
from utils.contratos_service import aplicar_filtros_carteira, opcoes_coluna
from utils.formatters import formatar_data, formatar_quantidade


RISK_COLUMNS = [
    "CONTRATO",
    "FORNECEDOR",
    "CNPJ_FORNECEDOR",
    "FILIAL_NOME",
    "TIPO",
    "STATUS",
    "DATA_INICIO",
    "DATA_FIM",
    "DIAS_RESTANTES",
    "CLASSIFICACAO_PRAZO",
]

CRITICAL_DEADLINE_COLUMNS = [
    "CONTRATO",
    "FORNECEDOR",
    "FILIAL_NOME",
    "STATUS",
    "DATA_FIM",
    "DIAS_RESTANTES",
    "CLASSIFICACAO_PRAZO",
]


def _classificar_prazo(dias_restantes: Any) -> str:
    if pd.isna(dias_restantes):
        return "Sem data"
    dias = int(dias_restantes)
    if dias <= 30:
        return "Critico"
    if dias <= 90:
        return "Atencao"
    return "Normal"


def _preparar_vigencia(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if "DATA_FIM" in result.columns:
        result["DATA_FIM"] = pd.to_datetime(result["DATA_FIM"], errors="coerce")
        hoje = pd.Timestamp.now().normalize()
        result["DIAS_RESTANTES"] = (result["DATA_FIM"] - hoje).dt.days
    elif "DIAS_RESTANTES" not in result.columns:
        result["DIAS_RESTANTES"] = pd.NA

    result["CLASSIFICACAO_PRAZO"] = result["DIAS_RESTANTES"].apply(_classificar_prazo)
    return result


def _period_bounds(periodo: Any) -> tuple[Any, Any]:
    if isinstance(periodo, tuple) and len(periodo) == 2:
        return periodo[0], periodo[1]
    if isinstance(periodo, list) and len(periodo) == 2:
        return periodo[0], periodo[1]
    return None, None


def _filtrar_periodo_vencimento(df: pd.DataFrame, data_inicio: Any, data_fim: Any) -> pd.DataFrame:
    if df.empty or "DATA_FIM" not in df.columns:
        return df

    result = df.copy()
    if data_inicio:
        result = result[result["DATA_FIM"] >= pd.Timestamp(data_inicio)]
    if data_fim:
        result = result[result["DATA_FIM"] <= pd.Timestamp(data_fim)]
    return result


def _contar_ativos(df: pd.DataFrame) -> int:
    if df.empty:
        return 0

    if "SITUACAO" not in df.columns:
        return 0

    return int(df["SITUACAO"].fillna("").astype(str).str.strip().eq("05").sum())


def _distribuicao_situacao(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "CLASSIFICACAO_PRAZO" not in df.columns:
        return pd.DataFrame(columns=["CLASSIFICACAO_PRAZO", "QTD_CONTRATOS"])

    return (
        df.groupby("CLASSIFICACAO_PRAZO", dropna=False)
        .size()
        .reset_index(name="QTD_CONTRATOS")
        .sort_values("QTD_CONTRATOS", ascending=False)
    )


def _risk_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=RISK_COLUMNS)
    present = [column for column in RISK_COLUMNS if column in df.columns]
    if "DIAS_RESTANTES" in df.columns:
        result = df.sort_values("DIAS_RESTANTES", na_position="last")[present].copy()
    else:
        result = df[present].copy()
    if "DATA_INICIO" in result.columns:
        result["DATA_INICIO"] = result["DATA_INICIO"].apply(formatar_data)
    if "DATA_FIM" in result.columns:
        result["DATA_FIM"] = result["DATA_FIM"].apply(formatar_data)
    if "DIAS_RESTANTES" in result.columns:
        result["DIAS_RESTANTES"] = result["DIAS_RESTANTES"].apply(formatar_quantidade)
    return result


def _upcoming_deadlines(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    base = df.copy()
    if "DIAS_RESTANTES" in base.columns:
        dias_restantes = pd.to_numeric(base["DIAS_RESTANTES"], errors="coerce")
        base = base[dias_restantes.ge(0).fillna(False)]
    elif "DATA_FIM" in base.columns:
        hoje = pd.Timestamp.now().normalize()
        data_fim = pd.to_datetime(base["DATA_FIM"], errors="coerce")
        base = base[data_fim.ge(hoje).fillna(False)]
    return base


def _critical_deadlines_table(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=CRITICAL_DEADLINE_COLUMNS)

    base = _upcoming_deadlines(df)

    if base.empty:
        return pd.DataFrame(columns=CRITICAL_DEADLINE_COLUMNS)

    risk_table = _risk_table(base)
    present = [column for column in CRITICAL_DEADLINE_COLUMNS if column in risk_table.columns]
    return risk_table[present].head(limit)


def render_vigencia_prazos(
    df_contratos: Any = None,
    df_fornecedores: Any = None,
    df_medicoes: Any = None,
    df_financeiro: Any = None,
    df_itens: Any = None,
) -> None:
    st.header("Vigencia e Prazos")
    st.caption("Monitoramento de vencimentos e risco de prazo de todos os contratos.")

    if df_contratos is None or getattr(df_contratos, "empty", True):
        st.warning("Nenhum contrato retornado pela consulta do Protheus.")
        return

    base = _preparar_vigencia(df_contratos)

    with st.expander("Filtros", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filial = select_filter("Filial", options=opcoes_coluna(base, "FILIAL_NOME"), key="vigencia_filial")
        with col2:
            tipo = select_filter("Tipo contrato", options=opcoes_coluna(base, "TIPO"), key="vigencia_tipo")
        with col3:
            situacao = select_filter("Situacao", options=opcoes_coluna(base, "STATUS"), key="vigencia_status")
        with col4:
            periodo = st.date_input("Periodo de vencimento", value=[], key="vigencia_periodo")

    data_inicio, data_fim = _period_bounds(periodo)

    df = aplicar_filtros_carteira(
        base,
        {
            "filial": filial,
            "tipo": tipo,
            "situacao": situacao,
        },
    )
    df = _filtrar_periodo_vencimento(df, data_inicio, data_fim)

    vencidos = int((df["DIAS_RESTANTES"] < 0).sum()) if "DIAS_RESTANTES" in df.columns else 0
    vencendo_30 = int(df["DIAS_RESTANTES"].between(0, 30).sum()) if "DIAS_RESTANTES" in df.columns else 0
    vencendo_90 = int(df["DIAS_RESTANTES"].between(0, 90).sum()) if "DIAS_RESTANTES" in df.columns else 0
    total_contratos = int(len(df))
    ativos = _contar_ativos(df)

    cards = [
        {"title": "Total de contratos", "value": formatar_quantidade(total_contratos), "subtitle": "Carteira filtrada"},
        {"title": "Contratos ativos", "value": formatar_quantidade(ativos), "subtitle": "Dentro da vigencia"},
        {"title": "Contratos vencidos", "value": formatar_quantidade(vencidos), "subtitle": "Contratos vencidos independente do status"},
        {"title": "Vencendo em 30 dias", "value": formatar_quantidade(vencendo_30), "subtitle": "Prazo critico"},
        {"title": "Vencendo em 90 dias", "value": formatar_quantidade(vencendo_90), "subtitle": "Janela de risco"},
    ]
    render_kpi_cards(cards, columns=5)

    if df.empty:
        st.warning("Nenhum contrato encontrado para os filtros selecionados.")
        return

    col1, col2 = st.columns(2)
    with col1:
        render_table_section(
            title="Proximos vencimentos criticos",
            columns=CRITICAL_DEADLINE_COLUMNS,
            df=_critical_deadlines_table(df),
            empty_message="Sem vencimentos criticos para exibir.",
            height=340,
            download=False,
        )
    with col2:
        render_bar_chart(
            "Distribuicao por situacao de prazo",
            _distribuicao_situacao(df),
            x="QTD_CONTRATOS",
            y="CLASSIFICACAO_PRAZO",
            orientation="h",
            empty_message="Sem situacoes para exibir.",
        )

    render_table_section(
        title="Ranking dos contratos mais proximos do vencimento",
        columns=RISK_COLUMNS,
        df=_risk_table(_upcoming_deadlines(df)),
    )
