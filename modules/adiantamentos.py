"""Adiantamentos module."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.cards import render_insights, render_kpi_cards
from components.charts import render_bar_chart, render_line_chart
from components.filters import select_filter, text_filter
from components.tables import render_table_section
from config.settings import FILIAIS
from utils.adiantamentos_service import (
    aplicar_filtros_adiantamentos,
    comparativo_valor_saldo,
    detalhes_adiantamentos,
    evolucao_adiantamentos_mensal,
    get_adiantamentos_insights,
    ranking_adiantamentos,
    resumo_adiantamentos,
)
from utils.contratos_repository import get_adiantamentos
from utils.contratos_service import opcoes_coluna
from utils.formatters import formatar_data, formatar_moeda, formatar_percentual, formatar_quantidade


MONEY_COLUMNS = ["VALOR_ADIANTAMENTO", "SALDO_ADIANTAMENTO"]
DATE_COLUMNS = ["DATA_ADIANTAMENTO"]


def _opcoes_filial_exibicao(df: pd.DataFrame) -> tuple[list[str], dict[str, str]]:
    opcoes_filial = opcoes_coluna(df, "FILIAL")
    opcoes_exibicao = []
    filial_por_exibicao = {}

    for filial in opcoes_filial:
        if filial == "Todos":
            opcoes_exibicao.append(filial)
            filial_por_exibicao[filial] = filial
            continue

        exibicao = FILIAIS.get(str(filial).strip(), filial)
        opcoes_exibicao.append(exibicao)
        filial_por_exibicao[exibicao] = filial

    return opcoes_exibicao, filial_por_exibicao


def _render_filters(df: pd.DataFrame) -> pd.DataFrame:
    opcoes_filial, filial_por_exibicao = _opcoes_filial_exibicao(df)

    with st.expander("Filtros", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            filial_exibicao = select_filter("Filial", opcoes_filial, key="adiantamentos_filial")
            contrato = text_filter("Contrato", key="adiantamentos_contrato", placeholder="Numero do contrato")
        with col2:
            tipo = select_filter("Tipo contrato", opcoes_coluna(df, "TIPO"), key="adiantamentos_tipo")
            fornecedor = text_filter("Fornecedor", key="adiantamentos_fornecedor", placeholder="Nome, codigo ou loja")
        with col3:
            situacao = select_filter("Situacao", opcoes_coluna(df, "STATUS"), key="adiantamentos_status")
            adiantamento = text_filter("Adiantamento", key="adiantamentos_numero", placeholder="Numero")

    return aplicar_filtros_adiantamentos(
        df,
        {
            "filial": filial_por_exibicao.get(filial_exibicao, filial_exibicao),
            "tipo": tipo,
            "situacao": situacao,
            "contrato": contrato,
            "fornecedor": fornecedor,
            "adiantamento": adiantamento,
        },
    )


def _format_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()
    for column in MONEY_COLUMNS:
        if column in result.columns:
            result[column] = result[column].apply(formatar_moeda)
    for column in DATE_COLUMNS:
        if column in result.columns:
            result[column] = result[column].apply(formatar_data)
    return result


def render_adiantamentos(
    df_contratos: Any = None,
    df_fornecedores: Any = None,
    df_medicoes: Any = None,
    df_financeiro: Any = None,
    df_itens: Any = None,
) -> None:
    st.header("Adiantamentos")
    st.caption("Analise dos adiantamentos de contratos registrados na CNX010.")

    base = get_adiantamentos()
    if base.empty:
        st.warning("Nenhum adiantamento retornado pela consulta do Protheus.")
        return

    df = _render_filters(base)
    kpis = resumo_adiantamentos(df, df_contratos)

    cards = [
        {"title": "Valor Total Adiantado", "value": formatar_moeda(kpis["valor_total_adiantado"]), "subtitle": "Valor total adiantado em contratos"},
        #{"title": "Saldo Total dos Adiantamentos", "value": formatar_moeda(kpis["saldo_total_adiantamentos"]), "subtitle": "CNX_SALDO"},
        #{"title": "Quantidade de Adiantamentos", "value": formatar_quantidade(kpis["qtd_adiantamentos"]), "subtitle": "CNX_NUMERO"},
        {"title": "Contratos com Adiantamento", "value": formatar_quantidade(kpis["qtd_contratos_adiantamento"]), "subtitle": "Quantidade de contratos com adiantamento"},
        {"title": "Ticket Medio dos Adiantamentos", "value": formatar_moeda(kpis["ticket_medio_adiantamentos"]), "subtitle": "Valor medio dos adiantamentos"},
    ]
    render_kpi_cards(cards, columns=5)

    render_insights(get_adiantamentos_insights(df, kpis, money_formatter=formatar_moeda, percent_formatter=formatar_percentual))

    if df.empty:
        st.warning("Nenhum adiantamento encontrado para os filtros selecionados.")
        return

    col1, col2 = st.columns(2)
    with col1:
        render_line_chart(
            "Evolucao dos Adiantamentos por mes",
            evolucao_adiantamentos_mensal(df),
            x="MES_ADIANTAMENTO",
            y="VALOR_ADIANTAMENTO",
            empty_message="Sem meses de adiantamento para exibir.",
        )
    with col2:
        render_bar_chart(
            "Top Fornecedores por Valor Adiantado",
            ranking_adiantamentos(df, "FORNECEDOR"),
            x="VALOR_ADIANTAMENTO",
            y="FORNECEDOR",
            orientation="h",
            empty_message="Sem fornecedores para exibir.",
        )
     
    render_table_section(
        title="Detalhamento dos adiantamentos",
        columns=[
            "FILIAL",
            "CONTRATO",
            "FORNECEDOR",
            "CNPJ_FORNECEDOR",
            "NUMERO_ADIANTAMENTO",
            "DATA_ADIANTAMENTO",
            "VALOR_ADIANTAMENTO",
            "SALDO_ADIANTAMENTO",
            "STATUS",
            "TIPO",
        ],
        df=_format_table(detalhes_adiantamentos(df)),
    )