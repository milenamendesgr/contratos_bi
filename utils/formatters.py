"""
Utilitários de formatação para o Dashboard de Contratos - CONTRATOS BI
"""

import pandas as pd


def _formatar_decimal(valor, casas: int) -> str:
    try:
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            valor = 0
        v = float(valor)
        return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return f"{0:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_moeda(valor) -> str:
    """Formata um valor numérico como moeda brasileira (R$ X.XXX,XX)."""
    return f"R$ {_formatar_decimal(valor, 2)}"


def formatar_numero(valor, casas: int = 2) -> str:
    """Formata um número com separador brasileiro e casas decimais configuráveis."""
    return _formatar_decimal(valor, casas)


def formatar_percentual(valor) -> str:
    """Formata um percentual no padrão brasileiro com duas casas decimais."""
    return f"{_formatar_decimal(valor, 2)}%"


def formatar_quantidade(valor) -> str:
    """Formata uma quantidade com separador de milhar e sem casas decimais."""
    return _formatar_decimal(valor, 0)


def formatar_cnpj(valor) -> str:
    """Formata um CNPJ no padrao 00.000.000/0000-00 quando houver 14 digitos."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    digits = "".join(ch for ch in str(valor).strip() if ch.isdigit())
    if len(digits) != 14:
        return str(valor).strip()
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def formatar_data(data) -> str:
    """Formata uma data para o padrão dd/mm/AAAA."""
    try:
        if data is None:
            return ""
        if isinstance(data, str):
            data = data.strip()
            if not data:
                return ""
            if data.lower() in {"nat", "nan", "none"}:
                return ""
            if data.isdigit() and len(data) == 8:
                ts = pd.to_datetime(data, format="%Y%m%d", errors="coerce")
            else:
                ts = pd.to_datetime(data, dayfirst=True, errors="coerce")
        elif isinstance(data, int) or (isinstance(data, float) and data.is_integer()):
            data_str = str(int(data))
            if len(data_str) == 8:
                ts = pd.to_datetime(data_str, format="%Y%m%d", errors="coerce")
            else:
                ts = pd.Timestamp(data)
        else:
            ts = pd.Timestamp(data)
        if pd.isna(ts):
            return ""
        return ts.strftime("%d/%m/%Y")
    except Exception:
        return ""


def cor_status_alerta(alerta: str) -> str:
    """Retorna a cor HTML correspondente ao status de alerta de vencimento."""
    mapa = {
        "Vencido":      "#C0392B",
        "Vence em 30d": "#E74C3C",
        "Vence em 60d": "#E67E22",
        "Vence em 90d": "#F39C12",
        "No Prazo":     "#1B7A3E",
        "Inativo":      "#7F8C8D",
        "Sem Data":     "#95A5A6",
    }
    return mapa.get(alerta, "#555555")


def formatar_valor_abreviado(valor) -> str:
    """Formata valor com abreviação K / M."""
    try:
        v = float(valor)
        if abs(v) >= 1_000_000:
            return f"R$ {_formatar_decimal(v / 1_000_000, 1)}M"
        if abs(v) >= 1_000:
            return f"R$ {_formatar_decimal(v / 1_000, 1)}K"
        return f"R$ {_formatar_decimal(v, 0)}"
    except Exception:
        return "R$ 0"
