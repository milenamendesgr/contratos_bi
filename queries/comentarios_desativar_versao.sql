UPDATE contrato_comentario
SET versao_atual = 0
WHERE id_comentario = :id_comentario
  AND versao = :versao
  AND versao_atual = 1;
