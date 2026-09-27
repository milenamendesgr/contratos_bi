"""Business rules for contract advances analysis."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd


TEXT_COLUMNS = [
    "FILIAL",
    "CONTRATO",
    "TIPO_CONTRATO",
    "DESC_TIPO_CONTRATO",
    "COD_FORNECEDOR",
    "LOJA_FORNECEDOR",
    "NOME_FORNECEDOR",
    "CNPJ_FORNECEDOR",
    "NUMERO_ADIANTAMENTO",
    "SITUACAO",
    "STATUS_CONTRATO",
]
NUMERIC_COLUMNS = ["VALOR_ADIANTAMENTO", "SALDO_ADIANTAMENTO", "VALOR_ATUAL_CONTRATO"]
DATE_COLUMNS = ["DATA_ADIANTAMENTO", "DATA_INICIO", "DATA_FINAL"]
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
DETALHE_COLUMNS = [
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
]


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


def _to_datetime(series: pd.Series) -> pd.Series:
    values = series.astype(str).str.strip().replace({"": None, "nan": None, "None": None})
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    protheus_mask = values.str.fullmatch(r"\d{8}", na=False)
    result.loc[protheus_mask] = pd.to_datetime(values.loc[protheus_mask], format="%Y%m%d", errors="coerce")
    result.loc[~protheus_mask] = pd.to_datetime(values.loc[~protheus_mask], dayfirst=True, errors="coerce")
    return result


def _normalize_status(status_contrato: pd.Series, situacao: pd.Series) -> pd.Series:
    status = status_contrato.fillna("").astype(str).str.strip()
    fallback = situacao.fillna("").astype(str).str.strip().map(STATUS_LABELS).fillna(situacao.fillna("").astype(str).str.strip())
    return status.where(status.ne(""), fallback).replace("", "Nao informado")


def preparar_adiantamentos(df: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize CNX010 advances rows and add dashboard helper fields."""
    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()
    result.columns = [str(column).strip().upper() for column in result.columns]

    for column in TEXT_COLUMNS:
        if column not in result.columns:
            result[column] = ""
        result[column] = result[column].fillna("").astype(str).str.strip()

    for column in NUMERIC_COLUMNS:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = _to_number(result[column])

    for column in DATE_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NaT
        result[column] = _to_datetime(result[column])

    result["TIPO"] = result["DESC_TIPO_CONTRATO"].where(
        result["DESC_TIPO_CONTRATO"].ne(""),
        result["TIPO_CONTRATO"].replace("", "Nao informado"),
    )
    result["STATUS"] = _normalize_status(result["STATUS_CONTRATO"], result["SITUACAO"])
    codigo_loja = (result["COD_FORNECEDOR"] + " / " + result["LOJA_FORNECEDOR"]).str.strip(" /-")
    result["FORNECEDOR"] = result["NOME_FORNECEDOR"].where(result["NOME_FORNECEDOR"].ne(""), codigo_loja)
    result["FORNECEDOR_CHAVE"] = (codigo_loja + " - " + result["FORNECEDOR"]).str.strip(" -")
    result["MES_ADIANTAMENTO"] = result["DATA_ADIANTAMENTO"].dt.to_period("M").astype(str).replace("NaT", "Sem data")

    return result.sort_values("DATA_ADIANTAMENTO", ascending=False, na_position="last").reset_index(drop=True)


def aplicar_filtros_adiantamentos(df: pd.DataFrame, filtros: Mapping[str, Any]) -> pd.DataFrame:
    """Apply advances module filters."""
    if df.empty:
        return df

    result = df.copy()
    filial = filtros.get("filial")
    tipo = filtros.get("tipo")
    situacao = filtros.get("situacao")
    contrato = str(filtros.get("contrato") or "").strip().lower()
    fornecedor = str(filtros.get("fornecedor") or "").strip().lower()
    adiantamento = str(filtros.get("adiantamento") or "").strip().lower()

    if filial and filial != "Todos" and "FILIAL" in result.columns:
        result = result[result["FILIAL"] == filial]
    if tipo and tipo != "Todos" and "TIPO" in result.columns:
        result = result[result["TIPO"] == tipo]
    if situacao and situacao != "Todos" and "STATUS" in result.columns:
        result = result[result["STATUS"] == situacao]
    if contrato and "CONTRATO" in result.columns:
        result = result[result["CONTRATO"].astype(str).str.lower().str.contains(contrato, na=False)]
    if fornecedor and "FORNECEDOR" in result.columns:
        result = result[result["FORNECEDOR"].astype(str).str.lower().str.contains(fornecedor, na=False)]
    if adiantamento and "NUMERO_ADIANTAMENTO" in result.columns:
        result = result[result["NUMERO_ADIANTAMENTO"].astype(str).str.lower().str.contains(adiantamento, na=False)]

    return result


