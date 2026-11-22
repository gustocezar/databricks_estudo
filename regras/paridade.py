"""Paridade: as funções de regra devolvem exatamente o que o pipeline já gravou?

Antes de o pipeline e a Genie passarem a chamar as funções (etapa 2), cada regra é comparada linha a linha com os dados
atuais. Critério: 0 divergência na gold e na silver aceita; na quarentena, a função reprova todos os totais que a
barreira reprovou por `valor_total_inconsistente`. Também mede o impacto das decisões novas (dias negativos, CPF com
dígitos repetidos) nos dados de hoje.

    .venv/bin/python paridade.py      # imprime o relatório e grava resultados/paridade.json; sai com 1 se divergir
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import uc

R = f"{uc.CATALOGO}.{uc.SCHEMA}"
C = uc.CATALOGO


def iguais(a, b):
    return f"count_if(NOT ({a} <=> {b}))"


CHECAGENS = [
    {
        "nome": "gold · fato diária (pendência × dia)",
        "sql": f"""SELECT count(*) AS linhas,
  {iguais('faixa_atraso_sk', f'xxhash64({R}.faixa_atraso(dias_atraso))')} AS faixa,
  {iguais('valor_multa', f'{R}.valor_multa(valor_parcela)')} AS multa,
  {iguais('valor_juros', f'{R}.valor_juros(valor_parcela, dias_atraso)')} AS juros,
  {iguais('valor_total_pendente', f'{R}.valor_total_pendente(valor_parcela, dias_atraso)')} AS total,
  count_if(dias_atraso < 0) AS impacto_dias_negativos
FROM {C}.gold.fact_pagamento_pendente_snapshot""",
        "zero": ["faixa", "multa", "juros", "total"],
    },
    {
        "nome": "silver · eventos aceitos pela barreira",
        "sql": f"""SELECT count(*) AS linhas,
  {iguais('faixa_atraso', f'{R}.faixa_atraso(dias_atraso)')} AS faixa,
  {iguais('valor_multa', f'{R}.valor_multa(valor_parcela)')} AS multa,
  {iguais('valor_juros', f'{R}.valor_juros(valor_parcela, dias_atraso)')} AS juros,
  {iguais('valor_total_pendente', f'{R}.valor_total_pendente(valor_parcela, dias_atraso)')} AS total,
  {iguais('NOT dq_cpf_invalido', f'{R}.cpf_valido(cliente_cpf)')} AS cpf,
  count_if(regexp_replace(cliente_cpf, '[^0-9]', '') RLIKE '^(\\\\d)\\\\1{{10}}$') AS impacto_cpf_repetido,
  count_if(dias_atraso < 0) AS impacto_dias_negativos
FROM {C}.silver.pendencia_evento""",
        "zero": ["faixa", "multa", "juros", "total", "cpf"],
    },
    {
        "nome": "quarentena · total reprovado pela barreira",
        "sql": f"""SELECT count(*) AS linhas,
  count_if(valor_total_pendente <=> {R}.valor_total_pendente(valor_parcela, dias_atraso)) AS total_aceito_pela_funcao
FROM {C}.silver.pendencia_evento_quarentena
WHERE motivo_rejeicao = 'valor_total_inconsistente'""",
        "zero": ["total_aceito_pela_funcao"],
    },
]


def main() -> int:
    resultado, ok = [], True
    for c in CHECAGENS:
        linhas = uc.executar(c["sql"], espera="30s")
        # nomes das colunas na ordem do SELECT
        nomes = [p.strip().split(" AS ")[-1] for p in c["sql"].split("FROM")[0].replace("SELECT", "", 1).split(",\n")]
        valores = dict(zip(nomes, (int(v) for v in linhas[0])))
        divergentes = {k: valores[k] for k in c["zero"] if valores[k]}
        ok &= not divergentes
        resultado.append({"checagem": c["nome"], **valores, "status": "ok" if not divergentes else "DIVERGE"})
        print(f"{'OK ' if not divergentes else 'DIV'} {c['nome']}")
        for k, v in valores.items():
            print(f"      {k:28} {v:>12,}".replace(",", "."))
    pasta = Path(__file__).parent / "resultados"
    pasta.mkdir(exist_ok=True)
    (pasta / "paridade.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1))
    print("PARIDADE:", "100% (nenhuma divergência)" if ok else "há divergências")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
