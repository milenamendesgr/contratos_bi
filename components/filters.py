"""Reusable filter blocks for contracts modules."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import streamlit as st


def select_filter(label: str, options: Optional[Iterable[str]], key: str) -> Any:
    """Generic selectbox filter prepared for dynamic options."""
    option_list = list(options) if options else ["Todos"]
    return st.selectbox(label, option_list, key=key)


def text_filter(label: str, key: str, placeholder: str = "") -> str:
    """Generic text input filter."""
    return st.text_input(label, value="", placeholder=placeholder, key=key)


def render_period_filter(prefix: str) -> Dict[str, Any]:
    """Default period controls used across modules."""
    col1, col2 = st.columns(2)
    with col1:
        dt_inicio = st.date_input("Data inicio", key=f"{prefix}_dt_inicio")
    with col2:
        dt_fim = st.date_input("Data fim", key=f"{prefix}_dt_fim")

    return {"data_inicio": dt_inicio, "data_fim": dt_fim}
