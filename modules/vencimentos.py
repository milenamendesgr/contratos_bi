"""
Módulo: Vencimentos de Contratos
Descrição: Alertas, gráficos e rastreamento de contratos próximos ao vencimento - CONTRATOS BI
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.cards import render_insights
from utils.formatters import cor_status_alerta, formatar_cnpj, formatar_data, formatar_moeda
from utils.insights import get_vencimentos_insights


# ---------------------------------------------------------------------------
# HELPERS VISUAIS
# ---------------------------------------------------------------------------

def _card_alerta(alerta: str, quantidade: int, valor_total: float) -> str:
    cor = cor_status_alerta(alerta)
    return (
        f"<div style='background:white;padding:18px 12px;border-radius:12px;"
        f"border-left:5px solid {cor};box-shadow:0 2px 8px rgba(0,0,0,0.08);"
        f"text-align:center;margin-bottom:8px;'>"
        f"<div style='font-size:1.85rem;font-weight:800;color:{cor};margin:4px 0;'>{quantidade}</div>"
        f"<div style='font-size:0.72rem;color:{cor};font-weight:700;"
        f"text-transform:uppercase;letter-spacing:0.5px;'>{alerta}</div>"
        f"<div style='font-size:0.75rem;color:#888;margin-top:3px;'>{formatar_moeda(valor_total)}</div>"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# RENDER PRINCIPAL
# ---------------------------------------------------------------------------

def render_vencimentos():
    """Renderiza o módulo de Vencimentos."""

    if "df_contratos" not in st.session_state:
        st.info(
            "Nenhum dado carregado. Acesse **Lista de Contratos** "
            "para importar os dados primeiro."
        )
        return

    df = st.session_state["df_contratos"].copy()
    if "FORNECEDOR" not in df.columns and "NOME_FORNECEDOR" in df.columns:
        df["FORNECEDOR"] = df["NOME_FORNECEDOR"]

    if "ALERTA_VENCIMENTO" not in df.columns or "DATA_FIM" not in df.columns:
        st.error("Dados incompletos — verifique se o arquivo contém a coluna de vencimento.")
        return

    hoje = pd.Timestamp.now().normalize()

    # ──────────────────────────────────────────────────────────────────────
    # PAINÉIS DE ALERTA
    # ──────────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='font-size:0.85rem;color:#004B23;font-weight:700;
    text-transform:uppercase;letter-spacing:0.8px;margin-bottom:12px;'>
     Situação dos Vencimentos</div>
    """, unsafe_allow_html=True)

    ordem_alertas = ["Vencido", "Vence em 30d", "Vence em 60d", "Vence em 90d", "No Prazo", "Inativo", "Sem Data"]
    cols_al = st.columns(len(ordem_alertas))

    for i, alerta in enumerate(ordem_alertas):
        sub = df[df["ALERTA_VENCIMENTO"] == alerta]
        qtd = len(sub)
        val = sub["VALOR_TOTAL"].sum() if "VALOR_TOTAL" in sub.columns else 0
        cols_al[i].markdown(_card_alerta(alerta, qtd, val), unsafe_allow_html=True)

    render_insights(get_vencimentos_insights(df))

    st.markdown("---")

    # ──────────────────────────────────────────────────────────────────────
    # GRÁFICOS
    # ──────────────────────────────────────────────────────────────────────
    col_g1, col_g2 = st.columns([3, 2])

    # Gráfico 1 — vencimentos futuros por mês
    with col_g1:
        st.markdown("""
        <div style='font-size:0.82rem;color:#004B23;font-weight:700;
        text-transform:uppercase;margin-bottom:8px;'>
         Vencimentos por Mês (próximos 12 meses)</div>
        """, unsafe_allow_html=True)

        df_futuro = df[df["DATA_FIM"] >= hoje].copy()

        if df_futuro.empty:
            st.info("Nenhum contrato com vencimento futuro.")
        else:
            df_futuro["MES_VENC"]  = df_futuro["DATA_FIM"].dt.to_period("M").astype(str)
            df_futuro["MES_LABEL"] = df_futuro["DATA_FIM"].dt.to_period("M").dt.to_timestamp().apply(formatar_data)

            df_por_mes = (
                df_futuro
                .groupby(["MES_VENC", "MES_LABEL"])
                .agg(QTDE=("NUMERO_CONTRATO", "count"), VALOR=("VALOR_TOTAL", "sum"))
                .reset_index()
                .sort_values("MES_VENC")
                .head(12)
            )

            fig1 = go.Figure()
            fig1.add_trace(go.Bar(
                x=df_por_mes["MES_LABEL"],
                y=df_por_mes["QTDE"],
                name="Contratos",
                marker_color="#1B7A3E",
                text=df_por_mes["QTDE"],
                textposition="outside",
            ))
            fig1.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=40),
                paper_bgcolor="white",
                plot_bgcolor="#F8F9FA",
                showlegend=False,
                xaxis=dict(title=""),
                yaxis=dict(title="Qtde Contratos"),
                font=dict(family="sans-serif", size=11),
            )
            st.plotly_chart(fig1, use_container_width=True)

    # Gráfico 2 — pizza por alerta
    with col_g2:
        st.markdown("""
        <div style='font-size:0.82rem;color:#004B23;font-weight:700;
        text-transform:uppercase;margin-bottom:8px;'>
         Distribuição por Alerta</div>
        """, unsafe_allow_html=True)

        df_pizza = df["ALERTA_VENCIMENTO"].value_counts().reset_index()
        df_pizza.columns = ["Alerta", "Quantidade"]
        cores_pizza = [cor_status_alerta(a) for a in df_pizza["Alerta"]]

        fig2 = px.pie(
            df_pizza,
            values="Quantidade",
            names="Alerta",
            color_discrete_sequence=cores_pizza,
            hole=0.45,
        )
        fig2.update_traces(textposition="inside", textinfo="percent+label")
        fig2.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="white",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.35),
            font=dict(family="sans-serif", size=11),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ──────────────────────────────────────────────────────────────────────
    # TABELA DE CONTRATOS CRÍTICOS (Vencidos ou Vence em 30d)
    # ──────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.85rem;color:#C0392B;font-weight:700;
    text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;'>
     Contratos Vencidos ou Vencendo em até 30 dias</div>
    """, unsafe_allow_html=True)

    df_crit = df[df["ALERTA_VENCIMENTO"].isin(["Vencido", "Vence em 30d"])].copy()

    if df_crit.empty:
        st.success("Nenhum contrato vencido ou vencendo nos próximos 30 dias!")
    else:
        df_crit = df_crit.sort_values("DIAS_RESTANTES")

        colunas_crit = [
            "NUMERO_CONTRATO", "CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "CLIENTE", "FILIAL_NOME",
            "DATA_FIM", "DIAS_RESTANTES", "VALOR_TOTAL",
            "STATUS", "RESPONSAVEL",
        ]
        colunas_crit = [c for c in colunas_crit if c in df_crit.columns]
        df_crit_exib = df_crit[colunas_crit].copy()

        df_crit_exib = df_crit_exib.rename(columns={
            "NUMERO_CONTRATO": "Nº Contrato",
            "CONTRATO":        "Contrato",
            "FORNECEDOR":      "Fornecedor",
            "CNPJ_FORNECEDOR": "CNPJ/CPF",
            "CLIENTE":         "Cliente",
            "FILIAL_NOME":     "Filial",
            "DATA_FIM":        "Vencimento",
            "DIAS_RESTANTES":  "Dias",
            "VALOR_TOTAL":     "Valor Total",
            "STATUS":          "Status",
            "RESPONSAVEL":     "Responsável",
        })

        if "Vencimento" in df_crit_exib.columns:
            df_crit_exib["Vencimento"] = df_crit_exib["Vencimento"].apply(formatar_data)
        if "Valor Total" in df_crit_exib.columns:
            df_crit_exib["Valor Total"] = df_crit_exib["Valor Total"].apply(formatar_moeda)
        if "CNPJ/CPF" in df_crit_exib.columns:
            df_crit_exib["CNPJ/CPF"] = df_crit_exib["CNPJ/CPF"].apply(formatar_cnpj)

        st.dataframe(df_crit_exib, use_container_width=True, hide_index=True)

        st.markdown(
            f"<div style='background:#FFEBEE;padding:10px 16px;border-radius:8px;"
            f"border:1px solid #EF9A9A;margin-top:8px;'>"
            f"<span style='color:#C0392B;font-weight:700;'> Atenção:</span>"
            f"<span style='color:#555;'> {len(df_crit)} contrato(s) requerem ação imediata.</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ──────────────────────────────────────────────────────────────────────
    # TABELA: VENCENDO EM 31–90 DIAS
    # ──────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.85rem;color:#E67E22;font-weight:700;
    text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;'>
     Contratos Vencendo em 31 a 90 dias</div>
    """, unsafe_allow_html=True)

    df_atencao = df[df["ALERTA_VENCIMENTO"].isin(["Vence em 60d", "Vence em 90d"])].copy()

    if df_atencao.empty:
        st.success(" Nenhum contrato vencendo entre 31 e 90 dias.")
    else:
        df_atencao = df_atencao.sort_values("DIAS_RESTANTES")

        colunas_at = [
            "NUMERO_CONTRATO", "CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "CLIENTE", "FILIAL_NOME",
            "DATA_FIM", "DIAS_RESTANTES", "ALERTA_VENCIMENTO",
            "VALOR_TOTAL", "STATUS", "RESPONSAVEL",
        ]
        colunas_at = [c for c in colunas_at if c in df_atencao.columns]
        df_at_exib = df_atencao[colunas_at].copy()

        df_at_exib = df_at_exib.rename(columns={
            "NUMERO_CONTRATO":   "Nº Contrato",
            "CONTRATO":          "Contrato",
            "FORNECEDOR":        "Fornecedor",
            "CNPJ_FORNECEDOR":   "CNPJ/CPF",
            "CLIENTE":           "Cliente",
            "FILIAL_NOME":       "Filial",
            "DATA_FIM":          "Vencimento",
            "DIAS_RESTANTES":    "Dias",
            "ALERTA_VENCIMENTO": "Alerta",
            "VALOR_TOTAL":       "Valor Total",
            "STATUS":            "Status",
            "RESPONSAVEL":       "Responsável",
        })

        if "Vencimento" in df_at_exib.columns:
            df_at_exib["Vencimento"] = df_at_exib["Vencimento"].apply(formatar_data)
        if "Valor Total" in df_at_exib.columns:
            df_at_exib["Valor Total"] = df_at_exib["Valor Total"].apply(formatar_moeda)
        if "CNPJ/CPF" in df_at_exib.columns:
            df_at_exib["CNPJ/CPF"] = df_at_exib["CNPJ/CPF"].apply(formatar_cnpj)

        st.dataframe(df_at_exib, use_container_width=True, hide_index=True)
