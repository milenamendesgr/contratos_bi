"""Business rules for contract portfolio DataFrames."""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping

import pandas as pd

from config.settings import FILIAIS


DATE_COLUMNS = ["DATA_INICIO", "DATA_ASSINATURA", "DATA_FIM", "DATA_ULT_STATUS"]
NUMERIC_COLUMNS = [
    "VALOR_INICIAL",
    "VALOR_ATUAL",
    "SALDO_CONTRATO",
    "VALOR_REAJUSTE",
    "VALOR_ADITIVO",
    "PERCENTUAL_REAJUSTE",
    "VALOR_REAJUSTADO",
]
TEXT_COLUMNS = [
    "FILIAL",
    "CONTRATO",
    "COD_FORNECEDOR",
    "LOJA_FORNECEDOR",
    "NOME_FORNECEDOR",
    "CNPJ_FORNECEDOR",
    "TIPO_CONTRATO",
    "DESC_TIPO_CONTRATO",
    "DESCRICAO",
    "UNIDADE_VIGENCIA",
    "SITUACAO",
    "CONDICAO_PAGAMENTO",
    "DESCRICAO_CONDICAO_PAGAMENTO",
    "COND_PAGAMENTO",
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


def preparar_carteira_contratos(df: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize Protheus contract rows and add calculated portfolio fields."""
    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy() #cria uma copia do dataframe original para nao alterar o original
    result.columns = [str(col).strip().upper() for col in result.columns] #aqui padroniza os nomes das colunas do dataframe, removendo espacos e colocando em maiusculo
    if "DESCRICAO_TIPO_CONTRATO" in result.columns and "DESC_TIPO_CONTRATO" not in result.columns:
        result["DESC_TIPO_CONTRATO"] = result["DESCRICAO_TIPO_CONTRATO"] #aqui padroniza o nome da coluna de descricao do tipo de contrato, caso exista a coluna DESCRICAO_TIPO_CONTRATO e nao exista a coluna DESC_TIPO_CONTRATO
    if "DATA_FINAL" in result.columns and "DATA_FIM" not in result.columns:
        result["DATA_FIM"] = result["DATA_FINAL"] #aqui padroniza o nome da coluna de data final do contrato, caso exista a coluna DATA_FINAL e nao exista a coluna DATA_FIM
    if "DATA_ULTIMO_STATUS" in result.columns and "DATA_ULT_STATUS" not in result.columns:
        result["DATA_ULT_STATUS"] = result["DATA_ULTIMO_STATUS"] #aqui padroniza o nome da coluna de data do ultimo status do contrato, caso exista a coluna DATA_ULTIMO_STATUS e nao exista a coluna DATA_ULT_STATUS

    for column in TEXT_COLUMNS: #padroniza as colunas de texto, caso nao existam no dataframe, cria a coluna com valores vazios
        if column not in result.columns:
            result[column] = ""
        result[column] = result[column].fillna("").astype(str).str.strip() #para cada coluna de texto, preenche os valores nulos com string vazia, converte para string e remove espacos em branco

    for column in DATE_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NaT
        result[column] = _to_datetime(result[column]) #para cada coluna de data, converte para datetime, caso nao exista no dataframe, cria a coluna com valores nulos

    for column in NUMERIC_COLUMNS:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = _to_number(result[column]) #padroniza as colunas numericas, caso nao existam no dataframe, cria a coluna com valores 0.0

    result["FILIAL_NOME"] = result["FILIAL"].map(FILIAIS).fillna(result["FILIAL"]) #nome da filial, caso exista no dicionario FILIAIS, caso contrario, mantem o valor original da coluna FILIAL
    result["FORNECEDOR"] = result["NOME_FORNECEDOR"] #nome do fornecedor, caso exista a coluna NOME_FORNECEDOR, caso contrario, mantem o valor original da coluna FORNECEDOR
    result["FORNECEDOR_CHAVE"] = (
        result["COD_FORNECEDOR"] + " / " + result["LOJA_FORNECEDOR"] + " - " + result["NOME_FORNECEDOR"]
    ).str.strip(" /-") #atribui uma chave unica para o fornecedor, concatenando o codigo do fornecedor, a loja do fornecedor e o nome do fornecedor, removendo espacos em branco e caracteres especiais no inicio e fim da string
    result["TIPO"] = result["DESC_TIPO_CONTRATO"].where(
        result["DESC_TIPO_CONTRATO"].ne(""),
        result["TIPO_CONTRATO"].replace("", "Nao informado"), #se existir a coluna DESC_TIPO_CONTRATO, utiliza o valor dela, caso contrario, utiliza o valor da coluna TIPO_CONTRATO, substituindo valores vazios por "Nao informado"
    )
    if "STATUS_CONTRATO" in result.columns:
        result["STATUS_CONTRATO"] = result["STATUS_CONTRATO"].fillna("").astype(str).str.strip() #remove espacos em branco e converte para string, caso exista a coluna STATUS_CONTRATO
        result["STATUS"] = _normalize_status(result["STATUS_CONTRATO"], result["SITUACAO"]) #aqui converte o status do contrato para um valor padronizado, utilizando a funcao _normalize_status, que recebe como parametros a coluna STATUS_CONTRATO e a coluna SITUACAO
    else:
        result["STATUS"] = _normalize_status(pd.Series("", index=result.index), result["SITUACAO"])
    result["VALOR_TOTAL"] = result["VALOR_INICIAL"] #so copia
    result["SALDO_CONTRATUAL"] = result["SALDO_CONTRATO"] #só copia
    result["VALOR_EXECUTADO"] = (result["VALOR_ATUAL"] - result["SALDO_CONTRATO"]).clip(lower=0) #valor executado é igual ao valor atual menos o saldo do contrato, caso o resultado seja negativo, atribui 0 (clip=lower se o valor for menor que 0 faz ele ser apresentado como 0)
    result["PERCENTUAL_EXECUCAO"] = result.apply( #apply = aplica uma funcao a cada linha do dataframe, nesse caso, calcula o percentual de execucao do contrato, que é igual ao valor executado dividido pelo valor atual vezes 100, caso o valor atual seja 0, atribui 0.0
        lambda row: (row["VALOR_EXECUTADO"] / row["VALOR_ATUAL"] * 100) if row["VALOR_ATUAL"] else 0.0,
        axis=1, #lambda = funcao anonima, row = cada linha do dataframe, axis=1 = aplica a funcao a cada linha do dataframe, o axis 1 =  trabalhe linha por linha, axis 2= trabalhe coluna por coluna
    )

    today = pd.Timestamp.now().normalize()
    result["DIAS_RESTANTES"] = (result["DATA_FIM"] - today).dt.days
    result["ALERTA_VENCIMENTO"] = result["DIAS_RESTANTES"].apply(classificar_alerta_vencimento)
    result["MES_INICIO"] = result["DATA_INICIO"].dt.to_period("M").astype(str).replace("NaT", "Sem data")

    return result


def classificar_alerta_vencimento(dias_restantes: Any) -> str:
    if pd.isna(dias_restantes):
        return "Sem data"
    dias = int(dias_restantes)
    if dias < 0:
        return "Vencido"
    if dias <= 30:
        return "Vence em 30d"
    if dias <= 90:
        return "Vence em 90d"
    return "No prazo"


def aplicar_filtros_carteira(df: pd.DataFrame, filtros: Mapping[str, Any]) -> pd.DataFrame:
    """Apply prepared UI filters to the portfolio DataFrame."""
    if df.empty:
        return df

    result = df.copy()
    filial = filtros.get("filial")
    tipo = filtros.get("tipo")
    situacao = filtros.get("situacao")
    contrato = str(filtros.get("contrato") or "").strip().lower()
    fornecedor = str(filtros.get("fornecedor") or "").strip().lower()
    data_inicio = filtros.get("data_inicio")
    data_fim = filtros.get("data_fim")

    if filial and filial != "Todos" and "FILIAL_NOME" in result.columns:
        result = result[result["FILIAL_NOME"] == filial]
    if tipo and tipo != "Todos" and "TIPO" in result.columns:
        result = result[result["TIPO"] == tipo]
    if situacao and situacao != "Todos" and "STATUS" in result.columns:
        result = result[result["STATUS"] == situacao]
    if contrato and "CONTRATO" in result.columns:
        result = result[result["CONTRATO"].astype(str).str.lower().str.contains(contrato, na=False)]
    if fornecedor and "FORNECEDOR" in result.columns:
        result = result[result["FORNECEDOR"].astype(str).str.lower().str.contains(fornecedor, na=False)]
    if isinstance(data_inicio, date) and "DATA_INICIO" in result.columns:
        result = result[result["DATA_INICIO"] >= pd.Timestamp(data_inicio)]
    if isinstance(data_fim, date) and "DATA_FIM" in result.columns:
        result = result[result["DATA_FIM"] <= pd.Timestamp(data_fim)]

    return result


def opcoes_coluna(df: pd.DataFrame, column: str) -> list[str]:
    if df.empty or column not in df.columns:
        return ["Todos"]
    values = sorted(value for value in df[column].dropna().astype(str).unique() if value.strip())
    return ["Todos"] + values


def resumo_kpis(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "total_contratos": 0,
            "contratos_ativos": 0,
            "valor_total": 0.0,
            "valor_atual": 0.0,
            "valor_executado": 0.0,
            "saldo_contratual": 0.0,
            "percentual_medio_execucao": 0.0,
            "total_adiantamentos": None,
        }

    status = df["STATUS"].astype(str).str.upper() if "STATUS" in df.columns else pd.Series(dtype=str)
    ativos = status.str.contains("ATIV|VIGENTE|ABERT", na=False).sum()

    valor_atual_vigente = (
        df.loc[df["SITUACAO"].astype(str).str.strip().eq("05"), "VALOR_ATUAL"].sum()
        if "SITUACAO" in df.columns and "VALOR_ATUAL" in df.columns
        else 0.0
    )

    return {
        "total_contratos": int(len(df)),
        "contratos_ativos": int(ativos),
        "valor_total": float(df.get("VALOR_INICIAL", pd.Series(dtype=float)).sum()),
        "valor_atual": float(valor_atual_vigente),
        "valor_executado": float(df.get("VALOR_EXECUTADO", pd.Series(dtype=float)).sum()),
        "saldo_contratual": float(df.get("SALDO_CONTRATUAL", pd.Series(dtype=float)).sum()),
        "percentual_medio_execucao": float(df.get("PERCENTUAL_EXECUCAO", pd.Series(dtype=float)).mean() or 0.0),
        "total_adiantamentos": None,
    }


def agrupar_valor(df: pd.DataFrame, group_column: str, value_column: str = "VALOR_ATUAL", limit: int = 10) -> pd.DataFrame:
    if df.empty or group_column not in df.columns or value_column not in df.columns:
        return pd.DataFrame(columns=[group_column, value_column])
    return (
        df.groupby(group_column, dropna=False)[value_column]
        .sum()
        .sort_values(ascending=False)
        .head(limit)
        .reset_index()
    )


def ranking_contratos(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    columns = ["CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "FILIAL_NOME", "TIPO", "STATUS", "VALOR_ATUAL", "SALDO_CONTRATUAL", "PERCENTUAL_EXECUCAO"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    present = [column for column in columns if column in df.columns]
    return df.sort_values("VALOR_ATUAL", ascending=False).head(limit)[present]


def evolucao_carteira(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "MES_INICIO" not in df.columns:
        return pd.DataFrame(columns=["MES_INICIO", "VALOR_ATUAL"])
    result = (
        df[df["MES_INICIO"].ne("Sem data")]
        .groupby("MES_INICIO", dropna=False)["VALOR_ATUAL"]
        .sum()
        .sort_index()
        .reset_index()
    )
    result["VALOR_ACUMULADO"] = result["VALOR_ATUAL"].cumsum()
    return result
