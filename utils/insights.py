"""Reusable insight calculations for the contract BI dashboards.

This module only consumes already loaded DataFrames and returns simple Python
objects ready for presentation. It does not access databases, execute SQL,
render Streamlit components, or mutate the input DataFrames.
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd


Insight = dict[str, str]
Formatter = Callable[[Any], str]


def _empty_frame(df: pd.DataFrame | None) -> bool:
    return df is None or df.empty


def _number_series(df: pd.DataFrame, column: str) -> pd.Series:
    if _empty_frame(df) or column not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(0.0)


def _sum(df: pd.DataFrame, column: str) -> float:
    return float(_number_series(df, column).sum())


def _mean(df: pd.DataFrame, column: str) -> float:
    values = _number_series(df, column)
    return float(values.mean() or 0.0) if not values.empty else 0.0


def _count_contracts(df: pd.DataFrame) -> int:
    if _empty_frame(df):
        return 0
    if "CONTRATO" in df.columns:
        return int(df["CONTRATO"].nunique())
    return int(len(df))


def _format_default(value: Any) -> str:
    return str(value)


def get_total_contratos(df: pd.DataFrame) -> int:
    """Return the number of contracts in the DataFrame."""
    return _count_contracts(df)


def get_valor_total(df: pd.DataFrame, value_column: str = "VALOR_ATUAL") -> float:
    """Return the total contract value using the selected numeric column."""
    return _sum(df, value_column)


def get_valor_medio(df: pd.DataFrame, value_column: str = "VALOR_ATUAL") -> float:
    """Return the average contract value using the selected numeric column."""
    return _mean(df, value_column)


def get_maior_contrato(df: pd.DataFrame, value_column: str = "VALOR_ATUAL") -> dict[str, Any]:
    """Return the highest-value contract record as a simple dictionary."""
    return _top_record(df, value_column=value_column, ascending=False)


def get_menor_contrato(df: pd.DataFrame, value_column: str = "VALOR_ATUAL") -> dict[str, Any]:
    """Return the lowest-value contract record as a simple dictionary."""
    return _top_record(df, value_column=value_column, ascending=True)


def get_top_fornecedor(df: pd.DataFrame, value_column: str = "VALOR_CONTRATO", supplier_column: str = "FORNECEDOR") -> dict[str, Any]:
    """Return the supplier with the highest value and its portfolio percentage."""
    if _empty_frame(df) or supplier_column not in df.columns or value_column not in df.columns:
        return {"fornecedor": "", "valor": 0.0, "percentual": 0.0}

    values = df[[supplier_column, value_column]].copy()
    values[value_column] = pd.to_numeric(values[value_column], errors="coerce").fillna(0.0)
    grouped = values.groupby(supplier_column, dropna=False)[value_column].sum().sort_values(ascending=False)
    if grouped.empty:
        return {"fornecedor": "", "valor": 0.0, "percentual": 0.0}

    total = float(grouped.sum())
    fornecedor = str(grouped.index[0])
    valor = float(grouped.iloc[0])
    percentual = (valor / total * 100) if total else 0.0
    return {"fornecedor": fornecedor, "valor": valor, "percentual": float(percentual)}


def get_top_filial(df: pd.DataFrame, value_column: str = "VALOR_ATUAL", branch_column: str = "FILIAL_NOME") -> dict[str, Any]:
    """Return the branch with the highest total value."""
    top = get_top_fornecedor(df, value_column=value_column, supplier_column=branch_column)
    return {"filial": top["fornecedor"], "valor": top["valor"], "percentual": top["percentual"]}


def get_percentual_execucao(df: pd.DataFrame, percent_column: str = "PERCENTUAL_EXECUCAO") -> float:
    """Return the average execution percentage."""
    return _mean(df, percent_column)


def get_status_contratos(df: pd.DataFrame, status_column: str = "STATUS") -> dict[str, int]:
    """Return contract counts grouped by status."""
    if _empty_frame(df) or status_column not in df.columns:
        return {}
    return {str(key): int(value) for key, value in df[status_column].value_counts(dropna=False).to_dict().items()}


def get_contratos_vencidos(df: pd.DataFrame) -> dict[str, Any]:
    """Return expired contracts and their quantity."""
    if _empty_frame(df) or "DIAS_RESTANTES" not in df.columns:
        return {"quantidade": 0, "lista": []}
    result = df.loc[_number_series(df, "DIAS_RESTANTES") < 0].copy()
    return {"quantidade": int(len(result)), "lista": result.to_dict("records")}


def get_contratos_vencendo(df: pd.DataFrame, dias: int = 30) -> dict[str, Any]:
    """Return contracts expiring in the selected number of days."""
    if _empty_frame(df) or "DIAS_RESTANTES" not in df.columns:
        return {"quantidade": 0, "lista": [], "dias_restantes": []}
    remaining = _number_series(df, "DIAS_RESTANTES")
    result = df.loc[(remaining >= 0) & (remaining <= dias)].copy()
    return {
        "quantidade": int(len(result)),
        "lista": result.to_dict("records"),
        "dias_restantes": [int(value) for value in remaining.loc[result.index].tolist()],
    }


def get_menor_vigencia(df: pd.DataFrame) -> dict[str, Any]:
    """Return the contract with the shortest remaining term."""
    return _top_record(df, value_column="DIAS_RESTANTES", ascending=True)


def get_maior_vigencia(df: pd.DataFrame) -> dict[str, Any]:
    """Return the contract with the longest remaining term."""
    return _top_record(df, value_column="DIAS_RESTANTES", ascending=False)


def get_tempo_medio_restante(df: pd.DataFrame) -> float:
    """Return the average remaining term in days."""
    return _mean(df, "DIAS_RESTANTES")


def get_resumo_contrato(df: pd.DataFrame) -> dict[str, Any]:
    """Return a safe summary for the first contract in the DataFrame."""
    if _empty_frame(df):
        return {}
    return df.iloc[0].to_dict()


def get_percentual_consumo(df: pd.DataFrame, measured_column: str = "VALOR_MEDIDO", total_column: str = "VALOR_CONTRATADO") -> float:
    """Return consumed percentage based on measured and contracted values."""
    total = _sum(df, total_column)
    return float((_sum(df, measured_column) / total * 100) if total else 0.0)


def get_resumo_financeiro(df: pd.DataFrame) -> dict[str, float]:
    """Return financial totals from the provided DataFrame."""
    return {
        "valor_previsto": get_valor_previsto(df),
        "valor_realizado": get_valor_realizado(df),
        "saldo_financeiro": get_saldo_financeiro(df),
    }


def get_resumo_medicoes(df: pd.DataFrame) -> dict[str, Any]:
    """Return measurement totals from the provided DataFrame."""
    return {"quantidade": int(_sum(df, "QTD_MEDICOES")), "valor_medido": _sum(df, "VALOR_MEDIDO")}


def get_top_execucao(df: pd.DataFrame) -> dict[str, Any]:
    """Return the contract with the highest execution percentage."""
    return _top_record(df, value_column="PERCENTUAL_EXECUCAO", ascending=False)


def get_contratos_sem_medicao(df: pd.DataFrame) -> dict[str, Any]:
    """Return contracts with no registered measurements."""
    if _empty_frame(df) or "QTD_MEDICOES" not in df.columns:
        return {"quantidade": 0, "lista": []}
    result = df.loc[_number_series(df, "QTD_MEDICOES") == 0].copy()
    return {"quantidade": int(len(result)), "lista": result.to_dict("records")}


def get_media_execucao(df: pd.DataFrame) -> float:
    """Return the average execution percentage."""
    return get_percentual_execucao(df)


def get_maior_execucao(df: pd.DataFrame) -> dict[str, Any]:
    """Return the contract with the highest execution percentage."""
    return get_top_execucao(df)


def get_menor_execucao(df: pd.DataFrame) -> dict[str, Any]:
    """Return the contract with the lowest execution percentage."""
    return _top_record(df, value_column="PERCENTUAL_EXECUCAO", ascending=True)


def get_parcelas_vencidas(df: pd.DataFrame) -> int:
    """Return the number of overdue parcels."""
    return int(_sum(df, "PARCELAS_ATRASADAS"))


def get_proximo_vencimento(df: pd.DataFrame) -> Any:
    """Return the closest future due date."""
    if _empty_frame(df) or "DATA_VENCIMENTO" not in df.columns:
        return None
    hoje = pd.Timestamp.now().normalize()
    dates = pd.to_datetime(df["DATA_VENCIMENTO"], errors="coerce")
    future_dates = dates.loc[dates.ge(hoje)].dropna()
    return future_dates.min() if not future_dates.empty else None


def get_valor_previsto(df: pd.DataFrame) -> float:
    """Return the total expected financial value."""
    return _sum(df, "VALOR_PREVISTO")


def get_valor_realizado(df: pd.DataFrame) -> float:
    """Return the total realized financial value."""
    return _sum(df, "VALOR_REALIZADO")


def get_saldo_financeiro(df: pd.DataFrame) -> float:
    """Return expected minus realized value."""
    if _empty_frame(df):
        return 0.0
    if "SALDO_FINANCEIRO" in df.columns:
        return _sum(df, "SALDO_FINANCEIRO")
    return get_valor_previsto(df) - get_valor_realizado(df)


def get_fornecedor_maior_valor(df: pd.DataFrame) -> dict[str, Any]:
    """Return the supplier with the highest contracted value."""
    return get_top_fornecedor(df)


def get_fornecedor_maior_saldo(df: pd.DataFrame) -> dict[str, Any]:
    """Return the supplier with the highest balance."""
    return get_top_fornecedor(df, value_column="SALDO_CONTRATO")


def get_quantidade_contratos_fornecedor(df: pd.DataFrame, supplier_column: str = "FORNECEDOR") -> dict[str, int]:
    """Return contract quantities grouped by supplier."""
    if _empty_frame(df) or supplier_column not in df.columns:
        return {}
    return {str(key): int(value) for key, value in df.groupby(supplier_column, dropna=False).size().to_dict().items()}


def get_top5_fornecedores(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return the top five suppliers by contracted value."""
    if _empty_frame(df) or "FORNECEDOR" not in df.columns:
        return []
    ranking = (
        df.assign(VALOR_CONTRATO_NUM=_number_series(df, "VALOR_CONTRATO"))
        .groupby("FORNECEDOR", dropna=False)["VALOR_CONTRATO_NUM"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )
    return [{"fornecedor": str(key), "valor": float(value)} for key, value in ranking.items()]


def get_concentracao_fornecedores(df: pd.DataFrame) -> dict[str, Any]:
    """Return top-three supplier concentration over total contracted value."""
    top5 = get_top5_fornecedores(df)
    total = get_valor_total(df, "VALOR_CONTRATO")
    top3_value = sum(item["valor"] for item in top5[:3])
    percentual = (top3_value / total * 100) if total else 0.0
    return {"valor_top3": float(top3_value), "percentual_top3": float(percentual)}


def get_item_mais_caro(df: pd.DataFrame) -> dict[str, Any]:
    """Return the highest-value item."""
    return _top_record(df, value_column="VALOR_UNITARIO", ascending=False)


def get_item_mais_utilizado(df: pd.DataFrame) -> dict[str, Any]:
    """Return the item with the highest measured quantity."""
    return _top_record(df, value_column="QUANTIDADE_MEDIDA", ascending=False)


def get_itens_sem_medicao(df: pd.DataFrame) -> dict[str, Any]:
    """Return items without measured quantity."""
    if _empty_frame(df) or "QUANTIDADE_MEDIDA" not in df.columns:
        return {"quantidade": 0, "lista": []}
    result = df.loc[_number_series(df, "QUANTIDADE_MEDIDA") == 0].copy()
    return {"quantidade": int(len(result)), "lista": result.to_dict("records")}


def get_maior_planilha(df: pd.DataFrame) -> dict[str, Any]:
    """Return the highest-value spreadsheet or contract item group."""
    return _top_record(df, value_column="VALOR_CONTRATADO", ascending=False)


def get_percentual_consumo_itens(df: pd.DataFrame) -> float:
    """Return consumed item percentage based on measured and contracted values."""
    return get_percentual_consumo(df)


def get_alertas_criticos(df: pd.DataFrame) -> dict[str, Any]:
    """Return critical alerts from the alert DataFrame."""
    return _filter_alerts(df, "CRIT")


def get_alertas_vencimento(df: pd.DataFrame) -> dict[str, Any]:
    """Return due-date alerts from the alert DataFrame."""
    return _filter_alerts(df, "VENC")


def get_alertas_execucao(df: pd.DataFrame) -> dict[str, Any]:
    """Return execution alerts from the alert DataFrame."""
    return _filter_alerts(df, "EXEC")


def get_alertas_financeiros(df: pd.DataFrame) -> dict[str, Any]:
    """Return financial alerts from the alert DataFrame."""
    return _filter_alerts(df, "FINANC")


def get_dashboard_executivo_insights(
    df: pd.DataFrame,
    top_fornecedor: pd.DataFrame | None = None,
    money_formatter: Formatter = _format_default,
    percent_formatter: Formatter = _format_default,
) -> list[Insight]:
    """Return the executive dashboard insight payloads."""
    total_contratos = 0 if _empty_frame(df) else int(len(df))
    status = df["STATUS"].astype(str).str.upper() if not _empty_frame(df) and "STATUS" in df.columns else pd.Series(dtype=str)
    contratos_ativos = int(status.str.contains("ATIV|VIGENTE|ABERT", na=False).sum())
    percentual_medio = get_percentual_execucao(df)
    saldo = _sum(df, "SALDO_CONTRATUAL")

    insights: list[Insight] = []
    if total_contratos:
        insights.append({"title": "Carteira", "text": f"A visao filtrada possui {total_contratos} contrato(s), com {contratos_ativos} ativo(s).", "severity": "positive"})
    if percentual_medio >= 90:
        insights.append({"title": "Execucao", "text": f"A execucao media da carteira filtrada esta em {percent_formatter(percentual_medio)}.", "severity": "warning"})
    if saldo > 0:
        insights.append({"title": "Saldo", "text": f"Ainda ha {money_formatter(saldo)} de saldo contratual na carteira filtrada.", "severity": "neutral"})
    if top_fornecedor is not None and not top_fornecedor.empty:
        fornecedor = str(top_fornecedor.iloc[0].get("FORNECEDOR", "") or "").strip()
        valor = top_fornecedor.iloc[0].get("VALOR_CONTRATADO", 0)
        if fornecedor:
            insights.append({"title": "Fornecedor", "text": f"{fornecedor} concentra o maior valor contratado: {money_formatter(valor)}.", "severity": "neutral"})
    return insights


def get_execucao_insights(
    df: pd.DataFrame,
    money_formatter: Formatter = _format_default,
    percent_formatter: Formatter = _format_default,
) -> list[Insight]:
    """Return execution dashboard insight payloads."""
    percentual_medio = get_media_execucao(df)
    saldo = _sum(df, "SALDO_EXECUCAO")
    multas = _sum(df, "VALOR_MULTA")
    sem_medicao = get_contratos_sem_medicao(df)["quantidade"]

    insights: list[Insight] = []
    if percentual_medio >= 90:
        insights.append({"title": "Execucao", "text": f"A execucao media esta em {percent_formatter(percentual_medio)}, indicando contratos proximos do limite.", "severity": "warning"})
    if saldo > 0:
        insights.append({"title": "Saldo", "text": f"O saldo total de execucao e {money_formatter(saldo)}.", "severity": "neutral"})
    if multas > 0:
        insights.append({"title": "Multas", "text": f"Foram identificadas multas no total de {money_formatter(multas)}.", "severity": "critical"})
    if sem_medicao:
        insights.append({"title": "Medicoes", "text": f"Existem {sem_medicao} contrato(s) sem medicao registrada na visao filtrada.", "severity": "warning"})
    return insights


def get_financeiro_insights(
    df: pd.DataFrame,
    money_formatter: Formatter = _format_default,
    percent_formatter: Formatter = _format_default,
) -> list[Insight]:
    """Return financial dashboard insight payloads."""
    parcelas_atrasadas = get_parcelas_vencidas(df)
    saldo = get_saldo_financeiro(df)
    percentual_realizado = get_percentual_consumo(df, measured_column="VALOR_REALIZADO", total_column="VALOR_PREVISTO")
    valor_adiantado = _sum(df, "VALOR_ADIANTADO")

    insights: list[Insight] = []
    if parcelas_atrasadas:
        insights.append({"title": "Atrasos", "text": f"Existem {parcelas_atrasadas} parcela(s) atrasada(s) na visao filtrada.", "severity": "critical"})
    if saldo > 0:
        insights.append({"title": "Saldo", "text": f"O saldo financeiro em aberto e {money_formatter(saldo)}.", "severity": "warning"})
    if percentual_realizado >= 90:
        insights.append({"title": "Realizacao", "text": f"O percentual realizado chegou a {percent_formatter(percentual_realizado)} do previsto.", "severity": "warning"})
    if valor_adiantado > 0:
        insights.append({"title": "Adiantamentos", "text": f"Foram identificados {money_formatter(valor_adiantado)} em adiantamentos.", "severity": "neutral"})
    return insights


def get_fluxo_financeiro_insights(
    df: pd.DataFrame,
    money_formatter: Formatter = _format_default,
    date_formatter: Formatter = _format_default,
) -> list[Insight]:
    """Return financial flow insight payloads."""
    hoje = pd.Timestamp.now().normalize()
    datas = pd.to_datetime(df["DATA_VENCIMENTO"], errors="coerce") if not _empty_frame(df) and "DATA_VENCIMENTO" in df.columns else pd.Series(dtype="datetime64[ns]")
    proximos_30 = datas.between(hoje, hoje + pd.Timedelta(days=30), inclusive="both") if not datas.empty else pd.Series(dtype=bool)
    valor_previsto_30_dias = float(_number_series(df, "VALOR_PREVISTO").loc[proximos_30].sum()) if not proximos_30.empty else 0.0
    saldo = get_saldo_financeiro(df)
    proximo_vencimento = get_proximo_vencimento(df)

    insights: list[Insight] = []
    if valor_previsto_30_dias > 0:
        insights.append({"title": "Proximos 30 dias", "text": f"Ha {money_formatter(valor_previsto_30_dias)} previsto para vencer nos proximos 30 dias.", "severity": "warning"})
    if saldo > 0:
        insights.append({"title": "Saldo", "text": f"O fluxo filtrado possui {money_formatter(saldo)} de saldo financeiro.", "severity": "neutral"})
    if proximo_vencimento is not None:
        insights.append({"title": "Vencimento", "text": f"O proximo vencimento identificado e {date_formatter(proximo_vencimento)}.", "severity": "warning"})
    return insights


def get_fornecedores_insights(
    df: pd.DataFrame,
    concentracao: str,
    descricao_concentracao: str,
    inconsistencias_fornecedor: int,
    ranking: pd.DataFrame | None = None,
    percent_formatter: Formatter = _format_default,
    quantity_formatter: Formatter = _format_default,
) -> list[Insight]:
    """Return supplier dashboard insight payloads."""
    insights: list[Insight] = [
        {"title": "Concentracao", "text": f"{concentracao}: {descricao_concentracao}", "severity": "warning" if "alta" in str(concentracao).lower() else "neutral"},
    ]
    if ranking is not None and not ranking.empty:
        fornecedor = str(ranking.iloc[0].get("FORNECEDOR", "") or "").strip()
        participacao = ranking.iloc[0].get("PARTICIPACAO", 0)
        if fornecedor:
            insights.append({"title": "Fornecedor", "text": f"{fornecedor} possui a maior participacao da carteira: {percent_formatter(participacao)}.", "severity": "neutral"})
    else:
        top = get_top_fornecedor(df)
        if top["fornecedor"]:
            insights.append({"title": "Fornecedor", "text": f"{top['fornecedor']} possui a maior participacao da carteira: {percent_formatter(top['percentual'])}.", "severity": "neutral"})
    if inconsistencias_fornecedor:
        insights.append({"title": "Cadastro", "text": f"Existem {quantity_formatter(inconsistencias_fornecedor)} inconsistência(s) de relacionamento CN9/CNC/SA2.", "severity": "critical"})
    return insights


def get_medicoes_insights(
    df: pd.DataFrame,
    indicadores: dict[str, Any] | None = None,
    money_formatter: Formatter = _format_default,
    quantity_formatter: Formatter = _format_default,
    percent_formatter: Formatter = _format_default,
) -> list[Insight]:
    """Return measurement dashboard insight payloads."""
    if _empty_frame(df):
        return []

    indicadores = indicadores or {}
    insights: list[Insight] = []

    top_fornecedor = get_top_fornecedor(df, value_column="VALOR_TOTAL_MEDICAO", supplier_column="FORNECEDOR")
    if top_fornecedor["fornecedor"]:
        insights.append(
            {
                "title": "Fornecedor com maior valor medido",
                "text": f"{top_fornecedor['fornecedor']} concentra {money_formatter(top_fornecedor['valor'])} em medicoes ({percent_formatter(top_fornecedor['percentual'])} do total).",
                "severity": "positive",
            }
        )

    top_fornecedor_qtd = (
        df.groupby("FORNECEDOR", dropna=False)["MEDICAO_CHAVE"]
        .nunique()
        .sort_values(ascending=False)
    )
    if not top_fornecedor_qtd.empty and top_fornecedor_qtd.iloc[0] > 0:
        insights.append(
            {
                "title": "Fornecedor com maior quantidade de medicoes",
                "text": f"{top_fornecedor_qtd.index[0]} possui {quantity_formatter(int(top_fornecedor_qtd.iloc[0]))} medicoes registradas.",
                "severity": "neutral",
            }
        )

    top_contrato_qtd = (
        df.groupby(["CONTRATO_CHAVE", "CONTRATO"], dropna=False)["MEDICAO_CHAVE"]
        .nunique()
        .sort_values(ascending=False)
    )
    if not top_contrato_qtd.empty and top_contrato_qtd.iloc[0] > 0:
        contrato = top_contrato_qtd.index[0][1]
        insights.append(
            {
                "title": "Contrato com maior quantidade de medicoes",
                "text": f"Contrato {contrato} possui {quantity_formatter(int(top_contrato_qtd.iloc[0]))} medicoes.",
                "severity": "neutral",
            }
        )

    competencia_total = (
        df.groupby("COMPETENCIA_LABEL", dropna=False)["VALOR_TOTAL_MEDICAO"]
        .sum()
        .sort_values(ascending=False)
    )
    if not competencia_total.empty and competencia_total.iloc[0] > 0:
        insights.append(
            {
                "title": "Competencia com maior volume financeiro",
                "text": f"{competencia_total.index[0]} registrou o maior volume: {money_formatter(float(competencia_total.iloc[0]))}.",
                "severity": "positive",
            }
        )
        menor = competencia_total.sort_values(ascending=True)
        if not menor.empty and menor.iloc[0] >= 0:
            insights.append(
                {
                    "title": "Competencia com menor volume financeiro",
                    "text": f"{menor.index[0]} registrou o menor volume: {money_formatter(float(menor.iloc[0]))}.",
                    "severity": "neutral",
                }
            )

    maior_medicao = _top_record(df, value_column="VALOR_TOTAL_MEDICAO", ascending=False)
    if maior_medicao and float(maior_medicao.get("VALOR_TOTAL_MEDICAO", 0) or 0) > 0:
        insights.append(
            {
                "title": "Maior valor de uma unica medicao",
                "text": f"Medicao {maior_medicao.get('NUMERO_MEDICAO', '')} do contrato {maior_medicao.get('CONTRATO', '')} com {money_formatter(float(maior_medicao.get('VALOR_TOTAL_MEDICAO', 0)))}.",
                "severity": "positive",
            }
        )

    maior_liquido = _top_record(df, value_column="VALOR_LIQUIDO", ascending=False)
    if maior_liquido and float(maior_liquido.get("VALOR_LIQUIDO", 0) or 0) > 0:
        insights.append(
            {
                "title": "Maior valor liquido",
                "text": f"Medicao {maior_liquido.get('NUMERO_MEDICAO', '')} do contrato {maior_liquido.get('CONTRATO', '')} com {money_formatter(float(maior_liquido.get('VALOR_LIQUIDO', 0)))} de liquido.",
                "severity": "positive",
            }
        )

    desconto_total = float(_sum(df, "VALOR_ADIANTAMENTO") + _sum(df, "VALOR_CAUCAO"))
    if desconto_total > 0:
        insights.append(
            {
                "title": "Maior desconto aplicado",
                "text": f"Adiantamentos e caucao somam {money_formatter(desconto_total)} em descontos aplicados.",
                "severity": "warning",
            }
        )

    multas = _sum(df, "VALOR_MULTAS")
    if multas > 0:
        maior_multa = _top_record(df, value_column="VALOR_MULTAS", ascending=False)
        insights.append(
            {
                "title": "Maior multa aplicada",
                "text": f"Foram aplicadas {money_formatter(multas)} em multas. Maior medicao: {money_formatter(float(maior_multa.get('VALOR_MULTAS', 0) or 0))}.",
                "severity": "critical",
            }
        )

    bonificacoes = _sum(df, "VALOR_BONIFICACOES")
    if bonificacoes > 0:
        maior_bonificacao = _top_record(df, value_column="VALOR_BONIFICACOES", ascending=False)
        insights.append(
            {
                "title": "Maior bonificacao",
                "text": f"Bonificacoes totais de {money_formatter(bonificacoes)}. Maior medicao: {money_formatter(float(maior_bonificacao.get('VALOR_BONIFICACOES', 0) or 0))}.",
                "severity": "positive",
            }
        )

    media_itens = float(df["QTD_ITENS"].mean() or 0.0)
    media_valor = float(df["VALOR_TOTAL_MEDICAO"].mean() or 0.0)
    insights.append(
        {
            "title": "Medias",
            "text": f"Quantidade media de itens por medicao: {quantity_formatter(media_itens)}. Valor medio das medicoes: {money_formatter(media_valor)}.",
            "severity": "neutral",
        }
    )

    total_contratos_carteira = (
        indicadores.get("qtd_contratos_com_medicao", 0)
        + indicadores.get("qtd_contratos_sem_medicao", 0)
    )
    if total_contratos_carteira > 0:
        pct_sem = indicadores.get("qtd_contratos_sem_medicao", 0) / total_contratos_carteira * 100
        pct_uma = indicadores.get("qtd_contratos_uma_medicao", 0) / total_contratos_carteira * 100
        insights.append(
            {
                "title": "Distribuicao de contratos",
                "text": f"{percent_formatter(pct_sem)} sem medicao e {percent_formatter(pct_uma)} com apenas uma medicao.",
                "severity": "warning" if pct_sem > 20 else "neutral",
            }
        )

    return insights


def get_itens_planilhas_insights(
    df: pd.DataFrame,
    money_formatter: Formatter = _format_default,
    quantity_formatter: Formatter = _format_default,
    percent_formatter: Formatter = _format_default,
) -> list[Insight]:
    """Return item and spreadsheet insight payloads."""
    if _empty_frame(df):
        return []

    result = df.copy()
    for column in ["FILIAL", "CONTRATO", "PLANILHA", "ITEM", "FORNECEDOR"]:
        if column not in result.columns:
            result[column] = ""
        result[column] = result[column].fillna("").astype(str).str.strip()

    if "TEM_CONTRATO" not in result.columns:
        result["TEM_CONTRATO"] = result["FILIAL"].ne("") & result["CONTRATO"].ne("")
    if "TEM_PLANILHA" not in result.columns:
        result["TEM_PLANILHA"] = result["TEM_CONTRATO"] & result["PLANILHA"].ne("")
    if "TEM_ITEM" not in result.columns:
        result["TEM_ITEM"] = result["TEM_PLANILHA"] & result["ITEM"].ne("")

    contratos = result[result["TEM_CONTRATO"]][["FILIAL", "CONTRATO"]].drop_duplicates()
    planilhas = result[result["TEM_PLANILHA"]][["FILIAL", "CONTRATO", "PLANILHA"]].drop_duplicates()
    itens = result[result["TEM_ITEM"]].copy()

    total_contratos = int(len(contratos))
    total_planilhas = int(len(planilhas))
    total_itens = int(len(itens))

    planilhas_por_contrato = (
        result[result["TEM_CONTRATO"]]
        .groupby(["FILIAL", "CONTRATO"], dropna=False)["TEM_PLANILHA"]
        .sum()
        .reset_index(name="QTD_PLANILHAS")
    )
    contratos_sem_planilha = int((planilhas_por_contrato["QTD_PLANILHAS"] == 0).sum()) if not planilhas_por_contrato.empty else 0

    itens_por_planilha = (
        result[result["TEM_PLANILHA"]]
        .groupby(["FILIAL", "CONTRATO", "PLANILHA"], dropna=False)["TEM_ITEM"]
        .sum()
        .reset_index(name="QTD_ITENS")
    )
    planilhas_sem_itens = itens_por_planilha[itens_por_planilha["QTD_ITENS"] == 0] if not itens_por_planilha.empty else pd.DataFrame()
    qtd_planilhas_sem_itens = int(len(planilhas_sem_itens))
    contratos_incompletos = int(planilhas_sem_itens[["FILIAL", "CONTRATO"]].drop_duplicates().shape[0]) if not planilhas_sem_itens.empty else 0

    pct_sem_planilha = (contratos_sem_planilha / total_contratos * 100) if total_contratos else 0.0
    pct_incompletos = (contratos_incompletos / total_contratos * 100) if total_contratos else 0.0
    media_itens_contrato = (total_itens / total_contratos) if total_contratos else 0.0
    media_planilhas_contrato = (total_planilhas / total_contratos) if total_contratos else 0.0
    media_itens_planilha = (total_itens / total_planilhas) if total_planilhas else 0.0

    top_fornecedor_itens = (
        itens.assign(FORNECEDOR=lambda data: data["FORNECEDOR"].replace("", "Nao informado"))
        .groupby("FORNECEDOR", dropna=False)
        .size()
        .sort_values(ascending=False)
    ) if not itens.empty else pd.Series(dtype=int)
    top_contrato_planilhas = planilhas_por_contrato.sort_values("QTD_PLANILHAS", ascending=False).head(1)
    itens_por_contrato = (
        itens.groupby(["FILIAL", "CONTRATO"], dropna=False)
        .size()
        .reset_index(name="QTD_ITENS")
        .sort_values("QTD_ITENS", ascending=False)
    ) if not itens.empty else pd.DataFrame()
    saldo = _sum(itens, "VALOR_CONTRATADO") - _sum(itens, "VALOR_MEDIDO")

    insights: list[Insight] = []
    if total_contratos:
        insights.append({"title": "Contratos sem planilha", "text": f"{percent_formatter(pct_sem_planilha)} dos contratos filtrados nao possuem planilha cadastrada.", "severity": "warning" if contratos_sem_planilha else "positive"})
    if total_contratos:
        insights.append({"title": "Planilhas incompletas", "text": f"{percent_formatter(pct_incompletos)} dos contratos filtrados possuem ao menos uma planilha sem item.", "severity": "warning" if contratos_incompletos else "positive"})
    if not top_fornecedor_itens.empty:
        insights.append({"title": "Fornecedor", "text": f"{top_fornecedor_itens.index[0]} concentra a maior quantidade de itens cadastrados: {quantity_formatter(int(top_fornecedor_itens.iloc[0]))}.", "severity": "neutral"})
    if not top_contrato_planilhas.empty:
        row = top_contrato_planilhas.iloc[0]
        insights.append({"title": "Maior numero de planilhas", "text": f"Contrato {row['FILIAL']} / {row['CONTRATO']} possui {quantity_formatter(int(row['QTD_PLANILHAS']))} planilha(s).", "severity": "neutral"})
    if not itens_por_contrato.empty:
        row = itens_por_contrato.iloc[0]
        insights.append({"title": "Maior numero de itens", "text": f"Contrato {row['FILIAL']} / {row['CONTRATO']} possui {quantity_formatter(int(row['QTD_ITENS']))} item(ns).", "severity": "neutral"})
    if total_contratos:
        insights.append({"title": "Medias", "text": f"Medias filtradas: {quantity_formatter(media_itens_contrato)} itens por contrato, {quantity_formatter(media_planilhas_contrato)} planilhas por contrato e {quantity_formatter(media_itens_planilha)} itens por planilha.", "severity": "neutral"})
    if saldo > 0:
        insights.append({"title": "Saldo", "text": f"O saldo contratado dos itens filtrados e {money_formatter(saldo)}.", "severity": "neutral"})
    return insights


def get_alertas_insights(
    df: pd.DataFrame,
    total_alertas: int,
    consumo_medio: float,
    percent_formatter: Formatter = _format_default,
    quantity_formatter: Formatter = _format_default,
) -> list[Insight]:
    """Return alert dashboard insight payloads."""
    criticos = int((df["NIVEL_RISCO"] == "Critico").sum()) if not _empty_frame(df) and "NIVEL_RISCO" in df.columns else 0
    atencao = int((df["NIVEL_RISCO"] == "Atencao").sum()) if not _empty_frame(df) and "NIVEL_RISCO" in df.columns else 0

    insights: list[Insight] = []
    if criticos:
        insights.append({"title": "Critico", "text": f"Existem {quantity_formatter(criticos)} contrato(s) em nivel critico nos filtros atuais.", "severity": "critical"})
    if atencao:
        insights.append({"title": "Atencao", "text": f"Existem {quantity_formatter(atencao)} contrato(s) em atencao para acompanhamento.", "severity": "warning"})
    if total_alertas:
        insights.append({"title": "Alertas", "text": f"A carteira monitorada possui {quantity_formatter(total_alertas)} contrato(s) com alerta ativo.", "severity": "warning"})
    if consumo_medio >= 90:
        insights.append({"title": "Consumo", "text": f"O consumo medio dos exibidos esta em {percent_formatter(consumo_medio)}.", "severity": "critical"})
    return insights


def get_consulta_contrato_insights(
    detalhe: pd.Series | dict[str, Any],
    medicoes_contrato: pd.DataFrame,
    financeiro_contrato: pd.DataFrame,
    percent_formatter: Formatter = _format_default,
) -> list[Insight]:
    """Return detail-page insight payloads for a selected contract."""
    percentual_execucao = float(_mapping_get(detalhe, "PERCENTUAL_EXECUCAO", 0) or 0)
    dias_restantes = _mapping_get(detalhe, "DIAS_RESTANTES", None)
    situacao_contrato = str(
        _mapping_get(detalhe, "STATUS", _mapping_get(detalhe, "STATUS_CONTRATO", _mapping_get(detalhe, "SITUACAO", ""))) or ""
    ).strip().upper()
    contrato_encerrado = situacao_contrato in {"CANCELADO", "FINALIZADO", "01", "08"}
    try:
        dias_restantes_num = float(dias_restantes)
    except (TypeError, ValueError):
        dias_restantes_num = None

    insights: list[Insight] = []
    if percentual_execucao >= 90:
        insights.append({"title": "Execucao", "text": f"Este contrato ja consumiu {percent_formatter(percentual_execucao)} do valor acompanhado.", "severity": "warning"})
    if dias_restantes_num is not None and pd.notna(dias_restantes_num):
        if dias_restantes_num < 0 and not contrato_encerrado:
            insights.append({"title": "Vencimento", "text": "Este contrato esta com vencimento ultrapassado.", "severity": "critical"})
        elif dias_restantes_num <= 30 and not contrato_encerrado:
            insights.append({"title": "Vencimento", "text": f"Este contrato vence em {int(dias_restantes_num)} dia(s).", "severity": "warning"})
    if medicoes_contrato.empty:
        insights.append({"title": "Medicoes", "text": "Nao ha medicoes relacionadas a este contrato no contexto carregado.", "severity": "warning"})
    if financeiro_contrato.empty:
        insights.append({"title": "Financeiro", "text": "Nao ha parcelas financeiras relacionadas a este contrato no contexto carregado.", "severity": "neutral"})
    return insights


def get_indicadores_insights(total: int, ativos: int, vencidos: int, vencendo_30: int, pct_ativos: str, pct_venc: str) -> list[Insight]:
    """Return general indicators insight payloads."""
    insights: list[Insight] = []
    if vencidos:
        insights.append({"title": "Vencidos", "text": f"Existem {vencidos} contrato(s) vencido(s), representando {pct_venc}.", "severity": "critical"})
    if vencendo_30:
        insights.append({"title": "Proximidade", "text": f"{vencendo_30} contrato(s) vencem em ate 30 dias.", "severity": "warning"})
    if total:
        insights.append({"title": "Ativos", "text": f"{ativos} contrato(s) estao ativos, ou {pct_ativos}.", "severity": "positive"})
    return insights


def get_lista_contratos_insights(df: pd.DataFrame, total_filt: int, valor_total: float, vencidos: int, money_formatter: Formatter = _format_default) -> list[Insight]:
    """Return contract-list insight payloads."""
    insights: list[Insight] = []
    if vencidos:
        insights.append({"title": "Vencidos", "text": f"Existem {vencidos} contrato(s) vencido(s) nos filtros atuais.", "severity": "critical"})
    if "ALERTA_VENCIMENTO" in df.columns:
        vencendo_30 = int((df["ALERTA_VENCIMENTO"] == "Vence em 30d").sum())
        if vencendo_30:
            insights.append({"title": "Vencimento", "text": f"{vencendo_30} contrato(s) vencem nos proximos 30 dias.", "severity": "warning"})
    if total_filt:
        insights.append({"title": "Carteira", "text": f"A lista filtrada representa {money_formatter(valor_total)} em valor total.", "severity": "neutral"})
    return insights


def get_vencimentos_insights(df: pd.DataFrame) -> list[Insight]:
    """Return due-date dashboard insight payloads."""
    if _empty_frame(df) or "ALERTA_VENCIMENTO" not in df.columns:
        return []

    vencidos = int((df["ALERTA_VENCIMENTO"] == "Vencido").sum())
    vence_30 = int((df["ALERTA_VENCIMENTO"] == "Vence em 30d").sum())
    vence_90 = int(df["ALERTA_VENCIMENTO"].isin(["Vence em 60d", "Vence em 90d"]).sum())
    insights: list[Insight] = []
    if vencidos:
        insights.append({"title": "Vencidos", "text": f"Existem {vencidos} contrato(s) vencido(s) que exigem acao imediata.", "severity": "critical"})
    if vence_30:
        insights.append({"title": "30 dias", "text": f"{vence_30} contrato(s) vencem nos proximos 30 dias.", "severity": "warning"})
    if vence_90:
        insights.append({"title": "31 a 90 dias", "text": f"{vence_90} contrato(s) entram na janela de acompanhamento de 31 a 90 dias.", "severity": "warning"})
    return insights


def _mapping_get(values: pd.Series | dict[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(values, pd.Series):
        return values.get(key, default)
    return values.get(key, default)


def _top_record(df: pd.DataFrame, value_column: str, ascending: bool) -> dict[str, Any]:
    if _empty_frame(df) or value_column not in df.columns:
        return {}
    result = df.copy()
    result[value_column] = pd.to_numeric(result[value_column], errors="coerce").fillna(0.0)
    if result.empty:
        return {}
    return result.sort_values(value_column, ascending=ascending).iloc[0].to_dict()


def _filter_alerts(df: pd.DataFrame, token: str) -> dict[str, Any]:
    if _empty_frame(df):
        return {"quantidade": 0, "lista": []}
    columns = [column for column in ["ALERTA", "TIPO_ALERTA", "CATEGORIA", "SEVERIDADE"] if column in df.columns]
    if not columns:
        return {"quantidade": 0, "lista": []}
    mask = pd.Series(False, index=df.index)
    for column in columns:
        mask = mask | df[column].astype(str).str.upper().str.contains(token, na=False)
    result = df.loc[mask].copy()
    return {"quantidade": int(len(result)), "lista": result.to_dict("records")}