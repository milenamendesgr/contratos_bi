"""Itens e planilhas module."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import streamlit as st

from components.cards import render_insights, render_kpi_cards
from components.charts import render_bar_chart
from components.filters import select_filter, text_filter
from components.tables import render_table_section
from utils import contratos_repository
from utils.contratos_repository import get_carteira_contratos, run_sql
from utils.contratos_service import opcoes_coluna
from utils.formatters import formatar_moeda, formatar_percentual, formatar_quantidade
from utils.insights import get_itens_planilhas_insights
from config.settings import FILIAIS, DEMO_MODE
from utils.demo_data import carregar_demo


QUERY_PATH = Path(__file__).resolve().parents[1] / "queries" / "itens_planilhas.sql"

NUMERIC_COLUMNS = [
    "QUANTIDADE_CONTRATADA",
    "VALOR_UNITARIO",
    "VALOR_CONTRATADO",
    "DESCONTO",
    "QUANTIDADE_SOLICITADA",
    "QUANTIDADE_MEDIDA",
    "QUANTIDADE_REALIZADA",
    "VALOR_MEDIDO",
    "VALOR_LIQUIDADO",
    "VALOR_MULTA",
    "SALDO_QUANTIDADE",
    "PERCENTUAL_EXECUCAO",
    "QTD_REGISTROS_MEDICAO",
]

MONEY_COLUMNS = ["VALOR_UNITARIO", "VALOR_CONTRATADO", "DESCONTO", "VALOR_MEDIDO", "VALOR_LIQUIDADO", "VALOR_MULTA"]
QUANTITY_COLUMNS = ["QUANTIDADE_CONTRATADA", "QUANTIDADE_MEDIDA", "QUANTIDADE_REALIZADA", "SALDO_QUANTIDADE", "QTD_PLANILHAS", "QTD_ITENS", "QTD_CONTRATOS"]

SITUACAO_CONTRATO_LABELS = {
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


def _normalize_situacao_contrato(series: pd.Series) -> pd.Series:
    values = series.fillna("").astype(str).str.strip()

    # Converte valores numericos serializados (ex.: "5.0") para codigo de 2 digitos ("05").
    numeric_mask = values.str.fullmatch(r"\d+(?:\.0+)?", na=False)
    values.loc[numeric_mask] = (
        pd.to_numeric(values.loc[numeric_mask], errors="coerce")
        .fillna(0)
        .astype(int)
        .astype(str)
        .str.zfill(2)
    )

    return values


def _format_situacao_contrato_label(series: pd.Series) -> pd.Series:
    codes = _normalize_situacao_contrato(series)
    descriptions = codes.map(SITUACAO_CONTRATO_LABELS)
    labels = codes.where(descriptions.isna(), codes + " - " + descriptions)
    return labels.replace("", "Nao informado")


def _has_value(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().ne("")


def _normalize_itens(df: Any) -> pd.DataFrame:
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()

    result = df.copy()
    result.columns = [str(column).strip().upper() for column in result.columns]

    if "SITUACAO_CONTRATO" not in result.columns and "SITUAO_CONTRATO" in result.columns:
        result["SITUACAO_CONTRATO"] = result["SITUAO_CONTRATO"]

    for column in NUMERIC_COLUMNS:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = _to_number(result[column])

    for column in ["FILIAL", "CONTRATO", "COD_FORNECEDOR", "LOJA_FORNECEDOR", "NOME_FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO_CONTRATO", "DESC_TIPO_CONTRATO", "PLANILHA", "TIPO_PLANILHA", "DESC_TIPO_PLANILHA", "ITEM", "PRODUTO", "DESC_PRODUTO", "UNIDADE"]:
        if column not in result.columns:
            result[column] = ""
        result[column] = result[column].fillna("").astype(str).str.strip()

    if "SITUACAO_CONTRATO" not in result.columns:
        result["SITUACAO_CONTRATO"] = ""
    result["SITUACAO_CONTRATO"] = _normalize_situacao_contrato(result["SITUACAO_CONTRATO"])
    result["SITUACAO_CONTRATO_LABEL"] = _format_situacao_contrato_label(result["SITUACAO_CONTRATO"])

    result["FILIAL_NOME"] = result["FILIAL"].map(FILIAIS).fillna(result["FILIAL"])

    result["FORNECEDOR"] = result["NOME_FORNECEDOR"]
    result["FORNECEDOR_CHAVE"] = (
        result["COD_FORNECEDOR"] + " / " + result["LOJA_FORNECEDOR"] + " - " + result["NOME_FORNECEDOR"]
    ).str.strip(" /-")
    result["SALDO_VALOR"] = result["VALOR_CONTRATADO"] - result["VALOR_MEDIDO"]
    result["TEM_MEDICAO"] = result["QTD_REGISTROS_MEDICAO"] > 0
    result["TEM_CONTRATO"] = _has_value(result["FILIAL"]) & _has_value(result["CONTRATO"])
    result["TEM_PLANILHA"] = result["TEM_CONTRATO"] & _has_value(result["PLANILHA"])
    result["TEM_ITEM"] = result["TEM_PLANILHA"] & _has_value(result["ITEM"])
    result["CONTRATO_CHAVE"] = result["FILIAL"] + " | " + result["CONTRATO"]
    result["PLANILHA_CHAVE"] = result["CONTRATO_CHAVE"] + " | " + result["PLANILHA"]
    result["CONTRATO_LABEL"] = result["FILIAL"] + " / " + result["CONTRATO"]
    result["PLANILHA_LABEL"] = result["CONTRATO_LABEL"] + " / " + result["PLANILHA"]
    if "PERCENTUAL_EXECUCAO" in result.columns:
        result["PERCENTUAL_EXECUCAO"] = result["PERCENTUAL_EXECUCAO"].clip(lower=0, upper=100)
    return result


def _run_itens_planilhas_sql(sql: str) -> pd.DataFrame:
    return _normalize_itens(run_sql(sql.rstrip().rstrip(";")))


def _load_itens_planilhas_from_protheus() -> pd.DataFrame:
    if DEMO_MODE:
        return _normalize_itens(carregar_demo("itens"))
    sql = QUERY_PATH.read_text(encoding="utf-8")
    return _run_itens_planilhas_sql(sql)


def _load_itens_planilhas(df_itens: Any = None) -> pd.DataFrame:
    normalized = _normalize_itens(df_itens)
    if not normalized.empty:
        return normalized
    return _load_itens_planilhas_from_protheus()


@st.cache_data(ttl=900, show_spinner=False)
def _load_carteira_contratos() -> pd.DataFrame:
    carteira = get_carteira_contratos()
    if carteira is None or getattr(carteira, "empty", True):
        return pd.DataFrame()

    base = carteira.copy()
    base.columns = [str(column).strip().upper() for column in base.columns]
    for column in ["FILIAL", "CONTRATO", "DESC_TIPO_CONTRATO", "SITUACAO"]:
        if column not in base.columns:
            base[column] = ""
        base[column] = base[column].fillna("").astype(str).str.strip()

    base["FILIAL_NOME"] = base["FILIAL"].map(FILIAIS).fillna(base["FILIAL"])
    base["SITUACAO_CONTRATO_LABEL"] = _format_situacao_contrato_label(base["SITUACAO"])
    return base


def _count_total_contratos_carteira_filtrados() -> int:
    base = _load_carteira_contratos()
    if base.empty:
        return 0

    result = base.copy()
    filial = st.session_state.get("itens_planilhas_filial", "Todos")
    tipo_contrato = st.session_state.get("itens_planilhas_tipo_contrato", "Todos")
    situacao_contrato = st.session_state.get("itens_planilhas_situacao_contrato", "Todos")
    contrato = str(st.session_state.get("itens_planilhas_contrato", "") or "").strip().lower()

    if filial and filial != "Todos" and "FILIAL_NOME" in result.columns:
        result = result[result["FILIAL_NOME"] == filial]
    if tipo_contrato and tipo_contrato != "Todos" and "DESC_TIPO_CONTRATO" in result.columns:
        result = result[result["DESC_TIPO_CONTRATO"] == tipo_contrato]
    if situacao_contrato and situacao_contrato != "Todos" and "SITUACAO_CONTRATO_LABEL" in result.columns:
        result = result[result["SITUACAO_CONTRATO_LABEL"] == situacao_contrato]
    if contrato and "CONTRATO" in result.columns:
        result = result[result["CONTRATO"].astype(str).str.lower().str.contains(contrato, na=False)]

    if "FILIAL" in result.columns and "CONTRATO" in result.columns:
        return int(result[["FILIAL", "CONTRATO"]].drop_duplicates().shape[0])
    if "CONTRATO" in result.columns:
        return int(result["CONTRATO"].astype(str).str.strip().replace("", pd.NA).dropna().nunique())
    return int(len(result))


def _format_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()
    for column in MONEY_COLUMNS + ["SALDO_VALOR"]:
        if column in result.columns:
            result[column] = result[column].apply(formatar_moeda)
    for column in QUANTITY_COLUMNS:
        if column in result.columns:
            result[column] = result[column].apply(formatar_quantidade)
    if "PERCENTUAL_EXECUCAO" in result.columns:
        result["PERCENTUAL_EXECUCAO"] = result["PERCENTUAL_EXECUCAO"].apply(formatar_percentual)
    return result


def _apply_filters(df: pd.DataFrame, filters: Mapping[str, Any]) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()
    filial = filters.get("filial")
    tipo_planilha = filters.get("tipo_planilha")
    tipo_contrato = filters.get("tipo_contrato")
    contrato = str(filters.get("contrato") or "").strip().lower()
    produto = str(filters.get("produto") or "").strip().lower()
    situacao_contrato = filters.get("situacao_contrato")

    if filial and filial != "Todos" and "FILIAL_NOME" in result.columns:
        result = result[result["FILIAL_NOME"] == filial]
    if tipo_planilha and tipo_planilha != "Todos" and "DESC_TIPO_PLANILHA" in result.columns:
        result = result[result["DESC_TIPO_PLANILHA"] == tipo_planilha]
    if tipo_contrato and tipo_contrato != "Todos" and "DESC_TIPO_CONTRATO" in result.columns:
        result = result[result["DESC_TIPO_CONTRATO"] == tipo_contrato]
    if contrato and "CONTRATO" in result.columns:
        result = result[result["CONTRATO"].astype(str).str.lower().str.contains(contrato, na=False)]
    if produto:
        mask = result["PRODUTO"].astype(str).str.lower().str.contains(produto, na=False)
        mask = mask | result["DESC_PRODUTO"].astype(str).str.lower().str.contains(produto, na=False)
        result = result[mask]
    if situacao_contrato and situacao_contrato != "Todos" and "SITUACAO_CONTRATO_LABEL" in result.columns:
        result = result[result["SITUACAO_CONTRATO_LABEL"] == situacao_contrato]

    return result


def _distinct_count(df: pd.DataFrame, columns: list[str], flag_column: str | None = None) -> int:
    if df.empty or any(column not in df.columns for column in columns):
        return 0
    result = df
    if flag_column and flag_column in result.columns:
        result = result[result[flag_column].fillna(False).astype(bool)]
    return int(result[columns].drop_duplicates().shape[0])


def _contratos_sem_planilha(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["FILIAL", "CONTRATO", "FORNECEDOR", "DESC_TIPO_CONTRATO", "SITUACAO_CONTRATO_LABEL"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    base = df[df["TEM_CONTRATO"]].copy()
    if base.empty:
        return pd.DataFrame(columns=columns)

    planilhas_por_contrato = (
        base.groupby(["FILIAL", "CONTRATO"], dropna=False)["TEM_PLANILHA"]
        .sum()
        .reset_index(name="QTD_PLANILHAS")
    )
    sem_planilha = planilhas_por_contrato[planilhas_por_contrato["QTD_PLANILHAS"] == 0][["FILIAL", "CONTRATO"]]
    if sem_planilha.empty:
        return pd.DataFrame(columns=columns)

    return (
        base.merge(sem_planilha, on=["FILIAL", "CONTRATO"], how="inner")
        .drop_duplicates(["FILIAL", "CONTRATO"])
        .sort_values(["FILIAL", "CONTRATO"])[columns]
    )


def _planilhas_sem_itens(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["FILIAL", "CONTRATO", "PLANILHA", "DESC_TIPO_PLANILHA", "FORNECEDOR"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    base = df[df["TEM_PLANILHA"]].copy()
    if base.empty:
        return pd.DataFrame(columns=columns)

    itens_por_planilha = (
        base.groupby(["FILIAL", "CONTRATO", "PLANILHA"], dropna=False)["TEM_ITEM"]
        .sum()
        .reset_index(name="QTD_ITENS")
    )
    sem_itens = itens_por_planilha[itens_por_planilha["QTD_ITENS"] == 0][["FILIAL", "CONTRATO", "PLANILHA"]]
    if sem_itens.empty:
        return pd.DataFrame(columns=columns)

    return (
        base.merge(sem_itens, on=["FILIAL", "CONTRATO", "PLANILHA"], how="inner")
        .drop_duplicates(["FILIAL", "CONTRATO", "PLANILHA"])
        .sort_values(["FILIAL", "CONTRATO", "PLANILHA"])[columns]
    )


def _render_filters(df: pd.DataFrame) -> pd.DataFrame:
    with st.expander("Filtros", expanded=True):
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            filial = select_filter("Filial", opcoes_coluna(df, "FILIAL_NOME"), key="itens_planilhas_filial")
        with col6:
            situacao_contrato = select_filter("Situação contrato", opcoes_coluna(df, "SITUACAO_CONTRATO_LABEL"), key="itens_planilhas_situacao_contrato")
        with col2:
            tipo_planilha = select_filter("Tipo planilha", opcoes_coluna(df, "DESC_TIPO_PLANILHA"), key="itens_planilhas_tipo_planilha")
        with col3:
            tipo_contrato = select_filter("Tipo contrato", opcoes_coluna(df, "DESC_TIPO_CONTRATO"), key="itens_planilhas_tipo_contrato")
        with col4:
            contrato = text_filter("Contrato", key="itens_planilhas_contrato", placeholder="Numero")
        with col5:
            produto = text_filter("Produto", key="itens_planilhas_produto", placeholder="Codigo ou descricao")

    return _apply_filters(
        df,
        {
            "filial": filial,
            "tipo_planilha": tipo_planilha,
            "tipo_contrato": tipo_contrato,
            "contrato": contrato,
            "produto": produto,
            "situacao_contrato": situacao_contrato,
        },
    )


def _summary(df: pd.DataFrame) -> dict[str, float | int]:
    contratos_sem_planilha = _contratos_sem_planilha(df)
    planilhas_sem_itens = _planilhas_sem_itens(df)

    if df.empty:
        return {
            "qtd_contratos": 0,
            "qtd_planilhas": 0,
            "qtd_itens": 0,
            "qtd_contratos_sem_planilha": 0,
            "qtd_contratos_planilha_sem_item": 0,
            "qtd_planilhas_sem_itens": 0,
            "valor_contratado": 0.0,
            "valor_medido": 0.0,
            "quantidade_medida": 0.0,
            "saldo_contratado": 0.0,
        }

    linhas_itens = df[df["TEM_ITEM"]]
    return {
        "qtd_contratos": _distinct_count(df, ["FILIAL", "CONTRATO"], "TEM_CONTRATO"),
        "qtd_planilhas": _distinct_count(df, ["FILIAL", "CONTRATO", "PLANILHA"], "TEM_PLANILHA"),
        "qtd_itens": int(df["TEM_ITEM"].sum()),
        "qtd_contratos_sem_planilha": _distinct_count(contratos_sem_planilha, ["FILIAL", "CONTRATO"]),
        "qtd_contratos_planilha_sem_item": _distinct_count(planilhas_sem_itens, ["FILIAL", "CONTRATO"]),
        "qtd_planilhas_sem_itens": _distinct_count(planilhas_sem_itens, ["FILIAL", "CONTRATO", "PLANILHA"]),
        "valor_contratado": float(linhas_itens["VALOR_CONTRATADO"].sum()),
        "valor_medido": float(linhas_itens["VALOR_MEDIDO"].sum()),
        "quantidade_medida": float(linhas_itens["QUANTIDADE_MEDIDA"].sum()),
        "saldo_contratado": float((linhas_itens["VALOR_CONTRATADO"] - linhas_itens["VALOR_MEDIDO"]).sum()),
    }


def _contratos_maior_qtd_planilhas(df: pd.DataFrame, limit: int | None = 15) -> pd.DataFrame:
    columns = ["FILIAL", "CONTRATO", "FORNECEDOR", "QTD_PLANILHAS", "QTD_ITENS", "VALOR_CONTRATADO"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    contratos = df[df["TEM_CONTRATO"]].drop_duplicates(["FILIAL", "CONTRATO"])[["FILIAL", "CONTRATO", "FORNECEDOR"]]
    planilhas = (
        df[df["TEM_PLANILHA"]]
        .drop_duplicates(["FILIAL", "CONTRATO", "PLANILHA"])
        .groupby(["FILIAL", "CONTRATO"], dropna=False)
        .size()
        .reset_index(name="QTD_PLANILHAS")
    )
    itens = (
        df[df["TEM_ITEM"]]
        .groupby(["FILIAL", "CONTRATO"], dropna=False)
        .agg(QTD_ITENS=("ITEM", "count"), VALOR_CONTRATADO=("VALOR_CONTRATADO", "sum"))
        .reset_index()
    )

    result = contratos.merge(planilhas, on=["FILIAL", "CONTRATO"], how="left").merge(itens, on=["FILIAL", "CONTRATO"], how="left")
    result[["QTD_PLANILHAS", "QTD_ITENS", "VALOR_CONTRATADO"]] = result[["QTD_PLANILHAS", "QTD_ITENS", "VALOR_CONTRATADO"]].fillna(0)
    result = result.sort_values(["QTD_PLANILHAS", "QTD_ITENS"], ascending=False)
    if limit is not None:
        result = result.head(limit)
    return result[columns]


def _planilhas_maior_qtd_itens(df: pd.DataFrame, limit: int = 15) -> pd.DataFrame:
    columns = ["FILIAL", "CONTRATO", "PLANILHA", "DESC_TIPO_PLANILHA", "QTD_ITENS", "VALOR_CONTRATADO"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    planilhas = df[df["TEM_PLANILHA"]].drop_duplicates(["FILIAL", "CONTRATO", "PLANILHA"])[
        ["FILIAL", "CONTRATO", "PLANILHA", "DESC_TIPO_PLANILHA"]
    ]
    itens = (
        df[df["TEM_ITEM"]]
        .groupby(["FILIAL", "CONTRATO", "PLANILHA"], dropna=False)
        .agg(QTD_ITENS=("ITEM", "count"), VALOR_CONTRATADO=("VALOR_CONTRATADO", "sum"))
        .reset_index()
    )
    result = planilhas.merge(itens, on=["FILIAL", "CONTRATO", "PLANILHA"], how="left")
    result[["QTD_ITENS", "VALOR_CONTRATADO"]] = result[["QTD_ITENS", "VALOR_CONTRATADO"]].fillna(0)
    return result.sort_values(["QTD_ITENS", "VALOR_CONTRATADO"], ascending=False).head(limit)[columns]


def _ranking_contratos_itens(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    ranking = _contratos_maior_qtd_planilhas(df, limit=None)
    if ranking.empty:
        return ranking.assign(CONTRATO_LABEL=pd.Series(dtype=str))
    ranking = ranking.sort_values("QTD_ITENS", ascending=False).head(limit).copy()
    ranking["CONTRATO_LABEL"] = ranking["FILIAL"] + " / " + ranking["CONTRATO"]
    return ranking


def _ranking_contratos_planilhas(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    ranking = _contratos_maior_qtd_planilhas(df, limit=limit).copy()
    if ranking.empty:
        return ranking.assign(CONTRATO_LABEL=pd.Series(dtype=str))
    ranking["CONTRATO_LABEL"] = ranking["FILIAL"] + " / " + ranking["CONTRATO"]
    return ranking


def _ranking_fornecedores_itens(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    columns = ["FORNECEDOR", "QTD_ITENS"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    return (
        df[df["TEM_ITEM"]]
        .assign(FORNECEDOR=lambda data: data["FORNECEDOR"].replace("", "Nao informado"))
        .groupby("FORNECEDOR", dropna=False)
        .size()
        .reset_index(name="QTD_ITENS")
        .sort_values("QTD_ITENS", ascending=False)
        .head(limit)
    )


def _ranking_fornecedores_planilhas(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    columns = ["FORNECEDOR", "QTD_PLANILHAS"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    return (
        df[df["TEM_PLANILHA"]]
        .assign(FORNECEDOR=lambda data: data["FORNECEDOR"].replace("", "Nao informado"))
        .drop_duplicates(["FORNECEDOR", "FILIAL", "CONTRATO", "PLANILHA"])
        .groupby("FORNECEDOR", dropna=False)
        .size()
        .reset_index(name="QTD_PLANILHAS")
        .sort_values("QTD_PLANILHAS", ascending=False)
        .head(limit)
    )


def _distribuicao_por_contrato(df: pd.DataFrame, value_column: str) -> pd.DataFrame:
    columns = [value_column, "QTD_CONTRATOS"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    contratos = _contratos_maior_qtd_planilhas(df, limit=None)
    if contratos.empty or value_column not in contratos.columns:
        return pd.DataFrame(columns=columns)
    return (
        contratos[value_column]
        .astype(int)
        .value_counts()
        .sort_index()
        .rename_axis(value_column)
        .reset_index(name="QTD_CONTRATOS")
    )


def _ranking_itens_valor(df: pd.DataFrame, limit: int = 15) -> pd.DataFrame:
    columns = ["PRODUTO", "DESC_PRODUTO", "VALOR_CONTRATADO"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    return (
        df.groupby(["PRODUTO", "DESC_PRODUTO"], dropna=False)["VALOR_CONTRATADO"]
        .sum()
        .sort_values(ascending=False)
        .head(limit)
        .reset_index()
    )


def _ranking_consumo(df: pd.DataFrame, limit: int = 15) -> pd.DataFrame:
    columns = ["PRODUTO", "DESC_PRODUTO", "QUANTIDADE_CONTRATADA", "QUANTIDADE_MEDIDA", "PERCENTUAL_EXECUCAO"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    result = (
        df.groupby(["PRODUTO", "DESC_PRODUTO"], dropna=False)[["QUANTIDADE_CONTRATADA", "QUANTIDADE_MEDIDA"]]
        .sum()
        .reset_index()
    )
    result["PERCENTUAL_EXECUCAO"] = result.apply(
        lambda row: min((row["QUANTIDADE_MEDIDA"] / row["QUANTIDADE_CONTRATADA"] * 100), 100.0) if row["QUANTIDADE_CONTRATADA"] else 0.0,
        axis=1,
    )
    return result.sort_values("PERCENTUAL_EXECUCAO", ascending=False).head(limit)


def _itens_criticos(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "PLANILHA", "ITEM", "PRODUTO", "DESC_PRODUTO", "QUANTIDADE_CONTRATADA", "QUANTIDADE_MEDIDA", "PERCENTUAL_EXECUCAO", "SALDO_QUANTIDADE"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    return df[df["PERCENTUAL_EXECUCAO"] >= 90].sort_values("PERCENTUAL_EXECUCAO", ascending=False)[columns]


def _itens_sem_medicao(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "PLANILHA", "ITEM", "PRODUTO", "DESC_PRODUTO", "QUANTIDADE_CONTRATADA", "VALOR_CONTRATADO"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    return df[~df["TEM_MEDICAO"]].sort_values("VALOR_CONTRATADO", ascending=False)[columns]


def _distribuicao_tipo_planilha(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["DESC_TIPO_PLANILHA", "QTD_PLANILHAS", "QTD_ITENS", "VALOR_CONTRATADO"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    planilhas = df[df["TEM_PLANILHA"]].drop_duplicates(["DESC_TIPO_PLANILHA", "FILIAL", "CONTRATO", "PLANILHA"])
    qtd_planilhas = planilhas.groupby("DESC_TIPO_PLANILHA", dropna=False).size().reset_index(name="QTD_PLANILHAS")
    itens = (
        df[df["TEM_ITEM"]]
        .groupby("DESC_TIPO_PLANILHA", dropna=False)
        .agg(QTD_ITENS=("ITEM", "count"), VALOR_CONTRATADO=("VALOR_CONTRATADO", "sum"))
        .reset_index()
    )
    result = qtd_planilhas.merge(itens, on="DESC_TIPO_PLANILHA", how="left")
    result[["QTD_ITENS", "VALOR_CONTRATADO"]] = result[["QTD_ITENS", "VALOR_CONTRATADO"]].fillna(0)
    result = result.sort_values("VALOR_CONTRATADO", ascending=False)
    result["DESC_TIPO_PLANILHA"] = result["DESC_TIPO_PLANILHA"].replace("", "Nao informado")
    return result


def render_itens_planilhas(
    df_contratos: Any = None,
    df_fornecedores: Any = None,
    df_medicoes: Any = None,
    df_financeiro: Any = None,
    df_itens: Any = None,
) -> None:
    st.header("Itens e Planilhas")
    st.caption("Analise granular de planilhas, itens contratados, consumo e limites de execucao.")

    base = _load_itens_planilhas(df_itens)
    if base.empty:
        st.warning("Nenhum contrato, planilha ou item foi retornado pela consulta de Itens de Planilhas.")
        if contratos_repository.LAST_ERROR:
            st.caption(f"Detalhe da consulta Protheus: {contratos_repository.LAST_ERROR}")
        return

    df = _render_filters(base)
    kpis = _summary(df)

    cards = [
        {"title": "Quantidade de contratos", "value": formatar_quantidade(kpis["qtd_contratos"]), "subtitle": "Distinto por filial + contrato"},
        {"title": "Quantidade de planilhas", "value": formatar_quantidade(kpis["qtd_planilhas"]), "subtitle": "Distinto por filial + contrato + planilha"},
        {"title": "Quantidade total de itens", "value": formatar_quantidade(kpis["qtd_itens"]), "subtitle": "Registros reais de itens"},
        {"title": "Contratos sem planilha", "value": formatar_quantidade(kpis["qtd_contratos_sem_planilha"]), "subtitle": "Contrato sem planilha vinculada"},
        {"title": "Contratos com planilha sem item", "value": formatar_quantidade(kpis["qtd_contratos_planilha_sem_item"]), "subtitle": "Contratos afetados"},
        {"title": "Planilhas sem itens", "value": formatar_quantidade(kpis["qtd_planilhas_sem_itens"]), "subtitle": "Planilhas sem itens vinculados"},
    ]
    render_kpi_cards(cards, columns=3)

    render_insights(
        get_itens_planilhas_insights(
            df,
            money_formatter=formatar_moeda,
            percent_formatter=formatar_percentual,
            quantity_formatter=formatar_quantidade,
        )
    )

    if df.empty:
        st.warning("Nenhum item encontrado para os filtros selecionados.")
        return
    
    
    render_table_section(
        title="Contratos sem planilha",
        columns=["FILIAL", "CONTRATO", "FORNECEDOR", "DESC_TIPO_CONTRATO", "SITUACAO_CONTRATO_LABEL"],
        df=_contratos_sem_planilha(df),
        empty_message="Todos os contratos filtrados possuem ao menos uma planilha vinculada.",
    )

    render_table_section(
        title="Planilhas sem itens",
        columns=["FILIAL", "CONTRATO", "PLANILHA", "DESC_TIPO_PLANILHA", "FORNECEDOR"],
        df=_planilhas_sem_itens(df),
        empty_message="Todas as planilhas filtradas possuem ao menos um item vinculado.",
    )

    col7, col8 = st.columns(2)
    with col7:
        render_table_section(
            title="Contratos com maior quantidade de planilhas",
            columns=["FILIAL", "CONTRATO", "FORNECEDOR", "QTD_PLANILHAS", "QTD_ITENS", "VALOR_CONTRATADO"],
            df=_format_table(_contratos_maior_qtd_planilhas(df)),
        )
    with col8:
        render_table_section(
            title="Planilhas com maior quantidade de itens",
            columns=["FILIAL", "CONTRATO", "PLANILHA", "DESC_TIPO_PLANILHA", "QTD_ITENS", "VALOR_CONTRATADO"],
            df=_format_table(_planilhas_maior_qtd_itens(df)),
        )

    distribuicao = _distribuicao_tipo_planilha(df)

    render_table_section(
        title="Distribuicao por tipo de planilha",
        columns=["DESC_TIPO_PLANILHA", "QTD_PLANILHAS", "QTD_ITENS", "VALOR_CONTRATADO"],
        df=_format_table(distribuicao),
    )

    render_table_section(
        title="Detalhamento completo",
        columns=["FILIAL", "CONTRATO", "FORNECEDOR", "PLANILHA", "DESC_TIPO_PLANILHA", "ITEM", "PRODUTO", "DESC_PRODUTO", "UNIDADE", "QUANTIDADE_CONTRATADA", "VALOR_UNITARIO", "VALOR_CONTRATADO", "DESCONTO"],
        df=_format_table(
            df[
                [
                    "FILIAL",
                    "CONTRATO",
                    "FORNECEDOR",
                    "PLANILHA",
                    "DESC_TIPO_PLANILHA",
                    "ITEM",
                    "PRODUTO",
                    "DESC_PRODUTO",
                    "UNIDADE",
                    "QUANTIDADE_CONTRATADA",
                    "VALOR_UNITARIO",
                    "VALOR_CONTRATADO",
                    "DESCONTO",
                ]
            ]
        ),
    )
