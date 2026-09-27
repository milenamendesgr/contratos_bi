from __future__ import annotations
from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from components.cards import render_insights, render_kpi_cards, render_section_header
from components.charts import render_bar_chart, render_line_chart
from components.filters import select_filter, text_filter
from components.tables import render_table_section
from utils.contratos_repository import get_adiantamentos, get_fornecedores
from utils.contratos_service import (
    agrupar_valor,
    aplicar_filtros_carteira,
    evolucao_carteira,
    opcoes_coluna,
    ranking_contratos,
    resumo_kpis,
)
from utils.formatters import formatar_cnpj, formatar_data, formatar_moeda, formatar_percentual, formatar_quantidade
from utils.insights import get_dashboard_executivo_insights


ADIANTAMENTO_COLUMNS = [
    "VALOR_ADIANTAMENTO",
    "VALOR_ADIANTADO",
    "TOTAL_ADIANTAMENTO",
    "TOTAL_ADIANTADO",
    "ADIANTAMENTO",
    "ADIANTADO",
]
FORNECEDOR_COLUMNS = ["FORNECEDOR", "NOME_FORNECEDOR", "RAZAO_SOCIAL", "A2_NOME", "NOME"]
VALOR_FORNECEDOR_COLUMNS = ["VALOR_CONTRATO", "VALOR_CONTRATADO", "CN9_VLATU", "VALOR_ATUAL", "TOTAL_CONTRATADO", "TOTAL"]
CONTRATO_COLUMNS = ["CONTRATO", "NUM_CONTRATO", "NUMERO_CONTRATO", "CN9_NUMERO"]

def _format_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    result = df.copy()
    for column in ["VALOR_ATUAL", "SALDO_CONTRATUAL", "VALOR_CONTRATADO", "Valor Atual", "Saldo do Contrato"]:
        if column in result.columns:
            result[column] = result[column].apply(formatar_moeda)
    for column in ["DATA_INICIO", "DATA_FIM", "DATA_FINAL", "Data de Inicio", "Data Final"]:
        if column in result.columns:
            result[column] = result[column].apply(formatar_data)
    for column in ["PERCENTUAL_EXECUCAO"]:
        if column in result.columns:
            result[column] = result[column].apply(formatar_percentual)
    for column in ["QTD_CONTRATOS"]:
        if column in result.columns:
            result[column] = result[column].apply(formatar_quantidade)
    for column in ["CNPJ", "CNPJ_FORNECEDOR", "CNPJ/CPF"]:
        if column in result.columns:
            result[column] = result[column].apply(formatar_cnpj)
    result = result.rename(columns={"CNPJ_FORNECEDOR": "CNPJ/CPF", "CNPJ": "CNPJ/CPF"})
    return result


def _normalize_columns(df: Any) -> pd.DataFrame:
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    result = df.copy()
    result.columns = [str(column).strip().upper() for column in result.columns]
    return result


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


