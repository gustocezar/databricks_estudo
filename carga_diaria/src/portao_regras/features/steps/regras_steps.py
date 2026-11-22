"""Passos dos cenários: traduzem a frase de negócio em uma chamada à função do Unity Catalog e conferem a resposta.

Finos de propósito: a regra mora na função (pos_venda.regras.*), não aqui.
"""
from __future__ import annotations

from decimal import Decimal

from behave import given, then, when

import uc

Q = f"{uc.CATALOGO}.{uc.SCHEMA}"


def reais(texto: str) -> Decimal:
    """'1.234,56' -> Decimal('1234.56')"""
    return Decimal(texto.strip().replace(".", "").replace(",", "."))


def brl(v) -> str:
    return "sem valor" if v is None else f"R$ {Decimal(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------------------------------------------------------------------------------------- faixa de atraso
@given("uma parcela com {dias} dias de atraso")
def parcela_dias(context, dias):
    context.dias = int(dias)


@when("calculo a faixa de atraso")
def calcula_faixa(context):
    context.faixa = uc.valor(f"faixa_atraso({context.dias})")


@then('a faixa é "{faixa}"')
def confere_faixa(context, faixa):
    assert context.faixa == faixa, f"{context.dias} dias: esperado {faixa}, a função devolveu {context.faixa}"


@then("a parcela fica sem faixa")
def sem_faixa(context):
    assert context.faixa is None, f"{context.dias} dias: esperado sem faixa, a função devolveu {context.faixa}"


# ------------------------------------------------------------------------------------------- multa, juros e total
@given("uma parcela de R$ {parcela} com {dias} dias de atraso")
def parcela_valor_dias(context, parcela, dias):
    context.parcela, context.dias = reais(parcela), int(dias)
    context.total_gravado = None


@given("um total gravado de R$ {total}")
def total_gravado(context, total):
    context.total_gravado = reais(total)


@when("calculo os valores da pendência")
def calcula_valores(context):
    p = f"CAST({context.parcela} AS DECIMAL(14,2))"
    d = context.dias
    linha = uc.executar(f"SELECT {Q}.valor_multa({p}), {Q}.valor_juros({p}, {d}), {Q}.valor_total_pendente({p}, {d})")[0]
    context.multa, context.juros, context.total = (None if v is None else Decimal(v) for v in linha)


def _confere(nome, obtido, esperado, context):
    assert obtido == reais(esperado), (f"parcela {brl(context.parcela)}, {context.dias} dias: {nome} esperado "
                                       f"R$ {esperado}, a função devolveu {brl(obtido)}")


@then("a multa é R$ {valor}")
def confere_multa(context, valor):
    _confere("multa", context.multa, valor, context)


@then("os juros são R$ {valor}")
def confere_juros(context, valor):
    _confere("juros", context.juros, valor, context)


@then("o total pendente é R$ {valor}")
def confere_total(context, valor):
    _confere("total pendente", context.total, valor, context)


@then("os juros ficam sem valor")
def juros_sem_valor(context):
    assert context.juros is None, f"esperado sem juros, a função devolveu {brl(context.juros)}"


@then("o total pendente fica sem valor")
def total_sem_valor(context):
    assert context.total is None, f"esperado sem total, a função devolveu {brl(context.total)}"


@then("o total gravado não confere com a regra")
def total_inconsistente(context):
    assert context.total is not None and context.total_gravado != context.total, (
        f"total gravado {brl(context.total_gravado)} deveria divergir da regra ({brl(context.total)})")


# --------------------------------------------------------------------------------------------------------- CPF
@given('o CPF ""')
def cpf_vazio(context):
    context.cpf_sql = "''"


@given('o CPF "{cpf}"')
def cpf_informado(context, cpf):
    context.cpf_sql = "'" + cpf.replace("'", "") + "'"


@given("um CPF não informado")
def cpf_nulo(context):
    context.cpf_sql = "CAST(NULL AS STRING)"


@when("verifico o CPF")
def verifica_cpf(context):
    context.cpf_ok = uc.valor(f"cpf_valido({context.cpf_sql})") == "true"


@then("o CPF é válido")
def cpf_valido(context):
    assert context.cpf_ok, f"CPF {context.cpf_sql} deveria ser válido"


@then("o CPF é inválido")
def cpf_invalido(context):
    assert not context.cpf_ok, f"CPF {context.cpf_sql} deveria ser inválido"
