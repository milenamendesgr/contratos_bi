"""
CONTRATOS BI - Dashboard de Contratos
Arquivo Principal (Roteador)
Versão: 1.0 - Arquitetura Modular

IMPORTANTE - TEMA BRANCO OBRIGATÓRIO
- O fundo da aplicação DEVE ser SEMPRE BRANCO (#FFFFFF)
- Nunca remover o script de forçar tema claro
- Nunca remover o CSS de background-color branco
- Design profissional e moderno requer fundo branco
"""

import streamlit as st
from datetime import datetime

# Importar configurações e módulos
from config.settings import CORES, FILIAIS, DEMO_MODE
from modules.adiantamentos import render_adiantamentos
from modules.dashboard_executivo import render_dashboard_executivo
from modules.vigencia_prazos import render_vigencia_prazos
from modules.execucao_contratual import render_execucao_contratual
from modules.financeiro import render_financeiro
from modules.fornecedores import render_fornecedores
from modules.itens_planilhas import render_itens_planilhas
from modules.medicoes import render_medicoes
from modules.alertas import render_alertas
from modules.consulta_contratos import render_consulta_contratos
from utils.contratos_repository import get_carteira_contratos

# ==================================================
# CONFIGURAÇÃO DA PÁGINA
# ==================================================
st.set_page_config(
    page_title="CONTRATOS BI - Contratos",
    layout="wide",
    page_icon=" ",
    initial_sidebar_state="expanded",
)

# Inicializar sessão
if "dados_precarregados" not in st.session_state:
    st.session_state["dados_precarregados"] = True

# Script para remover botão de colapsar sidebar
st.markdown("""
<script>
    const removeCollapseButton = () => {
        const buttons = window.parent.document.querySelectorAll('button[kind="header"]');
        buttons.forEach(btn => btn.style.display = 'none');
        const collapseControl = window.parent.document.querySelector('[data-testid="collapsedControl"]');
        if (collapseControl) collapseControl.style.display = 'none';
    };
    removeCollapseButton();
    const observer = new MutationObserver(removeCollapseButton);
    observer.observe(window.parent.document.body, { childList: true, subtree: true });
</script>
""", unsafe_allow_html=True)

# ==================================================
# CRÍTICO: FORÇAR TEMA CLARO - NÃO REMOVER!
# ==================================================
st.markdown("""
<script>
    const forceWhiteTheme = () => {
        const doc = window.parent.document;
        doc.documentElement.setAttribute('data-theme', 'light');
        doc.body.style.backgroundColor = '#FFFFFF';
        const mainElement = doc.querySelector('.main');
        if (mainElement) mainElement.style.backgroundColor = '#FFFFFF';
        const containers = doc.querySelectorAll('[data-testid="stAppViewContainer"]');
        containers.forEach(c => { c.style.backgroundColor = '#FFFFFF'; });
        const stApp = doc.querySelector('.stApp');
        if (stApp) stApp.style.backgroundColor = '#FFFFFF';
    };
    forceWhiteTheme();
    let counter = 0;
    const interval = setInterval(() => {
        forceWhiteTheme();
        counter++;
        if (counter > 30) clearInterval(interval);
    }, 100);
    const observer = new MutationObserver(forceWhiteTheme);
    observer.observe(window.parent.document.body, {
        childList: true, subtree: true,
        attributes: true, attributeFilter: ['data-theme', 'style', 'class']
    });
</script>
""", unsafe_allow_html=True)

# Inicializar data de início de sessão
if "data_inicio_sessao" not in st.session_state:
    st.session_state["data_inicio_sessao"] = datetime.now()

