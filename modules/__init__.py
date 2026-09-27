"""Modules package for contratos BI skeleton."""

from .adiantamentos import render_adiantamentos
from .alertas import render_alertas
from .consulta_contratos import render_consulta_contratos
from .dashboard_executivo import render_dashboard_executivo
from .execucao_contratual import render_execucao_contratual
from .financeiro import render_financeiro
from .fornecedores import render_fornecedores
from .itens_planilhas import render_itens_planilhas
from .vigencia_prazos import render_vigencia_prazos

__all__ = [
	"render_adiantamentos",
	"render_alertas",
	"render_consulta_contratos",
	"render_dashboard_executivo",
	"render_execucao_contratual",
	"render_financeiro",
	"render_fornecedores",
	"render_itens_planilhas",
	"render_vigencia_prazos",
]
