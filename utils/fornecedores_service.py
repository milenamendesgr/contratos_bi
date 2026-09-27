"""Business rules for supplier and contract portfolio analysis."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from config.settings import FILIAIS


TEXT_COLUMNS = [
    "FILIAL",
    "COD_FORNECEDOR",
    "LOJA_FORNECEDOR",
    "NOME_FORNECEDOR",
    "CNPJ_FORNECEDOR",
    "CONTRATO",
    "TIPO_CONTRATO",
    "DESC_TIPO_CONTRATO",
    "SITUACAO",
    "STATUS_CONTRATO",
]
DATE_COLUMNS = ["DATA_INICIO", "DATA_FINAL"]
NUMERIC_COLUMNS = ["VALOR_CONTRATO", "SALDO_CONTRATO"]
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


def _to_datetime(series: pd.Series) -> pd.Series:
    values = series.astype(str).str.strip().replace({"": None, "nan": None, "None": None})
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    protheus_mask = values.str.fullmatch(r"\d{8}", na=False)
    result.loc[protheus_mask] = pd.to_datetime(values.loc[protheus_mask], format="%Y%m%d", errors="coerce")
    result.loc[~protheus_mask] = pd.to_datetime(values.loc[~protheus_mask], dayfirst=True, errors="coerce")
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


def _normalize_status(status_contrato: pd.Series, situacao: pd.Series) -> pd.Series:
    status = status_contrato.fillna("").astype(str).str.strip()
    situacao_texto = situacao.fillna("").astype(str).str.strip()
    fallback = situacao_texto.map(STATUS_LABELS).fillna(situacao_texto)
    return status.where(status.ne(""), fallback).replace("", "Nao informado")


def preparar_fornecedores(df: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize supplier rows returned by the official CN9/CNC/SA2 relationship."""
    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()
    result.columns = [str(column).strip().upper() for column in result.columns]

    for column in TEXT_COLUMNS:
        if column not in result.columns:
            result[column] = ""
        result[column] = result[column].fillna("").astype(str).str.strip()

    for column in DATE_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NaT
        result[column] = _to_datetime(result[column])

    for column in NUMERIC_COLUMNS:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = _to_number(result[column])

    result["TIPO"] = result["DESC_TIPO_CONTRATO"].where(
        result["DESC_TIPO_CONTRATO"].ne(""),
        result["TIPO_CONTRATO"].replace("", "Nao informado"),
    )
    result["STATUS"] = _normalize_status(result["STATUS_CONTRATO"], result["SITUACAO"])
    result["FORNECEDOR"] = result["NOME_FORNECEDOR"]
    result["FORNECEDOR_CHAVE"] = result["COD_FORNECEDOR"] + " / " + result["LOJA_FORNECEDOR"] + " - " + result["FORNECEDOR"]

    valor_total = float(result["VALOR_CONTRATO"].sum())
    result["PARTICIPACAO_FORNECEDOR"] = 0.0
    if valor_total:
        valores_fornecedor = result.groupby("FORNECEDOR_CHAVE")["VALOR_CONTRATO"].transform("sum")
        result["PARTICIPACAO_FORNECEDOR"] = valores_fornecedor / valor_total * 100

    result["FILIAL_NOME"] = result["FILIAL"].map(FILIAIS).fillna(result["FILIAL"])

    return result.sort_values("VALOR_CONTRATO", ascending=False).reset_index(drop=True)


def aplicar_filtros_fornecedores(df: pd.DataFrame, filtros: Mapping[str, Any]) -> pd.DataFrame:
    """Apply supplier dashboard filters."""
    if df.empty:
        return df

    result = df.copy()
    filial = filtros.get("filial")
    fornecedor = str(filtros.get("fornecedor") or "").strip().lower()
    tipo = filtros.get("tipo")
    situacao = filtros.get("situacao")
    contrato = str(filtros.get("contrato") or "").strip().lower()

    if filial and filial != "Todos" and "FILIAL_NOME" in result.columns:
        result = result[result["FILIAL_NOME"] == filial]
    if fornecedor and "FORNECEDOR_CHAVE" in result.columns:
        result = result[result["FORNECEDOR_CHAVE"].astype(str).str.lower().str.contains(fornecedor, na=False)]
    if tipo and tipo != "Todos" and "TIPO" in result.columns:
        result = result[result["TIPO"] == tipo]
    if situacao and situacao != "Todos" and "STATUS" in result.columns:
        result = result[result["STATUS"] == situacao]
    if contrato and "CONTRATO" in result.columns:
        result = result[result["CONTRATO"].astype(str).str.lower().str.contains(contrato, na=False)]

    return result


