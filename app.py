"""Streamlit entrypoint for the Contratos BI skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

import streamlit as st
from config.settings import DEMO_MODE

from modules.adiantamentos import render_adiantamentos
from modules.alertas import render_alertas
from modules.consulta_contratos import render_consulta_contratos
from modules.dashboard_executivo import render_dashboard_executivo
from modules.execucao_contratual import render_execucao_contratual
from modules.financeiro import render_financeiro
from modules.fornecedores import render_fornecedores
from modules.itens_planilhas import render_itens_planilhas
from modules.medicoes import render_medicoes
from modules.vigencia_prazos import render_vigencia_prazos
from utils.contratos_repository import get_carteira_contratos


@dataclass
class DataContext:
    """Future contract data sources loaded from database integrations."""

    df_contratos: Any = None
    df_fornecedores: Any = None
    df_medicoes: Any = None
    df_financeiro: Any = None
    df_itens: Any = None


def load_data_context() -> DataContext:
    """Centralized DataFrame loader for Protheus integrations."""
    df_contratos = st.session_state.get("df_contratos")
    if df_contratos is None or (hasattr(df_contratos, "empty") and df_contratos.empty):
        df_contratos = get_carteira_contratos()
        st.session_state["df_contratos"] = df_contratos

    return DataContext(
        df_contratos=df_contratos,
        df_fornecedores=st.session_state.get("df_fornecedores"),
        df_medicoes=st.session_state.get("df_medicoes"),
        df_financeiro=st.session_state.get("df_financeiro"),
        df_itens=st.session_state.get("df_itens"),
    )


def apply_page_style() -> None:
    """Minimal professional layout style for the skeleton phase."""
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1.2rem;
                padding-bottom: 2rem;
                max-width: 1400px;
            }
            .module-header {
                border-left: 6px solid #0C5E42;
                padding: 8px 14px;
                background: linear-gradient(90deg, #F2F7F4 0%, #FFFFFF 100%);
                border-radius: 8px;
                margin-bottom: 8px;
            }
            .module-subtitle {
                color: #506070;
                margin-top: 0.2rem;
                margin-bottom: 1rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_title() -> None:
    st.markdown('<div class="module-header"><h2>BI Gestao de Contratos</h2></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="module-subtitle">Arquitetura modular preparada para integracao futura com TOTVS Protheus.</div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="BI Contratos", page_icon=" ", layout="wide")
    apply_page_style()
    render_title()
    if DEMO_MODE:
        st.info("DEMONSTRACAO | Todos os dados sao ficticios e gerados localmente.")

    data_context = load_data_context()

    menu: Dict[str, Callable[..., None]] = {
        "1) Dashboard Executivo": render_dashboard_executivo,
        "2) Vigencia e Prazos": render_vigencia_prazos,
        "3) Execucao Contratual": render_execucao_contratual,
        "4) Financeiro": render_financeiro,
        "5) Adiantamentos": render_adiantamentos,
        "6) Fornecedores": render_fornecedores,
        "7) Itens e Planilhas": render_itens_planilhas,
        "8) Medicoes": render_medicoes,
        "9) Alertas": render_alertas,
        "10) Consulta de Contratos": render_consulta_contratos,
    }

    st.sidebar.title("Menu Principal")
    selected_menu = st.sidebar.radio("Navegacao", list(menu.keys()), label_visibility="collapsed")

    render_module = menu[selected_menu]
    render_module(
        df_contratos=data_context.df_contratos,
        df_fornecedores=data_context.df_fornecedores,
        df_medicoes=data_context.df_medicoes,
        df_financeiro=data_context.df_financeiro,
        df_itens=data_context.df_itens,
    )


if __name__ == "__main__":
    main()
