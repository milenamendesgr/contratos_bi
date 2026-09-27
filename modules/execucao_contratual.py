"""Execucao contratual module."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.cards import render_insights, render_kpi_cards
from components.charts import render_bar_chart
from components.filters import select_filter, text_filter
from components.tables import render_table_section
from utils.contratos_repository import get_execucao_contratual
from utils.contratos_service import opcoes_coluna
from utils.execucao_contratual_service import (
    aplicar_filtros_execucao,
    distribuicao_execucao,
    ranking_execucao,
    resumo_execucao,
    volume_medicoes,
)
from utils.formatters import formatar_moeda, formatar_percentual, formatar_quantidade
from utils.insights import get_execucao_insights


MONEY_COLUMNS = ["VALOR_ATUAL", "VALOR_MEDIDO", "VALOR_LIQUIDADO", "SALDO_EXECUCAO", "VALOR_MULTA"]
PERCENT_COLUMNS = ["PERCENTUAL_EXECUCAO", "PERCENTUAL_SALDO"]


def _format_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()
    for column in MONEY_COLUMNS:
        if column in result.columns:
            result[column] = result[column].apply(formatar_moeda)
    for column in PERCENT_COLUMNS:
        if column in result.columns:
            result[column] = result[column].apply(formatar_percentual)
    return result


def _load_execucao(df_medicoes: Any = None) -> pd.DataFrame:
    return get_execucao_contratual()


def _render_filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.expander("Filtros", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filial = select_filter("Filial", opcoes_coluna(df, "FILIAL"), key="execucao_filial")
        with col2:
            tipo = select_filter("Tipo de contrato", opcoes_coluna(df, "TIPO"), key="execucao_tipo")
        with col3:
            situacao = select_filter("Situacao", opcoes_coluna(df, "STATUS"), key="execucao_status")
        with col4:
            contrato = text_filter("Contrato", key="execucao_contrato", placeholder="Numero do contrato")

    return aplicar_filtros_execucao(
        df,
        {
            "filial": filial,
            "tipo": tipo,
            "situacao": situacao,
            "contrato": contrato,
        },
    )


def render_execucao_contratual(
    df_contratos: Any = None,
    df_fornecedores: Any = None,
    df_medicoes: Any = None,
    df_financeiro: Any = None,
    df_itens: Any = None,
) -> None:
    st.header("Execucao Contratual")
    st.caption("Acompanhamento operacional e gerencial da execucao real dos contratos.")

    base = _load_execucao(df_medicoes)
    if base.empty:
        st.warning("Nenhum dado de execucao contratual retornado pela consulta do Protheus.")
        return

    df = _render_filters(base)
    kpis = resumo_execucao(df)

    cards = [
        {"title": "Quantidade total de contratos", "value": formatar_quantidade(kpis["total_contratos"]), "subtitle": "Carteira filtrada"},
        {"title": "Valor total atualizado", "value": formatar_moeda(kpis["valor_total_atualizado"]), "subtitle": "Base tratada"},
        {"title": "Valor total medido", "value": formatar_moeda(kpis["valor_total_medido"]), "subtitle": "Necessario validação"},
        {"title": "Valor total liquidado", "value": formatar_moeda(kpis["valor_total_liquidado"]), "subtitle": "Necessario validação"},
        {"title": "Saldo total de execucao", "value": formatar_moeda(kpis["saldo_total_execucao"]), "subtitle": "Valor atual menos medido"},
        {"title": "Percentual medio de execucao", "value": formatar_percentual(kpis["percentual_medio_execucao"]), "subtitle": "Media dos contratos"},
        {"title": "Quantidade total de medicoes", "value": formatar_quantidade(kpis["qtd_total_medicoes"]), "subtitle": "NÃO COLOCAR DISTINTO"},
        #{"title": "Valor total de multas", "value": formatar_moeda(kpis["valor_total_multas"]), "subtitle": "CNE_MULTA"},
    ]
    render_kpi_cards(cards, columns=4)

    render_insights(get_execucao_insights(df, money_formatter=formatar_moeda, percent_formatter=formatar_percentual))

    if df.empty:
        st.warning("Nenhum contrato encontrado para os filtros selecionados.")
        return

    col1, col2 = st.columns(2)
    with col1:
        render_table_section(
            title="Ranking de contratos",
            columns=["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO", "STATUS", "VALOR_ATUAL", "VALOR_MEDIDO", "SALDO_EXECUCAO", "PERCENTUAL_EXECUCAO"],
            df=_format_table(ranking_execucao(df, sort_column="VALOR_ATUAL")),
        )
    with col2:
        render_bar_chart(
            "Distribuicao da execucao",
            distribuicao_execucao(df),
            x="FAIXA_EXECUCAO",
            y="QTD_CONTRATOS",
            empty_message="Sem faixas de execucao para exibir.",
        )

    col3, col4 = st.columns(2)
    with col3:
        render_table_section(
            title="Contratos com maior saldo",
            columns=["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO", "STATUS", "VALOR_ATUAL", "VALOR_MEDIDO", "SALDO_EXECUCAO", "PERCENTUAL_EXECUCAO"],
            df=_format_table(ranking_execucao(df, sort_column="SALDO_EXECUCAO")),
        )
    with col4:
        render_table_section(
            title="Contratos com maior valor executado",
            columns=["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO", "STATUS", "VALOR_ATUAL", "VALOR_MEDIDO", "SALDO_EXECUCAO", "PERCENTUAL_EXECUCAO"],
            df=_format_table(ranking_execucao(df, sort_column="VALOR_MEDIDO")),
        )

    col5 = st.columns(1)
    with col5[0]:
        render_table_section(
            title="Classificacao da execucao",
            columns=["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO", "STATUS", "PERCENTUAL_EXECUCAO", "PERCENTUAL_SALDO", "CLASSIFICACAO_EXECUCAO"],
            df=_format_table(df[["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO", "STATUS", "PERCENTUAL_EXECUCAO", "PERCENTUAL_SALDO", "CLASSIFICACAO_EXECUCAO"]]),
        )
