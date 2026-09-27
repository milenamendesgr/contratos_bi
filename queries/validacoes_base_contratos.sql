SELECT
    'CONTRATOS_CN9010_X_BASE' AS VALIDACAO,
    (
        SELECT COUNT(*)
        FROM CN9010 CN9
        WHERE CN9.D_E_L_E_T_ = ' '
    ) AS VALOR_ORIGINAL,
    (
        SELECT COUNT(*)
        FROM CN9010 CN9
        WHERE CN9.D_E_L_E_T_ = ' '
        AND NOT EXISTS (
            SELECT 1
            FROM CN9010 CN9B
            WHERE CN9B.CN9_NUMERO = CN9.CN9_NUMERO
            AND CN9B.CN9_FILIAL = CN9.CN9_FILIAL
            AND CN9B.D_E_L_E_T_ = ' '
            AND (
        NVL(CN9B.CN9_DTULST, ' ') > NVL(CN9.CN9_DTULST, ' ')
        OR (
            NVL(CN9B.CN9_DTULST, ' ') = NVL(CN9.CN9_DTULST, ' ')
            AND CN9B.R_E_C_N_O_ > CN9.R_E_C_N_O_
        )
    )
        )
    ) AS VALOR_TRATADO,
    (
        SELECT COUNT(*)
        FROM CN9010 CN9
        WHERE CN9.D_E_L_E_T_ = ' '
    ) - (
        SELECT COUNT(*)
        FROM CN9010 CN9
        WHERE CN9.D_E_L_E_T_ = ' '
        AND NOT EXISTS (
            SELECT 1
            FROM CN9010 CN9B
            WHERE CN9B.CN9_NUMERO = CN9.CN9_NUMERO
            AND CN9B.CN9_FILIAL = CN9.CN9_FILIAL
            AND CN9B.D_E_L_E_T_ = ' '
            AND (
        NVL(CN9B.CN9_DTULST, ' ') > NVL(CN9.CN9_DTULST, ' ')
        OR (
            NVL(CN9B.CN9_DTULST, ' ') = NVL(CN9.CN9_DTULST, ' ')
            AND CN9B.R_E_C_N_O_ > CN9.R_E_C_N_O_
        )
    )
        )
    ) AS DIFERENCA
FROM DUAL

UNION ALL

SELECT
    'VALOR_TOTAL_CN9010_X_BASE' AS VALIDACAO,
    (
        SELECT NVL(SUM(CN9.CN9_VLATU), 0)
        FROM CN9010 CN9
        WHERE CN9.D_E_L_E_T_ = ' '
    ) AS VALOR_ORIGINAL,
    (
        SELECT NVL(SUM(CN9.CN9_VLATU), 0)
        FROM CN9010 CN9
        WHERE CN9.D_E_L_E_T_ = ' '
        AND NOT EXISTS (
            SELECT 1
            FROM CN9010 CN9B
            WHERE CN9B.CN9_NUMERO = CN9.CN9_NUMERO
            AND CN9B.CN9_FILIAL = CN9.CN9_FILIAL
            AND CN9B.D_E_L_E_T_ = ' '
            AND (
        NVL(CN9B.CN9_DTULST, ' ') > NVL(CN9.CN9_DTULST, ' ')
        OR (
            NVL(CN9B.CN9_DTULST, ' ') = NVL(CN9.CN9_DTULST, ' ')
            AND CN9B.R_E_C_N_O_ > CN9.R_E_C_N_O_
        )
    )
        )
    ) AS VALOR_TRATADO,
    (
        SELECT NVL(SUM(CN9.CN9_VLATU), 0)
        FROM CN9010 CN9
        WHERE CN9.D_E_L_E_T_ = ' '
    ) - (
        SELECT NVL(SUM(CN9.CN9_VLATU), 0)
        FROM CN9010 CN9
        WHERE CN9.D_E_L_E_T_ = ' '
        AND NOT EXISTS (
            SELECT 1
            FROM CN9010 CN9B
            WHERE CN9B.CN9_NUMERO = CN9.CN9_NUMERO
            AND CN9B.CN9_FILIAL = CN9.CN9_FILIAL
            AND CN9B.D_E_L_E_T_ = ' '
            AND (
        NVL(CN9B.CN9_DTULST, ' ') > NVL(CN9.CN9_DTULST, ' ')
        OR (
            NVL(CN9B.CN9_DTULST, ' ') = NVL(CN9.CN9_DTULST, ' ')
            AND CN9B.R_E_C_N_O_ > CN9.R_E_C_N_O_
        )
    )
        )
    ) AS DIFERENCA
