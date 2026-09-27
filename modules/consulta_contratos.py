"""Consulta de contratos module."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.cards import render_insights, render_kpi_cards, render_section_header
from components.charts import render_bar_chart, render_line_chart
from components.filters import select_filter, text_filter
from components.tables import render_table_section
from modules.adiantamentos import _format_table as _format_adiantamentos_table
from modules.financeiro import _format_table as _format_financeiro_table, _load_financeiro
from modules.itens_planilhas import (
    _contratos_maior_qtd_planilhas,
    _distribuicao_tipo_planilha,
    _format_table as _format_itens_table,
    _load_itens_planilhas,
    _planilhas_maior_qtd_itens,
    _summary as _summary_itens,
)
from utils.adiantamentos_service import (
    aplicar_filtros_adiantamentos,
    comparativo_valor_saldo,
    detalhes_adiantamentos,
    evolucao_adiantamentos_mensal,
    get_adiantamentos_insights,
    ranking_adiantamentos as ranking_adiantamentos_por_coluna,
    resumo_adiantamentos,
)
from utils.contratos_repository import get_adiantamentos, get_medicoes
from utils.contratos_service import aplicar_filtros_carteira, opcoes_coluna
from utils.financeiro_service import (
    aplicar_filtros_financeiro,
    comparativo_previsto_realizado,
    distribuicao_por_situacao,
    ranking_adiantamentos as ranking_adiantamentos_financeiro,
    ranking_atrasos,
    ranking_saldo_financeiro,
    resumo_financeiro,
)
from utils.formatters import formatar_cnpj, formatar_data, formatar_moeda, formatar_percentual, formatar_quantidade
from utils.insights import get_consulta_contrato_insights, get_financeiro_insights, get_itens_planilhas_insights
from utils.medicoes_service import preparar_medicoes


FORNECEDOR_COLUMNS = ["FORNECEDOR", "NOME_FORNECEDOR", "RAZAO_SOCIAL", "A2_NOME", "NOME"]
CONTRATO_COLUMNS = ["CONTRATO", "NUM_CONTRATO", "NUMERO_CONTRATO", "CN9_NUMERO"]
UNIDADE_VIGENCIA_LABELS = {
    "1": "Dias",
    "2": "Meses",
    "3": "Anos",
    "4": "Indeterminada",
}

def _normalize_columns(df: Any) -> pd.DataFrame:
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    result = df.copy()
    result.columns = [str(column).strip().upper() for column in result.columns]
    return result


def _first_present(columns: pd.Index, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in columns:
            return column
    return None


def _filter_by_text(df: pd.DataFrame, column: str, value: str) -> pd.DataFrame:
    if df.empty or not value or column not in df.columns:
        return df
    return df[df[column].astype(str).str.lower().str.contains(value.strip().lower(), na=False)]


def _filter_related_by_contract(df: Any, contrato: Any) -> pd.DataFrame:
    result = _normalize_columns(df)
    if result.empty:
        return result

    contract_column = _first_present(result.columns, CONTRATO_COLUMNS)
    if not contract_column:
        return pd.DataFrame(columns=result.columns)

    selected = str(contrato).strip()
    return result[result[contract_column].astype(str).str.strip() == selected]


def _lookup_fornecedor(row: pd.Series, df_fornecedores: Any = None) -> str:
    for column in FORNECEDOR_COLUMNS:
        value = row.get(column)
        if pd.notna(value) and str(value).strip():
            return str(value).strip()

    fornecedores = _filter_related_by_contract(df_fornecedores, row.get("CONTRATO", ""))
    if fornecedores.empty:
        return ""

    fornecedor_column = _first_present(fornecedores.columns, FORNECEDOR_COLUMNS)
    if not fornecedor_column:
        return ""

    value = fornecedores.iloc[0].get(fornecedor_column, "")
    return str(value).strip()


def _lookup_cnpj(row: pd.Series, df_fornecedores: Any = None) -> str:
    value = row.get("CNPJ_FORNECEDOR")
    if pd.notna(value) and str(value).strip():
        return str(value).strip()

    fornecedores = _filter_related_by_contract(df_fornecedores, row.get("CONTRATO", ""))
    if fornecedores.empty or "CNPJ_FORNECEDOR" not in fornecedores.columns:
        return ""

    value = fornecedores.iloc[0].get("CNPJ_FORNECEDOR", "")
    return str(value).strip()


def _select_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    present = list(dict.fromkeys(column for column in columns if column in df.columns))
    return df[present] if present else df


def _rename_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(
        columns={
            "FILIAL_NOME": "FILIAL",
            "DESCRICAO": "DESCRIÇÃO",
            "DATA_INICIO": "DATA_INÍCIO",
            "PERCENTUAL_EXECUCAO": "PERCENTUAL_EXECUÇÃO",
        }
    )


def _filter_exact_contract(df: Any, contrato: Any) -> pd.DataFrame:
    result = _normalize_columns(df)
    if result.empty or "CONTRATO" not in result.columns:
        return result
    selected = str(contrato).strip()
    return result[result["CONTRATO"].astype(str).str.strip() == selected]


def _filter_detail_scope(df: Any, contrato: Any, filial: Any, filial_nome: Any = "") -> pd.DataFrame:
    result = _filter_exact_contract(df, contrato)
    if result.empty:
        return result

    filial_codigo = str(filial or "").strip()
    filial_exibicao = str(filial_nome or "").strip()
    if filial_codigo and "FILIAL" in result.columns:
        return result[result["FILIAL"].astype(str).str.strip() == filial_codigo]
    if filial_exibicao and "FILIAL_NOME" in result.columns:
        return result[result["FILIAL_NOME"].astype(str).str.strip() == filial_exibicao]
    return result


def _load_medicoes(df_medicoes: Any = None) -> pd.DataFrame:
    if df_medicoes is not None and not (hasattr(df_medicoes, "empty") and df_medicoes.empty):
        return preparar_medicoes(df_medicoes)
    return get_medicoes()


def _filiais_detalhamento(df: pd.DataFrame) -> tuple[list[str], dict[str, dict[str, str]]]:
    if df.empty:
        return [], {}

    labels: list[str] = []
    filial_por_label: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        codigo = str(row.get("FILIAL", "") or "").strip()
        nome = str(row.get("FILIAL_NOME", "") or "").strip()
        label = nome or codigo or "Nao informado"
        if label in filial_por_label and codigo and filial_por_label[label].get("codigo") != codigo:
            label = f"{label} ({codigo})"
        if label not in filial_por_label:
            labels.append(label)
            filial_por_label[label] = {"codigo": codigo, "nome": nome}
    return labels, filial_por_label


def _format_display_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    result = df.copy()
    for column in result.columns:
        column_upper = str(column).upper()
        if "DATA" in column_upper or column_upper.startswith("DT_"):
            result[column] = result[column].apply(formatar_data)
        elif "PERCENT" in column_upper or "PARTICIPACAO" in column_upper:
            result[column] = result[column].apply(formatar_percentual)
        elif any(token in column_upper for token in ["VALOR", "SALDO", "TOTAL"]):
            result[column] = result[column].apply(formatar_moeda)
        elif any(token in column_upper for token in ["QUANTIDADE", "QTD"]):
            result[column] = result[column].apply(formatar_quantidade)
        elif column_upper in {"CNPJ", "CNPJ_FORNECEDOR"}:
            result[column] = result[column].apply(formatar_cnpj)
    return result


def _render_selectable_contracts_table(df: pd.DataFrame, columns: list[str]) -> str | None:
    render_section_header("Contratos encontrados", "Detalhamento disponivel para conferencia e exportacao.")
    if df.empty:
        st.warning("DataFrame carregado, porem vazio.")
        st.caption("Colunas esperadas: " + " | ".join(columns))
        return None

    tabela = df.copy()
    tabela.insert(0, "SELECIONAR", False)
    disabled_columns = [column for column in tabela.columns if column != "SELECIONAR"]
    selecionado = st.data_editor(
        tabela,
        use_container_width=True,
        hide_index=True,
        height=420,
        disabled=disabled_columns,
        column_config={"SELECIONAR": st.column_config.CheckboxColumn("Selecionar")},
        key="consulta_contratos_selecao_tabela",
    )
    linhas_selecionadas = selecionado[selecionado["SELECIONAR"]]
    if linhas_selecionadas.empty:
        return None
    if len(linhas_selecionadas) > 1:
        st.info("Mais de um contrato marcado. Vou detalhar o primeiro selecionado.")
    return str(linhas_selecionadas.iloc[0].get("CONTRATO", "")).strip() or None


def _format_unidade_vigencia(value: Any) -> str:
    codigo = str(value or "").strip()
    if codigo.endswith(".0"):
        codigo = codigo[:-2]
    return UNIDADE_VIGENCIA_LABELS.get(codigo, codigo)


def _detail_frame(row: pd.Series, fornecedor: str, cnpj_fornecedor: str) -> pd.DataFrame:
    data = [
        ("Contrato", row.get("CONTRATO", "")),
        ("Filial", row.get("FILIAL_NOME", row.get("FILIAL", ""))),
        ("Tipo contrato", row.get("TIPO_CONTRATO", "")),
        ("Descricao tipo", row.get("DESC_TIPO_CONTRATO", row.get("TIPO", ""))),
        ("Situacao", row.get("STATUS", row.get("SITUACAO", ""))),
        ("Fornecedor", fornecedor),
        ("CNPJ/CPF", formatar_cnpj(cnpj_fornecedor)),
        ("Data inicio", formatar_data(row.get("DATA_INICIO"))),
        ("Data assinatura", formatar_data(row.get("DATA_ASSINATURA"))),
        ("Data fim", formatar_data(row.get("DATA_FIM"))),
        ("Condicao pagamento", row.get("CONDICAO_PAGAMENTO", row.get("COND_PAGAMENTO", ""))),
        ("Descricao condicao pagamento", row.get("DESCRICAO_CONDICAO_PAGAMENTO", "")),
        ("Unidade vigencia", _format_unidade_vigencia(row.get("UNIDADE_VIGENCIA", ""))),
        ("Dias restantes", row.get("DIAS_RESTANTES", "")),
    ]
    result = pd.DataFrame(data, columns=["Campo", "Valor"])
    result["Valor"] = result["Valor"].astype(str)
    return result


def render_consulta_contratos(
    df_contratos: Any = None,
    df_fornecedores: Any = None,
    df_medicoes: Any = None,
    df_financeiro: Any = None,
    df_itens: Any = None,
) -> None:
    st.header("Consulta de Contratos")
    st.caption("Tela detalhada para consulta unificada do contrato.")

    if df_contratos is None or getattr(df_contratos, "empty", True):
        st.warning("Nenhum contrato retornado pela consulta do Protheus.")
        return

    base = df_contratos.copy()
    fornecedor_base = _normalize_columns(df_fornecedores)
    if "FORNECEDOR" not in base.columns and not fornecedor_base.empty:
        base["FORNECEDOR"] = base["CONTRATO"].apply(lambda contrato: _lookup_fornecedor(pd.Series({"CONTRATO": contrato}), fornecedor_base))

    with st.expander("Filtros de consulta", expanded=True):
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            contrato = text_filter("Numero contrato", key="consulta_numero", placeholder="Ex.: 000001")
        with col2:
            filial = select_filter("Filial", options=opcoes_coluna(base, "FILIAL_NOME"), key="consulta_filial")
        with col3:
            fornecedor = text_filter("Fornecedor", key="consulta_fornecedor", placeholder="Nome ou razao social")
        with col4:
            tipo = select_filter("Tipo contrato", options=opcoes_coluna(base, "TIPO"), key="consulta_tipo")
        with col5:
            situacao = select_filter("Situação contrato", options=opcoes_coluna(base, "STATUS"), key="consulta_situacao")

    df = aplicar_filtros_carteira(
        base,
        {"contrato": contrato, "filial": filial, "tipo": tipo, "situacao": situacao},
    )
    df = _filter_by_text(df, "FORNECEDOR", fornecedor)

    st.markdown("### Resultado da consulta")
    colunas_base = [
        "CONTRATO",
        "FORNECEDOR",
        "CNPJ_FORNECEDOR",
        "FILIAL_NOME",
        "TIPO",
        "DESC_TIPO_CONTRATO",
        "DESCRICAO",
        "OBJETO_DO_CONTRATO",
        "DATA_INICIO",
        "DATA_FIM",
        "STATUS",
        "VALOR_INICIAL",
        "VALOR_ATUAL",
        "VALOR_EXECUTADO",
        "SALDO_CONTRATUAL",
        "PERCENTUAL_EXECUCAO",
    ]
    colunas_exibicao = [
        "CONTRATO",
        "FORNECEDOR",
        "CNPJ_FORNECEDOR",
        "FILIAL",
        "TIPO",
        "DESC_TIPO_CONTRATO",
        "DESCRIÇÃO",
        "OBJETO DO CONTRATO",
        "DATA_INÍCIO",
        "DATA_FIM",
        "STATUS",
        "VALOR_INICIAL",
        "VALOR_ATUAL",
        "VALOR_EXECUTADO",
        "SALDO_CONTRATUAL",
        "PERCENTUAL_EXECUÇÃO",
    ]
    colunas_presentes = list(dict.fromkeys(column for column in colunas_base if column in df.columns))
    df_exibicao = _format_display_table(df[colunas_presentes] if colunas_presentes else df)
    contrato_tabela = _render_selectable_contracts_table(_rename_display_columns(df_exibicao), colunas_exibicao)

    if df.empty:
        return

    opcoes_contrato = df["CONTRATO"].astype(str).drop_duplicates().sort_values().tolist()
    contrato_selecionado = contrato_tabela or st.selectbox("Detalhar contrato", opcoes_contrato, key="consulta_detalhe")
    contratos_detalhe = df[df["CONTRATO"].astype(str) == str(contrato_selecionado)].copy()
    opcoes_filial_detalhe, filial_por_label = _filiais_detalhamento(contratos_detalhe)
    filial_label = st.selectbox("Filial do contrato", opcoes_filial_detalhe, key="consulta_detalhe_filial")
    filial_detalhe = filial_por_label.get(filial_label, {})
    filial_codigo_detalhe = filial_detalhe.get("codigo", "")
    filial_nome_detalhe = filial_detalhe.get("nome", filial_label)
    detalhe_df = _filter_detail_scope(contratos_detalhe, contrato_selecionado, filial_codigo_detalhe, filial_nome_detalhe)
    if detalhe_df.empty:
        st.warning("Nenhum contrato encontrado para o detalhamento selecionado.")
        return

    detalhe = detalhe_df.iloc[0]
    fornecedor_detalhe = _lookup_fornecedor(detalhe, fornecedor_base)
    cnpj_detalhe = _lookup_cnpj(detalhe, fornecedor_base)
    filtros_detalhe = {"contrato": contrato_selecionado, "filial": filial_codigo_detalhe}
    medicoes_base = _load_medicoes(df_medicoes)
    medicoes_contrato = _filter_detail_scope(medicoes_base, contrato_selecionado, filial_codigo_detalhe, filial_nome_detalhe)
    itens_base = _load_itens_planilhas(df_itens)
    itens_contrato = _filter_detail_scope(itens_base, contrato_selecionado, filial_codigo_detalhe, filial_nome_detalhe)
    financeiro_base = _load_financeiro(df_financeiro)
    financeiro_contrato = _filter_detail_scope(aplicar_filtros_financeiro(financeiro_base, filtros_detalhe), contrato_selecionado, filial_codigo_detalhe, filial_nome_detalhe)
    adiantamentos_base = get_adiantamentos()
    adiantamentos_contrato = _filter_detail_scope(
        aplicar_filtros_adiantamentos(adiantamentos_base, filtros_detalhe),
        contrato_selecionado,
        filial_codigo_detalhe,
        filial_nome_detalhe,
    )

    st.markdown(
        f"""
        <div style="position:sticky;top:0;z-index:20;background:#FFFFFF;border:1px solid #DCE3EA;border-radius:12px;padding:14px 16px;margin:12px 0;box-shadow:0 2px 10px rgba(17,24,39,0.06);">
            <div style="font-size:0.78rem;color:#6B7280;text-transform:uppercase;letter-spacing:0.03em;">Ficha do contrato</div>
            <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:8px;font-size:0.88rem;color:#111827;">
                <div><strong>Contrato</strong><br>{detalhe.get("CONTRATO", "")}</div>
                <div><strong>Tipo</strong><br>{detalhe.get("TIPO", "")}</div>
                <div><strong>Descricao</strong><br>{detalhe.get("DESC_TIPO_CONTRATO", detalhe.get("TIPO", ""))}</div>
                <div><strong>Filial</strong><br>{detalhe.get("FILIAL_NOME", detalhe.get("FILIAL", ""))}</div>
                <div><strong>Situacao</strong><br>{detalhe.get("STATUS", detalhe.get("SITUACAO", ""))}</div>
                <div><strong>Fornecedor</strong><br>{fornecedor_detalhe}</div>
                <div><strong>CNPJ/CPF</strong><br>{formatar_cnpj(cnpj_detalhe)}</div>
                <div><strong>Data inicio</strong><br>{formatar_data(detalhe.get("DATA_INICIO"))}</div>
                <div><strong>Data fim</strong><br>{formatar_data(detalhe.get("DATA_FIM"))}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_kpi_cards(
        [
            {"title": "Valor inicial", "value": formatar_moeda(detalhe.get("VALOR_INICIAL", 0)), "subtitle": "Base tratada"},
            {"title": "Valor atualizado", "value": formatar_moeda(detalhe.get("VALOR_ATUAL", 0)), "subtitle": "Carteira atual"},
            {"title": "Valor executado", "value": formatar_moeda(detalhe.get("VALOR_EXECUTADO", 0)), "subtitle": "Valor atual menos saldo"},
            {"title": "Saldo", "value": formatar_moeda(detalhe.get("SALDO_CONTRATUAL", 0)), "subtitle": "Saldo contratual"},
            {"title": "Percentual executado", "value": formatar_percentual(detalhe.get("PERCENTUAL_EXECUCAO", 0)), "subtitle": "Execucao calculada"},
        ],
        columns=5,
    )

    render_insights(get_consulta_contrato_insights(detalhe, medicoes_contrato, financeiro_contrato, percent_formatter=formatar_percentual))

    tab_geral, tab_itens, tab_financeiro, tab_adiantamentos = st.tabs(
        ["Geral", "Itens", "Financeiro", "Adiantamentos"]
    )

    with tab_geral:
        render_table_section(
            title="Dados cadastrais do contrato",
            columns=["Campo", "Valor"],
            df=_detail_frame(detalhe, fornecedor_detalhe, cnpj_detalhe),
        )

    with tab_itens:
        kpis_itens = _summary_itens(itens_contrato)
        qtd_produtos = int(itens_contrato.loc[itens_contrato.get("TEM_ITEM", pd.Series(False, index=itens_contrato.index)).fillna(False).astype(bool), "PRODUTO"].nunique()) if "PRODUTO" in itens_contrato.columns else 0
        render_kpi_cards(
            [
                {"title": "Quantidade de planilhas", "value": formatar_quantidade(kpis_itens["qtd_planilhas"]), "subtitle": "Distinto por filial + contrato + planilha"},
                {"title": "Quantidade total de itens", "value": formatar_quantidade(kpis_itens["qtd_itens"]), "subtitle": "Registros reais de itens"},
                {"title": "Quantidade de produtos", "value": formatar_quantidade(qtd_produtos), "subtitle": "Produtos distintos no contrato"},
                {"title": "Valor contratado", "value": formatar_moeda(kpis_itens["valor_contratado"]), "subtitle": "Itens do contrato"},
                {"title": "Quantidade medida", "value": formatar_quantidade(kpis_itens["quantidade_medida"]), "subtitle": "CNB_QTDMED"},
                {"title": "Saldo contratado", "value": formatar_moeda(kpis_itens["saldo_contratado"]), "subtitle": "Contratado menos medido"},
            ],
            columns=3,
        )
        render_insights(
            get_itens_planilhas_insights(
                itens_contrato,
                money_formatter=formatar_moeda,
                percent_formatter=formatar_percentual,
                quantity_formatter=formatar_quantidade,
            )
        )

        render_table_section(
                title="Detalhamento completo",
                columns=["FILIAL", "CONTRATO", "FORNECEDOR", "PLANILHA", "DESC_TIPO_PLANILHA", "ITEM", "PRODUTO", "DESC_PRODUTO", "UNIDADE", "QUANTIDADE_CONTRATADA", "VALOR_UNITARIO", "VALOR_CONTRATADO", "DESCONTO"],
                df=_format_itens_table(_select_columns(itens_contrato, ["FILIAL", "CONTRATO", "FORNECEDOR", "PLANILHA", "DESC_TIPO_PLANILHA", "ITEM", "PRODUTO", "DESC_PRODUTO", "UNIDADE", "QUANTIDADE_CONTRATADA", "VALOR_UNITARIO", "VALOR_CONTRATADO", "DESCONTO"])),
            )

    with tab_financeiro:
        kpis_financeiro = resumo_financeiro(financeiro_contrato)
        render_kpi_cards(
            [
                {"title": "Valor total contratado", "value": formatar_moeda(kpis_financeiro["valor_total_contratado"]), "subtitle": "Base tratada"},
                {"title": "Valor previsto", "value": formatar_moeda(kpis_financeiro["valor_previsto"]), "subtitle": "CNF_VLPREV"},
                {"title": "Valor realizado", "value": formatar_moeda(kpis_financeiro["valor_realizado"]), "subtitle": "CNF_VLREAL"},
                {"title": "Saldo financeiro", "value": formatar_moeda(kpis_financeiro["saldo_financeiro"]), "subtitle": "Previsto menos realizado"},
                {"title": "Percentual realizado", "value": formatar_percentual(kpis_financeiro["percentual_realizado"]), "subtitle": "Realizado sobre previsto"},
                {"title": "Quantidade de parcelas", "value": formatar_quantidade(kpis_financeiro["qtd_parcelas"]), "subtitle": "Parcelas financeiras"},
                {"title": "Parcelas atrasadas", "value": formatar_quantidade(kpis_financeiro["parcelas_atrasadas"]), "subtitle": "Vencimento anterior ao realizado"},
                {"title": "Valor total adiantado", "value": formatar_moeda(kpis_financeiro["valor_total_adiantado"]), "subtitle": "CNX_VLADT"},
                {"title": "Saldo de adiantamentos", "value": formatar_moeda(kpis_financeiro["saldo_adiantamentos"]), "subtitle": "CNX_SALDO"},
            ],
            columns=3,
        )
        render_insights(get_financeiro_insights(financeiro_contrato, money_formatter=formatar_moeda, percent_formatter=formatar_percentual))

 
        render_table_section(
                title="Classificacao financeira dos contratos",
                columns=["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO", "STATUS", "PERCENTUAL_REALIZADO", "SALDO_FINANCEIRO", "CLASSIFICACAO_FINANCEIRA"],
                df=_format_financeiro_table(_select_columns(financeiro_contrato, ["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO", "STATUS", "PERCENTUAL_REALIZADO", "SALDO_FINANCEIRO", "CLASSIFICACAO_FINANCEIRA"])),
            )

    with tab_adiantamentos:
        kpis_adiantamentos = resumo_adiantamentos(adiantamentos_contrato, df[df["CONTRATO"].astype(str) == str(contrato_selecionado)])
        render_kpi_cards(
            [
                {"title": "Valor Total Adiantado", "value": formatar_moeda(kpis_adiantamentos["valor_total_adiantado"]), "subtitle": "Valor total adiantado em contratos"},
                {"title": "Contratos com Adiantamento", "value": formatar_quantidade(kpis_adiantamentos["qtd_contratos_adiantamento"]), "subtitle": "Quantidade de contratos com adiantamento"},
                {"title": "Ticket Medio dos Adiantamentos", "value": formatar_moeda(kpis_adiantamentos["ticket_medio_adiantamentos"]), "subtitle": "Valor medio dos adiantamentos"},
            ],
            columns=3,
        )
        render_insights(get_adiantamentos_insights(adiantamentos_contrato, kpis_adiantamentos, money_formatter=formatar_moeda, percent_formatter=formatar_percentual))

        if adiantamentos_contrato.empty:
            st.warning("Nenhum adiantamento encontrado para o contrato selecionado.")
        else:
            col_adt_1, col_adt_2 = st.columns(2)
            with col_adt_1:
                render_line_chart(
                    "Evolucao dos Adiantamentos por mes",
                    evolucao_adiantamentos_mensal(adiantamentos_contrato),
                    x="MES_ADIANTAMENTO",
                    y="VALOR_ADIANTAMENTO",
                    empty_message="Sem meses de adiantamento para exibir.",
                )
            with col_adt_2:
                render_bar_chart(
                    "Comparativo valor x saldo",
                    comparativo_valor_saldo(adiantamentos_contrato),
                    x="INDICADOR",
                    y="VALOR",
                    empty_message="Sem valores de adiantamento para exibir.",
                )

            render_table_section(
                title="Top Fornecedores por Valor Adiantado",
                columns=["FORNECEDOR", "VALOR_ADIANTAMENTO"],
                df=_format_adiantamentos_table(ranking_adiantamentos_por_coluna(adiantamentos_contrato, "FORNECEDOR")),
            )
            render_table_section(
                title="Detalhamento dos adiantamentos",
                columns=["FILIAL", "CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "NUMERO_ADIANTAMENTO", "DATA_ADIANTAMENTO", "VALOR_ADIANTAMENTO", "SALDO_ADIANTAMENTO", "STATUS", "TIPO"],
                df=_format_adiantamentos_table(detalhes_adiantamentos(adiantamentos_contrato)),
            )
