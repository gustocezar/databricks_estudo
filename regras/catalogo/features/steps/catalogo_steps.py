"""Passos do catálogo de regras: frase de negócio → um SELECT no warehouse → conferência."""
from __future__ import annotations

from behave import then, when

import uc

S = f"{uc.CATALOGO}.{uc.SCHEMA}"
VIGENTE = ("c.status = 'aprovada' AND d.dia >= coalesce(c.vigente_de, DATE'0001-01-01') "
           "AND d.dia < coalesce(c.vigente_ate, DATE'9999-12-31')")


@when("confiro as versões vigentes em todos os dias da base")
def confere_cobertura(context):
    context.linhas = uc.executar(f"""WITH d AS (SELECT DISTINCT data_extracao AS dia FROM {uc.CATALOGO}.bronze.pagamentos_pendentes_eventos),
r AS (SELECT DISTINCT regra_id FROM {S}.catalogo_regras)
SELECT d.dia, r.regra_id, count(c.versao) FROM d CROSS JOIN r
LEFT JOIN {S}.catalogo_regras c ON c.regra_id = r.regra_id AND {VIGENTE}
GROUP BY ALL HAVING count(c.versao) <> 1 LIMIT 5""")


@then("nenhum dia fica sem versão ou com duas versões da mesma regra")
def sem_buraco(context):
    assert not context.linhas, f"dia × regra fora da regra (até 5): {context.linhas}"


@when('consulto a versão vigente da regra "{regra}" no dia {dia}')
def consulta_versao(context, regra, dia):
    context.versao = uc.executar(f"SELECT {S}.versao_vigente('{regra}', DATE'{dia}')")[0][0]


@then("a versão é {versao:d}")
def confere_versao(context, versao):
    assert context.versao is not None and int(context.versao) == versao, f"esperado {versao}, obtido {context.versao}"


@then("a regra não tem versão nesse dia")
def sem_versao(context):
    assert context.versao is None, f"esperado sem versão, obtido {context.versao}"


@when("listo os motivos de rejeição da quarentena")
def motivos(context):
    context.fora = uc.executar(f"""SELECT DISTINCT motivo_rejeicao FROM {uc.CATALOGO}.silver.pendencia_evento_quarentena
WHERE motivo_rejeicao NOT IN (SELECT regra_id FROM {S}.catalogo_regras WHERE tipo = 'erro')""")


@then("todos são regras de erro do catálogo")
def todos_no_catalogo(context):
    assert not context.fora, f"motivos fora do catálogo: {context.fora}"


@when("confiro as versões aprovadas do catálogo")
def aprovadas(context):
    context.sem_aprovacao = uc.executar(f"""SELECT regra_id, versao FROM {S}.catalogo_regras
WHERE status = 'aprovada' AND (aprovado_por IS NULL OR aprovado_em IS NULL)""")
    context.sem_motivo = uc.executar(f"""SELECT regra_id, versao FROM {S}.catalogo_regras
WHERE versao > 1 AND (motivo IS NULL OR origem IS NULL)""")


@then("toda versão aprovada tem quem aprovou e quando")
def com_aprovacao(context):
    assert not context.sem_aprovacao, f"sem aprovado_por/aprovado_em: {context.sem_aprovacao}"


@then("toda versão depois da primeira tem motivo e origem")
def com_motivo(context):
    assert not context.sem_motivo, f"sem motivo/origem: {context.sem_motivo}"


@when('tento registrar uma triagem com a classificação "{classificacao}"')
def registra_triagem(context, classificacao):
    # A CHECK constraint recusa antes de gravar: a tabela continua vazia de testes.
    try:
        uc.executar(f"""INSERT INTO {S}.triagem_regras VALUES ('T-TESTE-BDD', 'uf_invalida', 1, DATE'2026-12-07',
DATE'2026-12-13', '{classificacao}', 'teste do BDD', NULL, 'squad pos-venda', current_timestamp())""")
        context.erro = None
    except RuntimeError as e:
        context.erro = str(e)


@then("o registro é recusado pela tabela")
def recusado(context):
    assert context.erro and "CHECK" in context.erro.upper(), f"a tabela aceitou uma classificação fora do combinado: {context.erro}"
