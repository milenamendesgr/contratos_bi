"""Financeiro module."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.cards import render_insights, render_kpi_cards, render_section_header
from components.charts import render_bar_chart, render_line_chart
from components.filters import select_filter, text_filter
from components.tables import render_table_section
from utils.contratos_repository import get_financeiro, get_fluxo_financeiro
from utils.contratos_service import opcoes_coluna
from utils.financeiro_service import (
    aplicar_filtros_fluxo_financeiro,
    aplicar_filtros_financeiro,
    comparativo_previsto_realizado,
    detalhes_fluxo_financeiro,
    distribuicao_por_situacao,
    evolucao_fluxo_mensal,
    fluxo_futuro_desembolso,
    ranking_adiantamentos,
    ranking_atrasos,
    ranking_competencias_previsto,
    ranking_saldo_financeiro,
    resumo_fluxo_financeiro,
    resumo_financeiro,
)
from utils.formatters import formatar_data, formatar_moeda, formatar_percentual, formatar_quantidade
from utils.insights import get_financeiro_insights, get_fluxo_financeiro_insights
from config.settings import FILIAIS

MONEY_COLUMNS = [
    "VALOR_CONTRATO",
    "VALOR_PREVISTO",
    "VALOR_REALIZADO",
    "SALDO_FINANCEIRO",
    "VALOR_ADIANTADO",
    "SALDO_ADIANTAMENTO",
]
PERCENT_COLUMNS = ["PERCENTUAL_REALIZADO"]
DATE_COLUMNS = ["DATA_VENCIMENTO"]

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
    for column in DATE_COLUMNS:
        if column in result.columns:
            result[column] = result[column].apply(formatar_data)
    return result


def _load_financeiro(df_financeiro: Any = None) -> pd.DataFrame:
    return get_financeiro()


def _load_fluxo_financeiro() -> pd.DataFrame:
    return get_fluxo_financeiro()


def _render_filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.expander("Filtros", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filial = select_filter("Filial", opcoes_coluna(df, "FILIAL"), key="financeiro_filial")
        with col2:
            tipo = select_filter("Tipo contrato", opcoes_coluna(df, "TIPO"), key="financeiro_tipo")
        with col3:
            situacao = select_filter("Situacao", opcoes_coluna(df, "STATUS"), key="financeiro_status")
        with col4:
            contrato = text_filter("Contrato", key="financeiro_contrato", placeholder="Numero do contrato")

    return aplicar_filtros_financeiro(
        df,
        {
            "filial": filial,
            "tipo": tipo,
            "situacao": situacao,
            "contrato": contrato,
        },
    )


def _render_fluxo_filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.expander("Filtros do Fluxo Financeiro", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filial = select_filter("Filial", opcoes_coluna(df, "FILIAL"), key="fluxo_financeiro_filial")
        with col2:
            tipo = select_filter("Tipo contrato", opcoes_coluna(df, "TIPO"), key="fluxo_financeiro_tipo")
        with col3:
            competencia = select_filter("Competencia", opcoes_coluna(df, "COMPETENCIA"), key="fluxo_financeiro_competencia")
        with col4:
            contrato = text_filter("Contrato", key="fluxo_financeiro_contrato", placeholder="Numero do contrato")
        datas_validas = df["DATA_VENCIMENTO"].dropna() if "DATA_VENCIMENTO" in df.columns else pd.Series(dtype="datetime64[ns]")
        data_inicio_padrao = datas_validas.min().date() if not datas_validas.empty else None
        data_fim_padrao = datas_validas.max().date() if not datas_validas.empty else None
        col5, col6 = st.columns(2)
        with col5:
            data_inicio = st.date_input("Data inicio", value=data_inicio_padrao, key="fluxo_financeiro_dt_inicio")
        with col6:
            data_fim = st.date_input("Data fim", value=data_fim_padrao, key="fluxo_financeiro_dt_fim")

    return aplicar_filtros_fluxo_financeiro(
        df,
        {
            "filial": filial,
            "tipo": tipo,
            "competencia": competencia,
            "contrato": contrato,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
    )


def _render_visao_financeira(df_financeiro: Any = None) -> None:
    base = _load_financeiro(df_financeiro)
    if base.empty:
        st.warning("Nenhum dado financeiro retornado pela consulta do Protheus.")
        return

    df = _render_filters(base)
    kpis = resumo_financeiro(df)

    cards = [
        {"title": "Valor total contratado", "value": formatar_moeda(kpis["valor_total_contratado"]), "subtitle": "Base tratada"},
        {"title": "Valor previsto", "value": formatar_moeda(kpis["valor_previsto"]), "subtitle": "Valor previsto para pagamento"},
        {"title": "Valor realizado", "value": formatar_moeda(kpis["valor_realizado"]), "subtitle": "Valor realizado de pagamento"},
        {"title": "Saldo financeiro", "value": formatar_moeda(kpis["saldo_financeiro"]), "subtitle": "Previsto menos realizado"},
        {"title": "Percentual realizado", "value": formatar_percentual(kpis["percentual_realizado"]), "subtitle": "Realizado sobre previsto"},
        {"title": "Quantidade de parcelas", "value": formatar_quantidade(kpis["qtd_parcelas"]), "subtitle": "Parcelas financeiras"},
        {"title": "Parcelas pagas com atraso", "value": formatar_quantidade(kpis["parcelas_atrasadas"]), "subtitle": "Vencimento anterior a data de pagamento"},
        {"title": "Valor total adiantado", "value": formatar_moeda(kpis["valor_total_adiantado"]), "subtitle": "Valor total adiantado"},
        {"title": "Saldo de adiantamentos", "value": formatar_moeda(kpis["saldo_adiantamentos"]), "subtitle": "Saldo de adiantamentos"},
    ]
    render_kpi_cards(cards, columns=3)

    render_insights(get_financeiro_insights(df, money_formatter=formatar_moeda, percent_formatter=formatar_percentual))

    if df.empty:
        st.warning("Nenhum contrato encontrado para os filtros selecionados.")
        return

    col1, col2 = st.columns(2)
    with col1:
        render_bar_chart(
            "Comparativo previsto x realizado",
            comparativo_previsto_realizado(df),
            x="INDICADOR",
            y="VALOR",
            empty_message="Sem valores previstos ou realizados para exibir.",
        )
    with col2:
        render_bar_chart(
            "Distribuicao financeira por situacao",
            distribuicao_por_situacao(df),
            x="STATUS",
            y="SALDO_FINANCEIRO",
            empty_message="Sem situacoes de contrato para exibir.",
        )

    col3, col4 = st.columns(2)
    with col3:
        df_ranking_saldo = ranking_saldo_financeiro(df)
        render_section_header("Ranking de contratos por saldo financeiro", "Detalhamento disponivel para conferencia e exportacao.")
        filtro_saldo = st.text_input("Contrato", key="filtro_ranking_saldo_contrato", placeholder="Número do contrato", label_visibility="collapsed")
        if filtro_saldo:
            df_ranking_saldo = df_ranking_saldo[df_ranking_saldo["CONTRATO"].astype(str).str.contains(filtro_saldo, case=False, na=False)]
        st.caption(f"{len(df_ranking_saldo)} registro(s) exibido(s).")
        st.dataframe(_format_table(df_ranking_saldo), use_container_width=True, hide_index=True, height=420)
    with col4:
        df_ranking_atrasos = ranking_atrasos(df)
        render_section_header("Contratos com mais parcelas pagas com atraso", "Detalhamento disponivel para conferencia e exportacao.")
        filtro_atraso = st.text_input("Contrato", key="filtro_ranking_atraso_contrato", placeholder="Número do contrato", label_visibility="collapsed")
        if filtro_atraso:
            df_ranking_atrasos = df_ranking_atrasos[df_ranking_atrasos["CONTRATO"].astype(str).str.contains(filtro_atraso, case=False, na=False)]
        st.caption(f"{len(df_ranking_atrasos)} registro(s) exibido(s).")
        st.dataframe(_format_table(df_ranking_atrasos), use_container_width=True, hide_index=True, height=420)

    df_classificacao = df[
        [
            "CONTRATO",
            "FORNECEDOR",
            "CNPJ_FORNECEDOR",
            "TIPO",
            "STATUS",
            "PERCENTUAL_REALIZADO",
            "SALDO_FINANCEIRO",
            "CLASSIFICACAO_FINANCEIRA",
        ]
    ]
    render_section_header("Classificacao financeira dos contratos", "Detalhamento disponivel para conferencia e exportacao.")
    filtro_classificacao = st.text_input("Contrato", key="filtro_classificacao_contrato", placeholder="Número do contrato", label_visibility="collapsed")
    if filtro_classificacao:
        df_classificacao = df_classificacao[df_classificacao["CONTRATO"].astype(str).str.contains(filtro_classificacao, case=False, na=False)]
    st.caption(f"{len(df_classificacao)} registro(s) exibido(s).")
    st.dataframe(_format_table(df_classificacao), use_container_width=True, hide_index=True, height=420)


def _render_fluxo_financeiro() -> None:
    st.subheader("Fluxo Financeiro")
    st.caption("Visao temporal dos compromissos financeiros, desembolsos e vencimentos dos contratos.")

    base = _load_fluxo_financeiro()
    if base.empty:
        st.warning("Nenhum dado de fluxo financeiro retornado pela consulta do Protheus.")
        return

    df = _render_fluxo_filters(base)
    kpis = resumo_fluxo_financeiro(df)
    proximo_vencimento = formatar_data(kpis["proximo_vencimento"]) if kpis["proximo_vencimento"] is not None else "--"

    cards = [
        {"title": "Total previsto", "value": formatar_moeda(kpis["total_previsto"]), "subtitle": "Compromissos filtrados"},
        {"title": "Total realizado", "value": formatar_moeda(kpis["total_realizado"]), "subtitle": "Pagamentos realizados"},
        {"title": "Saldo financeiro", "value": formatar_moeda(kpis["saldo_financeiro"]), "subtitle": "Previsto menos realizado"},
        {"title": "Quantidade de parcelas", "value": formatar_quantidade(kpis["qtd_parcelas"]), "subtitle": "Linhas do fluxo"},
        {"title": "Proximo vencimento", "value": proximo_vencimento, "subtitle": "Menor vencimento futuro"},
        {"title": "Previsto proximos 30 dias", "value": formatar_moeda(kpis["valor_previsto_30_dias"]), "subtitle": "Vencimentos ate 30 dias"},
    ]
    render_kpi_cards(cards, columns=3)

    render_insights(get_fluxo_financeiro_insights(df, money_formatter=formatar_moeda, date_formatter=formatar_data))

    if df.empty:
        st.warning("Nenhuma parcela encontrada para os filtros selecionados.")
        return

    col1, col2 = st.columns(2)
    with col1:
        render_line_chart(
            "Evolucao financeira mensal",
            evolucao_fluxo_mensal(df),
            x="COMPETENCIA",
            y=["VALOR_PREVISTO", "VALOR_REALIZADO"],
            empty_message="Sem competencias para exibir na evolucao financeira.",
        )
    with col2:
        render_bar_chart(
            "Fluxo futuro de desembolso",
            fluxo_futuro_desembolso(df),
            x="COMPETENCIA",
            y="SALDO_FINANCEIRO",
            empty_message="Sem saldo financeiro futuro para exibir.",
        )


def render_financeiro(
    df_contratos: Any = None,
    df_fornecedores: Any = None,
    df_medicoes: Any = None,
    df_financeiro: Any = None,
    df_itens: Any = None,
) -> None:
    st.header("Financeiro")
    st.caption("Acompanhamento financeiro dos contratos, pagamentos realizados, saldos e adiantamentos.")

    _render_visao_financeira(df_financeiro)