# ==================================================
# CSS PRINCIPAL - FUNDO BRANCO OBRIGATÓRIO
# ==================================================
st.markdown("""
<style>
    /* =========================================== */
    /* FORÇAR TEMA BRANCO EM TODOS OS ELEMENTOS   */
    /* =========================================== */
    html, body, [data-testid="stAppViewContainer"],
    [data-testid="stApp"], .main, .stApp {
        background-color: #FFFFFF !important;
    }
    [data-theme="dark"] {
        --background-color: #FFFFFF !important;
        --secondary-background-color: #F8F9FA !important;
        --text-color: #1C1C1C !important;
    }

    /* =========================================== */
    /* CORES DA PALETA CONTRATOS BI                   */
    /* =========================================== */
    :root {
        --verde-primario:   #004B23;
        --verde-secundario: #1B7A3E;
        --verde-destaque:   #7FB77E;
        --fundo-principal:  #FFFFFF;
        --fundo-secundario: #F8F9FA;
        --fundo-card:       #FFFFFF;
        --texto-principal:  #1C1C1C;
        --texto-secundario: #555555;
        --borda-suave:      #E0E0E0;
        --borda-card:       #DCE3EA;
        --cinza-claro:      #F4F7F6;
        --cinza-medio:      #64748B;
        --azul-info:        #2563EB;
        --amarelo-atencao:  #D97706;
        --vermelho-alerta:  #C0392B;
        --sombra-suave:     0 12px 30px rgba(15, 23, 42, 0.07);
        --sombra-hover:     0 18px 40px rgba(15, 75, 35, 0.13);
    }

    html, body, .stApp, [data-testid="stAppViewContainer"] {
        color: var(--texto-principal) !important;
        font-family: "Aptos", "Segoe UI", sans-serif !important;
    }

    h1, h2, h3, h4, h5, h6 {
        color: var(--texto-principal) !important;
        letter-spacing: 0 !important;
    }

    /* Remove espaços do topo */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1.25rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1480px !important;
    }
    .main { padding-top: 0rem !important; }
    .main > div:first-child { padding-top: 0rem !important; }
    header[data-testid="stHeader"] { display: none !important; }
    footer { visibility: hidden !important; }

    /* Fundo branco garantido */
    .stApp,
    [data-testid="stAppViewContainer"],
    .main { background-color: #FFFFFF !important; }
    .block-container { background-color: transparent !important; }

    /* =========================================== */
    /* SIDEBAR CONTRATOS BI                           */
    /* =========================================== */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div {
        background: linear-gradient(180deg, #003A1B 0%, #075C31 48%, #0F6B3C 100%) !important;
        padding-top: 0rem !important;
        width: 204px !important;
        min-width: 204px !important;
        max-width: 204px !important;
        position: relative !important;
        transition: none !important;
        top: 0 !important;
        margin-top: 0 !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        width: 204px !important;
        padding-top: 0rem !important;
        margin-top: 0 !important;
    }
    [data-testid="stSidebar"][aria-expanded="false"] {
        width: 204px !important;
        min-width: 204px !important;
        margin-left: 0 !important;
        transform: none !important;
    }
    [data-testid="stSidebar"] * { color: white !important; }

    /* Remove botões de colapsar */
    [data-testid="collapsedControl"],
    [data-testid="baseButton-header"],
    button[kind="header"],
    section[data-testid="stSidebar"] button[kind="header"],
    [data-testid="stSidebar"] button[aria-label],
    .css-1dp5vir {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* =========================================== */
    /* LOGO DA SIDEBAR                            */
    /* =========================================== */
    .sidebar-logo {
        text-align: center;
        padding: 14px 10px 12px 10px;
        margin-bottom: 12px;
        margin-top: 0px;
        border-bottom: 1px solid rgba(255,255,255,0.22);
    }
    .sidebar-logo h1 {
        color: white !important;
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: 0.8px;
        margin: 0;
        padding-top: 1px;
        text-shadow: none;
    }
    .sidebar-logo div {
        font-size: 0.8rem !important;
        opacity: 0.95;
        letter-spacing: 0.6px;
        font-weight: 600;
        text-transform: uppercase;
        margin-top: 3px;
    }
    .sidebar-section-title {
        color: #7FB77E !important;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 8px 14px 6px 14px;
        margin-top: 8px;
    }

    /* =========================================== */
    /* RADIO BUTTONS DA SIDEBAR                   */
    /* =========================================== */
    [data-testid="stSidebar"] .stRadio > label { display: none !important; }
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] {
        width: 100% !important;
        gap: 6px;
        display: flex;
        flex-direction: column;
        align-items: stretch !important;
    }
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
        background: rgba(255,255,255,0.10) !important;
        padding: 10px 12px !important;
        border-radius: 10px !important;
        margin: 0 10px !important;
        transition: background-color 0.18s ease, border-color 0.18s ease, transform 0.18s ease !important;
        cursor: pointer !important;
        border: 1px solid transparent !important;
        box-shadow: none !important;
        min-height: 46px !important;
        height: auto !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover {
        background: rgba(255,255,255,0.18) !important;
        border-color: rgba(255,255,255,0.35) !important;
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-checked="true"] {
        background: rgba(255,255,255,0.24) !important;
        border-color: white !important;
        box-shadow: inset 3px 0 0 #FFFFFF !important;
        font-weight: 750 !important;
    }

    /* =========================================== */
    /* HEADER PRINCIPAL                           */
    /* =========================================== */
    .main-header {
        background: linear-gradient(135deg, #FFFFFF 0%, #F3FAF6 100%);
        color: var(--texto-principal);
        padding: 20px 24px;
        border-radius: 14px;
        border: 1px solid var(--borda-card);
        border-left: 5px solid var(--verde-primario);
        text-align: left;
        font-weight: 700;
        letter-spacing: 0;
        margin-bottom: 16px;
        margin-top: 0px;
        box-shadow: var(--sombra-suave);
    }
    .subtitle {
        color: var(--texto-secundario);
        font-size: 0.92rem;
        font-weight: 500;
        margin-top: 4px;
        letter-spacing: 0;
    }

    /* =========================================== */
    /* BOTÕES                                     */
    /* =========================================== */
    .stButton > button {
        border: 1px solid var(--verde-primario);
        background: white;
        color: var(--verde-primario);
        border-radius: 10px;
        padding: 8px 16px;
        font-weight: 600;
        transition: background-color 0.18s ease, color 0.18s ease, border-color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
        font-size: 0.85rem;
    }
    .stButton > button[kind="primary"],
    .stButton > button[data-baseweb="button"][kind="primary"] {
        background: #1C1C1C !important;
        color: white !important;
        border-color: #1C1C1C !important;
        box-shadow: none !important;
    }
    .stButton > button:hover {
        background: var(--verde-primario);
        color: white;
        transform: translateY(-1px);
        box-shadow: 0 10px 20px rgba(0, 75, 35, 0.16);
    }

    /* =========================================== */
    /* ABAS                                       */
    /* =========================================== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: var(--fundo-secundario);
        padding: 6px;
        border-radius: 8px;
        border: 1px solid var(--borda-card);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
        transition: background-color 0.15s ease, color 0.15s ease;
    }
    .stTabs [aria-selected="true"] {
        background: var(--verde-primario) !important;
        color: white !important;
        box-shadow: none;
    }

    /* =========================================== */
    /* FILTROS E FORMULARIOS                      */
    /* =========================================== */
    [data-testid="stExpander"] {
        border: 1px solid var(--borda-card) !important;
        border-radius: 14px !important;
        background: #FFFFFF !important;
        box-shadow: var(--sombra-suave) !important;
        margin: 10px 0 18px 0 !important;
    }
    [data-testid="stExpander"] summary {
        color: var(--verde-primario) !important;
        font-size: 0.82rem !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
        background: linear-gradient(90deg, #F3FAF6 0%, #FFFFFF 100%) !important;
        border-radius: 14px 14px 0 0 !important;
        min-height: 46px !important;
    }
    [data-baseweb="select"] > div,
    [data-testid="stTextInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        border-color: var(--borda-card) !important;
        border-radius: 10px !important;
        background-color: #FFFFFF !important;
        min-height: 40px !important;
        box-shadow: none !important;
    }
    [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] p {
        color: #374151 !important;
        font-size: 0.78rem !important;
        font-weight: 700 !important;
    }

    /* =========================================== */
    /* DATAFRAME — REMOVE ÍNDICE                  */
    /* =========================================== */
    [data-testid="stDataFrame"] div[role="gridcell"][aria-colindex="1"],
    [data-testid="stDataFrame"] div[role="columnheader"][aria-colindex="1"] {
        display: none !important;
        width: 0 !important;
        padding: 0 !important;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid var(--borda-card) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: var(--sombra-suave) !important;
        background: #FFFFFF !important;
    }
    [data-testid="stDataFrame"] div[role="columnheader"] {
        background: #F1F7F4 !important;
        color: #0F3D27 !important;
        font-weight: 800 !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 2 !important;
    }
    [data-testid="stDataFrame"] div[role="row"]:nth-child(even) div[role="gridcell"] {
        background-color: #FAFCFB !important;
    }
    [data-testid="stDataFrame"] div[role="row"]:hover div[role="gridcell"] {
        background-color: #EEF8F1 !important;
    }
    [data-testid="stMetric"] {
        background: #FFFFFF !important;
        border: 1px solid var(--borda-card) !important;
        border-radius: 12px !important;
        padding: 14px 16px !important;
        box-shadow: var(--sombra-suave) !important;
    }
    [data-testid="stPlotlyChart"] {
        background: #FFFFFF !important;
        border: 1px solid var(--borda-card) !important;
        border-radius: 12px !important;
        padding: 12px !important;
        box-shadow: var(--sombra-suave) !important;
    }
    div[data-testid="stDialog"] > div,
    [data-testid="stDialog"] section {
        border-radius: 18px !important;
        border: 1px solid var(--borda-card) !important;
        box-shadow: 0 28px 70px rgba(15, 23, 42, 0.22) !important;
    }
    [data-testid="stDialog"] [data-testid="stMetric"] {
        min-height: 96px;
        padding: 12px 14px 14px 14px;
        overflow: visible;
    }
    [data-testid="stDialog"] [data-testid="stMetricLabel"] p,
    [data-testid="stDialog"] [data-testid="stMetricValue"] div {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }
    [data-testid="stDialog"] [data-testid="stMetricValue"] div {
        overflow-wrap: anywhere;
        line-height: 1.15;
        font-size: clamp(1rem, 1.7vw, 1.45rem);
    }

    /* =========================================== */
    /* PADRAO EXECUTIVO DOS MODULOS               */
    /* =========================================== */
    .bi-section-header {
        margin: 24px 0 14px 0;
        padding: 0 0 12px 0;
        border-bottom: 1px solid #E2E8F0;
        color: #004B23;
        font-size: 0.9rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .bi-section-header p {
        margin: 4px 0 0 0;
        color: #6B7280;
        font-size: 0.78rem;
        font-weight: 500;
        text-transform: none;
        letter-spacing: 0;
    }
    .bi-kpi-card {
        min-height: 158px;
        border: 1px solid #DCE3EA;
        border-top: 4px solid #6B7280;
        border-radius: 14px;
        padding: 16px 18px;
        background: linear-gradient(180deg, #FFFFFF 0%, #FAFCFB 100%);
        box-shadow: var(--sombra-suave);
        margin-bottom: 14px;
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        animation: biFadeUp 0.28s ease both;
    }
    .bi-kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--sombra-hover);
        border-color: #B8D9C4;
    }
    .bi-kpi-topline {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    .bi-kpi-icon,
    .bi-insight-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 34px;
        height: 34px;
        border-radius: 10px;
        font-size: 0.74rem;
        font-weight: 850;
        text-transform: uppercase;
    }
    .bi-kpi-icon svg,
    .bi-insight-icon svg {
        width: 18px;
        height: 18px;
        fill: none;
        stroke: currentColor;
        stroke-width: 2;
        stroke-linecap: round;
        stroke-linejoin: round;
    }
    .bi-kpi-trend {
        border-radius: 999px;
        padding: 4px 8px;
        background: #F1F5F9;
        color: #64748B;
        font-size: 0.64rem;
        font-weight: 850;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .bi-kpi-title {
        display: flex;
        align-items: center;
        font-size: 0.76rem;
        color: #4A5568;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }
    .bi-kpi-value {
        font-size: 2.05rem;
        font-weight: 800;
        line-height: 1.08;
        margin-top: 10px;
        word-break: break-word;
    }
    .bi-kpi-subtitle {
        font-size: 0.78rem;
        color: #6B7280;
        margin-top: 8px;
        line-height: 1.35;
    }
    .bi-insight-box {
        min-height: 118px;
        border: 1px solid #E5E7EB;
        border-left: 4px solid #6B7280;
        border-radius: 14px;
        padding: 14px 16px;
        background: linear-gradient(180deg, #FFFFFF 0%, #FAFCFB 100%);
        box-shadow: var(--sombra-suave);
        margin-bottom: 12px;
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }
    .bi-insight-box:hover {
        transform: translateY(-2px);
        box-shadow: var(--sombra-hover);
    }
    .bi-insight-head {
        display: flex;
        gap: 10px;
        align-items: center;
        margin-bottom: 10px;
    }
    .bi-insight-meta {
        color: #6B7280;
        font-size: 0.66rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
    }
    .bi-insight-title {
        font-size: 0.74rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 6px;
    }
    .bi-insight-text {
        color: #374151;
        font-size: 0.9rem;
        line-height: 1.42;
    }

    @keyframes biFadeUp {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 900px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .main-header {
            padding: 16px 18px;
        }
        .bi-kpi-value {
            font-size: 1.55rem;
        }
    }

    /* =========================================== */
    /* SPINNER                                    */
    /* =========================================== */
    .stSpinner > div { border-color: var(--verde-primario) !important; }
</style>
""", unsafe_allow_html=True)