def resumo_fornecedores(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "total_fornecedores": 0,
            "total_contratos": 0,
            "valor_total_contratado": 0.0,
            "saldo_total_contratado": 0.0,
            "ticket_medio_fornecedor": 0.0,
            "inconsistencias_fornecedor": 0,
            "classificacao_concentracao": "Baixa concentração",
            "descricao_concentracao": "Carteira distribuída.",
        }

    fornecedores_validos = df.loc[df["FORNECEDOR"].astype(str).str.strip().ne(""), "FORNECEDOR_CHAVE"].nunique()
    if {"FILIAL", "CONTRATO"}.issubset(df.columns):
        total_contratos = df[["FILIAL", "CONTRATO"]].drop_duplicates().shape[0]
    else:
        total_contratos = df["CONTRATO"].nunique() if "CONTRATO" in df.columns else len(df)
    valor_total = float(df["VALOR_CONTRATO"].sum())
    saldo_total = float(df["SALDO_CONTRATO"].sum())
    ticket_medio = valor_total / fornecedores_validos if fornecedores_validos else 0.0
    inconsistencias_fornecedor = df.loc[df["FORNECEDOR"].astype(str).str.strip().eq(""), "CONTRATO"].nunique()

    ranking = ranking_fornecedores(df)
    participacao_top_3 = float(ranking.head(3)["PARTICIPACAO"].sum()) if not ranking.empty else 0.0
    classificacao, descricao = classificar_concentracao(participacao_top_3)

    return {
        "total_fornecedores": int(fornecedores_validos),
        "total_contratos": int(total_contratos),
        "valor_total_contratado": valor_total,
        "saldo_total_contratado": saldo_total,
        "ticket_medio_fornecedor": ticket_medio,
        "inconsistencias_fornecedor": int(inconsistencias_fornecedor),
        "classificacao_concentracao": classificacao,
        "descricao_concentracao": descricao,
    }


def classificar_concentracao(participacao_top_3: float) -> tuple[str, str]:
    if participacao_top_3 >= 70:
        return "Alto risco", "Grande dependência de poucos fornecedores."
    if participacao_top_3 >= 45:
        return "Atenção", "Alguns fornecedores possuem grande participação."
    return "Baixa concentração", "Carteira distribuída."


def ranking_fornecedores(df: pd.DataFrame, limit: int | None = None) -> pd.DataFrame:
    columns = ["FORNECEDOR", "CNPJ_FORNECEDOR", "COD_FORNECEDOR", "QTD_CONTRATOS", "VALOR_CONTRATADO", "SALDO", "PARTICIPACAO"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    valor_total = float(df["VALOR_CONTRATO"].sum())
    result = (
        df.groupby(["FORNECEDOR_CHAVE", "FORNECEDOR", "CNPJ_FORNECEDOR", "COD_FORNECEDOR"], dropna=False)
        .agg(
            QTD_CONTRATOS=("CONTRATO", "nunique"),
            VALOR_CONTRATADO=("VALOR_CONTRATO", "sum"),
            SALDO=("SALDO_CONTRATO", "sum"),
        )
        .reset_index()
        .sort_values("VALOR_CONTRATADO", ascending=False)
    )
    result["PARTICIPACAO"] = result["VALOR_CONTRATADO"].apply(lambda value: (value / valor_total * 100) if valor_total else 0.0)
    result = result[columns]
    if limit:
        result = result.head(limit)
    return result.reset_index(drop=True)



def top_fornecedores(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    ranking = ranking_fornecedores(df, limit=limit)
    if ranking.empty:
        return pd.DataFrame(columns=["FORNECEDOR", "VALOR_CONTRATADO"])
    return ranking[["FORNECEDOR", "VALOR_CONTRATADO"]]


def inconsistencias_fornecedor(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "COD_FORNECEDOR", "LOJA_FORNECEDOR", "VALOR_CONTRATO", "STATUS", "TIPO"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    result = df[df["FORNECEDOR"].astype(str).str.strip().eq("")]
    return result.sort_values("VALOR_CONTRATO", ascending=False)[columns].reset_index(drop=True)


def detalhe_fornecedor(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "COD_FORNECEDOR", "LOJA_FORNECEDOR", "TIPO", "STATUS", "VALOR_CONTRATO", "SALDO_CONTRATO"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    return df.sort_values("VALOR_CONTRATO", ascending=False)[columns].reset_index(drop=True)