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
WHERE id_comentario = :id_comentario
ORDER BY versao ASC;