# ==================================================
# INICIALIZAÇÃO DE ESTADOS
# ==================================================
if "modulo_selecionado" not in st.session_state:
    st.session_state["modulo_selecionado"] = "inicio"


def get_data_context() -> dict:
    """Centraliza os DataFrames esperados pelos modulos."""
    df_contratos = st.session_state.get("df_contratos")
    if df_contratos is None or (hasattr(df_contratos, "empty") and df_contratos.empty):
        df_contratos = get_carteira_contratos()
        st.session_state["df_contratos"] = df_contratos

    return {
        "df_contratos": df_contratos,
        "df_fornecedores": st.session_state.get("df_fornecedores"),
        "df_medicoes": st.session_state.get("df_medicoes"),
        "df_financeiro": st.session_state.get("df_financeiro"),
        "df_itens": st.session_state.get("df_itens"),
    }


# ==================================================
# CALLBACKS DE NAVEGAÇÃO
# ==================================================
def atualizar_modulo():
    menu = st.session_state.get("menu_radio_contratos", "Dashboard Executivo")
    mapa = {
        "Dashboard Executivo": "dashboard_executivo",
        "Vigência e Prazos": "vigencia_prazos",
        "Adiantamentos": "adiantamentos",
        "Medições": "medicoes",
        "Alertas": "alertas",
        "Consulta de Contratos": "consulta_contratos",
    }
    st.session_state["modulo_selecionado"] = mapa.get(menu, "dashboard_executivo")


