"""Fornecedores module."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.cards import render_insights, render_kpi_cards
from components.charts import render_bar_chart
from components.filters import select_filter, text_filter
from components.tables import render_table_section
from utils.contratos_repository import get_fornecedores
from utils.contratos_service import opcoes_coluna
from utils.formatters import formatar_moeda, formatar_percentual, formatar_quantidade
from utils.fornecedores_service import (
    aplicar_filtros_fornecedores,
    detalhe_fornecedor,
    ranking_fornecedores,
    resumo_fornecedores,
    top_fornecedores,
)
from utils.insights import get_fornecedores_insights


MONEY_COLUMNS = ["VALOR_CONTRATO", "VALOR_CONTRATADO", "SALDO_CONTRATO", "SALDO"]
PERCENT_COLUMNS = ["PARTICIPACAO"]


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


def _load_fornecedores(df_fornecedores: Any = None) -> pd.DataFrame:
    return get_fornecedores()


def _render_filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.expander("Filtros", expanded=True):
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            filial = select_filter("Filial", opcoes_coluna(df, "FILIAL_NOME"), key="fornecedores_filial")
        with col2:
            fornecedor = text_filter("Fornecedor", key="fornecedores_fornecedor", placeholder="Nome ou codigo")
        with col3:
            tipo = select_filter("Tipo contrato", opcoes_coluna(df, "TIPO"), key="fornecedores_tipo")
        with col4:
            situacao = select_filter("Situacao", opcoes_coluna(df, "STATUS"), key="fornecedores_status")
        with col5:
            contrato = text_filter("Contrato", key="fornecedores_contrato", placeholder="Numero")

    return aplicar_filtros_fornecedores(
        df,
        {
            "filial": filial,
            "fornecedor": fornecedor,
            "tipo": tipo,
            "situacao": situacao,
            "contrato": contrato,
        },
    )


def render_fornecedores(
    df_contratos: Any = None,
    df_fornecedores: Any = None,
    df_medicoes: Any = None,
    df_financeiro: Any = None,
    df_itens: Any = None,
) -> None:
    st.header("Fornecedores e Contratos")
    st.caption("Visao gerencial dos fornecedores vinculados aos contratos do Protheus.")

    base = _load_fornecedores(df_fornecedores)
    if base.empty:
        st.warning("Nenhum dado de fornecedores e contratos retornado pela consulta do Protheus.")
        return

    df = _render_filters(base)
    kpis = resumo_fornecedores(df)
    inconsistencias_fornecedor = int(kpis["inconsistencias_fornecedor"])

    cards = [
        {"title": "Quantidade total de fornecedores", "value": formatar_quantidade(kpis["total_fornecedores"]), "subtitle": "Fornecedores vinculados"},
        {"title": "Quantidade total de contratos", "value": formatar_quantidade(kpis["total_contratos"]), "subtitle": "Em sistema"},
        #{"title": "Valor total contratado", "value": formatar_moeda(kpis["valor_total_contratado"]), "subtitle": "Base tratada"},
        #{"title": "Saldo total contratado", "value": formatar_moeda(kpis["saldo_total_contratado"]), "subtitle": "Base tratada"},
        #{"title": "Ticket medio por fornecedor", "value": formatar_moeda(kpis["ticket_medio_fornecedor"]), "subtitle": "Valor total / fornecedores"},
        {
            "title": "Relacionamento fornecedor",
            "value": "OK" if inconsistencias_fornecedor == 0 else formatar_quantidade(inconsistencias_fornecedor),
            "subtitle": "Não existe contrato sem fornecedor vinculado" if inconsistencias_fornecedor == 0 else "Existem contratos sem fornecedor vinculado",
        },
    ]
    render_kpi_cards(cards, columns=3)

    render_insights(
        get_fornecedores_insights(
            df,
            kpis["classificacao_concentracao"],
            kpis["descricao_concentracao"],
            kpis["inconsistencias_fornecedor"],
            ranking=ranking_fornecedores(df, limit=1),
            percent_formatter=formatar_percentual,
            quantity_formatter=formatar_quantidade,
        )
    )

    col1, = st.columns(1)
    with col1:
        render_table_section(
            title="Concentracao de contratos por fornecedor",
            subtitle="Contratos agrupados por fornecedor e todos os tipos de situação, necessário aplicação de filtros para detalhamento caso necessário.",
            columns=["FORNECEDOR", "CNPJ_FORNECEDOR", "QTD_CONTRATOS", "VALOR_CONTRATADO", "PARTICIPACAO"],
            df=_format_table(ranking_fornecedores(df)[["FORNECEDOR", "CNPJ_FORNECEDOR", "QTD_CONTRATOS", "VALOR_CONTRATADO", "PARTICIPACAO"]]),
        )

    st.divider()

    st.subheader("Contratos")

    # Tabela detalhada de contratos com filtros locais.
    contratos_df = df.copy()

    filtro1, filtro2, filtro3 = st.columns(3)
    with filtro1:
        filtro_fornecedor = st.text_input(
            "Pesquisar fornecedor (nome ou código)",
            key="filtro_contrato_fornecedor",
            placeholder="Digite o nome ou código do fornecedor",
        )

    with filtro2:
        filtro_contrato = st.text_input(
            "Pesquisar contrato",
            key="filtro_contrato_numero",
            placeholder="Digite o número do contrato",
        )

    with filtro3:
        filtro_cnpj = st.text_input(
            "Pesquisar CNPJ do fornecedor",
            key="filtro_contrato_cnpj",
            placeholder="Digite o CNPJ do fornecedor",
        )

    if filtro_fornecedor:
        contratos_df = contratos_df[
            contratos_df["FORNECEDOR"]
            .fillna("")
            .str.contains(filtro_fornecedor, case=False, na=False)
        ]

    if filtro_contrato:
        contratos_df = contratos_df[
            contratos_df["CONTRATO"]
            .astype(str)
            .str.contains(filtro_contrato, case=False, na=False)
        ]

    if filtro_cnpj:
        contratos_df = contratos_df[
            contratos_df["CNPJ_FORNECEDOR"]
            .fillna("")
            .astype(str)
            .str.contains(filtro_cnpj, case=False, na=False)
        ]

    # Garante schema da tabela de contratos com base nas colunas reais da base.
    contratos_tabela = contratos_df.copy()
    if "VALOR_CONTRATADO" not in contratos_tabela.columns:
        contratos_tabela["VALOR_CONTRATADO"] = contratos_tabela.get("VALOR_CONTRATO", 0.0)
    if "SALDO" not in contratos_tabela.columns:
        contratos_tabela["SALDO"] = contratos_tabela.get("SALDO_CONTRATO", 0.0)
    if "PARTICIPACAO" not in contratos_tabela.columns:
        base_valor = pd.to_numeric(contratos_tabela.get("VALOR_CONTRATO", 0.0), errors="coerce").fillna(0.0)
        total_valor = float(base_valor.sum())
        contratos_tabela["PARTICIPACAO"] = (base_valor / total_valor * 100) if total_valor else 0.0

    table_columns = ["CONTRATO", "COD_FORNECEDOR", "CNPJ_FORNECEDOR", "FORNECEDOR", "VALOR_CONTRATADO", "SALDO", "PARTICIPACAO"]
    for column in table_columns:
        if column not in contratos_tabela.columns:
            contratos_tabela[column] = ""

    col2, = st.columns(1)
    with col2:
        render_table_section(
            title="Contratos",
            subtitle="Todos os contratos",
            columns=table_columns,
            df=_format_table(contratos_tabela[table_columns]),
        )