"""
Módulo: Indicadores de Contratos
Descrição: KPIs, métricas e gráficos de análise da carteira de contratos - CONTRATOS BI
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.cards import render_insights, render_kpi_cards
from utils.formatters import formatar_percentual, formatar_quantidade, formatar_valor_abreviado
from utils.insights import get_indicadores_insights


ACTIVE_STATUS = {"ATIVO", "VIGENTE", "ABERTO"}
STATUS_COLORS = {
    "VIGENTE": "#1B7A3E",
    "ELABORACAO": "#E67E22",
    "EMITIDO": "#2980B9",
    "APROVACAO": "#7FB77E",
    "PARALISADO": "#8E44AD",
    "CANCELADO": "#7F8C8D",
    "FINALIZADO": "#555555",
    "REVISAO": "#F39C12",
    "REVISADO": "#0C5E42",
    "SOLICITACAO_FINALIZACAO": "#C0392B",
}


def _active_mask(df: pd.DataFrame) -> pd.Series:
    if "STATUS" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["STATUS"].fillna("").astype(str).str.upper().isin(ACTIVE_STATUS)


def _vencido_mask(df: pd.DataFrame) -> pd.Series:
    if "ALERTA_VENCIMENTO" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["ALERTA_VENCIMENTO"].eq("Vencido")


# ---------------------------------------------------------------------------
# HELPERS VISUAIS
# ---------------------------------------------------------------------------

def _kpi_card(icon: str, label: str, valor: str, cor: str, sub: str = "") -> str:
    return (
        f"<div style='background:white;padding:20px 12px;border-radius:12px;"
        f"border-top:4px solid {cor};box-shadow:0 2px 10px rgba(0,0,0,0.07);"
        f"text-align:center;min-height:118px;"
        f"display:flex;flex-direction:column;justify-content:center;align-items:center;"
        f"margin-bottom:8px;'>"
        f"<div style='font-size:1.5rem;margin-bottom:4px;'>{icon}</div>"
        f"<div style='font-size:1.65rem;font-weight:800;color:{cor};line-height:1.2;'>{valor}</div>"
        f"<div style='font-size:0.70rem;color:#6c757d;margin-top:4px;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:0.6px;'>{label}</div>"
        + (f"<div style='font-size:0.71rem;color:#aaa;margin-top:2px;'>{sub}</div>" if sub else "")
        + "</div>"
    )


# ---------------------------------------------------------------------------
# RENDER PRINCIPAL
# ---------------------------------------------------------------------------

def render_indicadores():
    """Renderiza o módulo de Indicadores."""

    if "df_contratos" not in st.session_state:
        st.info(
            "Nenhum dado carregado. Acesse **Lista de Contratos** "
            "para importar os dados primeiro."
        )
        return

    df = st.session_state["df_contratos"].copy()

    # ──────────────────────────────────────────────────────────────────────
    # KPIs PRINCIPAIS
    # ──────────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='font-size:0.85rem;color:#004B23;font-weight:700;
    text-transform:uppercase;letter-spacing:0.8px;margin-bottom:12px;'>
    Indicadores Gerais</div>
    """, unsafe_allow_html=True)

    total        = len(df)
    ativos       = int(_active_mask(df).sum())
    vencidos     = int(_vencido_mask(df).sum())
    vencendo_30  = len(df[df["ALERTA_VENCIMENTO"] == "Vence em 30d"]) if "ALERTA_VENCIMENTO" in df.columns else 0
    valor_total  = df["VALOR_TOTAL"].sum()                if "VALOR_TOTAL"       in df.columns else 0
    valor_mensal = (
        df[_active_mask(df)]["VALOR_MENSAL"].sum()
        if "VALOR_MENSAL" in df.columns else 0
    )

    pct_ativos  = f"{formatar_percentual(ativos / total * 100)} do total"  if total else ""
    pct_venc    = f"{formatar_percentual(vencidos / total * 100)} do total" if total else ""

    render_kpi_cards(
        [
            {"title": "Total contratos", "value": formatar_quantidade(total), "subtitle": "Carteira carregada", "severity": "neutral"},
            {"title": "Ativos", "value": formatar_quantidade(ativos), "subtitle": pct_ativos or "Sem contratos", "severity": "positive"},
            {"title": "Vencidos", "value": formatar_quantidade(vencidos), "subtitle": pct_venc or "Sem contratos", "severity": "critical" if vencidos else "neutral"},
            {"title": "Vence em 30 dias", "value": formatar_quantidade(vencendo_30), "subtitle": "Requerem atencao", "severity": "warning" if vencendo_30 else "neutral"},
            {"title": "Valor total", "value": formatar_valor_abreviado(valor_total), "subtitle": "Carteira total", "severity": "positive"},
            {"title": "Receita mensal", "value": formatar_valor_abreviado(valor_mensal), "subtitle": "Contratos ativos", "severity": "positive"},
        ],
        columns=3,
    )

    render_insights(get_indicadores_insights(total, ativos, vencidos, vencendo_30, pct_ativos, pct_venc))

    st.markdown("---")

    # ──────────────────────────────────────────────────────────────────────
    # GRÁFICOS — LINHA 1
    # ──────────────────────────────────────────────────────────────────────
    col_g1, col_g2 = st.columns(2)

    # Gráfico 1: Contratos por Status
    with col_g1:
        st.markdown("""
        <div style='font-size:0.82rem;color:#004B23;font-weight:700;
        text-transform:uppercase;margin-bottom:8px;'>Contratos por Status</div>
        """, unsafe_allow_html=True)

        if "STATUS" in df.columns:
            df_status = df["STATUS"].value_counts().reset_index()
            df_status.columns = ["Status", "Quantidade"]

            cores_bar = [STATUS_COLORS.get(str(s).upper(), "#555") for s in df_status["Status"]]

            fig1 = go.Figure(go.Bar(
                x=df_status["Status"],
                y=df_status["Quantidade"],
                marker_color=cores_bar,
                text=df_status["Quantidade"],
                textposition="outside",
            ))
            fig1.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor="white",
                plot_bgcolor="#F8F9FA",
                showlegend=False,
                font=dict(size=11),
            )
            st.plotly_chart(fig1, use_container_width=True)

    # Gráfico 2: Contratos por Filial (Ativos)
    with col_g2:
        st.markdown("""
        <div style='font-size:0.82rem;color:#004B23;font-weight:700;
        text-transform:uppercase;margin-bottom:8px;'>Contratos Ativos por Filial</div>
        """, unsafe_allow_html=True)

        col_filial = "FILIAL_NOME" if "FILIAL_NOME" in df.columns else "FILIAL"
        if col_filial in df.columns:
            df_filial = (
                df[_active_mask(df)][col_filial]
                .value_counts()
                .head(10)
                .reset_index()
            )
            df_filial.columns = ["Filial", "Quantidade"]

            fig2 = px.bar(
                df_filial,
                x="Quantidade",
                y="Filial",
                orientation="h",
                color_discrete_sequence=["#004B23"],
                text="Quantidade",
            )
            fig2.update_traces(textposition="outside")
            fig2.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor="white",
                plot_bgcolor="#F8F9FA",
                showlegend=False,
                font=dict(size=11),
                yaxis=dict(title=""),
                xaxis=dict(title="Qtde"),
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ──────────────────────────────────────────────────────────────────────
    # GRÁFICOS — LINHA 2
    # ──────────────────────────────────────────────────────────────────────
    col_g3, col_g4 = st.columns(2)

    # Gráfico 3: Valor Total por Filial (Ativos)
    with col_g3:
        st.markdown("""
        <div style='font-size:0.82rem;color:#004B23;font-weight:700;
        text-transform:uppercase;margin-bottom:8px;'>Valor Total por Filial (Ativos)</div>
        """, unsafe_allow_html=True)

        col_filial = "FILIAL_NOME" if "FILIAL_NOME" in df.columns else "FILIAL"
        if col_filial in df.columns and "VALOR_TOTAL" in df.columns:
            df_val = (
                df[_active_mask(df)]
                .groupby(col_filial)["VALOR_TOTAL"]
                .sum()
                .sort_values(ascending=False)
                .head(10)
                .reset_index()
            )
            df_val.columns = ["Filial", "Valor"]

            fig3 = px.bar(
                df_val,
                x="Filial",
                y="Valor",
                color_discrete_sequence=["#1B7A3E"],
                text=df_val["Valor"].apply(formatar_valor_abreviado),
            )
            fig3.update_traces(textposition="outside")
            fig3.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=10, b=60),
                paper_bgcolor="white",
                plot_bgcolor="#F8F9FA",
                showlegend=False,
                font=dict(size=11),
                yaxis=dict(title=""),
                xaxis=dict(title=""),
            )
            st.plotly_chart(fig3, use_container_width=True)

    # Gráfico 4: Contratos por Tipo
    with col_g4:
        st.markdown("""
        <div style='font-size:0.82rem;color:#004B23;font-weight:700;
        text-transform:uppercase;margin-bottom:8px;'>Distribuição por Tipo de Contrato</div>
        """, unsafe_allow_html=True)

        if "TIPO" in df.columns:
            df_tipo = df["TIPO"].value_counts().reset_index()
            df_tipo.columns = ["Tipo", "Quantidade"]

            fig4 = px.pie(
                df_tipo,
                values="Quantidade",
                names="Tipo",
                color_discrete_sequence=px.colors.sequential.Greens_r,
                hole=0.4,
            )
            fig4.update_traces(textposition="inside", textinfo="percent+label")
            fig4.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="white",
                showlegend=False,
                font=dict(size=11),
            )
            st.plotly_chart(fig4, use_container_width=True)

    # ──────────────────────────────────────────────────────────────────────
    # GRÁFICO — LINHA 3: Valor Mensal por Responsável
    # ──────────────────────────────────────────────────────────────────────
    if "RESPONSAVEL" in df.columns and "VALOR_MENSAL" in df.columns:
        st.markdown("---")
        st.markdown("""
        <div style='font-size:0.82rem;color:#004B23;font-weight:700;
        text-transform:uppercase;margin-bottom:8px;'>
        Receita Mensal por Responsável (Contratos Ativos)</div>
        """, unsafe_allow_html=True)

        df_resp = (
            df[df["STATUS"] == "Ativo"]
            .groupby("RESPONSAVEL")["VALOR_MENSAL"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        df_resp.columns = ["Responsável", "Valor"]

        if not df_resp.empty:
            fig5 = px.bar(
                df_resp,
                x="Responsável",
                y="Valor",
                color_discrete_sequence=["#7FB77E"],
                text=df_resp["Valor"].apply(formatar_valor_abreviado),
            )
            fig5.update_traces(textposition="outside")
            fig5.update_layout(
                height=280,
                margin=dict(l=0, r=0, t=10, b=60),
                paper_bgcolor="white",
                plot_bgcolor="#F8F9FA",
                showlegend=False,
                font=dict(size=11),
                yaxis=dict(title=""),
                xaxis=dict(title=""),
            )
            st.plotly_chart(fig5, use_container_width=True)
