"""Regras de negócio do pós-venda como funções SQL do Unity Catalog (fonte única da regra).

Cada função reproduz exatamente o cálculo que o pipeline faz hoje como texto SQL (carga_diaria/gerar_carga.py), com uma
diferença explícita por função quando a entrada é inválida (documentada em `decisao`). Os cenários em
features/*.feature são o contrato; paridade.py prova que as funções batem com o que já está gravado na gold e na silver.

    .venv/bin/python funcoes.py            # cria o schema e (re)cria as funções; mostra o que mudou
    .venv/bin/python funcoes.py --mostrar  # só imprime o DDL
"""
from __future__ import annotations

import sys

import uc

Q = f"{uc.CATALOGO}.{uc.SCHEMA}"

SCHEMA_COMENTARIO = ("Regras de negócio do pós-venda (seguro de vida) como funções SQL: faixa de atraso, multa, juros, total "
                     "pendente e CPF válido. Fonte única das regras, testada por cenários BDD em português (pos_venda/regras).")


def txt(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


FUNCOES = [
    {
        "nome": "faixa_atraso",
        "args": [("dias_atraso", "INT", "Dias entre o vencimento da parcela e a data de referência.")],
        "retorna": "STRING",
        "comentario": ("Faixa de atraso (aging) da parcela: 00_VENCE_HOJE (0 dia), 01_1_A_15, 02_16_A_30, 03_31_A_60, "
                       "04_61_A_90, 05_91_A_120 e 06_ACIMA_120. Mesmos códigos da gold.dim_faixa_atraso. Nulo se os dias "
                       "forem nulos ou negativos (parcela ainda não vencida)."),
        "corpo": """CASE
    WHEN dias_atraso IS NULL OR dias_atraso < 0 THEN NULL
    WHEN dias_atraso = 0 THEN '00_VENCE_HOJE'
    WHEN dias_atraso <= 15 THEN '01_1_A_15'
    WHEN dias_atraso <= 30 THEN '02_16_A_30'
    WHEN dias_atraso <= 60 THEN '03_31_A_60'
    WHEN dias_atraso <= 90 THEN '04_61_A_90'
    WHEN dias_atraso <= 120 THEN '05_91_A_120'
    ELSE '06_ACIMA_120'
  END""",
        "decisao": "dias negativos: o pipeline devolvia 01_1_A_15; a função devolve nulo (não há parcela vencida).",
    },
    {
        "nome": "valor_multa",
        "args": [("valor_parcela", "DECIMAL(14,2)", "Valor da parcela (prêmio do período) em R$.")],
        "retorna": "DECIMAL(14,2)",
        "comentario": ("Multa por atraso: 2% do valor da parcela, arredondada em 2 casas. Fixa: não depende dos dias de "
                       "atraso (vale também para a parcela que vence hoje, como no pipeline atual)."),
        "corpo": "CAST(round(valor_parcela * 0.02, 2) AS DECIMAL(14,2))",
        "decisao": "nenhuma (mesmo cálculo do pipeline).",
    },
    {
        "nome": "valor_juros",
        "args": [("valor_parcela", "DECIMAL(14,2)", "Valor da parcela (prêmio do período) em R$."),
                 ("dias_atraso", "INT", "Dias de atraso na data de referência.")],
        "retorna": "DECIMAL(14,2)",
        "comentario": ("Juros de mora: 1% ao mês pró-rata (mês de 30 dias) sobre a parcela, arredondado em 2 casas: "
                       "parcela x 0,01 x dias / 30. Nulo se os dias forem nulos ou negativos."),
        "corpo": """CASE WHEN dias_atraso IS NULL OR dias_atraso < 0 THEN NULL
    ELSE CAST(round(valor_parcela * 0.01 * dias_atraso / 30.0, 2) AS DECIMAL(14,2)) END""",
        "decisao": "dias negativos: o pipeline devolvia juros negativos; a função devolve nulo.",
    },
    {
        "nome": "valor_total_pendente",
        "args": [("valor_parcela", "DECIMAL(14,2)", "Valor da parcela (prêmio do período) em R$."),
                 ("dias_atraso", "INT", "Dias de atraso na data de referência.")],
        "retorna": "DECIMAL(14,2)",
        "comentario": ("Valor total pendente da parcela: parcela + multa (valor_multa) + juros (valor_juros), cada parte "
                       "arredondada em 2 casas antes da soma. Nulo se os dias forem nulos ou negativos."),
        "corpo": f"CAST(valor_parcela + {Q}.valor_multa(valor_parcela) + {Q}.valor_juros(valor_parcela, dias_atraso) AS DECIMAL(14,2))",
        "decisao": "dias negativos: nulo, porque os juros são nulos.",
    },
    {
        "nome": "cpf_valido",
        "args": [("cpf", "STRING", "CPF com ou sem pontuação.")],
        "retorna": "BOOLEAN",
        "comentario": ("Verdadeiro se o CPF tem 11 dígitos (ignorando pontuação), os dois dígitos verificadores conferem "
                       "(módulo 11) e os dígitos não são todos iguais. Falso para nulo ou vazio."),
        "corpo": """CASE
    WHEN cpf IS NULL THEN false
    WHEN length(regexp_replace(cpf, '[^0-9]', '')) <> 11 THEN false
    WHEN regexp_replace(cpf, '[^0-9]', '') RLIKE '^(\\\\d)\\\\1{10}$' THEN false
    ELSE
      ((aggregate(zip_with(transform(sequence(1, 9), i -> CAST(substring(regexp_replace(cpf, '[^0-9]', ''), i, 1) AS INT)),
                           sequence(10, 2, -1), (d, p) -> d * p), 0, (a, v) -> a + v) * 10) % 11) % 10
        = CAST(substring(regexp_replace(cpf, '[^0-9]', ''), 10, 1) AS INT)
      AND
      ((aggregate(zip_with(transform(sequence(1, 10), i -> CAST(substring(regexp_replace(cpf, '[^0-9]', ''), i, 1) AS INT)),
                           sequence(11, 2, -1), (d, p) -> d * p), 0, (a, v) -> a + v) * 10) % 11) % 10
        = CAST(substring(regexp_replace(cpf, '[^0-9]', ''), 11, 1) AS INT)
  END""",
        "decisao": ("dígitos todos iguais (ex.: 111.111.111-11): passam no cálculo do módulo 11 e o pipeline aceitava; a "
                    "função recusa, como a Receita Federal."),
    },
]


def ddl(f: dict) -> str:
    args = ", ".join(f"{n} {t} COMMENT {txt(c)}" for n, t, c in f["args"])
    return (f"CREATE OR REPLACE FUNCTION {Q}.{f['nome']}({args})\n"
            f"RETURNS {f['retorna']}\nLANGUAGE SQL\nDETERMINISTIC\nCOMMENT {txt(f['comentario'])}\n"
            f"RETURN {f['corpo']}")


def implantar() -> None:
    uc.executar(f"CREATE SCHEMA IF NOT EXISTS {Q} COMMENT {txt(SCHEMA_COMENTARIO)}")
    uc.executar(f"COMMENT ON SCHEMA {Q} IS {txt(SCHEMA_COMENTARIO)}")
    for f in FUNCOES:                                   # ordem importa: valor_total_pendente usa multa e juros
        uc.executar(ddl(f))
        print(f"  {Q}.{f['nome']:<22} ok")
    linhas = uc.executar(f"SELECT routine_name, comment IS NOT NULL FROM {uc.CATALOGO}.information_schema.routines "
                         f"WHERE routine_schema = '{uc.SCHEMA}' ORDER BY 1")
    print("funções no schema:", [(n, d == "true") for n, d in linhas])


if __name__ == "__main__":
    if "--mostrar" in sys.argv:
        print(";\n\n".join(ddl(f) for f in FUNCOES) + ";")
    else:
        implantar()