menu_pendente = st.session_state.pop("_menu_radio_contratos_pendente", None)
if menu_pendente is not None:
    st.session_state["menu_radio_contratos"] = menu_pendente
    atualizar_modulo()


# ==================================================
# SIDEBAR — MENU DE NAVEGAÇÃO
# ==================================================
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <h1>CONTRATOS BI</h1>
        <div style="font-size:0.7rem;opacity:0.9;margin-top:2px;">Analise de contratos</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-title">MENU PRINCIPAL</div>', unsafe_allow_html=True)

    opcoes = [
        "Dashboard Executivo",
        "Vigência e Prazos",
        "Adiantamentos",
        "Medições",
        "Alertas",
        "Consulta de Contratos",
    ]
    modulo_atual = st.session_state.get("modulo_selecionado")

    indice_mapa = {
        "dashboard_executivo": 0, "vigencia_prazos": 1,
        "adiantamentos": 2, "medicoes": 3,
        "alertas": 4, "consulta_contratos": 5,
    }
    indice_atual = indice_mapa.get(modulo_atual, 0)
    if modulo_atual not in indice_mapa:
        st.session_state["modulo_selecionado"] = "dashboard_executivo"
    if st.session_state.get("menu_radio_contratos") not in opcoes:
        st.session_state["menu_radio_contratos"] = opcoes[indice_atual]

    st.radio(
        "navegacao",
        opcoes,
        index=indice_atual,
        key="menu_radio_contratos",
        label_visibility="collapsed",
        on_change=atualizar_modulo,
    )

    # Indicador de dados carregados na sidebar
    if "df_contratos" in st.session_state:
        qtd = len(st.session_state["df_contratos"])
        st.markdown(
            f"<div style='background:rgba(255,255,255,0.12);padding:10px 12px;"
            f"border-radius:8px;margin:8px;text-align:center;font-size:0.8rem;'>"
            f"<div style='color:#7FB77E;font-weight:700;'>DADOS CARREGADOS</div>"
            f"<div style='color:rgba(255,255,255,0.85);margin-top:2px;'>{qtd} contratos</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='background:rgba(255,255,255,0.08);padding:10px 12px;"
            "border-radius:8px;margin:8px;text-align:center;font-size:0.8rem;'>"
            "<div style='color:rgba(255,255,255,0.5);font-weight:600;'>SEM DADOS</div>"
            "<div style='color:rgba(255,255,255,0.35);margin-top:2px;font-size:0.72rem;'>"
            "Importe um arquivo</div>"
            "</div>",
            unsafe_allow_html=True,
        )

