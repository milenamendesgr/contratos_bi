"""
Módulo: Lista de Contratos
Descrição: Importação, filtros, visualização e exportação de contratos - CONTRATOS BI
"""

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from components.cards import render_insights, render_kpi_cards
from config.settings import CORES
from utils.data_loader import carregar_arquivo, gerar_dados_exemplo
from utils.formatters import cor_status_alerta, formatar_cnpj, formatar_data, formatar_moeda, formatar_quantidade
from utils.insights import get_lista_contratos_insights


ACTIVE_STATUS = {"ATIVO", "VIGENTE", "ABERTO"}
STATUS_COLORS = {
    "VIGENTE": ("#1B7A3E", "#E8F5E8"),
    "ELABORACAO": ("#E67E22", "#FFF3E0"),
    "EMITIDO": ("#2980B9", "#E3F2FD"),
    "APROVACAO": ("#7FB77E", "#F1F8F3"),
    "PARALISADO": ("#8E44AD", "#F3E5F5"),
    "CANCELADO": ("#7F8C8D", "#F5F5F5"),
    "FINALIZADO": ("#555555", "#F5F5F5"),
    "REVISAO": ("#F39C12", "#FFF8E1"),
    "REVISADO": ("#0C5E42", "#E8F5E8"),
    "SOLICITACAO_FINALIZACAO": ("#C0392B", "#FFEBEE"),
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

def _badge_status(status: str) -> str:
    cor_txt, cor_bg = STATUS_COLORS.get(str(status).upper(), ("#555", "#F5F5F5"))
    return (
        f"<span style='background:{cor_bg};color:{cor_txt};padding:3px 10px;"
        f"border-radius:12px;font-size:0.78rem;font-weight:700;"
        f"border:1px solid {cor_txt}40;'>{status}</span>"
    )


def _exportar_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df_exp = df.copy()
    for col in ["DATA_INICIO", "DATA_FIM"]:
        if col in df_exp.columns:
            df_exp[col] = df_exp[col].apply(formatar_data)
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_exp.to_excel(writer, index=False, sheet_name="Contratos")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# RENDER PRINCIPAL
# ---------------------------------------------------------------------------

def render_lista():
    """Renderiza o módulo de Lista de Contratos."""

    # ──────────────────────────────────────────────────────────────────────
    # SEÇÃO: IMPORTAÇÃO DE DADOS
    # ──────────────────────────────────────────────────────────────────────
    dados_carregados = "df_contratos" in st.session_state
    with st.expander("Importar / Atualizar Dados de Contratos", expanded=not dados_carregados):

        st.markdown("""
        <div style='background:#F8F9FA;padding:14px 20px;border-radius:10px;
        border-left:4px solid #004B23;margin-bottom:12px;'>
            <b style='color:#004B23;'>Formatos aceitos:</b> Excel (.xlsx) ou CSV (.csv)<br>
            <span style='color:#555;font-size:0.88rem;'>
            Colunas reconhecidas: <b>Número do Contrato, Cliente, Objeto, Filial, Tipo,
            Data de Início, Data de Fim, Valor Mensal, Valor Total, Status,
            Responsável, Observações</b>
            </span>
        </div>
        """, unsafe_allow_html=True)

        col_up, col_demo = st.columns([3, 1])

        with col_up:
            arquivo = st.file_uploader(
                "Selecione o arquivo de contratos",
                type=["xlsx", "xls", "csv"],
                key="uploader_contratos",
                label_visibility="collapsed",
            )

        with col_demo:
            st.markdown("<div style='margin-top:6px;'>", unsafe_allow_html=True)
            if st.button("Usar Dados de Exemplo", use_container_width=True, key="btn_demo_contratos"):
                with st.spinner("Gerando dados de exemplo..."):
                    st.session_state["df_contratos"] = gerar_dados_exemplo()
                    st.session_state["fonte_dados"]  = "Dados de Exemplo (40 contratos)"
                st.success("Dados de exemplo carregados!")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        if arquivo is not None:
            try:
                with st.spinner("Carregando arquivo..."):
                    df = carregar_arquivo(arquivo)
                st.session_state["df_contratos"] = df
                st.session_state["fonte_dados"]  = arquivo.name
                st.success(f"Arquivo carregado! {len(df)} contratos importados.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Erro inesperado: {e}")

    # ──────────────────────────────────────────────────────────────────────
    # SEM DADOS → mensagem de boas-vindas
    # ──────────────────────────────────────────────────────────────────────
    if "df_contratos" not in st.session_state:
        st.markdown("""
        <div style='text-align:center;padding:60px 20px;'>
            <div style='font-size:4rem;margin-bottom:16px;'> </div>
            <h3 style='color:#004B23;'>Nenhum dado carregado</h3>
            <p style='color:#555;'>Importe um arquivo Excel ou CSV com os contratos,<br>
            ou use os <b>dados de exemplo</b> para explorar o dashboard.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    df_orig = st.session_state["df_contratos"].copy()
    fonte   = st.session_state.get("fonte_dados", "arquivo importado")

    st.markdown(
        f"<div style='background:#E8F5E8;padding:8px 16px;border-radius:8px;margin-bottom:12px;"
        f"display:flex;align-items:center;gap:8px;border:1px solid #7FB77E;'>"
        f"<span style='color:#1B7A3E;font-weight:700;'>Dados ativos:</span>"
        f"<span style='color:#555;font-size:0.9rem;'>{fonte} — {len(df_orig)} contratos</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ──────────────────────────────────────────────────────────────────────
    # FILTROS
    # ──────────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='background:white;padding:16px 20px;border-radius:12px;
    border:1px solid #E0E0E0;margin-bottom:16px;box-shadow:0 2px 6px rgba(0,0,0,0.05);'>
        <div style='font-size:0.8rem;color:#004B23;font-weight:700;
        text-transform:uppercase;letter-spacing:0.8px;margin-bottom:10px;'>Filtros</div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    filiais_disp = sorted(df_orig["FILIAL_NOME"].dropna().unique().tolist()) if "FILIAL_NOME" in df_orig.columns else []
    filial_sel = c1.multiselect("Filial", ["Todas"] + filiais_disp, default=["Todas"], key="filtro_filial_lista")

    status_disp = sorted(df_orig["STATUS"].dropna().unique().tolist()) if "STATUS" in df_orig.columns else []
    status_sel = c2.multiselect("Status", ["Todos"] + status_disp, default=["Todos"], key="filtro_status_lista")

    tipos_disp = sorted(df_orig["TIPO"].dropna().unique().tolist()) if "TIPO" in df_orig.columns else []
    tipo_sel = c3.multiselect("Tipo", ["Todos"] + tipos_disp, default=["Todos"], key="filtro_tipo_lista")

    alertas_disp = sorted(df_orig["ALERTA_VENCIMENTO"].dropna().unique().tolist()) if "ALERTA_VENCIMENTO" in df_orig.columns else []
    alerta_sel = c4.multiselect("Alerta de Vencimento", ["Todos"] + alertas_disp, default=["Todos"], key="filtro_alerta_lista")

    st.markdown("</div>", unsafe_allow_html=True)

    # Aplicar filtros
    df = df_orig.copy()
    if "FORNECEDOR" not in df.columns and "NOME_FORNECEDOR" in df.columns:
        df["FORNECEDOR"] = df["NOME_FORNECEDOR"]
    if filial_sel and "Todas" not in filial_sel:
        df = df[df["FILIAL_NOME"].isin(filial_sel)]
    if status_sel and "Todos" not in status_sel:
        df = df[df["STATUS"].isin(status_sel)]
    if tipo_sel and "Todos" not in tipo_sel:
        df = df[df["TIPO"].isin(tipo_sel)]
    if alerta_sel and "Todos" not in alerta_sel:
        df = df[df["ALERTA_VENCIMENTO"].isin(alerta_sel)]

    # ──────────────────────────────────────────────────────────────────────
    # KPI RESUMO
    # ──────────────────────────────────────────────────────────────────────
    total_filt   = len(df)
    valor_total  = df["VALOR_TOTAL"].sum() if "VALOR_TOTAL" in df.columns else 0
    ativos       = int(_active_mask(df).sum())
    vencidos     = int(_vencido_mask(df).sum())

    render_kpi_cards(
        [
            {"title": "Total filtrado", "value": formatar_quantidade(total_filt), "subtitle": "Contratos exibidos", "severity": "neutral"},
            {"title": "Valor total", "value": formatar_moeda(valor_total), "subtitle": "Soma da carteira filtrada", "severity": "positive"},
            {"title": "Contratos vigentes", "value": formatar_quantidade(ativos), "subtitle": "Status VIGENTE", "severity": "positive"},
            {"title": "Contratos vencidos", "value": formatar_quantidade(vencidos), "subtitle": "Requerem atencao", "severity": "critical" if vencidos else "neutral"},
        ],
        columns=4,
    )

    render_insights(get_lista_contratos_insights(df, total_filt, valor_total, vencidos, money_formatter=formatar_moeda))

    # ──────────────────────────────────────────────────────────────────────
    # TABELA
    # ──────────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='font-size:0.85rem;color:#004B23;font-weight:700;
    text-transform:uppercase;letter-spacing:0.8px;margin:16px 0 8px 0;'>
    Lista de Contratos</div>
    """, unsafe_allow_html=True)

    if df.empty:
        st.info("Nenhum contrato encontrado com os filtros selecionados.")
        return

    colunas_ord = [
        "NUMERO_CONTRATO", "CONTRATO", "FORNECEDOR", "CNPJ_FORNECEDOR", "CLIENTE", "COD_FORNECEDOR", "LOJA_FORNECEDOR", "FILIAL_NOME", "TIPO",
        "DATA_INICIO", "DATA_FIM", "VALOR_TOTAL",
        "STATUS", "ALERTA_VENCIMENTO", "DIAS_RESTANTES", "RESPONSAVEL",
    ]
    colunas_pres = [c for c in colunas_ord if c in df.columns]
    df_exib = df[colunas_pres].copy()

    rename_exib = {
        "NUMERO_CONTRATO":   "Nº Contrato",
        "CONTRATO":          "Contrato",
        "FORNECEDOR":        "Fornecedor",
        "CNPJ_FORNECEDOR":   "CNPJ/CPF",
        "COD_FORNECEDOR":    "Cod. Fornecedor",
        "LOJA_FORNECEDOR":   "Loja Fornecedor",
        "CLIENTE":           "Cliente",
        "FILIAL_NOME":       "Filial",
        "TIPO":              "Tipo",
        "DATA_INICIO":       "Início",
        "DATA_FIM":          "Vencimento",
        "VALOR_TOTAL":       "Valor Total",
        "STATUS":            "Status",
        "ALERTA_VENCIMENTO": "Alerta",
        "DIAS_RESTANTES":    "Dias Rest.",
        "RESPONSAVEL":       "Responsável",
    }
    df_exib = df_exib.rename(columns=rename_exib)

    for col_d in ["Início", "Vencimento"]:
        if col_d in df_exib.columns:
            df_exib[col_d] = df_exib[col_d].apply(formatar_data)

    if "Valor Total" in df_exib.columns:
        df_exib["Valor Total"] = df_exib["Valor Total"].apply(formatar_moeda)

    if "CNPJ/CPF" in df_exib.columns:
        df_exib["CNPJ/CPF"] = df_exib["CNPJ/CPF"].apply(formatar_cnpj)

    if "Dias Rest." in df_exib.columns:
        df_exib = df_exib.sort_values("Dias Rest.")

    st.dataframe(df_exib, use_container_width=True, hide_index=True)

    # ──────────────────────────────────────────────────────────────────────
    # EXPORTAÇÃO
    # ──────────────────────────────────────────────────────────────────────
    col_exp1, col_exp2, _ = st.columns([1, 1, 5])

    with col_exp1:
        excel_bytes = _exportar_excel(df[colunas_pres])
        st.download_button(
            "Exportar Excel",
            data=excel_bytes,
            file_name=f"contratos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col_exp2:
        csv_bytes = df[colunas_pres].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        st.download_button(
            "Exportar CSV",
            data=csv_bytes,
            file_name=f"contratos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
