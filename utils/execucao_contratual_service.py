"""Business rules for contractual execution analysis."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd


TEXT_COLUMNS = [
    "FILIAL",
    "CONTRATO",
    "COD_FORNECEDOR",
    "LOJA_FORNECEDOR",
    "NOME_FORNECEDOR",
    "CNPJ_FORNECEDOR",
    "TIPO_CONTRATO",
    "DESC_TIPO_CONTRATO",
    "SITUACAO",
    "STATUS_CONTRATO",
]
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
NUMERIC_COLUMNS = [
    "VALOR_INICIAL",
    "VALOR_ATUAL",
    "SALDO_CONTRATO",
    "QTD_MEDICOES",
    "VALOR_MEDIDO",
    "VALOR_LIQUIDADO",
    "QUANTIDADE_MEDIDA",
    "VALOR_MULTA",
    "SALDO_EXECUCAO",
    "PERCENTUAL_EXECUCAO",
]
RANKING_COLUMNS = [
    "CONTRATO",
    "FORNECEDOR",
    "CNPJ_FORNECEDOR",
    "TIPO",
    "STATUS",
    "VALOR_ATUAL",
    "VALOR_MEDIDO",
    "SALDO_EXECUCAO",
    "PERCENTUAL_EXECUCAO",
    "CLASSIFICACAO_EXECUCAO",
]
EXECUTION_BINS = [0, 25, 50, 75, 100]
EXECUTION_LABELS = ["0% a 25%", "25% a 50%", "50% a 75%", "75% a 100%"]


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


def _safe_percent(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace(0, pd.NA)
    return (numerator / denominator * 100).fillna(0.0)


def _normalize_status(status_contrato: pd.Series, situacao: pd.Series) -> pd.Series:
    status = status_contrato.fillna("").astype(str).str.strip()
    situacao_texto = situacao.fillna("").astype(str).str.strip()
    fallback = situacao_texto.map(STATUS_LABELS).fillna(situacao_texto)
    return status.where(status.ne(""), fallback).replace("", "Nao informado")


def classificar_execucao(percentual: Any) -> str:
    value = float(percentual or 0.0)
    if value < 25:
        return "🔴 Baixa execução"
    if value < 75:
        return "🟡 Atenção"
    return "🟢 Execução adequada"


def preparar_execucao_contratual(df: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize Protheus execution rows and add calculated fields."""
    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()
    result.columns = [str(column).strip().upper() for column in result.columns]

    for column in TEXT_COLUMNS:
        if column not in result.columns:
            result[column] = ""
        result[column] = result[column].fillna("").astype(str).str.strip()

    date_columns = [column for column in result.columns if column.startswith("DATA") or column.startswith("DT_")]
    for column in date_columns:
        result[column] = _to_datetime(result[column])

    for column in NUMERIC_COLUMNS:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = _to_number(result[column])

    result["TIPO"] = result["DESC_TIPO_CONTRATO"].where(
        result["DESC_TIPO_CONTRATO"].ne(""),
        result["TIPO_CONTRATO"].replace("", "Nao informado"),
    )
    result["FORNECEDOR"] = result["NOME_FORNECEDOR"]
    result["FORNECEDOR_CHAVE"] = (
        result["COD_FORNECEDOR"] + " / " + result["LOJA_FORNECEDOR"] + " - " + result["NOME_FORNECEDOR"]
    ).str.strip(" /-")
    result["STATUS"] = _normalize_status(result["STATUS_CONTRATO"], result["SITUACAO"])
    result["PERCENTUAL_EXECUCAO"] = _safe_percent(result["VALOR_MEDIDO"], result["VALOR_ATUAL"])
    result["PERCENTUAL_SALDO"] = _safe_percent(result["SALDO_EXECUCAO"], result["VALOR_ATUAL"])
    result["CLASSIFICACAO_EXECUCAO"] = result["PERCENTUAL_EXECUCAO"].apply(classificar_execucao)
    result["FAIXA_EXECUCAO"] = pd.cut(
        result["PERCENTUAL_EXECUCAO"].clip(lower=0, upper=100),
        bins=EXECUTION_BINS,
        labels=EXECUTION_LABELS,
        include_lowest=True,
        right=True,
    ).astype(str)

    return result


def aplicar_filtros_execucao(df: pd.DataFrame, filtros: Mapping[str, Any]) -> pd.DataFrame:
    """Apply execution module filters to the prepared DataFrame."""
    if df.empty:
        return df

    result = df.copy()
    filial = filtros.get("filial")
    tipo = filtros.get("tipo")
    situacao = filtros.get("situacao")
    contrato = str(filtros.get("contrato") or "").strip().lower()

    if filial and filial != "Todos" and "FILIAL" in result.columns:
        result = result[result["FILIAL"] == filial]
    if tipo and tipo != "Todos" and "TIPO" in result.columns:
        result = result[result["TIPO"] == tipo]
    if situacao and situacao != "Todos" and "STATUS" in result.columns:
        result = result[result["STATUS"] == situacao]
    if contrato and "CONTRATO" in result.columns:
        result = result[result["CONTRATO"].astype(str).str.lower().str.contains(contrato, na=False)]

    return result


def resumo_execucao(df: pd.DataFrame) -> dict[str, Any]:
    """Return KPI totals for the filtered execution view."""
    if df.empty:
        return {
            "total_contratos": 0,
            "valor_total_atualizado": 0.0,
            "valor_total_medido": 0.0,
            "valor_total_liquidado": 0.0,
            "saldo_total_execucao": 0.0,
            "percentual_medio_execucao": 0.0,
            "qtd_total_medicoes": 0,
            "valor_total_multas": 0.0,
        }

    return {
        "total_contratos": int(len(df)),
        "valor_total_atualizado": float(df["VALOR_ATUAL"].sum()),
        "valor_total_medido": float(df["VALOR_MEDIDO"].sum()),
        "valor_total_liquidado": float(df["VALOR_LIQUIDADO"].sum()),
        "saldo_total_execucao": float(df["SALDO_EXECUCAO"].sum()),
        "percentual_medio_execucao": float(df["PERCENTUAL_EXECUCAO"].mean() or 0.0),
        "qtd_total_medicoes": int(df["QTD_MEDICOES"].sum()),
        "valor_total_multas": float(df["VALOR_MULTA"].sum()),
    }


def ranking_execucao(df: pd.DataFrame, sort_column: str = "VALOR_MEDIDO", limit: int = 20) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=RANKING_COLUMNS)
    present = [column for column in RANKING_COLUMNS if column in df.columns]
    return df.sort_values(sort_column, ascending=False).head(limit)[present]


def distribuicao_execucao(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "FAIXA_EXECUCAO" not in df.columns:
        return pd.DataFrame(columns=["FAIXA_EXECUCAO", "QTD_CONTRATOS"])

    result = df.groupby("FAIXA_EXECUCAO", dropna=False).size().reset_index(name="QTD_CONTRATOS")
    order = {label: index for index, label in enumerate(EXECUTION_LABELS)}
    result["ORDEM"] = result["FAIXA_EXECUCAO"].map(order).fillna(len(order))
    return result.sort_values("ORDEM")[["FAIXA_EXECUCAO", "QTD_CONTRATOS"]]


def volume_medicoes(df: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    columns = ["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO", "STATUS", "QTD_MEDICOES"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    present = [column for column in columns if column in df.columns]
    return df.sort_values("QTD_MEDICOES", ascending=False).head(limit)[present]