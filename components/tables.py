"""Table helpers to keep modules focused on business layout."""

from __future__ import annotations

from datetime import datetime
import re
import unicodedata
from typing import Any, Iterable, Optional

import pandas as pd
import streamlit as st

from components.cards import render_section_header
from utils.formatters import formatar_cnpj


EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")

STATUS_STYLE_MAP = {
    "VIGENTE": "background-color: #E8F5EE; color: #0F6B3C; font-weight: 700; border-radius: 999px; text-align: center;",
    "ATIVO": "background-color: #E8F5EE; color: #0F6B3C; font-weight: 700; border-radius: 999px; text-align: center;",
    "ABERTO": "background-color: #E8F5EE; color: #0F6B3C; font-weight: 700; border-radius: 999px; text-align: center;",
    "EM ELABORACAO": "background-color: #E8F1FF; color: #1D4ED8; font-weight: 700; border-radius: 999px; text-align: center;",
    "REVISAO": "background-color: #FFF7E6; color: #B45309; font-weight: 700; border-radius: 999px; text-align: center;",
    "CANCELADO": "background-color: #FDECEC; color: #B42318; font-weight: 700; border-radius: 999px; text-align: center;",
    "FINALIZADO": "background-color: #F3F4F6; color: #374151; font-weight: 700; border-radius: 999px; text-align: center;",
    "ENCERRADO": "background-color: #F3F4F6; color: #374151; font-weight: 700; border-radius: 999px; text-align: center;",
}


def _normalize_label(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return EMOJI_RE.sub("", text).upper().strip()


def _clean_table_labels(df: Any) -> Any:
    if not hasattr(df, "copy") or not hasattr(df, "columns"):
        return df
    result = df.copy()
    for column in result.columns:
        if getattr(result[column], "dtype", None) == "object":
            result[column] = result[column].map(lambda value: EMOJI_RE.sub("", value).strip() if isinstance(value, str) else value)
        if str(column).upper() in {"CNPJ", "CNPJ_FORNECEDOR"}:
            result[column] = result[column].map(formatar_cnpj)
    result = result.rename(columns={"CNPJ_FORNECEDOR": "CNPJ/CPF", "CNPJ": "CNPJ/CPF"})
    return result


def _display_columns(columns: Iterable[str]) -> list[str]:
    return ["CNPJ/CPF" if column in {"CNPJ", "CNPJ_FORNECEDOR"} else column for column in columns]


def _quick_search(df: Any, title: str) -> Any:
    if not hasattr(df, "astype") or not hasattr(df, "columns"):
        return df
    query = st.text_input(
        "Busca rapida",
        value="",
        placeholder="Digite para localizar registros nesta tabela",
        key=f"table_search_{re.sub(r'[^a-zA-Z0-9_]+', '_', title.lower()).strip('_')}",
    ).strip()
    if not query:
        return df
    mask = df.astype(str).apply(lambda column: column.str.contains(query, case=False, na=False, regex=False)).any(axis=1)
    return df.loc[mask]


def _style_table(df: Any) -> Any:
    if not isinstance(df, pd.DataFrame):
        return df

    money_columns = [column for column in df.columns if any(token in str(column).upper() for token in ["VALOR", "SALDO", "TOTAL", "MULTA", "BONIFICACAO"])]
    status_columns = [column for column in df.columns if "STATUS" in str(column).upper() or "SITUACAO" in str(column).upper()]

    def style_cell(value: Any, column: str) -> str:
        text = str(value).strip()
        normalized = _normalize_label(text)
        if column in status_columns:
            return STATUS_STYLE_MAP.get(normalized, "background-color: #F8FAFC; color: #475569; font-weight: 700; border-radius: 999px; text-align: center;")
        if column in money_columns:
            if "-" in text:
                return "color: #B42318; font-weight: 800; background-color: #FFF5F5;"
            return "color: #0F6B3C; font-weight: 750;"
        return ""

    return df.style.apply(lambda series: [style_cell(value, str(series.name)) for value in series], axis=0)


def render_table_section(
    title: str,
    columns: Iterable[str],
    subtitle: str | None = None,
    df: Optional[Any] = None,
    empty_message: str = "Sem dados para exibicao.",
    height: int | None = 420,
    download: bool = True,
) -> None:
    """Render a table section prepared for DataFrame input."""
    render_section_header(title, "Detalhamento disponivel para conferencia e exportacao.")

    if df is None:
        st.info(empty_message)
        st.caption("Colunas previstas: " + " | ".join(_display_columns(columns)))
        return

    if hasattr(df, "empty") and getattr(df, "empty"):
        st.warning("DataFrame carregado, porem vazio.")
        st.caption("Colunas esperadas: " + " | ".join(_display_columns(columns)))
        return

    df_display = _clean_table_labels(df)
    df_display = _quick_search(df_display, title)

    col_info, col_download = st.columns([4, 1])
    with col_info:
        st.caption(f"{len(df_display)} registro(s) exibido(s).")
    if download and hasattr(df_display, "to_csv"):
        with col_download:
            csv_bytes = df_display.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
            file_name = f"{title.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            st.download_button(
                "Baixar CSV",
                data=csv_bytes,
                file_name=file_name,
                mime="text/csv",
                use_container_width=True,
            )

    st.dataframe(_style_table(df_display), use_container_width=True, hide_index=True, height=height)
