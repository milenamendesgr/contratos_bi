SELECT
    id_registro,
    id_comentario,
    versao,
    versao_atual,
    filial,
    contrato,
    revisao_contrato,
    numero_medicao,
    comentario,
    usuario_criacao,
    data_criacao,
    usuario_alteracao,
    data_alteracao,
    excluido,
    usuario_exclusao,
    data_exclusao
FROM contrato_comentario
WHERE filial = :filial
  AND contrato = :contrato
  AND revisao_contrato = :revisao_contrato
  AND numero_medicao = :numero_medicao
  AND versao_atual = 1
  AND (:incluir_excluidos = 1 OR excluido = 0)
ORDER BY data_criacao ASC, id_comentario ASC;