FROM DUAL

UNION ALL

SELECT
    'MEDICOES_CNE_BASE_X_JOIN_BASE' AS VALIDACAO,
    (
        SELECT COUNT(DISTINCT CNE.CNE_FILIAL || '|' || CNE.CNE_CONTRA || '|' || CNE.CNE_NUMMED)
        FROM CNE010 CNE
        WHERE CNE.D_E_L_E_T_ = ' '
        AND EXISTS (
            SELECT 1
            FROM CN9010 CN9
            WHERE CN9.CN9_NUMERO = CNE.CNE_CONTRA
            AND CN9.CN9_FILIAL = CNE.CNE_FILIAL
            AND CN9.D_E_L_E_T_ = ' '
            AND NOT EXISTS (
                SELECT 1
                FROM CN9010 CN9B
                WHERE CN9B.CN9_NUMERO = CN9.CN9_NUMERO
                AND CN9B.CN9_FILIAL = CN9.CN9_FILIAL
                AND CN9B.D_E_L_E_T_ = ' '
                AND (
        NVL(CN9B.CN9_DTULST, ' ') > NVL(CN9.CN9_DTULST, ' ')
        OR (
            NVL(CN9B.CN9_DTULST, ' ') = NVL(CN9.CN9_DTULST, ' ')
            AND CN9B.R_E_C_N_O_ > CN9.R_E_C_N_O_
        )
    )
            )
        )
    ) AS VALOR_ORIGINAL,
    (
        SELECT COUNT(DISTINCT CNE.CNE_FILIAL || '|' || CNE.CNE_CONTRA || '|' || CNE.CNE_NUMMED)
        FROM CNE010 CNE
        WHERE CNE.D_E_L_E_T_ = ' '
        AND EXISTS (
            SELECT 1
            FROM CN9010 CN9
            WHERE CN9.CN9_NUMERO = CNE.CNE_CONTRA
            AND CN9.CN9_FILIAL = CNE.CNE_FILIAL
            AND CN9.D_E_L_E_T_ = ' '
            AND NOT EXISTS (
                SELECT 1
                FROM CN9010 CN9B
                WHERE CN9B.CN9_NUMERO = CN9.CN9_NUMERO
                AND CN9B.CN9_FILIAL = CN9.CN9_FILIAL
                AND CN9B.D_E_L_E_T_ = ' '
                AND (
        NVL(CN9B.CN9_DTULST, ' ') > NVL(CN9.CN9_DTULST, ' ')
        OR (
            NVL(CN9B.CN9_DTULST, ' ') = NVL(CN9.CN9_DTULST, ' ')
            AND CN9B.R_E_C_N_O_ > CN9.R_E_C_N_O_
        )
    )
            )
        )
    ) AS VALOR_TRATADO,
    0 AS DIFERENCA
FROM DUAL

UNION ALL

