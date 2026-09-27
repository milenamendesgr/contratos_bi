"""Business rules for contract financial analysis."""

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
    "VALOR_CONTRATO",
    "QTD_PARCELAS",
    "VALOR_PREVISTO",
    "VALOR_REALIZADO",
    "SALDO_FINANCEIRO",
    "PARCELAS_ATRASADAS",
    "VALOR_ADIANTADO",
    "SALDO_ADIANTAMENTO",
    "PERCENTUAL_REALIZADO",
]
RANKING_SALDO_COLUMNS = ["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO", "STATUS", "VALOR_PREVISTO", "VALOR_REALIZADO", "SALDO_FINANCEIRO", "CLASSIFICACAO_FINANCEIRA"]
ATRASO_COLUMNS = ["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO", "STATUS", "PARCELAS_ATRASADAS", "SALDO_FINANCEIRO", "CLASSIFICACAO_FINANCEIRA"]
ADIANTAMENTO_COLUMNS = ["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO", "STATUS", "VALOR_ADIANTADO", "SALDO_ADIANTAMENTO"]
FLUXO_TEXT_COLUMNS = ["FILIAL", "CONTRATO", "COD_FORNECEDOR", "LOJA_FORNECEDOR", "NOME_FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO_CONTRATO", "DESC_TIPO_CONTRATO", "COMPETENCIA"]
FLUXO_NUMERIC_COLUMNS = ["VALOR_PREVISTO", "VALOR_REALIZADO", "SALDO_FINANCEIRO"]
FLUXO_DETALHE_COLUMNS = [
    "CONTRATO",
    "FORNECEDOR",
    "CNPJ_FORNECEDOR",
    "TIPO",
    "COMPETENCIA",
    "DATA_VENCIMENTO",
    "VALOR_PREVISTO",
    "VALOR_REALIZADO",
    "SALDO_FINANCEIRO",
    "PERCENTUAL_REALIZADO",
    "CLASSIFICACAO_ATRASO",
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


def _safe_percent(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace(0, pd.NA)
    return (numerator / denominator * 100).fillna(0.0)


def _normalize_status(status_contrato: pd.Series, situacao: pd.Series) -> pd.Series:
    status = status_contrato.fillna("").astype(str).str.strip()
    situacao_texto = situacao.fillna("").astype(str).str.strip()
    fallback = situacao_texto.map(STATUS_LABELS).fillna(situacao_texto)
    return status.where(status.ne(""), fallback).replace("", "Nao informado")


def classificar_financeiro(row: pd.Series) -> str:
    percentual = float(row.get("PERCENTUAL_REALIZADO", 0.0) or 0.0)
    saldo = float(row.get("SALDO_FINANCEIRO", 0.0) or 0.0)
    valor_previsto = float(row.get("VALOR_PREVISTO", 0.0) or 0.0)
    parcelas_atrasadas = float(row.get("PARCELAS_ATRASADAS", 0.0) or 0.0)
    percentual_saldo = (saldo / valor_previsto * 100) if valor_previsto else 0.0

    if parcelas_atrasadas > 0 or (valor_previsto > 0 and percentual < 25):
        return "🔴 Crítico"
    if saldo > 0 and (percentual_saldo >= 50 or parcelas_atrasadas > 0):
        return "🟡 Atenção"
    return "🟢 Regular"


def preparar_financeiro(df: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize Protheus financial rows and add calculated fields."""
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

    result["TIPO"] = result["DESC_TIPO_CONTRATO"].where(
        result["DESC_TIPO_CONTRATO"].ne(""),
        result["TIPO_CONTRATO"].replace("", "Nao informado"),
    )
    result["FORNECEDOR"] = result["NOME_FORNECEDOR"]
    result["FORNECEDOR_CHAVE"] = (
        result["COD_FORNECEDOR"] + " / " + result["LOJA_FORNECEDOR"] + " - " + result["NOME_FORNECEDOR"]
    ).str.strip(" /-")
    result["STATUS"] = _normalize_status(result["STATUS_CONTRATO"], result["SITUACAO"])
    result["SALDO_FINANCEIRO"] = result["VALOR_PREVISTO"] - result["VALOR_REALIZADO"]
    result["PERCENTUAL_REALIZADO"] = _safe_percent(result["VALOR_REALIZADO"], result["VALOR_PREVISTO"])
    result["CLASSIFICACAO_FINANCEIRA"] = result.apply(classificar_financeiro, axis=1)

    return result


def aplicar_filtros_financeiro(df: pd.DataFrame, filtros: Mapping[str, Any]) -> pd.DataFrame:
    """Apply financial module filters to the prepared DataFrame."""
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


def resumo_financeiro(df: pd.DataFrame) -> dict[str, Any]:
    """Return KPI totals for the filtered financial view."""
    if df.empty:
        return {
            "valor_total_contratado": 0.0,
            "valor_previsto": 0.0,
            "valor_realizado": 0.0,
            "saldo_financeiro": 0.0,
            "percentual_realizado": 0.0,
            "qtd_parcelas": 0,
            "parcelas_atrasadas": 0,
            "valor_total_adiantado": 0.0,
            "saldo_adiantamentos": 0.0,
        }

    valor_previsto = float(df["VALOR_PREVISTO"].sum())
    valor_realizado = float(df["VALOR_REALIZADO"].sum())
    percentual_realizado = (valor_realizado / valor_previsto * 100) if valor_previsto else 0.0

    return {
        "valor_total_contratado": float(df["VALOR_CONTRATO"].sum()),
        "valor_previsto": valor_previsto,
        "valor_realizado": valor_realizado,
        "saldo_financeiro": float(valor_previsto - valor_realizado),
        "percentual_realizado": float(percentual_realizado),
        "qtd_parcelas": int(df["QTD_PARCELAS"].sum()),
        "parcelas_atrasadas": int(df["PARCELAS_ATRASADAS"].sum()),
        "valor_total_adiantado": float(df["VALOR_ADIANTADO"].sum()),
        "saldo_adiantamentos": float(df["SALDO_ADIANTAMENTO"].sum()),
    }


def ranking_saldo_financeiro(df: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=RANKING_SALDO_COLUMNS)
    present = [column for column in RANKING_SALDO_COLUMNS if column in df.columns]
    return df.sort_values("SALDO_FINANCEIRO", ascending=False).head(limit)[present]


def ranking_atrasos(df: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=ATRASO_COLUMNS)
    present = [column for column in ATRASO_COLUMNS if column in df.columns]
    return df.sort_values(["PARCELAS_ATRASADAS", "SALDO_FINANCEIRO"], ascending=[False, False]).head(limit)[present]


def comparativo_previsto_realizado(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["INDICADOR", "VALOR"])
    return pd.DataFrame(
        [
            {"INDICADOR": "Previsto", "VALOR": float(df["VALOR_PREVISTO"].sum())},
            {"INDICADOR": "Realizado", "VALOR": float(df["VALOR_REALIZADO"].sum())},
        ]
    )


def ranking_adiantamentos(df: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=ADIANTAMENTO_COLUMNS)
    present = [column for column in ADIANTAMENTO_COLUMNS if column in df.columns]
    return df.sort_values(["VALOR_ADIANTADO", "SALDO_ADIANTAMENTO"], ascending=[False, False]).head(limit)[present]


def distribuicao_por_situacao(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["STATUS", "QTD_CONTRATOS", "VALOR_PREVISTO", "VALOR_REALIZADO", "SALDO_FINANCEIRO"]
    if df.empty or "STATUS" not in df.columns:
        return pd.DataFrame(columns=columns)

    return (
        df.groupby("STATUS", dropna=False)
        .agg(
            QTD_CONTRATOS=("CONTRATO", "nunique"),
            VALOR_PREVISTO=("VALOR_PREVISTO", "sum"),
            VALOR_REALIZADO=("VALOR_REALIZADO", "sum"),
            SALDO_FINANCEIRO=("SALDO_FINANCEIRO", "sum"),
        )
        .sort_values("SALDO_FINANCEIRO", ascending=False)
        .reset_index()
    )


def classificar_atraso_fluxo(row: pd.Series) -> str:
    data_vencimento = row.get("DATA_VENCIMENTO")
    valor_previsto = float(row.get("VALOR_PREVISTO", 0.0) or 0.0)
    valor_realizado = float(row.get("VALOR_REALIZADO", 0.0) or 0.0)
    hoje = pd.Timestamp.now().normalize()

    if valor_previsto > 0 and valor_realizado >= valor_previsto:
        return "🟢 Realizado"
    if pd.notna(data_vencimento) and data_vencimento < hoje and valor_realizado == 0:
        return "🔴 Atrasado"
    if pd.notna(data_vencimento) and hoje <= data_vencimento <= hoje + pd.Timedelta(days=30):
        return "🟡 Próximo vencimento"
    return "🟡 Próximo vencimento"


def preparar_fluxo_financeiro(df: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize Protheus financial flow rows and add calculated fields."""
    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()
    result.columns = [str(column).strip().upper() for column in result.columns]

    for column in FLUXO_TEXT_COLUMNS:
        if column not in result.columns:
            result[column] = ""
        result[column] = result[column].fillna("").astype(str).str.strip()

    if "DATA_VENCIMENTO" not in result.columns:
        result["DATA_VENCIMENTO"] = pd.NaT
    result["DATA_VENCIMENTO"] = _to_datetime(result["DATA_VENCIMENTO"])

    for column in FLUXO_NUMERIC_COLUMNS:
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
    result["SALDO_FINANCEIRO"] = result["VALOR_PREVISTO"] - result["VALOR_REALIZADO"]
    result["PERCENTUAL_REALIZADO"] = _safe_percent(result["VALOR_REALIZADO"], result["VALOR_PREVISTO"])
    result["CLASSIFICACAO_ATRASO"] = result.apply(classificar_atraso_fluxo, axis=1)

    return result


def aplicar_filtros_fluxo_financeiro(df: pd.DataFrame, filtros: Mapping[str, Any]) -> pd.DataFrame:
    """Apply financial flow filters to the prepared DataFrame."""
    if df.empty:
        return df

    result = df.copy()
    filial = filtros.get("filial")
    tipo = filtros.get("tipo")
    competencia = filtros.get("competencia")
    contrato = str(filtros.get("contrato") or "").strip().lower()
    data_inicio = filtros.get("data_inicio")
    data_fim = filtros.get("data_fim")

    if filial and filial != "Todos" and "FILIAL" in result.columns:
        result = result[result["FILIAL"] == filial]
    if tipo and tipo != "Todos" and "TIPO" in result.columns:
        result = result[result["TIPO"] == tipo]
    if competencia and competencia != "Todos" and "COMPETENCIA" in result.columns:
        result = result[result["COMPETENCIA"] == competencia]
    if contrato and "CONTRATO" in result.columns:
        result = result[result["CONTRATO"].astype(str).str.lower().str.contains(contrato, na=False)]
    if pd.notna(data_inicio) and "DATA_VENCIMENTO" in result.columns:
        result = result[result["DATA_VENCIMENTO"] >= pd.Timestamp(data_inicio)]
    if pd.notna(data_fim) and "DATA_VENCIMENTO" in result.columns:
        result = result[result["DATA_VENCIMENTO"] <= pd.Timestamp(data_fim)]

    return result


def resumo_fluxo_financeiro(df: pd.DataFrame) -> dict[str, Any]:
    """Return KPI totals for the filtered financial flow view."""
    if df.empty:
        return {
            "total_previsto": 0.0,
            "total_realizado": 0.0,
            "saldo_financeiro": 0.0,
            "qtd_parcelas": 0,
            "proximo_vencimento": None,
            "valor_previsto_30_dias": 0.0,
        }

    hoje = pd.Timestamp.now().normalize()
    proximos_30 = df["DATA_VENCIMENTO"].between(hoje, hoje + pd.Timedelta(days=30), inclusive="both")
    vencimentos_futuros = df.loc[df["DATA_VENCIMENTO"].ge(hoje), "DATA_VENCIMENTO"].dropna()
    total_previsto = float(df["VALOR_PREVISTO"].sum())
    total_realizado = float(df["VALOR_REALIZADO"].sum())

    return {
        "total_previsto": total_previsto,
        "total_realizado": total_realizado,
        "saldo_financeiro": float(total_previsto - total_realizado),
        "qtd_parcelas": int(len(df)),
        "proximo_vencimento": vencimentos_futuros.min() if not vencimentos_futuros.empty else None,
        "valor_previsto_30_dias": float(df.loc[proximos_30, "VALOR_PREVISTO"].sum()),
    }


def evolucao_fluxo_mensal(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["COMPETENCIA", "VALOR_PREVISTO", "VALOR_REALIZADO"]
    if df.empty or "COMPETENCIA" not in df.columns:
        return pd.DataFrame(columns=columns)
    return (
        df.groupby("COMPETENCIA", dropna=False)[["VALOR_PREVISTO", "VALOR_REALIZADO"]]
        .sum()
        .sort_index()
        .reset_index()
    )


def fluxo_futuro_desembolso(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["COMPETENCIA", "SALDO_FINANCEIRO"]
    if df.empty or "COMPETENCIA" not in df.columns:
        return pd.DataFrame(columns=columns)
    hoje = pd.Timestamp.now().normalize()
    futuro = df[df["DATA_VENCIMENTO"].isna() | df["DATA_VENCIMENTO"].ge(hoje)]
    return (
        futuro.groupby("COMPETENCIA", dropna=False)["SALDO_FINANCEIRO"]
        .sum()
        .sort_index()
        .reset_index()
    )


def ranking_competencias_previsto(df: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    columns = ["COMPETENCIA", "VALOR_PREVISTO", "VALOR_REALIZADO", "SALDO_FINANCEIRO"]
    if df.empty or "COMPETENCIA" not in df.columns:
        return pd.DataFrame(columns=columns)
    return (
        df.groupby("COMPETENCIA", dropna=False)[["VALOR_PREVISTO", "VALOR_REALIZADO", "SALDO_FINANCEIRO"]]
        .sum()
        .sort_values("VALOR_PREVISTO", ascending=False)
        .head(limit)
        .reset_index()
    )


def detalhes_fluxo_financeiro(df: pd.DataFrame, limit: int = 200) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=FLUXO_DETALHE_COLUMNS)
    present = [column for column in FLUXO_DETALHE_COLUMNS if column in df.columns]
    return df.sort_values(["DATA_VENCIMENTO", "CONTRATO"], ascending=[True, True]).head(limit)[present]