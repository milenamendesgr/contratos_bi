"""Business rules for contract measurement analysis (CND010/CNE010)."""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

import pandas as pd

from config.settings import FILIAIS


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
    "REVISAO_CONTRATO",
    "NUMERO_MEDICAO",
    "NUMERO_PLANILHA",
    "COMPETENCIA",
    "STATUS_MEDICAO",
    "STATUS_MEDICAO_DESC",
]

NUMERIC_COLUMNS = [
    "VALOR_PREVISTO",
    "VALOR_TOTAL_MEDICAO",
    "VALOR_LIQUIDO",
    "VALOR_ADIANTAMENTO",
    "VALOR_CAUCAO",
    "VALOR_MULTAS",
    "VALOR_BONIFICACOES",
    "SALDO_MEDICAO",
    "VALOR_ATUAL",
    "QTD_ITENS",
    "QTD_PRODUTOS_DISTINTOS",
    "QTD_SOLICITADA",
    "QTD_MEDIDA",
    "TOTAL_ITENS",
    "TOTAL_LIQUIDO_ITENS",
    "TOTAL_MULTAS_ITENS",
    "TOTAL_BONIFICACOES_ITENS",
]

DATE_COLUMNS = [
    "DATA_INICIO",
    "DATA_FIM",
    "DATA_ENCERRAMENTO",
    "DATA_VENCIMENTO",
]

MEDICAO_STATUS_LABELS = {
    "E": "ENCERRADA",
    "A": "APROVADA",
    "C": "CANCELADA",
    "L": "LIBERADA",
    "R": "REPROVADA",
    "P": "PAGA",
    "01": "CANCELADA",
    "02": "ELABORACAO",
    "03": "APROVADA",
    "04": "PAGA",
    "05": "ENCERRADA",
    "06": "LIBERADA",
    "07": "REPROVADA",
}

CONTRATO_STATUS_LABELS = {
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

FAIXAS_QTD_MEDICOES = [0, 1, 5, 10, 20, float("inf")]
FAIXAS_QTD_MEDICOES_LABELS = [
    "1 medicao",
    "2 a 5",
    "6 a 10",
    "11 a 20",
    "Mais de 20",
]


def _to_datetime(series: pd.Series) -> pd.Series:
    values = series.astype(str).str.strip().replace({"": None, "nan": None, "None": None, "NaT": None})
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    protheus_mask = values.str.fullmatch(r"\d{8}", na=False)
    result.loc[protheus_mask] = pd.to_datetime(
        values.loc[protheus_mask], format="%Y%m%d", errors="coerce"
    )
    result.loc[~protheus_mask] = pd.to_datetime(
        values.loc[~protheus_mask], dayfirst=True, errors="coerce"
    )
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
        .replace({"": "0", "nan": "0", "None": "0", "NaT": "0"})
    )
    return pd.to_numeric(normalized, errors="coerce").fillna(0.0)


def _normalize_status(series: pd.Series) -> pd.Series:
    values = series.fillna("").astype(str).str.strip()
    numeric_mask = values.str.fullmatch(r"\d+(?:\.0+)?", na=False)
    values.loc[numeric_mask] = (
        pd.to_numeric(values.loc[numeric_mask], errors="coerce")
        .fillna(0)
        .astype(int)
        .astype(str)
        .str.zfill(2)
    )
    descriptions = values.map(MEDICAO_STATUS_LABELS).fillna(values)
    return descriptions.replace("", "Nao informado")


def _format_situacao_contrato(series: pd.Series) -> pd.Series:
    values = series.fillna("").astype(str).str.strip()
    numeric_mask = values.str.fullmatch(r"\d+(?:\.0+)?", na=False)
    values.loc[numeric_mask] = (
        pd.to_numeric(values.loc[numeric_mask], errors="coerce")
        .fillna(0)
        .astype(int)
        .astype(str)
        .str.zfill(2)
    )
    descriptions = values.map(CONTRATO_STATUS_LABELS)
    labels = values.where(descriptions.isna(), values + " - " + descriptions)
    return labels.replace("", "Nao informado")


def _format_competencia(value: Any) -> str:
    value = str(value).strip()
    if value.isdigit() and len(value) == 6:
        return f"{value[:4]}-{value[4:]}"
    return value