SELECT
    'MEDICOES_CNE_SEM_BASE' AS VALIDACAO,
    (
        SELECT COUNT(DISTINCT CNE.CNE_FILIAL || '|' || CNE.CNE_CONTRA || '|' || CNE.CNE_NUMMED)
        FROM CNE010 CNE
        WHERE CNE.D_E_L_E_T_ = ' '
        AND NOT EXISTS (
            SELECT 1
            FROM CN9010 CN9
            WHERE CN9.CN9_NUMERO = CNE.CNE_CONTRA
            AND CN9.CN9_FILIAL = CNE.CNE_FILIAL
            AND CN9.D_E_L_E_T_ = ' '
            AND NOT EXISTS (
                SELECT 1
                FROM CN9010 CN9B
                WHERE CN9B.CN9_NUMERO = CN9.CN9_NUMERO
                AND CN9B.CN9_FILIAL = CN9.CN9_FILIAL
                AND CN9B.D_E_L_E_T_ = ' '
                AND (
        NVL(CN9B.CN9_DTULST, ' ') > NVL(CN9.CN9_DTULST, ' ')
        OR (
            NVL(CN9B.CN9_DTULST, ' ') = NVL(CN9.CN9_DTULST, ' ')
            AND CN9B.R_E_C_N_O_ > CN9.R_E_C_N_O_
        )
    )
            )
        )
    ) AS VALOR_ORIGINAL,
    (
        SELECT COUNT(DISTINCT CNE.CNE_FILIAL || '|' || CNE.CNE_CONTRA || '|' || CNE.CNE_NUMMED)
        FROM CNE010 CNE
        WHERE CNE.D_E_L_E_T_ = ' '
        AND NOT EXISTS (
            SELECT 1
            FROM CN9010 CN9
            WHERE CN9.CN9_NUMERO = CNE.CNE_CONTRA
            AND CN9.CN9_FILIAL = CNE.CNE_FILIAL
            AND CN9.D_E_L_E_T_ = ' '
            AND NOT EXISTS (
                SELECT 1
                FROM CN9010 CN9B
                WHERE CN9B.CN9_NUMERO = CN9.CN9_NUMERO
                AND CN9B.CN9_FILIAL = CN9.CN9_FILIAL
                AND CN9B.D_E_L_E_T_ = ' '
                AND (
        NVL(CN9B.CN9_DTULST, ' ') > NVL(CN9.CN9_DTULST, ' ')
        OR (
            NVL(CN9B.CN9_DTULST, ' ') = NVL(CN9.CN9_DTULST, ' ')
            AND CN9B.R_E_C_N_O_ > CN9.R_E_C_N_O_
        )
    )
            )
        )
    ) AS VALOR_TRATADO,
    0 AS DIFERENCA
FROM DUAL

UNION ALL

SELECT
    'PARCELAS_CNF_BASE_X_JOIN_BASE' AS VALIDACAO,
    (
        SELECT COUNT(DISTINCT CNF.CNF_FILIAL || '|' || CNF.CNF_CONTRA || '|' || CNF.CNF_PARCEL)
        FROM CNF010 CNF
        WHERE CNF.D_E_L_E_T_ = ' '
        AND EXISTS (
            SELECT 1
            FROM CN9010 CN9
            WHERE CN9.CN9_NUMERO = CNF.CNF_CONTRA
            AND CN9.CN9_FILIAL = CNF.CNF_FILIAL
            AND CN9.D_E_L_E_T_ = ' '
            AND NOT EXISTS (
                SELECT 1
                FROM CN9010 CN9B
                WHERE CN9B.CN9_NUMERO = CN9.CN9_NUMERO
                AND CN9B.CN9_FILIAL = CN9.CN9_FILIAL
                AND CN9B.D_E_L_E_T_ = ' '
                AND (
        NVL(CN9B.CN9_DTULST, ' ') > NVL(CN9.CN9_DTULST, ' ')
        OR (
            NVL(CN9B.CN9_DTULST, ' ') = NVL(CN9.CN9_DTULST, ' ')
            AND CN9B.R_E_C_N_O_ > CN9.R_E_C_N_O_
        )
    )
            )
        )
    ) AS VALOR_ORIGINAL,
    (
        SELECT COUNT(DISTINCT CNF.CNF_FILIAL || '|' || CNF.CNF_CONTRA || '|' || CNF.CNF_PARCEL)
        FROM CNF010 CNF
        WHERE CNF.D_E_L_E_T_ = ' '
        AND EXISTS (
            SELECT 1
            FROM CN9010 CN9
            WHERE CN9.CN9_NUMERO = CNF.CNF_CONTRA
            AND CN9.CN9_FILIAL = CNF.CNF_FILIAL
            AND CN9.D_E_L_E_T_ = ' '
            AND NOT EXISTS (
                SELECT 1
                FROM CN9010 CN9B
                WHERE CN9B.CN9_NUMERO = CN9.CN9_NUMERO
                AND CN9B.CN9_FILIAL = CN9.CN9_FILIAL
                AND CN9B.D_E_L_E_T_ = ' '
                AND (
        NVL(CN9B.CN9_DTULST, ' ') > NVL(CN9.CN9_DTULST, ' ')
        OR (
            NVL(CN9B.CN9_DTULST, ' ') = NVL(CN9.CN9_DTULST, ' ')
            AND CN9B.R_E_C_N_O_ > CN9.R_E_C_N_O_
        )
    )
            )
        )
    ) AS VALOR_TRATADO,
    0 AS DIFERENCA
