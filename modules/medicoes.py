"""Medicoes module."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.cards import render_insights, render_kpi_cards
from components.charts import render_bar_chart, render_line_chart, render_pie_chart
from components.filters import select_filter, text_filter
from components.tables import render_table_section
from modules.comentarios import render_comentarios
from utils.contratos_repository import get_carteira_contratos, get_medicoes, get_medicoes_itens_detalhe
from utils.contratos_service import opcoes_coluna
from utils.formatters import formatar_data, formatar_moeda, formatar_percentual, formatar_quantidade
from utils.insights import get_medicoes_insights
from utils.medicoes_service import (
    aplicar_filtros_medicoes,
    comparativo_previsto_realizado,
    contratos_sem_medicao,
    evolucao_medicoes,
    faixas_medicoes,
    indicadores_contratos,
    medicoes_com_divergencia,
    medicoes_por_competencia,
    medicoes_por_fornecedor,
    medicoes_por_status,
    preparar_medicoes,
    ranking_competencias,
    ranking_contratos,
    ranking_fornecedores,
    resumo_medicoes,
    top10_contratos,
    top10_fornecedores,
)


MONEY_COLUMNS = [
    "VALOR_PREVISTO",
    "VALOR_TOTAL_MEDICAO",
    "VALOR_LIQUIDO",
    "VALOR_ADIANTAMENTO",
    "VALOR_CAUCAO",
    "VALOR_MULTAS",
    "VALOR_BONIFICACOES",
    "SALDO_MEDICAO",
    "VALOR_ATUAL",
    "VALOR_CONTRATADO",
    "TOTAL_ITENS",
    "TOTAL_LIQUIDO_ITENS",
    "TOTAL_MULTAS_ITENS",
    "TOTAL_BONIFICACOES_ITENS",
    "VALOR_TOTAL_ITEM",
    "VALOR_LIQUIDO_ITEM",
    "VALOR_MULTA_ITEM",
    "VALOR_BONIFICACAO_ITEM",
    "VALOR",
]
PERCENT_COLUMNS = ["PERCENTUAL"]
DATE_COLUMNS = ["DATA_INICIO", "DATA_FIM", "DATA_ENCERRAMENTO", "DATA_VENCIMENTO"]
QUANTITY_COLUMNS = [
    "QTD_ITENS",
    "QTD_PRODUTOS_DISTINTOS",
    "QTD_SOLICITADA",
    "QTD_MEDIDA",
    "QTD_MEDICOES",
    "QTD_CONTRATOS",
    "QTD_SOLICITADA_ITEM",
    "QTD_MEDIDA_ITEM",
]

ITEM_TEXT_COLUMNS = ["FILIAL", "CONTRATO", "REVISAO_CONTRATO", "NUMERO_MEDICAO", "ITEM", "PRODUTO"]
ITEM_NUMERIC_COLUMNS = [
    "QTD_SOLICITADA_ITEM",
    "QTD_MEDIDA_ITEM",
    "VALOR_TOTAL_ITEM",
    "VALOR_LIQUIDO_ITEM",
    "VALOR_MULTA_ITEM",
    "VALOR_BONIFICACAO_ITEM",
]


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
    for column in QUANTITY_COLUMNS:
        if column in result.columns:
            result[column] = result[column].apply(formatar_quantidade)
    return result


def _load_medicoes(df_medicoes: Any = None) -> pd.DataFrame:
    if df_medicoes is not None and not (hasattr(df_medicoes, "empty") and df_medicoes.empty):
        return preparar_medicoes(df_medicoes)
    return get_medicoes()


def _to_number(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0.0)
    normalized = (
        series.astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
        .replace({"": "0", "nan": "0", "None": "0", "NaT": "0"})
    )
    return pd.to_numeric(normalized, errors="coerce").fillna(0.0)


def _prepare_medicoes_itens(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()
    result.columns = [str(column).strip().upper() for column in result.columns]
    required_columns = {"FILIAL", "CONTRATO", "REVISAO_CONTRATO", "NUMERO_MEDICAO"}
    if not required_columns.issubset(set(result.columns)):
        return pd.DataFrame()

    for column in ITEM_TEXT_COLUMNS:
        if column not in result.columns:
            result[column] = ""
        result[column] = result[column].fillna("").astype(str).str.strip()
    for column in ITEM_NUMERIC_COLUMNS:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = _to_number(result[column])

    result["MEDICAO_CHAVE"] = (
        result["FILIAL"] + " | " + result["CONTRATO"] + " | " + result["REVISAO_CONTRATO"] + " | " + result["NUMERO_MEDICAO"]
    )
    return result.reset_index(drop=True)


def _load_medicoes_itens(df_itens: Any = None) -> pd.DataFrame:
    itens_contexto = _prepare_medicoes_itens(df_itens if isinstance(df_itens, pd.DataFrame) else None)
    if not itens_contexto.empty:
        return itens_contexto
    return _prepare_medicoes_itens(get_medicoes_itens_detalhe())


def _load_contratos() -> pd.DataFrame:
    return get_carteira_contratos()


def _resumo_contratos_medicoes(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "CONTRATO_CHAVE",
        "FILIAL",
        "CONTRATO",
        "FORNECEDOR",
        "TIPO",
        "SITUACAO_CONTRATO",
        "VALOR_CONTRATADO",
        "QTD_MEDICOES",
        "PRIMEIRA_COMPETENCIA",
        "ULTIMA_COMPETENCIA",
        "VALOR_TOTAL_MEDICAO",
        "VALOR_LIQUIDO",
        "STATUS",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)

    ordered = df.sort_values(["CONTRATO_CHAVE", "COMPETENCIA_ORDEM", "NUMERO_MEDICAO"]).copy()
    if "VALOR_ATUAL" not in ordered.columns:
        ordered["VALOR_ATUAL"] = 0.0
    if "SITUACAO_CONTRATO" not in ordered.columns:
        ordered["SITUACAO_CONTRATO"] = "Nao informado"

    result = (
        ordered.groupby(["CONTRATO_CHAVE", "FILIAL", "CONTRATO"], dropna=False)
        .agg(
            FORNECEDOR=("FORNECEDOR", "last"),
            TIPO=("TIPO", "last"),
            SITUACAO_CONTRATO=("SITUACAO_CONTRATO", "last"),
            VALOR_CONTRATADO=("VALOR_ATUAL", "max"),
            QTD_MEDICOES=("MEDICAO_CHAVE", "nunique"),
            PRIMEIRA_COMPETENCIA=("COMPETENCIA_LABEL", "first"),
            ULTIMA_COMPETENCIA=("COMPETENCIA_LABEL", "last"),
            VALOR_TOTAL_MEDICAO=("VALOR_TOTAL_MEDICAO", "sum"),
            VALOR_LIQUIDO=("VALOR_LIQUIDO", "sum"),
            STATUS=("STATUS", "last"),
        )
        .reset_index()
    )
    return result[columns].sort_values("VALOR_TOTAL_MEDICAO", ascending=False).reset_index(drop=True)


def _insights_medicao(medicao: pd.Series, itens_medicao: pd.DataFrame) -> list[str]:
    insights = []
    valor_total = float(medicao.get("VALOR_TOTAL_MEDICAO", 0) or 0)
    valor_liquido = float(medicao.get("VALOR_LIQUIDO", 0) or 0)
    saldo = float(medicao.get("SALDO_MEDICAO", 0) or 0)
    valor_itens = float(itens_medicao["VALOR_TOTAL_ITEM"].sum()) if not itens_medicao.empty else 0.0

    insights.append(f"Competencia com {formatar_quantidade(medicao.get('QTD_ITENS', 0))} item(ns) medido(s).")
    if valor_itens and abs(valor_itens - valor_total) > 0.01:
        insights.append(f"Total dos itens CNE difere do cabecalho em {formatar_moeda(valor_itens - valor_total)}.")
    if valor_liquido != valor_total:
        insights.append(f"Valor liquido representa {formatar_percentual((valor_liquido / valor_total) if valor_total else 0)} do valor medido.")
    if saldo < 0:
        insights.append("Saldo da medicao esta negativo.")
    if float(medicao.get("VALOR_MULTAS", 0) or 0) > 0:
        insights.append("Medicao possui multas registradas.")
    if float(medicao.get("VALOR_BONIFICACOES", 0) or 0) > 0:
        insights.append("Medicao possui bonificacoes registradas.")
    return insights


def _safe_key(value: Any) -> str:
    return "".join(char if char.isalnum() else "_" for char in str(value))

@st.dialog("Detalhes da medicao", width="large")
def _render_medicao_dialog(medicao_chave: str, df: pd.DataFrame, itens: pd.DataFrame) -> None:
    medicao_df = df[df["MEDICAO_CHAVE"] == medicao_chave].copy()
    if medicao_df.empty:
        st.warning("Medicao selecionada nao encontrada no conjunto filtrado.")
        return

    medicao = medicao_df.iloc[0]
    itens_medicao = itens[itens["MEDICAO_CHAVE"] == medicao_chave].copy() if not itens.empty else pd.DataFrame()

    st.markdown(f"### Contrato {medicao.get('CONTRATO', '')}")
    st.caption(f"Competencia {medicao.get('COMPETENCIA_LABEL', '')} | Detalhes da medicao selecionada")

    cols = st.columns(3)
    cols[0].metric("Contrato", str(medicao.get("CONTRATO", "") or "Nao informado"))
    cols[1].metric("Competencia", str(medicao.get("COMPETENCIA_LABEL", "") or "Nao informado"))
    cols[2].metric("No medicao", str(medicao.get("NUMERO_MEDICAO", "") or "Nao informado"))

    cols = st.columns(2)
    cols[0].metric("Revisao", str(medicao.get("REVISAO_CONTRATO", "") or "Sem revisao"))
    cols[1].metric("Status", str(medicao.get("STATUS", "") or "Nao informado"))

    cols = st.columns(4)
    cols[0].metric("Valor previsto", formatar_moeda(medicao_df["VALOR_PREVISTO"].sum()))
    cols[1].metric("Valor medido", formatar_moeda(medicao_df["VALOR_TOTAL_MEDICAO"].sum()))
    cols[2].metric("Valor liquido", formatar_moeda(medicao_df["VALOR_LIQUIDO"].sum()))
    cols[3].metric("Saldo", formatar_moeda(medicao_df["SALDO_MEDICAO"].sum()))

    tab_geral, tab_itens, tab_financeiro, tab_comentarios = st.tabs(
        ["Geral", "Itens", "Financeiro", "Comentários"]
    )

    with tab_geral:
        cols = st.columns(4)
        cols[0].metric("Quantidade de itens", formatar_quantidade(medicao_df["QTD_ITENS"].sum()))
        cols[1].metric("Quantidade medida", formatar_quantidade(medicao_df["QTD_MEDIDA"].sum()))
        cols[2].metric("Quantidade solicitada", formatar_quantidade(medicao_df["QTD_SOLICITADA"].sum()))
        cols[3].metric(
            "Produtos distintos",
            formatar_quantidade(itens_medicao["PRODUTO"].nunique() if not itens_medicao.empty else medicao_df["QTD_PRODUTOS_DISTINTOS"].sum()),
        )

        st.caption(
            "Datas: "
            f"inicio {formatar_data(medicao.get('DATA_INICIO'))} | "
            f"fim {formatar_data(medicao.get('DATA_FIM'))} | "
            f"encerramento {formatar_data(medicao.get('DATA_ENCERRAMENTO'))} | "
            f"vencimento {formatar_data(medicao.get('DATA_VENCIMENTO'))}"
        )

        medicao_agregada = medicao.copy()
        for column in ["VALOR_TOTAL_MEDICAO", "VALOR_LIQUIDO", "SALDO_MEDICAO", "VALOR_MULTAS", "VALOR_BONIFICACOES", "QTD_ITENS"]:
            medicao_agregada[column] = medicao_df[column].sum()
        insights = _insights_medicao(medicao_agregada, itens_medicao)
        render_insights([{"title": "Competencia", "text": insight, "severity": "warning" if "negativo" in insight.lower() or "difere" in insight.lower() else "neutral"} for insight in insights])

    with tab_itens:
        if itens_medicao.empty:
            st.info("Nenhum item da CNE encontrado para esta medicao.")
        else:
            colunas_itens = [
                "ITEM",
                "PRODUTO",
                "QTD_SOLICITADA_ITEM",
                "QTD_MEDIDA_ITEM",
                "VALOR_TOTAL_ITEM",
                "VALOR_LIQUIDO_ITEM",
                "VALOR_MULTA_ITEM",
                "VALOR_BONIFICACAO_ITEM",
            ]
            render_table_section(
                title="Tabela completa dos itens da CNE",
                columns=colunas_itens,
                df=_format_table(itens_medicao[colunas_itens]),
                height=360,
            )

    with tab_financeiro:
        financeiro = pd.DataFrame(
            [
                {"INDICADOR": "Valor previsto", "VALOR": medicao_df["VALOR_PREVISTO"].sum()},
                {"INDICADOR": "Valor medido", "VALOR": medicao_df["VALOR_TOTAL_MEDICAO"].sum()},
                {"INDICADOR": "Valor liquido", "VALOR": medicao_df["VALOR_LIQUIDO"].sum()},
                {"INDICADOR": "Saldo", "VALOR": medicao_df["SALDO_MEDICAO"].sum()},
            ]
        )
        render_table_section(
            title="Resumo financeiro da medicao",
            columns=["INDICADOR", "VALOR"],
            df=_format_table(financeiro),
            height=300,
        )

    with tab_comentarios:
        render_comentarios(
            filial=medicao.get("FILIAL", ""),
            contrato=medicao.get("CONTRATO", ""),
            revisao_contrato=medicao.get("REVISAO_CONTRATO", ""),
            numero_medicao=medicao.get("NUMERO_MEDICAO", ""),
        )

    if st.button("Fechar", key=f"fechar_medicao_{_safe_key(medicao_chave)}"):
        st.rerun()


def _render_navegacao_medicoes(df: pd.DataFrame, itens: pd.DataFrame) -> None:
    resumo = _resumo_contratos_medicoes(df)
    colunas_resumo = [
        "FILIAL",
        "CONTRATO",
        "FORNECEDOR",
        "TIPO",
        "SITUACAO_CONTRATO",
        "VALOR_CONTRATADO",
        "QTD_MEDICOES",
        "PRIMEIRA_COMPETENCIA",
        "ULTIMA_COMPETENCIA",
        "VALOR_TOTAL_MEDICAO",
        "VALOR_LIQUIDO",
        "STATUS",
    ]
    render_table_section(
        title="Contratos com medicoes",
        columns=colunas_resumo,
        df=_format_table(resumo[colunas_resumo]),
        height=360,
    )

    if resumo.empty:
        return

    labels = {
        row["CONTRATO_CHAVE"]: f"{row['CONTRATO']} - {row['FORNECEDOR']}"
        for _, row in resumo.iterrows()
    }
    contrato_chave = st.selectbox(
        "Contrato",
        options=resumo["CONTRATO_CHAVE"].tolist(),
        format_func=lambda value: labels.get(value, value),
        key="medicoes_contrato_drilldown",
    )

    contrato_df = (
        df[df["CONTRATO_CHAVE"] == contrato_chave]
        .sort_values(["COMPETENCIA_ORDEM", "NUMERO_MEDICAO"])
        .drop_duplicates(subset=["MEDICAO_CHAVE"], keep="last")
    )
    if contrato_df.empty:
        st.info("Contrato sem competencias disponiveis para detalhamento.")
        return

    st.markdown(f"**Contrato {contrato_df['CONTRATO'].iloc[0]}**")
    st.caption("Competencias existentes para o contrato selecionado")

    header = st.columns([1.1, 1.0, 0.8, 1.0, 1.2, 1.0, 1.2, 1.2, 0.9])
    header[0].markdown("**Competencia**")
    header[1].markdown("**No medicao**")
    header[2].markdown("**Revisao**")
    header[3].markdown("**Status**")
    header[4].markdown("**Situacao contrato**")
    header[5].markdown("**Itens**")
    header[6].markdown("**Valor medido**")
    header[7].markdown("**Valor liquido**")
    header[8].markdown("**Acao**")

    for row_position, (_, medicao) in enumerate(contrato_df.iterrows()):
        cols = st.columns([1.1, 1.0, 0.8, 1.0, 1.2, 1.0, 1.2, 1.2, 0.9])
        medicao_chave = str(medicao.get("MEDICAO_CHAVE", ""))
        revisao = str(medicao.get("REVISAO_CONTRATO", "")).strip() or "Sem revisao"
        cols[0].write(medicao.get("COMPETENCIA_LABEL", ""))
        cols[1].write(medicao.get("NUMERO_MEDICAO", ""))
        cols[2].write(revisao)
        cols[3].write(medicao.get("STATUS", ""))
        cols[4].write(medicao.get("SITUACAO_CONTRATO", "Nao informado"))
        cols[5].write(formatar_quantidade(medicao.get("QTD_ITENS", 0)))
        cols[6].write(formatar_moeda(medicao.get("VALOR_TOTAL_MEDICAO", 0)))
        cols[7].write(formatar_moeda(medicao.get("VALOR_LIQUIDO", 0)))
        if cols[8].button("Visualizar", key=f"visualizar_medicao_{row_position}_{_safe_key(medicao_chave)}"):
            _render_medicao_dialog(medicao_chave, df, itens)


def _render_filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.expander("Filtros", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filial = select_filter("Filial", opcoes_coluna(df, "FILIAL_NOME"), key="medicoes_filial")
        with col2:
            fornecedor = text_filter("Fornecedor", key="medicoes_fornecedor", placeholder="Nome do fornecedor")
        with col3:
            tipo = select_filter("Tipo contrato", opcoes_coluna(df, "TIPO"), key="medicoes_tipo")
        with col4:
            status = select_filter("Status medicao", opcoes_coluna(df, "STATUS"), key="medicoes_status")

        col5, col6, col7 = st.columns(3)
        with col5:
            competencia = select_filter("Competencia", opcoes_coluna(df, "COMPETENCIA_LABEL"), key="medicoes_competencia")
        with col6:
            contrato = text_filter("Contrato", key="medicoes_contrato", placeholder="Numero do contrato")
        with col7:
            situacao = select_filter("Situacao contrato", opcoes_coluna(df, "SITUACAO_CONTRATO"), key="medicoes_situacao")

    return aplicar_filtros_medicoes(
        df,
        {
            "filial": filial,
            "fornecedor": fornecedor,
            "tipo": tipo,
            "status": status,
            "situacao": situacao,
            "competencia": competencia,
            "contrato": contrato,
        },
    )


def render_medicoes(
    df_contratos: Any = None,
    df_fornecedores: Any = None,
    df_medicoes: Any = None,
    df_financeiro: Any = None,
    df_itens: Any = None,
) -> None:
    st.header("Medicoes")
    st.caption("Analise detalhada das medicoes dos contratos (CND010/CNE010).")

    base = _load_medicoes(df_medicoes)
    if base.empty:
        st.warning("Nenhuma medicao retornada pela consulta do Protheus.")
        return

    df = _render_filters(base)
    kpis = resumo_medicoes(df)
    indicadores = indicadores_contratos(df, df_contratos=df_contratos)

    cards = [
        {"title": "Contratos com medicoes", "value": formatar_quantidade(kpis["contratos_com_medicao"]), "subtitle": "Quantidade distinta de contratos"},
        {"title": "Total de medicoes", "value": formatar_quantidade(kpis["total_medicoes"]), "subtitle": "Chave filial + contrato + revisao + medicao"},
        {"title": "Valor total das medicoes", "value": formatar_moeda(kpis["valor_total_medicoes"]), "subtitle": "SUM(CND_VLTOT)"},
        {"title": "Valor liquido", "value": formatar_moeda(kpis["valor_liquido"]), "subtitle": "SUM(CND_VLLIQD)"},
        {"title": "Valor previsto", "value": formatar_moeda(kpis["valor_previsto"]), "subtitle": "SUM(CND_VLPREV)"},
        {"title": "Total de multas", "value": formatar_moeda(kpis["total_multas"]), "subtitle": "SUM(CND_VLMULT)"},
        {"title": "Total de bonificacoes", "value": formatar_moeda(kpis["total_bonificacoes"]), "subtitle": "SUM(CND_VLBONI)"},
    ]
    render_kpi_cards(cards, columns=4)

    render_insights(
        get_medicoes_insights(
            df,
            indicadores=indicadores,
            money_formatter=formatar_moeda,
            quantity_formatter=formatar_quantidade,
            percent_formatter=formatar_percentual,
        )
    )

    if df.empty:
        st.warning("Nenhuma medicao encontrada para os filtros selecionados.")
        return

    itens_medicoes = _load_medicoes_itens(df_itens)

    if st.checkbox("Exibir graficos", key="medicoes_exibir_graficos"):
        col1, = st.columns(1)
        with col1:
            render_line_chart(
                "Evolucao das medicoes",
                evolucao_medicoes(df, value_column="VALOR_TOTAL_MEDICAO"),
                x="COMPETENCIA",
                y="VALOR_TOTAL_MEDICAO",
                empty_message="Sem dados de evolucao para exibir.",
            )
        col2, = st.columns(1)
        with col2:
            render_bar_chart(
                "Quantidade de contratos por faixa de medicoes",
                faixas_medicoes(df),
                x="FAIXA",
                y="QTD_CONTRATOS",
                empty_message="Sem faixas para exibir.",
            )

    st.divider()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Contratos e competencias",
        "Ranking dos contratos",
        "Ranking fornecedores",
        "Competencias",
        "Status das medicoes",
        "Contratos sem medicao",
    ])

    with tab1:
        _render_navegacao_medicoes(df, itens_medicoes)

    with tab2:
        render_table_section(
            title="Ranking dos contratos",
            columns=["CONTRATO", "FORNECEDOR", "QTD_MEDICOES", "VALOR_TOTAL_MEDICAO", "VALOR_LIQUIDO", "VALOR_PREVISTO", "SALDO_MEDICAO"],
            df=_format_table(ranking_contratos(df)),
        )

    with tab3:
        render_table_section(
            title="Ranking fornecedores",
            columns=["FORNECEDOR", "QTD_CONTRATOS", "QTD_MEDICOES", "VALOR_TOTAL_MEDICAO", "VALOR_LIQUIDO"],
            df=_format_table(ranking_fornecedores(df)),
        )

    with tab4:
        render_table_section(
            title="Competencias",
            columns=["COMPETENCIA", "QTD_MEDICOES", "VALOR_TOTAL_MEDICAO", "VALOR_LIQUIDO", "VALOR_PREVISTO"],
            df=_format_table(ranking_competencias(df)),
        )

    with tab5:
        render_table_section(
            title="Status das medicoes",
            columns=["STATUS", "QTD_MEDICOES", "VALOR_TOTAL_MEDICAO", "VALOR_LIQUIDO"],
            df=_format_table(medicoes_por_status(df)),
        )

    with tab6:
        render_table_section(
            title="Contratos sem medicao",
            columns=["FILIAL", "CONTRATO", "FORNECEDOR", "TIPO", "STATUS", "VALOR_ATUAL"],
            df=_format_table(contratos_sem_medicao(df, df_contratos)),
        )

    st.divider()

    render_table_section(
        title="Medicoes com divergencia",
        columns=["FILIAL", "CONTRATO", "FORNECEDOR", "NUMERO_MEDICAO", "DIVERGENCIA", "VALOR_LIQUIDO", "VALOR_TOTAL_MEDICAO", "QTD_SOLICITADA", "QTD_MEDIDA", "VALOR_PREVISTO", "SALDO_MEDICAO"],
        df=_format_table(medicoes_com_divergencia(df)),
    )
