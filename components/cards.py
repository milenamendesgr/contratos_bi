"""Card and executive summary components for KPI visualization."""

from __future__ import annotations

from html import escape
import re
from typing import Iterable, Mapping, Optional

import streamlit as st


SEVERITY_COLORS = {
    "neutral": "#6B7280",
    "positive": "#1B7A3E",
    "warning": "#D97706",
    "critical": "#C0392B",
}

SEVERITY_ICONS = {
    "neutral": "i",
    "positive": "up",
    "warning": "!",
    "critical": "x",
}

KEYWORD_ICONS = {
    "contrato": "doc",
    "financeiro": "$",
    "fornecedor": "id",
    "medicao": "ruler",
    "medicoes": "ruler",
    "valor": "$",
    "saldo": "$",
    "pagamento": "$",
    "alerta": "!",
    "vencimento": "cal",
    "vigencia": "cal",
    "data": "cal",
    "documento": "doc",
    "planilha": "grid",
    "item": "grid",
    "total": "sum",
    "quantidade": "#",
    "status": "tag",
}

ICON_SVGS = {
    "i": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/></svg>',
    "up": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7"/><path d="M8 7h9v9"/></svg>',
    "!": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 4.5 2.8 18a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L13.7 4.5a2 2 0 0 0-3.4 0Z"/></svg>',
    "x": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>',
    "$": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2v20"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7H14a3.5 3.5 0 0 1 0 7H6"/></svg>',
    "#": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9h16"/><path d="M4 15h16"/><path d="M10 3 8 21"/><path d="M16 3l-2 18"/></svg>',
    "cal": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 2v4"/><path d="M16 2v4"/><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M3 10h18"/></svg>',
    "doc": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h5"/></svg>',
    "grid": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M9 3v18"/><path d="M15 3v18"/></svg>',
    "id": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M6.5 16a3.5 3.5 0 0 1 5 0"/><path d="M14 10h4"/><path d="M14 14h4"/></svg>',
    "ruler": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m16 2 6 6L8 22l-6-6Z"/><path d="m7.5 10.5 2 2"/><path d="m10.5 7.5 2 2"/><path d="m13.5 4.5 2 2"/></svg>',
    "sum": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 7V4H6l6 8-6 8h12v-3"/></svg>',
    "tag": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.6 13.1 13 20.7a2 2 0 0 1-2.8 0L3 13.5V4h9.5l8.1 8.1a2 2 0 0 1 0 2.8Z"/><path d="M7.5 7.5h.01"/></svg>',
}

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def _clean_text(value: object) -> str:
    return EMOJI_RE.sub("", str(value)).strip()


def _severity_label(severity: str) -> str:
    labels = {
        "positive": "Positivo",
        "warning": "Atencao",
        "critical": "Critico",
    }
    return labels.get(severity, "Informativo")


def _icon_for(title: str, severity: str = "neutral") -> str:
    normalized = title.lower()
    for keyword, icon in KEYWORD_ICONS.items():
        if keyword in normalized:
            return icon
    return SEVERITY_ICONS.get(severity, SEVERITY_ICONS["neutral"])


def _icon_html(icon: str) -> str:
    return ICON_SVGS.get(icon, escape(icon))


def _trend_for(value: str, severity: str) -> tuple[str, str]:
    normalized = value.lower()
    if "-" in normalized or severity == "critical":
        return "down", "&#8595;"
    if "%" in normalized or severity == "positive":
        return "up", "&#8593;"
    if severity == "warning":
        return "attn", "!"
    return "stable", "-"


def render_section_header(title: str, description: str | None = None) -> None:
    """Render a consistent executive section title."""
    description_html = f"<p>{escape(description)}</p>" if description else ""
    st.markdown(
        f"""
        <div class="bi-section-header">
            <div>{escape(title)}</div>
            {description_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_cards(cards: Iterable[Mapping[str, str]], columns: int = 3) -> None:
    """Render responsive KPI cards.

    Expected keys in each card: title, value, subtitle.
    """
    card_list = list(cards)
    if not card_list:
        st.info("Nenhum indicador configurado para exibicao.")
        return

    render_section_header("Resumo Executivo", "Indicadores principais da visao filtrada.")

    for idx in range(0, len(card_list), columns):
        row = card_list[idx : idx + columns]
        cols = st.columns(columns)
        for col_idx, col in enumerate(cols):
            if col_idx >= len(row):
                col.empty()
                continue

            card = row[col_idx]
            title = _clean_text(card.get("title", "Indicador"))
            value = _clean_text(card.get("value", "--"))
            subtitle = _clean_text(card.get("subtitle", "Aguardando dados"))
            severity = card.get("severity", "neutral")
            color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["neutral"])
            icon = _icon_for(title, str(severity))
            icon_html = _icon_html(icon)
            trend_class, trend_label = _trend_for(value, str(severity))
            help_text: Optional[str] = card.get("help")

            with col:
                st.markdown(
                    f"""
                    <div class=\"bi-kpi-card\" style=\"border-top-color:{color};\">
                        <div class=\"bi-kpi-topline\">
                            <span class=\"bi-kpi-icon\" style=\"background:{color}1A;color:{color};\">{icon_html}</span>
                            <span class=\"bi-kpi-trend bi-trend-{escape(trend_class)}\">{trend_label}</span>
                        </div>
                        <div class=\"bi-kpi-title\">{escape(title)}</div>
                        <div class=\"bi-kpi-value\" style=\"color:{color};\">{escape(value)}</div>
                        <div class=\"bi-kpi-subtitle\">{escape(subtitle)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if help_text:
                    st.caption(help_text)


def render_insights(insights: Iterable[Mapping[str, str] | str], empty_message: str = "") -> None:
    """Render natural-language insights generated by each module from loaded data."""
    insight_list = list(insights)
    render_section_header("Principais Insights", "Leitura automatica dos dados ja carregados no modulo.")

    if not insight_list:
        if empty_message:
            st.success(empty_message)
        return

    for idx in range(0, len(insight_list), 2):
        row = insight_list[idx : idx + 2]
        cols = st.columns(2)
        for col_idx, col in enumerate(cols):
            if col_idx >= len(row):
                col.empty()
                continue

            item = row[col_idx]
            if isinstance(item, str):
                text = item
                severity = "neutral"
                title = "Insight"
            else:
                text = item.get("text", "")
                severity = item.get("severity", "neutral")
                title = item.get("title", "Insight")
            title = _clean_text(title)
            text = _clean_text(text)
            color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["neutral"])
            icon = _icon_for(title, str(severity))
            icon_html = _icon_html(icon)
            with col:
                st.markdown(
                    f"""
                    <div class=\"bi-insight-box\" style=\"border-left-color:{color};\">
                        <div class=\"bi-insight-head\">
                            <span class=\"bi-insight-icon\" style=\"background:{color}1A;color:{color};\">{icon_html}</span>
                            <div>
                                <div class=\"bi-insight-meta\">{escape(_severity_label(str(severity)))}</div>
                                <div class=\"bi-insight-title\" style=\"color:{color};\">{escape(title)}</div>
                            </div>
                        </div>
                        <div class=\"bi-insight-text\">{escape(text)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
