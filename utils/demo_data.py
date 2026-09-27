"""Dados sintéticos relacionados, sem leitura de arquivos ou acesso à rede."""

from datetime import date

import pandas as pd


def gerar_bases_demo(hoje: date | None = None) -> dict[str, pd.DataFrame]:
    """Gera a mesma carteira para uma data de referência; valores em reais.

    Identificadores DEMO e documentos não fiscais evitam associação a empresas.
    Os saldos são derivados das medições e os pagamentos do fluxo financeiro.
    """
    hoje = pd.Timestamp(hoje or date.today()).normalize()
    contratos, medicoes, detalhes, adiantamentos, fluxo, itens = [], [], [], [], [], []
    tipos = ["Serviços", "Fornecimento", "Manutenção", "Locação", "Consultoria"]
    status = ["05"] * 6 + ["06", "08", "02", "04", "09", "01"]
    for i in range(1, 49):
        situacao = status[(i - 1) % len(status)]
        inicio = hoje - pd.Timedelta(days=420 + i * 3)
        dias = [-45, 15, 55, 120, 240, 365][(i - 1) % 6]
        if situacao in {"08", "01"}:
            dias = -90
        fim = hoje + pd.Timedelta(days=dias)
        inicial = float(120000 + i * 17500)
        aditivo = inicial * (0.1 if i % 4 == 0 else 0)
        atual = inicial + aditivo
        fornecedor = (i - 1) % 12 + 1
        base = dict(
            FILIAL=f"D{(i - 1) % 4 + 1:03d}", CONTRATO=f"DEMO-{i:04d}",
            COD_FORNECEDOR=f"F{fornecedor:03d}", LOJA_FORNECEDOR="01",
            NOME_FORNECEDOR=f"Fornecedor Demonstração {fornecedor:02d}",
            CNPJ_FORNECEDOR=f"DEMO-{fornecedor:04d}",
            TIPO_CONTRATO=f"{(i - 1) % 5 + 1:02d}", DESC_TIPO_CONTRATO=tipos[(i - 1) % 5],
            SITUACAO=situacao, DATA_INICIO=inicio.strftime("%Y%m%d"),
            DATA_FIM=fim.strftime("%Y%m%d"), DATA_FINAL=fim.strftime("%Y%m%d"),
            DATA_ASSINATURA=inicio.strftime("%Y%m%d"), DATA_ULT_STATUS=hoje.strftime("%Y%m%d"),
            DESCRICAO=f"Contrato fictício de {tipos[(i - 1) % 5].lower()}",
            OBJETO_DO_CONTRATO="Prestação simulada para demonstração de análise de dados.",
            VALOR_INICIAL=inicial, VALOR_ATUAL=atual, VALOR_CONTRATO=atual,
            VALOR_ADITIVO=aditivo, VALOR_REAJUSTE=0.0, VALOR_REAJUSTADO=atual,
            PERCENTUAL_REAJUSTE=0.0, UNIDADE_VIGENCIA="Meses",
            CONDICAO_PAGAMENTO="030", DESCRICAO_CONDICAO_PAGAMENTO="30 dias",
        )
        n = 0 if situacao in {"02", "04", "01"} else (i % 6 + 1)
        percentual = 1.0 if situacao == "08" else [0.15, 0.35, 0.6, 0.85, 0.95][i % 5]
        executado = round(atual * percentual, 2) if n else 0.0
        total_centavos = round(executado * 100)
        for m in range(n):
            valor = (total_centavos // n + (m < total_centavos % n)) / 100
            data = min(hoje, fim) - pd.DateOffset(months=n - m)
            med = dict(base, REVISAO_CONTRATO="01", NUMERO_MEDICAO=f"{m + 1:04d}",
                       NUMERO_PLANILHA="001", COMPETENCIA=data.strftime("%Y%m"),
                       STATUS_MEDICAO="P" if m < n - 1 else "A",
                       DATA_INICIO=data.strftime("%Y%m%d"), DATA_FIM=data.strftime("%Y%m%d"),
                       DATA_ENCERRAMENTO=data.strftime("%Y%m%d"),
                       DATA_VENCIMENTO=(data + pd.Timedelta(days=30)).strftime("%Y%m%d"),
                       VALOR_PREVISTO=valor, VALOR_TOTAL_MEDICAO=valor, VALOR_LIQUIDO=valor,
                       SALDO_MEDICAO=0.0 if m < n - 1 else valor,
                       QTD_ITENS=2, QTD_PRODUTOS_DISTINTOS=2, QTD_SOLICITADA=20,
                       QTD_MEDIDA=20, TOTAL_ITENS=valor, TOTAL_LIQUIDO_ITENS=valor)
            medicoes.append(med)
            for k in range(2):
                centavos = round(valor * 100)
                parte = (centavos // 2 + (k < centavos % 2)) / 100
                detalhes.append(dict(FILIAL=base["FILIAL"], CONTRATO=base["CONTRATO"],
                    REVISAO_CONTRATO="01", NUMERO_MEDICAO=f"{m + 1:04d}", ITEM=f"{k + 1:03d}",
                    PRODUTO=f"DEMO-P{k + 1}", QTD_SOLICITADA_ITEM=10, QTD_MEDIDA_ITEM=10,
                    VALOR_TOTAL_ITEM=parte, VALOR_LIQUIDO_ITEM=parte,
                    VALOR_MULTA_ITEM=0.0, VALOR_BONIFICACAO_ITEM=0.0))
        base.update(SALDO_CONTRATO=atual - executado, VALOR_MEDIDO=executado,
                    VALOR_LIQUIDADO=executado, QTD_MEDICOES=n, QUANTIDADE_MEDIDA=n * 20,
                    SALDO_EXECUCAO=atual - executado, VALOR_MULTA=0.0)
        valor_adiantado = round(atual * 0.1, 2) if n and i % 3 == 0 else 0.0
        saldo_adiantado = round(valor_adiantado * (1 - percentual), 2)
        if valor_adiantado:
            adiantamentos.append(dict(base, NUMERO_ADIANTAMENTO=f"AD-DEMO-{i:04d}",
                DATA_ADIANTAMENTO=inicio.strftime("%Y%m%d"), VALOR_ADIANTAMENTO=valor_adiantado,
                SALDO_ADIANTAMENTO=saldo_adiantado, VALOR_ATUAL_CONTRATO=atual))
        # Duas parcelas por contrato: uma vencida e outra futura.
        pago = round(executado * 0.8, 2)
        for p, previsto in enumerate([executado, atual - executado]):
            vencimento = hoje + pd.Timedelta(days=-20 if p == 0 else 20 + i)
            fluxo.append(dict(base, COMPETENCIA=vencimento.strftime("%Y%m"),
                DATA_VENCIMENTO=vencimento.strftime("%Y%m%d"), VALOR_PREVISTO=previsto,
                VALOR_REALIZADO=pago if p == 0 else 0.0))
        base.update(VALOR_PREVISTO=atual, VALOR_REALIZADO=pago, QTD_PARCELAS=2,
                    PARCELAS_ATRASADAS=int(executado > pago), VALOR_ADIANTADO=valor_adiantado,
                    SALDO_ADIANTAMENTO=saldo_adiantado)
        base["TIPO_ALERTA"] = (
            "CONTRATO_VENCIDO" if dias < 0 and situacao == "05" else
            "CONTRATO_PARALISADO" if situacao == "06" else
            "PROXIMO_VENCIMENTO" if 0 <= dias <= 90 and situacao == "05" else
            "ALTO_CONSUMO" if n and percentual >= 0.9 and situacao == "05" else "SEM_ALERTA"
        )
        contratos.append(base)
        quantidade_contratada = n * 10 / percentual if n else 100
        for k in range(2):
            itens.append(dict(base, PLANILHA="001", TIPO_PLANILHA="01", DESC_TIPO_PLANILHA="Serviços simulados",
                ITEM=f"{k + 1:03d}", PRODUTO=f"DEMO-P{k + 1}", DESC_PRODUTO=f"Serviço fictício {k + 1}",
                UNIDADE="UN", SITUACAO_CONTRATO=situacao, QUANTIDADE_CONTRATADA=quantidade_contratada,
                VALOR_UNITARIO=atual / (2 * quantidade_contratada), VALOR_CONTRATADO=atual / 2,
                QUANTIDADE_SOLICITADA=n * 10, QUANTIDADE_MEDIDA=n * 10,
                QUANTIDADE_REALIZADA=n * 10, VALOR_MEDIDO=executado / 2,
                VALOR_LIQUIDADO=executado / 2, SALDO_QUANTIDADE=quantidade_contratada - n * 10,
                PERCENTUAL_EXECUCAO=executado / atual * 100, QTD_REGISTROS_MEDICAO=n))
    carteira = pd.DataFrame(contratos)
    return {
        "contratos": carteira, "execucao": carteira.copy(), "financeiro": carteira.copy(),
        "fornecedores": carteira.copy(), "alertas": carteira.copy(),
        "medicoes": pd.DataFrame(medicoes), "medicoes_itens": pd.DataFrame(detalhes),
        "adiantamentos": pd.DataFrame(adiantamentos), "fluxo": pd.DataFrame(fluxo),
        "itens": pd.DataFrame(itens),
        "validacoes": pd.DataFrame([dict(VALIDACAO="CONTRATOS_DEMO_UNICOS",
            VALOR_ORIGINAL=len(carteira), VALOR_TRATADO=carteira.CONTRATO.nunique(),
            DIFERENCA=len(carteira) - carteira.CONTRATO.nunique())]),
    }


def carregar_demo(nome: str) -> pd.DataFrame:
    return gerar_bases_demo()[nome]
