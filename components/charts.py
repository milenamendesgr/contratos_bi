"""Chart wrappers prepared for future DataFrame integrations."""

from __future__ import annotations

import re
from typing import Any, Optional

import plotly.express as px
import streamlit as st

from components.cards import render_section_header
from utils.formatters import formatar_moeda, formatar_percentual, formatar_quantidade


EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")
CHART_HEIGHT = 340
CHART_COLORS = ["#0F6B3C", "#2E8B57", "#7FB77E", "#2563EB", "#D97706", "#C0392B", "#64748B"]


def _clean_visual_text(value: Any) -> Any:
    if isinstance(value, str):
        return EMOJI_RE.sub("", value).strip()
    return value


def _prepare_chart_df(df: Any) -> Any:
    if not hasattr(df, "copy") or not hasattr(df, "columns"):
        return df
    result = df.copy()
    for column in result.columns:
        if getattr(result[column], "dtype", None) == "object":
            result[column] = result[column].map(_clean_visual_text)
    return result


def _format_chart_text(df: Any, column: str) -> Any:
    column_upper = str(column).upper()
    if not hasattr(df, "columns") or column not in df.columns:
        return column
    if "PERCENT" in column_upper or "PARTICIPACAO" in column_upper:
        return df[column].apply(formatar_percentual)
    if any(token in column_upper for token in ["VALOR", "SALDO", "TICKET", "MULTA", "RECEITA"]):
        return df[column].apply(formatar_moeda)
    if any(token in column_upper for token in ["QTD", "QTDE", "QUANTIDADE"]):
        return df[column].apply(formatar_quantidade)
    return df[column]


def render_chart_placeholder(
    title: str,
    description: str,
    df: Optional[Any] = None,
    empty_message: str = "Sem dados carregados para este grafico.",
) -> None:
    """Render a chart area that can receive a DataFrame in the future."""
    st.markdown(f"### {title}")
    st.caption(description)

    if df is None:
        st.info(f"PLACEHOLDER TEMPORARIO: {empty_message}")
        return

    if hasattr(df, "empty") and getattr(df, "empty"):
        st.warning("DataFrame recebido, mas sem linhas para visualizacao.")
        return

    st.success("DataFrame recebido. Substituir por grafico real na fase de integracao.")
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_bar_chart(
    title: str,
    df: Any,
    x: str,
    y: str,
    orientation: str = "v",
    color: str = "#004B23",
    empty_message: str = "Sem dados para este grafico.",
) -> None:
    """Render a simple Plotly bar chart with a consistent empty state."""
    render_section_header(title)
    if df is None or (hasattr(df, "empty") and getattr(df, "empty")):
        st.info(empty_message)
        return

    df = _prepare_chart_df(df)

    fig = px.bar(
        df,
        x=x,
        y=y,
        orientation=orientation,
        color_discrete_sequence=[color or CHART_COLORS[0]],
        text=_format_chart_text(df, y if orientation == "v" else x),
    )
    fig.update_traces(
        textposition="outside",
        marker_line_color="rgba(15, 107, 60, 0.25)",
        marker_line_width=1,
        hovertemplate="<b>%{x}</b><br>%{y}<extra></extra>" if orientation == "v" else "<b>%{y}</b><br>%{x}<extra></extra>",
    )
    fig.update_layout(
        height=CHART_HEIGHT,
        margin=dict(l=12, r=18, t=18, b=42),
        paper_bgcolor="white",
        plot_bgcolor="#FFFFFF",
        showlegend=False,
        font=dict(family="Aptos, Segoe UI, sans-serif", size=12, color="#334155"),
        xaxis_title="",
        yaxis_title="",
        bargap=0.34,
        hoverlabel=dict(bgcolor="#0F172A", font_size=12, font_color="#FFFFFF", bordercolor="#0F172A"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#EEF2F6", zeroline=False, linecolor="#CBD5E1", tickfont=dict(color="#475569"))
    fig.update_yaxes(showgrid=False, zeroline=False, linecolor="#CBD5E1", tickfont=dict(color="#475569"))
    st.plotly_chart(fig, use_container_width=True)


def render_line_chart(
    title: str,
    df: Any,
    x: str,
    y: str,
    color: str = "#1B7A3E",
    empty_message: str = "Sem dados para este grafico.",
) -> None:
    """Render a simple Plotly line chart with a consistent empty state."""
    render_section_header(title)
    if df is None or (hasattr(df, "empty") and getattr(df, "empty")):
        st.info(empty_message)
        return

    df = _prepare_chart_df(df)

    fig = px.line(df, x=x, y=y, markers=True, color_discrete_sequence=[color or CHART_COLORS[1]])
    fig.update_layout(
        height=CHART_HEIGHT,
        margin=dict(l=12, r=18, t=18, b=42),
        paper_bgcolor="white",
        plot_bgcolor="#FFFFFF",
        showlegend=False,
        font=dict(family="Aptos, Segoe UI, sans-serif", size=12, color="#334155"),
        xaxis_title="",
        yaxis_title="",
        hoverlabel=dict(bgcolor="#0F172A", font_size=12, font_color="#FFFFFF", bordercolor="#0F172A"),
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=7, line=dict(width=1, color="#FFFFFF")), hovertemplate="<b>%{x}</b><br>%{y}<extra></extra>")
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#CBD5E1", tickfont=dict(color="#475569"))
    fig.update_yaxes(showgrid=True, gridcolor="#EEF2F6", zeroline=False, linecolor="#CBD5E1", tickfont=dict(color="#475569"))
    st.plotly_chart(fig, use_container_width=True)


def render_pie_chart(
    title: str,
    df: Any,
    names: str,
    values: str,
    empty_message: str = "Sem dados para este grafico.",
) -> None:
    """Render a simple Plotly pie chart with a consistent empty state."""
    render_section_header(title)
    if df is None or (hasattr(df, "empty") and getattr(df, "empty")):
        st.info(empty_message)
        return

    df = _prepare_chart_df(df)

    fig = px.pie(
        df,
        names=names,
        values=values,
        hole=0.45,
        color_discrete_sequence=CHART_COLORS,
    )
    fig.update_layout(
        height=CHART_HEIGHT,
        margin=dict(l=12, r=18, t=18, b=42),
        paper_bgcolor="white",
        plot_bgcolor="#FFFFFF",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        font=dict(family="Aptos, Segoe UI, sans-serif", size=12, color="#334155"),
        hoverlabel=dict(bgcolor="#0F172A", font_size=12, font_color="#FFFFFF", bordercolor="#0F172A"),
    )
    fig.update_traces(textposition="outside", textinfo="label+percent", hoverinfo="label+value+percent")
    st.plotly_chart(fig, use_container_width=True)
