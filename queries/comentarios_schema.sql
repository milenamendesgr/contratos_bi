CREATE TABLE IF NOT EXISTS contrato_comentario (
    id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
    id_comentario INTEGER NOT NULL,
    versao INTEGER NOT NULL CHECK (versao >= 1),
    versao_atual INTEGER NOT NULL DEFAULT 1 CHECK (versao_atual IN (0, 1)),
    filial TEXT NOT NULL CHECK (length(trim(filial)) > 0),
    contrato TEXT NOT NULL CHECK (length(trim(contrato)) > 0),
    revisao_contrato TEXT NOT NULL DEFAULT '',
    numero_medicao TEXT NOT NULL CHECK (length(trim(numero_medicao)) > 0),
    comentario TEXT NOT NULL CHECK (length(trim(comentario)) > 0),
    usuario_criacao TEXT NOT NULL CHECK (length(trim(usuario_criacao)) > 0),
    data_criacao TEXT NOT NULL CHECK (length(trim(data_criacao)) > 0),
    usuario_alteracao TEXT,
    data_alteracao TEXT,
    excluido INTEGER NOT NULL DEFAULT 0 CHECK (excluido IN (0, 1)),
    usuario_exclusao TEXT,
    data_exclusao TEXT,
    CONSTRAINT uk_contrato_comentario_versao UNIQUE (id_comentario, versao),
    CONSTRAINT ck_contrato_comentario_alteracao CHECK (
        (usuario_alteracao IS NULL AND data_alteracao IS NULL)
        OR
        (
            usuario_alteracao IS NOT NULL
            AND data_alteracao IS NOT NULL
            AND length(trim(usuario_alteracao)) > 0
            AND length(trim(data_alteracao)) > 0
        )
    ),
    CONSTRAINT ck_contrato_comentario_exclusao CHECK (
        (excluido = 0 AND usuario_exclusao IS NULL AND data_exclusao IS NULL)
        OR
        (
            excluido = 1
            AND usuario_exclusao IS NOT NULL
            AND data_exclusao IS NOT NULL
            AND length(trim(usuario_exclusao)) > 0
            AND length(trim(data_exclusao)) > 0
        )
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_contrato_comentario_atual
    ON contrato_comentario (id_comentario)
    WHERE versao_atual = 1;

CREATE INDEX IF NOT EXISTS ix_contrato_comentario_contrato
    ON contrato_comentario (
        filial,
        contrato,
        versao_atual,
        excluido,
        data_criacao,
        id_comentario
    );