def _first_present(columns: pd.Index, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in columns:
            return column
    return None


def _total_adiantamentos(df_adiantamentos: Any, df_filtrado: pd.DataFrame) -> float | None:
    adiantamentos = _normalize_columns(df_adiantamentos)
    if adiantamentos.empty or "VALOR_ADIANTAMENTO" not in adiantamentos.columns:
        return None

    base = adiantamentos.copy()
    if "CONTRATO" in base.columns and "CONTRATO" in df_filtrado.columns:
        contratos = df_filtrado["CONTRATO"].astype(str).str.strip()
        base = base[base["CONTRATO"].astype(str).str.strip().isin(contratos)]
    if "FILIAL" in base.columns and "FILIAL" in df_filtrado.columns:
        filiais = df_filtrado["FILIAL"].astype(str).str.strip()
        base = base[base["FILIAL"].astype(str).str.strip().isin(filiais)]

    return float(_to_number(base["VALOR_ADIANTAMENTO"]).sum())


def _supplier_label(row: pd.Series) -> str:
    name = str(row.get("NOME_FORNECEDOR", "") or "").strip()
    code = str(row.get("COD_FORNECEDOR", "") or "").strip()
    store = str(row.get("LOJA_FORNECEDOR", "") or "").strip()
    invalid_codes = {"", "NAO INFORMADO", "NÃO INFORMADO", "NONE", "NAN"}
    invalid_names = {"", "NONE", "NAN"}

    if name.upper() not in invalid_names:
        return name
    if code.upper() not in invalid_codes:
        return f"{code}/{store}" if store.upper() not in invalid_codes else code
    return ""


def _enrich_fornecedores(df: pd.DataFrame, df_fornecedores: Any = None) -> pd.DataFrame:
    if "NOME_FORNECEDOR" in df.columns:
        base = df.copy()
        base["FORNECEDOR"] = base["NOME_FORNECEDOR"].fillna("").astype(str).str.strip()
        if "COD_FORNECEDOR" in base.columns and "LOJA_FORNECEDOR" in base.columns:
            base["FORNECEDOR_CHAVE"] = (
                base["COD_FORNECEDOR"].fillna("").astype(str).str.strip()
                + " / "
                + base["LOJA_FORNECEDOR"].fillna("").astype(str).str.strip()
                + " - "
                + base["FORNECEDOR"]
            ).str.strip(" /-")
        return base

    fornecedores = _normalize_columns(df_fornecedores)
    if fornecedores.empty:
        fornecedores = _normalize_columns(get_fornecedores())
    if fornecedores.empty or "CONTRATO" not in fornecedores.columns or "CONTRATO" not in df.columns:
        return df

    base = df.copy()
    origem = fornecedores.copy()
    origem["FORNECEDOR_DASH"] = origem.apply(_supplier_label, axis=1)
    origem["FORNECEDOR_CHAVE_DASH"] = (
        origem.get("COD_FORNECEDOR", pd.Series("", index=origem.index)).astype(str).str.strip()
        + " / "
        + origem.get("LOJA_FORNECEDOR", pd.Series("", index=origem.index)).astype(str).str.strip()
        + " - "
        + origem["FORNECEDOR_DASH"].astype(str).str.strip()
    ).str.strip()

    group_columns = ["CONTRATO"]
    if "FILIAL" in origem.columns and "FILIAL" in base.columns:
        group_columns.insert(0, "FILIAL")

    lookup_columns = group_columns + ["FORNECEDOR_DASH", "FORNECEDOR_CHAVE_DASH"]
    if "CNPJ_FORNECEDOR" in origem.columns:
        lookup_columns.append("CNPJ_FORNECEDOR")

    aggregations = {
        "FORNECEDOR": ("FORNECEDOR_DASH", lambda values: " | ".join(sorted(set(values)))),
        "FORNECEDOR_CHAVE": ("FORNECEDOR_CHAVE_DASH", lambda values: " | ".join(sorted(set(values)))),
    }
    if "CNPJ_FORNECEDOR" in origem.columns:
        aggregations["CNPJ_FORNECEDOR"] = ("CNPJ_FORNECEDOR", lambda values: " | ".join(sorted(set(str(value).strip() for value in values if str(value).strip()))))

    lookup = (
        origem[lookup_columns]
        .drop_duplicates()
        .groupby(group_columns, dropna=False)
        .agg(**aggregations)
        .reset_index()
    )
    return base.merge(lookup, on=group_columns, how="left")


def _apply_period_filter(df: pd.DataFrame, modo_periodo: str, data_especifica: Any = None, intervalo: Any = None) -> pd.DataFrame:
    if df.empty or "DATA_INICIO" not in df.columns or modo_periodo == "Sem filtro":
        return df

    datas = pd.to_datetime(df["DATA_INICIO"], errors="coerce").dt.normalize()
    result = df.copy()
    hoje = pd.Timestamp.now().normalize()

    if modo_periodo == "Ultimos 30 dias":
        return result[datas >= hoje - pd.Timedelta(days=30)]
    if modo_periodo == "Ultimos 90 dias":
        return result[datas >= hoje - pd.Timedelta(days=90)]
    if modo_periodo == "Data especifica" and isinstance(data_especifica, date):
        return result[datas == pd.Timestamp(data_especifica)]
    if modo_periodo == "Periodo personalizado" and isinstance(intervalo, tuple) and len(intervalo) == 2:
        data_inicio, data_fim = intervalo
        if isinstance(data_inicio, date):
            result = result[datas >= pd.Timestamp(data_inicio)]
            datas = pd.to_datetime(result["DATA_INICIO"], errors="coerce").dt.normalize()
        if isinstance(data_fim, date):
            result = result[datas <= pd.Timestamp(data_fim)]
        return result

    return result


def _ranking_fornecedores(df: pd.DataFrame, df_fornecedores: Any = None, limit: int = 10) -> pd.DataFrame:
    fornecedores = _normalize_columns(df_fornecedores)
    if fornecedores.empty:
        fornecedores = get_fornecedores()
        fornecedores = _normalize_columns(fornecedores)

    if not fornecedores.empty:
        fornecedor_column = _first_present(fornecedores.columns, FORNECEDOR_COLUMNS)
        value_column = _first_present(fornecedores.columns, VALOR_FORNECEDOR_COLUMNS)
        if fornecedor_column and value_column:
            base = fornecedores.copy()
            if "SITUACAO" in base.columns:
                base = base[base["SITUACAO"].astype(str).str.strip().eq("05")]
            if "CONTRATO" in base.columns and "CONTRATO" in df.columns and not df.empty:
                if "FILIAL" in base.columns and "FILIAL" in df.columns:
                    filtered_contracts = df[["FILIAL", "CONTRATO"]].drop_duplicates().copy()
                    filtered_contracts["FILIAL"] = filtered_contracts["FILIAL"].astype(str).str.strip()
                    filtered_contracts["CONTRATO"] = filtered_contracts["CONTRATO"].astype(str).str.strip()
                    base["FILIAL"] = base["FILIAL"].astype(str).str.strip()
                    base["CONTRATO"] = base["CONTRATO"].astype(str).str.strip()
                    base = base.merge(filtered_contracts, on=["FILIAL", "CONTRATO"], how="inner")
                else:
                    contratos_filtrados = df["CONTRATO"].astype(str).str.strip()
                    base = base[base["CONTRATO"].astype(str).str.strip().isin(contratos_filtrados)]
            if not base.empty:
                base["VALOR_CONTRATADO"] = _to_number(base[value_column])
                group_columns = [fornecedor_column]
                if "CNPJ_FORNECEDOR" in base.columns:
                    group_columns.append("CNPJ_FORNECEDOR")
                return (
                    base.groupby(group_columns, dropna=False)
                    .agg(QTD_CONTRATOS=("CONTRATO", "nunique"), VALOR_CONTRATADO=("VALOR_CONTRATADO", "sum"))
                    .sort_values("VALOR_CONTRATADO", ascending=False)
                    .head(limit)
                    .reset_index()
                    .rename(columns={fornecedor_column: "FORNECEDOR"})
                )

    if "FORNECEDOR" in df.columns and not df.empty:
        value_column = "VALOR_ATUAL" if "VALOR_ATUAL" in df.columns else "VALOR_INICIAL"
        result = (
            df.groupby("FORNECEDOR", dropna=False)
            .agg(QTD_CONTRATOS=("CONTRATO", "nunique"), VALOR_CONTRATADO=(value_column, "sum"))
            .sort_values("VALOR_CONTRATADO", ascending=False)
            .head(limit)
            .reset_index()
        )
        return result

    return pd.DataFrame(columns=["FORNECEDOR", "CNPJ_FORNECEDOR", "QTD_CONTRATOS", "VALOR_CONTRATADO"])


def _matches_supplier(value: Any, selected_supplier: str) -> bool:
    suppliers = [item.strip() for item in str(value or "").split("|") if item.strip()]
    return selected_supplier in suppliers or str(value or "").strip() == selected_supplier


def _contracts_for_supplier(df: pd.DataFrame, selected_supplier: str) -> pd.DataFrame:
    #aqui nasce a tabela
    if df.empty or "FORNECEDOR" not in df.columns:
        return pd.DataFrame()

    result = df[df["FORNECEDOR"].apply(lambda value: _matches_supplier(value, selected_supplier))].copy()
    #pega todos os contratos do fornecedor selecionado (apply = aplicar)
    if result.empty:
        return result

    if "CONTRATO" in result.columns:
        result = result.drop_duplicates(subset=["CONTRATO"])
        #remover duplicatas de contratos (drop = remover)

    data_final_column = "DATA_FIM" if "DATA_FIM" in result.columns else "DATA_FINAL"
    #as seguintes colunas vao ser apresentadas na tabela, caso existam no dataframe
    columns = [
        "CONTRATO",
        "FORNECEDOR",
        "CNPJ_FORNECEDOR",
        "TIPO",
        "SITUACAO",
        "DATA_INICIO",
        data_final_column,
        "VALOR_ATUAL",
        "SALDO_CONTRATUAL",
        "STATUS",
    ]
    present_columns = [column for column in columns if column and column in result.columns]
    display = result[present_columns].copy()
    #traz as colunas presentes no dataframe, caso existam
    return display.rename(
        columns={
            #aqui muda o nome das colunas para apresentacao na tabela (display.rename = renomear exibição)
            "CONTRATO": "Contrato",
            "FORNECEDOR": "Fornecedor",
            "CNPJ_FORNECEDOR": "CNPJ/CPF",
            "TIPO": "Tipo do Contrato",
            "SITUACAO": "Situacao",
            "DATA_INICIO": "Data de Inicio",
            "DATA_FIM": "Data Final",
            "DATA_FINAL": "Data Final",
            "VALOR_ATUAL": "Valor Atual",
            "SALDO_CONTRATUAL": "Saldo do Contrato",
            "STATUS": "Status",
        }
    )


def _supplier_contract_numbers(df: pd.DataFrame, selected_supplier: str) -> pd.Series:
    if df.empty or "FORNECEDOR" not in df.columns or "CONTRATO" not in df.columns:
        return pd.Series(dtype="object")

    contracts = df[df["FORNECEDOR"].apply(lambda value: _matches_supplier(value, selected_supplier))]["CONTRATO"]
    return contracts.astype(str).str.strip().dropna().drop_duplicates()


def _supplier_rows(df: pd.DataFrame, selected_supplier: str) -> pd.DataFrame:
    if df.empty or "FORNECEDOR" not in df.columns:
        return pd.DataFrame()

    result = df[df["FORNECEDOR"].apply(lambda value: _matches_supplier(value, selected_supplier))].copy()
    if result.empty:
        return result

    dedupe_columns = ["CONTRATO"]
    if "FILIAL" in result.columns:
        dedupe_columns.insert(0, "FILIAL")
    return result.drop_duplicates(subset=dedupe_columns)


def _filter_related_by_contracts(df: Any, contratos: pd.Series) -> pd.DataFrame:
    result = _normalize_columns(df)
    if result.empty or contratos.empty:
        return result.iloc[0:0] if not result.empty else result

    contract_column = _first_present(result.columns, CONTRATO_COLUMNS)
    if not contract_column:
        return pd.DataFrame(columns=result.columns)

    selected = set(contratos.astype(str).str.strip())
    return result[result[contract_column].astype(str).str.strip().isin(selected)]


def _supplier_summary(
    df: pd.DataFrame,
    selected_supplier: str,
    ranking_row: pd.Series,
    df_medicoes: Any = None,
    df_financeiro: Any = None,
    df_itens: Any = None,
) -> dict[str, str]:
    supplier_rows = _supplier_rows(df, selected_supplier)
    contracts = _supplier_contract_numbers(supplier_rows, selected_supplier)
    saldo = float(_to_number(supplier_rows["SALDO_CONTRATUAL"]).sum()) if "SALDO_CONTRATUAL" in supplier_rows.columns else 0.0
    itens = _filter_related_by_contracts(df_itens, contracts)
    planilhas = 0
    if not itens.empty and "PLANILHA" in itens.columns:
        planilhas = int(itens["PLANILHA"].astype(str).str.strip().replace("", pd.NA).dropna().nunique())

    return {
        "Quantidade de contratos": formatar_quantidade(ranking_row.get("QTD_CONTRATOS", len(contracts))),
        "Valor contratado": formatar_moeda(ranking_row.get("VALOR_CONTRATADO", 0)),
        "Saldo contratado": formatar_moeda(saldo),
        #"Medicoes": formatar_quantidade(len(_filter_related_by_contracts(df_medicoes, contracts))),
        #"Pagamentos": formatar_quantidade(len(_filter_related_by_contracts(df_financeiro, contracts))),
        #"Itens": formatar_quantidade(len(itens)),
        #"Planilhas": formatar_quantidade(planilhas),
    }


def _render_fornecedor_drilldown(
    df: pd.DataFrame,
    df_fornecedor: pd.DataFrame,
    df_medicoes: Any = None,
    df_financeiro: Any = None,
    df_itens: Any = None,
) -> None:
    render_section_header("Ranking dos fornecedores por valor contratado vigente - TOP 10", "Detalhamento disponivel ao selecionar uma linha.")

    if df_fornecedor.empty:
        st.warning("DataFrame carregado, porem vazio.")
        st.caption("Colunas esperadas: FORNECEDOR | QTD_CONTRATOS | VALOR_CONTRATADO")
        return

    display_ranking = df_fornecedor.reset_index(drop=True).copy()
    col_info, col_download = st.columns([4, 1])
    with col_info:
        st.caption(f"{len(display_ranking)} registro(s) exibido(s).")
    with col_download:
        csv_bytes = _format_table(display_ranking).to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        st.download_button(
            "Baixar CSV",
            data=csv_bytes,
            file_name="ranking_dos_fornecedores_por_valor_contratado.csv",
            mime="text/csv",
            use_container_width=True,
        )

    event = st.dataframe(
        _format_table(display_ranking),
        use_container_width=True,
        hide_index=True,
        height=420,
        on_select="rerun",
        selection_mode="single-row",
        key=f"dash_exec_ranking_fornecedores_{len(display_ranking)}",
    )

    if df.empty or "FORNECEDOR" not in display_ranking.columns:
        return

    if not event or not event.selection or not event.selection.rows:
        return

    selected_index = event.selection.rows[0]
    if selected_index >= len(display_ranking):
        return

    ranking_row = display_ranking.iloc[selected_index]
    selected_supplier = str(ranking_row.get("FORNECEDOR", "")).strip()
    if not selected_supplier:
        return

    supplier_contracts = _contracts_for_supplier(df, selected_supplier)
    #função pede para buscar todos os contratos do fornecedor 
    if supplier_contracts.empty:
        st.info("Nao ha contratos desse fornecedor nos filtros atuais.")
        return

    with st.expander(f"Detalhes do fornecedor selecionado: {selected_supplier}", expanded=True):
        summary = _supplier_summary(df, selected_supplier, ranking_row, df_medicoes, df_financeiro, df_itens)
        metric_columns = st.columns(4)
        for index, (label, value) in enumerate(summary.items()):
            with metric_columns[index % 4]:
                st.metric(label, value)

        st.markdown("#### Contratos")
        st.dataframe(
            _format_table(supplier_contracts),
            use_container_width=True,
            hide_index=True,
            height=min(420, max(160, len(supplier_contracts) * 38 + 50)),
        )


def _render_filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.expander("Filtros", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            filial = select_filter("Filial", opcoes_coluna(df, "FILIAL_NOME"), key="dash_filial")
            contrato = text_filter("Contrato", key="dash_contrato", placeholder="Numero do contrato")
        with col2:
            tipo = select_filter("Tipo de contrato", opcoes_coluna(df, "TIPO"), key="dash_tipo")
            fornecedor = text_filter("Fornecedor", key="dash_fornecedor", placeholder="Nome, codigo ou loja")
        with col3:
            situacao = select_filter("Situacao", opcoes_coluna(df, "STATUS"), key="dash_status")
            modo_periodo = select_filter(
                "Periodo",
                ["Sem filtro", "Ultimos 30 dias", "Ultimos 90 dias", "Data especifica", "Periodo personalizado"],
                key="dash_periodo_modo",
            )

        data_especifica = None
        intervalo = None
        if modo_periodo == "Data especifica":
            data_especifica = st.date_input("Data de inicio", value=date.today(), key="dash_data_especifica")
        elif modo_periodo == "Periodo personalizado":
            intervalo = st.date_input(
                "Intervalo de inicio",
                value=(date.today() - timedelta(days=90), date.today()),
                key="dash_periodo_intervalo",
            )

    result = aplicar_filtros_carteira(
        df,
        {
            "filial": filial,
            "tipo": tipo,
            "situacao": situacao,
            "contrato": contrato,
            "fornecedor": fornecedor,
            "data_inicio": None,
            "data_fim": None,
        },
    )
    return _apply_period_filter(result, modo_periodo, data_especifica, intervalo)


def render_dashboard_executivo(
    df_contratos: Any = None,
    df_fornecedores: Any = None,
    df_medicoes: Any = None,
    df_financeiro: Any = None,
    df_itens: Any = None,
) -> None:
    st.header("Dashboard Executivo")
    st.caption("Visao consolidada de contratos para leitura executiva.")

    if df_contratos is None or getattr(df_contratos, "empty", True):
        st.warning("Nenhum contrato retornado pela consulta do Protheus.")
        return

    base = _enrich_fornecedores(df_contratos.copy(), df_fornecedores)
    df = _render_filters(base)
    kpis = resumo_kpis(df)
    df_adiantamentos = get_adiantamentos()
    total_adiantamentos = _total_adiantamentos(df_adiantamentos, df)

    cards = [
        {"title": "Total de contratos", "value": formatar_quantidade(kpis["total_contratos"]), "subtitle": "Total de contratos"},
        {"title": "Contratos ativos", "value": formatar_quantidade(kpis["contratos_ativos"]), "subtitle": "Contratos com situação vigente"},
        {"title": "Valor total contratado", "value": formatar_moeda(kpis["valor_total"]), "subtitle": "Valor total dos contratos"},
        {"title": "Valor atualizado", "value": formatar_moeda(kpis["valor_atual"]), "subtitle": "Valor de contratos vigentes"},
        {"title": "Valor executado", "value": formatar_moeda(kpis["valor_executado"]), "subtitle": "Valor atual menos saldo"},
        {"title": "Saldo contratual", "value": formatar_moeda(kpis["saldo_contratual"]), "subtitle": "Valor de saldo de todos os contratos"},
        {"title": "Execucao media", "value": formatar_percentual(kpis["percentual_medio_execucao"]), "subtitle": "Media da carteira"},
        {
            "title": "Adiantamentos",
            "value": formatar_moeda(total_adiantamentos) if total_adiantamentos is not None else "--",
            "subtitle": "Não esta filtrando por data" if total_adiantamentos is not None else "CNX010 sem retorno",
        },
    ]
    render_kpi_cards(cards, columns=4)

    df_fornecedor_insight = _ranking_fornecedores(df, df_fornecedores, limit=1)
    render_insights(
        get_dashboard_executivo_insights(
            df,
            top_fornecedor=df_fornecedor_insight,
            money_formatter=formatar_moeda,
            percent_formatter=formatar_percentual,
        )
    )

    if df.empty:
        st.warning("Nenhum contrato encontrado para os filtros selecionados.")
        return

    df_graficos = df[df["SITUACAO"].astype(str).str.strip().eq("05")].copy() if "SITUACAO" in df.columns else df.iloc[0:0].copy()

    col1, col2 = st.columns(2)
    with col1:
        df_tipo = agrupar_valor(df_graficos, "TIPO")
        render_bar_chart(
            "Distribuicao por tipo de contratos vigentes",
            df_tipo,
            x="VALOR_ATUAL",
            y="TIPO",
            orientation="h",
        )

    with col2:
        df_filial = agrupar_valor(df_graficos, "FILIAL_NOME")
        render_bar_chart(
            "Distribuicao por filial de contratos vigentes",
            df_filial,
            x="VALOR_ATUAL",
            y="FILIAL_NOME",
            orientation="h",
        )

    df_ranking = ranking_contratos(df)
    render_table_section(
        title="Ranking dos maiores contratos",
        columns=["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "FILIAL_NOME", "TIPO", "STATUS", "VALOR_ATUAL", "SALDO_CONTRATUAL", "PERCENTUAL_EXECUCAO"],
        df=_format_table(df_ranking),
    )

    df_fornecedor = _ranking_fornecedores(df_graficos, df_fornecedores)
    _render_fornecedor_drilldown(df_graficos, df_fornecedor, df_medicoes, df_financeiro, df_itens)