FROM DUAL

UNION ALL

SELECT
    'PARCELAS_CNF_SEM_BASE' AS VALIDACAO,
    (
        SELECT COUNT(DISTINCT CNF.CNF_FILIAL || '|' || CNF.CNF_CONTRA || '|' || CNF.CNF_PARCEL)
        FROM CNF010 CNF
        WHERE CNF.D_E_L_E_T_ = ' '
        AND NOT EXISTS (
            SELECT 1
            FROM CN9010 CN9
            WHERE CN9.CN9_NUMERO = CNF.CNF_CONTRA
            AND CN9.CN9_FILIAL = CNF.CNF_FILIAL
            AND CN9.D_E_L_E_T_ = ' '
            AND NOT EXISTS (
                SELECT 1
                FROM CN9010 CN9B
                WHERE CN9B.CN9_NUMERO = CN9.CN9_NUMERO
                AND CN9B.CN9_FILIAL = CN9.CN9_FILIAL
                AND CN9B.D_E_L_E_T_ = ' '
                AND (
        NVL(CN9B.CN9_DTULST, ' ') > NVL(CN9.CN9_DTULST, ' ')
        OR (
            NVL(CN9B.CN9_DTULST, ' ') = NVL(CN9.CN9_DTULST, ' ')
            AND CN9B.R_E_C_N_O_ > CN9.R_E_C_N_O_
        )
    )
            )
        )
    ) AS VALOR_ORIGINAL,
    (
        SELECT COUNT(DISTINCT CNF.CNF_FILIAL || '|' || CNF.CNF_CONTRA || '|' || CNF.CNF_PARCEL)
        FROM CNF010 CNF
        WHERE CNF.D_E_L_E_T_ = ' '
        AND NOT EXISTS (
            SELECT 1
            FROM CN9010 CN9
            WHERE CN9.CN9_NUMERO = CNF.CNF_CONTRA
            AND CN9.CN9_FILIAL = CNF.CNF_FILIAL
            AND CN9.D_E_L_E_T_ = ' '
            AND NOT EXISTS (
                SELECT 1
                FROM CN9010 CN9B
                WHERE CN9B.CN9_NUMERO = CN9.CN9_NUMERO
                AND CN9B.CN9_FILIAL = CN9.CN9_FILIAL
                AND CN9B.D_E_L_E_T_ = ' '
                AND (
        NVL(CN9B.CN9_DTULST, ' ') > NVL(CN9.CN9_DTULST, ' ')
        OR (
            NVL(CN9B.CN9_DTULST, ' ') = NVL(CN9.CN9_DTULST, ' ')
            AND CN9B.R_E_C_N_O_ > CN9.R_E_C_N_O_
        )
    )
            )
        )
    ) AS VALOR_TRATADO,
    0 AS DIFERENCA
FROM DUAL