# ==================================================
# HEADER PRINCIPAL
# ==================================================
st.markdown("""
<div class="main-header">
    <div style="font-size:1.35rem;margin-bottom:4px;font-weight:800;">CONTRATOS BI</div>
    <div class="subtitle">Dashboard de Contratos</div>
</div>
""", unsafe_allow_html=True)

# ==================================================
# ROTEAMENTO DE MÓDULOS
# ==================================================
modulo = st.session_state.get("modulo_selecionado")
if DEMO_MODE:
    st.info("DEMONSTRACAO | Todos os dados sao ficticios e gerados localmente, sem conexao com a empresa.")

data_context = get_data_context()

if modulo == "inicio":
    st.markdown("""
    <div style='text-align:center;padding:28px 20px 12px 20px;'>
        <h2 style='color:#004B23;margin-bottom:6px;'>Início</h2>
        <p style='color:#555;'>Selecione um módulo no menu lateral para navegar pelo BI de Contratos.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Módulos de negócio", "10")
    c2.metric("Filiais mapeadas", str(len(FILIAIS)))
    c3.metric("Status", "Dados ficticios" if DEMO_MODE else "API")

    if st.button("Acessar Dashboard Executivo", type="primary"):
        st.session_state["_menu_radio_contratos_pendente"] = "Dashboard Executivo"
        st.rerun()

elif modulo == "dashboard_executivo":
    render_dashboard_executivo(**data_context)

elif modulo == "vigencia_prazos":
    render_vigencia_prazos(**data_context)

elif modulo == "execucao_contratual":
    render_execucao_contratual(**data_context)

elif modulo == "financeiro":
    render_financeiro(**data_context)

elif modulo == "adiantamentos":
    render_adiantamentos(**data_context)

elif modulo == "fornecedores":
    render_fornecedores(**data_context)

elif modulo == "itens_planilhas":
    render_itens_planilhas(**data_context)

elif modulo == "medicoes":
    render_medicoes(**data_context)

elif modulo == "alertas":
    render_alertas(**data_context)

elif modulo == "consulta_contratos":
    render_consulta_contratos(**data_context)

else:
    render_dashboard_executivo(**data_context)

# ==================================================
# FOOTER
# ==================================================
st.markdown("---")
st.markdown(
    f"<div style='text-align:center;color:#555;padding:20px;'>"
    f"<p style='font-size:1rem;font-weight:700;color:#004B23;'>CONTRATOS BI</p>"
    f"<p>Dashboard de Contratos v1.0 — Arquitetura Modular</p>"
    f"<p style='font-size:0.82rem;color:#888;margin-top:6px;'>"
    f"{len(FILIAIS)} Filiais Mapeadas | 10 Modulos | Dados demonstrativos"
    f"</p></div>",
    unsafe_allow_html=True,
)