def _competencia_sort_key(series: pd.Series) -> pd.Series:
    values = series.astype(str).str.strip()
    yyyymm = pd.to_numeric(values.str.replace("-", "", regex=False), errors="coerce")
    mm_yyyy_mask = values.str.fullmatch(r"\d{2}/\d{4}", na=False)
    yyyymm.loc[mm_yyyy_mask] = pd.to_numeric(
        values.loc[mm_yyyy_mask].str[3:7] + values.loc[mm_yyyy_mask].str[0:2],
        errors="coerce",
    )
    return yyyymm.fillna(0).astype(int)


def preparar_medicoes(df: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize Protheus measurement rows and add analytical fields."""
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

    result["FILIAL_NOME"] = result["FILIAL"].map(FILIAIS).fillna(result["FILIAL"])
    result["FORNECEDOR"] = result["NOME_FORNECEDOR"]
    result["FORNECEDOR_CHAVE"] = (
        result["COD_FORNECEDOR"] + " / " + result["LOJA_FORNECEDOR"] + " - " + result["NOME_FORNECEDOR"]
    ).str.strip(" /-")
    result["TIPO"] = result["DESC_TIPO_CONTRATO"].where(
        result["DESC_TIPO_CONTRATO"].ne(""),
        result["TIPO_CONTRATO"].replace("", "Nao informado"),
    )
    result["STATUS"] = _normalize_status(result["STATUS_MEDICAO"])
    result["STATUS"] = result["STATUS"].where(
        result["STATUS"].ne(""),
        result["STATUS_MEDICAO_DESC"].replace("", "Nao informado"),
    )
    result["SITUACAO_CONTRATO"] = _format_situacao_contrato(result["SITUACAO"])
    result["COMPETENCIA_LABEL"] = result["COMPETENCIA"].apply(_format_competencia)
    result["COMPETENCIA_ORDEM"] = _competencia_sort_key(result["COMPETENCIA_LABEL"])
    result["CONTRATO_CHAVE"] = result["FILIAL"] + " | " + result["CONTRATO"]
    result["MEDICAO_CHAVE"] = (
        result["FILIAL"] + " | " + result["CONTRATO"] + " | " + result["REVISAO_CONTRATO"] + " | " + result["NUMERO_MEDICAO"]
    )

    return result.reset_index(drop=True)


def aplicar_filtros_medicoes(df: pd.DataFrame, filtros: Mapping[str, Any]) -> pd.DataFrame:
    """Apply measurement module filters to the prepared DataFrame."""
    if df.empty:
        return df

    result = df.copy()
    filial = filtros.get("filial")
    fornecedor = str(filtros.get("fornecedor") or "").strip().lower()
    tipo = filtros.get("tipo")
    status = filtros.get("status")
    situacao = filtros.get("situacao")
    competencia = filtros.get("competencia")
    contrato = str(filtros.get("contrato") or "").strip().lower()
    data_inicio = filtros.get("data_inicio")
    data_fim = filtros.get("data_fim")

    if filial and filial != "Todos" and "FILIAL_NOME" in result.columns:
        result = result[result["FILIAL_NOME"] == filial]
    if fornecedor and "FORNECEDOR" in result.columns:
        result = result[result["FORNECEDOR"].astype(str).str.lower().str.contains(fornecedor, na=False)]
    if tipo and tipo != "Todos" and "TIPO" in result.columns:
        result = result[result["TIPO"] == tipo]
    if status and status != "Todos" and "STATUS" in result.columns:
        result = result[result["STATUS"] == status]
    if situacao and situacao != "Todos" and "SITUACAO_CONTRATO" in result.columns:
        result = result[result["SITUACAO_CONTRATO"] == situacao]
    if competencia and competencia != "Todos" and "COMPETENCIA_LABEL" in result.columns:
        result = result[result["COMPETENCIA_LABEL"] == competencia]
    if contrato and "CONTRATO" in result.columns:
        result = result[result["CONTRATO"].astype(str).str.lower().str.contains(contrato, na=False)]
    if isinstance(data_inicio, date) and "DATA_INICIO" in result.columns:
        result = result[result["DATA_INICIO"] >= pd.Timestamp(data_inicio)]
    if isinstance(data_fim, date) and "DATA_FIM" in result.columns:
        result = result[result["DATA_FIM"] <= pd.Timestamp(data_fim)]

    return result.reset_index(drop=True)


def resumo_medicoes(df: pd.DataFrame) -> dict[str, Any]:
    """Return main KPI totals for the measurement view."""
    if df.empty:
        return {
            "contratos_com_medicao": 0,
            "total_medicoes": 0,
            "total_planilhas": 0,
            "valor_total_medicoes": 0.0,
            "valor_liquido": 0.0,
            "valor_previsto": 0.0,
            "valor_adiantado": 0.0,
            "total_multas": 0.0,
            "total_bonificacoes": 0.0,
            "saldo_medicoes": 0.0,
            "media_itens_por_medicao": 0.0,
            "media_valor_por_medicao": 0.0,
            "media_valor_por_contrato": 0.0,
        }

    contratos_com_medicao = int(df["CONTRATO_CHAVE"].nunique())
    total_medicoes = int(df["MEDICAO_CHAVE"].nunique())
    total_planilhas = int(df["NUMERO_PLANILHA"].replace("", pd.NA).dropna().nunique())

    return {
        "contratos_com_medicao": contratos_com_medicao,
        "total_medicoes": total_medicoes,
        "total_planilhas": total_planilhas,
        "valor_total_medicoes": float(df["VALOR_TOTAL_MEDICAO"].sum()),
        "valor_liquido": float(df["VALOR_LIQUIDO"].sum()),
        "valor_previsto": float(df["VALOR_PREVISTO"].sum()),
        "valor_adiantado": float(df["VALOR_ADIANTAMENTO"].sum()),
        "total_multas": float(df["VALOR_MULTAS"].sum()),
        "total_bonificacoes": float(df["VALOR_BONIFICACOES"].sum()),
        "saldo_medicoes": float(df["SALDO_MEDICAO"].sum()),
        "media_itens_por_medicao": float(df["QTD_ITENS"].mean() or 0.0),
        "media_valor_por_medicao": float(df["VALOR_TOTAL_MEDICAO"].mean() or 0.0),
        "media_valor_por_contrato": float(df.groupby("CONTRATO_CHAVE")["VALOR_TOTAL_MEDICAO"].sum().mean() or 0.0),
    }


def indicadores_contratos(df_medicoes: pd.DataFrame, df_contratos: pd.DataFrame | None = None) -> dict[str, Any]:
    """Return contract-level measurement distribution indicators."""
    if df_medicoes.empty:
        return {
            "qtd_contratos_com_medicao": 0,
            "qtd_contratos_sem_medicao": 0,
            "qtd_contratos_uma_medicao": 0,
            "qtd_contratos_mais_de_uma": 0,
            "maior_qtd_medicoes_contrato": 0,
            "media_medicoes_por_contrato": 0.0,
        }

    medicoes_por_contrato = df_medicoes.groupby("CONTRATO_CHAVE")["MEDICAO_CHAVE"].nunique()
    contratos_com_medicao = int(medicoes_por_contrato.shape[0])
    contratos_uma_medicao = int((medicoes_por_contrato == 1).sum())
    contratos_mais_de_uma = int((medicoes_por_contrato > 1).sum())

    contratos_sem_medicao = 0
    if df_contratos is not None and not df_contratos.empty:
        base = df_contratos.copy()
        base.columns = [str(column).strip().upper() for column in base.columns]
        if "FILIAL" in base.columns and "CONTRATO" in base.columns:
            base["CONTRATO_CHAVE"] = base["FILIAL"].astype(str) + " | " + base["CONTRATO"].astype(str)
            contratos_base = set(base["CONTRATO_CHAVE"].dropna().astype(str).unique())
            contratos_com = set(df_medicoes["CONTRATO_CHAVE"].dropna().astype(str).unique())
            contratos_sem_medicao = int(len(contratos_base - contratos_com))

    return {
        "qtd_contratos_com_medicao": contratos_com_medicao,
        "qtd_contratos_sem_medicao": contratos_sem_medicao,
        "qtd_contratos_uma_medicao": contratos_uma_medicao,
        "qtd_contratos_mais_de_uma": contratos_mais_de_uma,
        "maior_qtd_medicoes_contrato": int(medicoes_por_contrato.max()) if not medicoes_por_contrato.empty else 0,
        "media_medicoes_por_contrato": float(medicoes_por_contrato.mean() or 0.0),
    }


def evolucao_medicoes(df: pd.DataFrame, value_column: str = "VALOR_TOTAL_MEDICAO") -> pd.DataFrame:
    if df.empty or "COMPETENCIA_LABEL" not in df.columns:
        return pd.DataFrame(columns=["COMPETENCIA", value_column])

    result = (
        df.groupby("COMPETENCIA_LABEL", dropna=False)[value_column]
        .sum()
        .reset_index()
        .rename(columns={"COMPETENCIA_LABEL": "COMPETENCIA", value_column: value_column})
    )
    result["ORDEM"] = _competencia_sort_key(result["COMPETENCIA"])
    return result.sort_values("ORDEM").drop(columns=["ORDEM"]).reset_index(drop=True)


def medicoes_por_competencia(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "COMPETENCIA_LABEL" not in df.columns:
        return pd.DataFrame(columns=["COMPETENCIA", "QTD_MEDICOES"])

    result = (
        df.groupby("COMPETENCIA_LABEL", dropna=False)["NUMERO_MEDICAO"]
        .nunique()
        .reset_index()
        .rename(columns={"COMPETENCIA_LABEL": "COMPETENCIA", "NUMERO_MEDICAO": "QTD_MEDICOES"})
    )
    result["ORDEM"] = _competencia_sort_key(result["COMPETENCIA"])
    return result.sort_values("ORDEM").drop(columns=["ORDEM"]).reset_index(drop=True)


def medicoes_por_status(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "STATUS" not in df.columns:
        return pd.DataFrame(columns=["STATUS", "QTD_MEDICOES", "VALOR_TOTAL_MEDICAO", "VALOR_LIQUIDO"])

    return (
        df.groupby("STATUS", dropna=False)
        .agg(
            QTD_MEDICOES=("MEDICAO_CHAVE", "nunique"),
            VALOR_TOTAL_MEDICAO=("VALOR_TOTAL_MEDICAO", "sum"),
            VALOR_LIQUIDO=("VALOR_LIQUIDO", "sum"),
        )
        .reset_index()
        .sort_values("VALOR_TOTAL_MEDICAO", ascending=False)
        .reset_index(drop=True)
    )


def comparativo_previsto_realizado(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["INDICADOR", "VALOR"])

    return pd.DataFrame({
        "INDICADOR": ["Valor previsto", "Valor realizado"],
        "VALOR": [
            float(df["VALOR_PREVISTO"].sum()),
            float(df["VALOR_TOTAL_MEDICAO"].sum()),
        ],
    })


def ranking_contratos(df: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    columns = [
        "CONTRATO",
        "FORNECEDOR",
        "CNPJ_FORNECEDOR",
        "TIPO",
        "STATUS",
        "QTD_MEDICOES",
        "VALOR_TOTAL_MEDICAO",
        "VALOR_LIQUIDO",
        "VALOR_PREVISTO",
        "SALDO_MEDICAO",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)

    result = (
        df.groupby(["CONTRATO_CHAVE", "CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "TIPO", "STATUS"], dropna=False)
        .agg(
            QTD_MEDICOES=("MEDICAO_CHAVE", "nunique"),
            VALOR_TOTAL_MEDICAO=("VALOR_TOTAL_MEDICAO", "sum"),
            VALOR_LIQUIDO=("VALOR_LIQUIDO", "sum"),
            VALOR_PREVISTO=("VALOR_PREVISTO", "sum"),
            SALDO_MEDICAO=("SALDO_MEDICAO", "sum"),
        )
        .reset_index()
    )
    result = result[columns].sort_values("VALOR_TOTAL_MEDICAO", ascending=False).head(limit)
    return result.reset_index(drop=True)


def ranking_fornecedores(df: pd.DataFrame, limit: int = 20) -> pd.DataFrame:
    columns = [
        "FORNECEDOR",
        "CNPJ_FORNECEDOR",
        "QTD_CONTRATOS",
        "QTD_MEDICOES",
        "VALOR_TOTAL_MEDICAO",
        "VALOR_LIQUIDO",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)

    result = (
        df.groupby(["FORNECEDOR_CHAVE", "FORNECEDOR", "CNPJ_FORNECEDOR"], dropna=False)
        .agg(
            QTD_CONTRATOS=("CONTRATO_CHAVE", "nunique"),
            QTD_MEDICOES=("MEDICAO_CHAVE", "nunique"),
            VALOR_TOTAL_MEDICAO=("VALOR_TOTAL_MEDICAO", "sum"),
            VALOR_LIQUIDO=("VALOR_LIQUIDO", "sum"),
        )
        .reset_index()
    )
    result = result[columns].sort_values("VALOR_TOTAL_MEDICAO", ascending=False).head(limit)
    return result.reset_index(drop=True)


def ranking_competencias(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["COMPETENCIA", "QTD_MEDICOES", "VALOR_TOTAL_MEDICAO", "VALOR_LIQUIDO", "VALOR_PREVISTO"]
    if df.empty or "COMPETENCIA_LABEL" not in df.columns:
        return pd.DataFrame(columns=columns)

    result = (
        df.groupby("COMPETENCIA_LABEL", dropna=False)
        .agg(
            QTD_MEDICOES=("MEDICAO_CHAVE", "nunique"),
            VALOR_TOTAL_MEDICAO=("VALOR_TOTAL_MEDICAO", "sum"),
            VALOR_LIQUIDO=("VALOR_LIQUIDO", "sum"),
            VALOR_PREVISTO=("VALOR_PREVISTO", "sum"),
        )
        .reset_index()
        .rename(columns={"COMPETENCIA_LABEL": "COMPETENCIA"})
    )
    result["ORDEM"] = _competencia_sort_key(result["COMPETENCIA"])
    return result.sort_values("ORDEM")[columns].reset_index(drop=True)


def status_medicoes(df: pd.DataFrame) -> pd.DataFrame:
    return medicoes_por_status(df)


def top10_contratos(df: pd.DataFrame) -> pd.DataFrame:
    return ranking_contratos(df, limit=10)


def top10_fornecedores(df: pd.DataFrame) -> pd.DataFrame:
    return ranking_fornecedores(df, limit=10)


def medicoes_por_fornecedor(df: pd.DataFrame, limit: int = 15) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["FORNECEDOR", "QTD_MEDICOES"])

    result = (
        df.groupby("FORNECEDOR", dropna=False)
        .agg(QTD_MEDICOES=("MEDICAO_CHAVE", "nunique"))
        .reset_index()
        .sort_values("QTD_MEDICOES", ascending=False)
        .head(limit)
    )
    return result.reset_index(drop=True)


def faixas_medicoes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["FAIXA", "QTD_CONTRATOS"])

    medicoes_por_contrato = df.groupby("CONTRATO_CHAVE")["MEDICAO_CHAVE"].nunique().reset_index(name="QTD_MEDICOES")
    medicoes_por_contrato["FAIXA"] = pd.cut(
        medicoes_por_contrato["QTD_MEDICOES"],
        bins=FAIXAS_QTD_MEDICOES,
        labels=FAIXAS_QTD_MEDICOES_LABELS,
        right=True,
        include_lowest=True,
    ).astype(str)

    result = (
        medicoes_por_contrato.groupby("FAIXA", dropna=False)
        .size()
        .reset_index(name="QTD_CONTRATOS")
    )
    order = {label: idx for idx, label in enumerate(FAIXAS_QTD_MEDICOES_LABELS)}
    result["ORDEM"] = result["FAIXA"].map(order).fillna(len(order))
    return result.sort_values("ORDEM").drop(columns=["ORDEM"]).reset_index(drop=True)


def contratos_sem_medicao(df_medicoes: pd.DataFrame, df_contratos: pd.DataFrame | None) -> pd.DataFrame:
    if df_contratos is None or df_contratos.empty:
        return pd.DataFrame(columns=["FILIAL", "CONTRATO", "FORNECEDOR", "TIPO", "STATUS", "VALOR_ATUAL"])

    base = df_contratos.copy()
    base.columns = [str(column).strip().upper() for column in base.columns]
    for column in ["FILIAL", "CONTRATO", "NOME_FORNECEDOR", "DESC_TIPO_CONTRATO", "STATUS", "VALOR_ATUAL"]:
        if column not in base.columns:
            base[column] = "" if column != "VALOR_ATUAL" else 0.0

    base["CONTRATO_CHAVE"] = base["FILIAL"].astype(str) + " | " + base["CONTRATO"].astype(str)
    medicoes_keys = set(df_medicoes["CONTRATO_CHAVE"].dropna().astype(str).unique()) if not df_medicoes.empty else set()

    sem_medicao = base[~base["CONTRATO_CHAVE"].isin(medicoes_keys)].copy()
    sem_medicao["FORNECEDOR"] = sem_medicao["NOME_FORNECEDOR"]
    sem_medicao["TIPO"] = sem_medicao["DESC_TIPO_CONTRATO"]

    columns = ["FILIAL", "CONTRATO", "FORNECEDOR", "TIPO", "STATUS", "VALOR_ATUAL"]
    for column in columns:
        if column not in sem_medicao.columns:
            sem_medicao[column] = "" if column != "VALOR_ATUAL" else 0.0

    return sem_medicao[columns].drop_duplicates().reset_index(drop=True)


def medicoes_com_divergencia(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[
            "FILIAL", "CONTRATO", "FORNECEDOR", "NUMERO_MEDICAO",
            "DIVERGENCIA", "VALOR_LIQUIDO", "VALOR_TOTAL_MEDICAO",
            "QTD_SOLICITADA", "QTD_MEDIDA", "VALOR_PREVISTO", "SALDO_MEDICAO",
        ])

    divergencias: list[pd.DataFrame] = []

    # Liquido maior que total
    mask = df["VALOR_LIQUIDO"] > df["VALOR_TOTAL_MEDICAO"]
    if mask.any():
        temp = df.loc[mask].copy()
        temp["DIVERGENCIA"] = "Valor liquido maior que valor total"
        divergencias.append(temp)

    # Quantidade medida maior que solicitada
    mask = df["QTD_MEDIDA"] > df["QTD_SOLICITADA"]
    if mask.any():
        temp = df.loc[mask].copy()
        temp["DIVERGENCIA"] = "Quantidade medida maior que quantidade solicitada"
        divergencias.append(temp)

    # Previsto zerado com valor medido maior que zero
    mask = (df["VALOR_PREVISTO"] == 0) & (df["VALOR_TOTAL_MEDICAO"] > 0)
    if mask.any():
        temp = df.loc[mask].copy()
        temp["DIVERGENCIA"] = "Valor previsto zerado com valor medido maior que zero"
        divergencias.append(temp)

    # Saldo negativo
    mask = df["SALDO_MEDICAO"] < 0
    if mask.any():
        temp = df.loc[mask].copy()
        temp["DIVERGENCIA"] = "Saldo da medicao negativo"
        divergencias.append(temp)

    # Medicao encerrada sem valor
    mask = df["STATUS"].astype(str).str.upper().eq("ENCERRADA") & (df["VALOR_TOTAL_MEDICAO"] == 0)
    if mask.any():
        temp = df.loc[mask].copy()
        temp["DIVERGENCIA"] = "Medicao encerrada sem valor"
        divergencias.append(temp)

    # Medicao sem itens associados na CNE010
    mask = df["QTD_ITENS"] == 0
    if mask.any():
        temp = df.loc[mask].copy()
        temp["DIVERGENCIA"] = "Medicao sem itens associados na CNE010"
        divergencias.append(temp)

    if not divergencias:
        return pd.DataFrame(columns=[
            "FILIAL", "CONTRATO", "FORNECEDOR", "NUMERO_MEDICAO",
            "DIVERGENCIA", "VALOR_LIQUIDO", "VALOR_TOTAL_MEDICAO",
            "QTD_SOLICITADA", "QTD_MEDIDA", "VALOR_PREVISTO", "SALDO_MEDICAO",
        ])

    result = pd.concat(divergencias, ignore_index=True)
    columns = [
        "FILIAL", "CONTRATO", "FORNECEDOR", "NUMERO_MEDICAO",
        "DIVERGENCIA", "VALOR_LIQUIDO", "VALOR_TOTAL_MEDICAO",
        "QTD_SOLICITADA", "QTD_MEDIDA", "VALOR_PREVISTO", "SALDO_MEDICAO",
    ]
    for column in columns:
        if column not in result.columns:
            result[column] = ""

    return result[columns].drop_duplicates().reset_index(drop=True)