def resumo_adiantamentos(df: pd.DataFrame, df_contratos: Any = None) -> dict[str, Any]:
    if df.empty:
        return {
            "valor_total_adiantado": 0.0,
            "saldo_total_adiantamentos": 0.0,
            "qtd_adiantamentos": 0,
            "qtd_contratos_adiantamento": 0,
            "ticket_medio_adiantamentos": 0.0,
            "percentual_contratos_adiantamentos": 0.0,
        }

    qtd_adiantamentos = int(df["NUMERO_ADIANTAMENTO"].nunique())
    qtd_contratos = int(df["CONTRATO"].nunique())
    valor_total = float(df["VALOR_ADIANTAMENTO"].sum())
    total_contratos_base = qtd_contratos
    if df_contratos is not None and not getattr(df_contratos, "empty", True) and "CONTRATO" in df_contratos.columns:
        total_contratos_base = int(df_contratos["CONTRATO"].astype(str).str.strip().nunique())
    percentual = (qtd_contratos / total_contratos_base * 100) if total_contratos_base else 0.0

    return {
        "valor_total_adiantado": valor_total,
        "saldo_total_adiantamentos": float(df["SALDO_ADIANTAMENTO"].sum()),
        "qtd_adiantamentos": qtd_adiantamentos,
        "qtd_contratos_adiantamento": qtd_contratos,
        "ticket_medio_adiantamentos": valor_total / qtd_adiantamentos if qtd_adiantamentos else 0.0,
        "percentual_contratos_adiantamentos": float(percentual),
    }


def evolucao_adiantamentos_mensal(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "MES_ADIANTAMENTO" not in df.columns:
        return pd.DataFrame(columns=["MES_ADIANTAMENTO", "VALOR_ADIANTAMENTO"])
    return (
        df[df["MES_ADIANTAMENTO"].ne("Sem data")]
        .groupby("MES_ADIANTAMENTO", dropna=False)["VALOR_ADIANTAMENTO"]
        .sum()
        .sort_index()
        .reset_index()
    )


def ranking_adiantamentos(df: pd.DataFrame, coluna: str, limit: int = 10) -> pd.DataFrame:
    columns = [coluna, "VALOR_ADIANTAMENTO"]
    if df.empty or coluna not in df.columns:
        return pd.DataFrame(columns=columns)
    return df.groupby(coluna, dropna=False)["VALOR_ADIANTAMENTO"].sum().sort_values(ascending=False).head(limit).reset_index()


def comparativo_valor_saldo(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["INDICADOR", "VALOR"])
    return pd.DataFrame(
        [
            {"INDICADOR": "Valor adiantado", "VALOR": float(df["VALOR_ADIANTAMENTO"].sum())},
            {"INDICADOR": "Saldo", "VALOR": float(df["SALDO_ADIANTAMENTO"].sum())},
        ]
    )


def detalhes_adiantamentos(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=DETALHE_COLUMNS)
    present = [column for column in DETALHE_COLUMNS if column in df.columns]
    return df[present]


def get_adiantamentos_insights(df: pd.DataFrame, resumo: Mapping[str, Any], money_formatter: Any, percent_formatter: Any) -> list[dict[str, str]]:
    if df.empty:
        return []

    contrato_valor = ranking_adiantamentos(df, "CONTRATO", limit=1)
    contrato_saldo = df.groupby("CONTRATO", dropna=False)["SALDO_ADIANTAMENTO"].sum().sort_values(ascending=False).head(1)
    fornecedor_valor = ranking_adiantamentos(df, "FORNECEDOR", limit=1)

    insights: list[dict[str, str]] = []
    if not contrato_valor.empty:
        row = contrato_valor.iloc[0]
        insights.append({"title": "Maior adiantamento", "text": f"Contrato {row['CONTRATO']} concentra {money_formatter(row['VALOR_ADIANTAMENTO'])} em adiantamentos.", "severity": "neutral"})
    if not contrato_saldo.empty:
        insights.append({"title": "Maior saldo", "text": f"Contrato {contrato_saldo.index[0]} possui {money_formatter(float(contrato_saldo.iloc[0]))} de saldo em adiantamentos.", "severity": "warning"})
    if not fornecedor_valor.empty:
        row = fornecedor_valor.iloc[0]
        insights.append({"title": "Fornecedor destaque", "text": f"{row['FORNECEDOR']} soma {money_formatter(row['VALOR_ADIANTAMENTO'])} em adiantamentos.", "severity": "neutral"})
    insights.append({"title": "Contratos com adiantamento", "text": f"Foram identificados {resumo['qtd_contratos_adiantamento']} contratos com adiantamentos.", "severity": "positive"})
    insights.append({"title": "Participacao na carteira", "text": f"{percent_formatter(resumo['percentual_contratos_adiantamentos'])} dos contratos possuem adiantamentos.", "severity": "neutral"})
    return insights