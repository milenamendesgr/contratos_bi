"""Helpers de normalizacao e classificacao de dados de contratos."""

import pandas as pd


def limpar_string(s) -> str:
    """Remove espacos extras e normaliza a string."""
    try:
        if s is None:
            return ""
        if isinstance(s, float) and pd.isna(s):
            return ""
        return str(s).strip()
    except Exception:
        return ""


def calcular_dias_restantes(data_fim) -> int | None:
    """Retorna quantidade de dias ate o vencimento (negativo = ja vencido)."""
    try:
        if data_fim is None:
            return None
        if isinstance(data_fim, float) and pd.isna(data_fim):
            return None
        hoje = pd.Timestamp.now().normalize()
        fim = pd.Timestamp(data_fim).normalize()
        if pd.isna(fim):
            return None
        return int((fim - hoje).days)
    except Exception:
        return None


def calcular_status_vencimento(data_fim, status_contrato: str = "") -> str:
    """Calcula o status de alerta baseado na data de vencimento."""
    if str(status_contrato).strip().upper() in {"CANCELADO", "PARALISADO", "FINALIZADO", "SOLICITACAO_FINALIZACAO"}:
        return "Inativo"
    dias = calcular_dias_restantes(data_fim)
    if dias is None:
        return "Sem Data"
    if dias < 0:
        return "Vencido"
    if dias <= 30:
        return "Vence em 30d"
    if dias <= 60:
        return "Vence em 60d"
    if dias <= 90:
        return "Vence em 90d"
    return "No Prazo"