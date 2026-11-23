"""RELY nas 14 chaves primárias da gold, com prova de unicidade e medição antes/depois.

Por quê: com `RELY` o otimizador confia que a chave é única e pode eliminar um LEFT JOIN com a dimensão quando a consulta
não usa nenhuma coluna dela (a visão `ontologia.posicao_carteira` junta 9 dimensões; uma pergunta só sobre o saldo por
dia não precisa de nenhuma). O Databricks não valida chaves: declarar RELY numa chave que não é única daria resultado
errado, por isso `verificar` roda antes e `aplicar` recusa se houver duplicata ou nulo.

Só as chaves PRIMÁRIAS ganham RELY. As 15 chaves estrangeiras da fato continuam sem RELY: a de forma de pagamento tem
órfãs de propósito (NAO_CADASTRADA), e RELY numa estrangeira deixaria o otimizador trocar o LEFT JOIN por INNER JOIN.

Não existe "ALTER CONSTRAINT ... RELY": a chave é removida e declarada de novo. Remover a chave de uma dimensão exige
CASCADE, que apaga as chaves estrangeiras da fato que apontam para ela; `aplicar` as recria no fim, iguais às de antes
(mesmos nomes, sem RELY). O script é idempotente: rodar de novo pula o que já está certo e recria o que faltar.

Uso:
    python3 aplicar_rely.py verificar          # unicidade e nulos das 14 chaves (só leitura)
    python3 aplicar_rely.py medir antes        # plano (junções e dimensões lidas), tempo e resultado das consultas
    python3 aplicar_rely.py aplicar            # RELY nas PKs + recria as FKs
    python3 aplicar_rely.py medir depois
    python3 aplicar_rely.py conferir           # 14 PK com RELY, 15 FK sem RELY
"""
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sql_util import CotaEsgotada, executar  # noqa: E402

GOLD = "pos_venda.gold"
FATO = "fact_pagamento_pendente_snapshot"
SAIDA = pathlib.Path(__file__).resolve().parent / "rely"

# tabela -> colunas da chave primária (as mesmas de carga_diaria/gerar_carga.py)
PKS = {
    "bridge_apolice_cobertura": ["apolice_sk", "cobertura_sk"], "dim_apolice": ["apolice_sk"], "dim_cliente": ["cliente_sk"],
    "dim_cobertura": ["cobertura_sk"], "dim_corretor": ["corretor_sk"], "dim_data": ["data_sk"],
    "dim_faixa_atraso": ["faixa_atraso_sk"], "dim_forma_pagamento": ["forma_pagamento_sk"],
    "dim_motivo_pendencia": ["motivo_pendencia_sk"], "dim_periodicidade": ["periodicidade_sk"],
    "dim_ponto_venda": ["ponto_venda_sk"], "dim_produto": ["produto_sk"], "dim_status_cobranca": ["status_cobranca_sk"],
    FATO: ["data_referencia_sk", "pendencia_id"],
}
# chaves estrangeiras da fato (coluna, dimensão, coluna da dimensão): as mesmas de 30_fato_snapshot, SEM RELY
FKS = [("cliente_sk", "dim_cliente", "cliente_sk"), ("apolice_sk", "dim_apolice", "apolice_sk"), ("produto_sk", "dim_produto", "produto_sk"),
       ("corretor_sk", "dim_corretor", "corretor_sk"), ("ponto_venda_sk", "dim_ponto_venda", "ponto_venda_sk"),
       ("periodicidade_sk", "dim_periodicidade", "periodicidade_sk"), ("forma_pagamento_sk", "dim_forma_pagamento", "forma_pagamento_sk"),
       ("status_cobranca_sk", "dim_status_cobranca", "status_cobranca_sk"), ("motivo_pendencia_sk", "dim_motivo_pendencia", "motivo_pendencia_sk"),
       ("faixa_atraso_sk", "dim_faixa_atraso", "faixa_atraso_sk"), ("data_referencia_sk", "dim_data", "data_sk"),
       ("data_vencimento_sk", "dim_data", "data_sk"), ("data_emissao_apolice_sk", "dim_data", "data_sk"),
       ("data_entrada_pendencia_sk", "dim_data", "data_sk"), ("data_ultima_tentativa_sk", "dim_data", "data_sk")]

# consultas medidas: perguntas típicas da Genie e dos painéis, e a fonte do Power BI
CONSULTAS = {
    "saldo_por_dia (metric view, sem dimensões)":
        "SELECT `Data de referência`, MEASURE(`Saldo em aberto`) AS saldo FROM pos_venda.ontologia.mv_carteira_em_aberto GROUP BY ALL",
    "saldo_por_produto (metric view, 1 dimensão)":
        "SELECT `Produto`, MEASURE(`Saldo em aberto`) AS saldo FROM pos_venda.ontologia.mv_carteira_em_aberto "
        "WHERE `Foto mais recente` GROUP BY ALL",
    "bi.carteira_diaria (fonte do Power BI)": "SELECT * FROM pos_venda.bi.carteira_diaria",
}


def sql(s):
    estado, erro, linhas = executar(s)
    if estado != "SUCCEEDED":
        raise RuntimeError(f"{s[:90]}... -> {estado}: {erro[:300]}")
    return linhas


def estado_pk(tabela):
    """(tem PK, tem RELY) lidos do SHOW CREATE TABLE (o information_schema não expõe RELY)."""
    txt = sql(f"SHOW CREATE TABLE {GOLD}.{tabela}")[0]["createtab_stmt"]
    m = re.search(rf"CONSTRAINT `pk_{tabela}` PRIMARY KEY \([^)]*\)( RELY)?", txt)
    return bool(m), bool(m and m.group(1))


def fks_existentes():
    linhas = sql("SELECT constraint_name FROM pos_venda.information_schema.referential_constraints WHERE constraint_schema = 'gold'")
    return {r["constraint_name"] for r in linhas}


def verificar():
    problemas = 0
    for t, cols in PKS.items():
        chave = cols[0] if len(cols) == 1 else f"struct({', '.join(cols)})"
        nulos = " OR ".join(f"{c} IS NULL" for c in cols)
        r = sql(f"SELECT count(*) AS n, count(DISTINCT {chave}) AS distintos, count_if({nulos}) AS nulos FROM {GOLD}.{t}")[0]
        n, d, z = int(r["n"]), int(r["distintos"]), int(r["nulos"])
        ok = n == d and z == 0
        problemas += not ok
        print(f"{'OK ' if ok else 'ERRO'} {t:36} linhas={n:>9}  distintas={d:>9}  nulos={z}")
    print("chaves únicas e sem nulo:", "14/14" if not problemas else f"{14 - problemas}/14")
    return problemas


def plano(consulta):
    txt = sql(f"EXPLAIN EXTENDED {consulta}")[0]["plan"]
    otimizado = txt.split("== Optimized Logical Plan ==")[1].split("== Physical Plan ==")[0]
    juncoes = len(re.findall(r"\bJoin (LeftOuter|Inner|LeftSemi|LeftAnti|RightOuter|FullOuter|Cross)\b", otimizado))
    dims = sorted(set(re.findall(r"pos_venda\.gold\.(dim_[a-z_]+|bridge_[a-z_]+)", otimizado)))
    return juncoes, dims


def medir(rotulo):
    SAIDA.mkdir(exist_ok=True)
    res = {"rotulo": rotulo, "quando": time.strftime("%Y-%m-%d %H:%M:%S"), "consultas": {}}
    for nome, c in CONSULTAS.items():
        juncoes, dims = plano(c)
        tempos = []
        for i in range(2):     # a 2ª execução é a medida (warehouse acordado); o comentário evita o cache de resultado
            t0 = time.time()
            linhas = sql(f"/* rely {rotulo} {time.time():.0f} {i} */ SELECT count(*) AS linhas, "
                         f"CAST(sum(hash(*)) AS STRING) AS assinatura FROM ({c})")
            tempos.append(round(time.time() - t0, 1))
        res["consultas"][nome] = {"juncoes": juncoes, "dimensoes_lidas": dims, "segundos": tempos[1],
                                  "linhas": int(linhas[0]["linhas"]), "assinatura": linhas[0]["assinatura"]}
        print(f"{nome:46} junções={juncoes}  dimensões={len(dims)}  {tempos[1]:>5}s  linhas={linhas[0]['linhas']}")
    (SAIDA / f"medicao_{rotulo}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return res


def aplicar():
    if verificar():
        sys.exit("há chave duplicada ou nula: RELY não aplicado")
    for t, cols in PKS.items():
        tem_pk, tem_rely = estado_pk(t)
        if tem_rely:
            print(f"já tinha RELY  {t}")
            continue
        if tem_pk:
            sql(f"ALTER TABLE {GOLD}.{t} DROP PRIMARY KEY CASCADE")
        sql(f"ALTER TABLE {GOLD}.{t} ADD CONSTRAINT pk_{t} PRIMARY KEY ({', '.join(cols)}) RELY")
        print(f"RELY aplicado  {t}")
    existentes = fks_existentes()
    for col, dim, dcol in FKS:
        nome = f"fk_fact_{col}"
        if nome not in existentes:
            sql(f"ALTER TABLE {GOLD}.{FATO} ADD CONSTRAINT {nome} FOREIGN KEY ({col}) REFERENCES {GOLD}.{dim}({dcol})")
            print(f"FK recriada    {nome} (sem RELY)")


def conferir():
    com_rely = sum(estado_pk(t)[1] for t in PKS)
    txt = sql(f"SHOW CREATE TABLE {GOLD}.{FATO}")[0]["createtab_stmt"]
    fks = re.findall(r"CONSTRAINT `(fk_fact_[a-z_]+)` FOREIGN KEY \([^)]*\) REFERENCES [^)]*\)( RELY)?", txt)
    fk_rely = [n for n, r in fks if r]
    print(f"PK com RELY: {com_rely}/14 · FK na fato: {len(fks)}/15 · FK com RELY: {len(fk_rely)} {fk_rely or ''}")
    return 0 if com_rely == 14 and len(fks) == 15 and not fk_rely else 1


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else "verificar"
    try:
        if acao == "verificar":
            sys.exit(1 if verificar() else 0)
        elif acao == "medir":
            medir(sys.argv[2] if len(sys.argv) > 2 else "agora")
        elif acao == "aplicar":
            aplicar()
            sys.exit(conferir())
        elif acao == "conferir":
            sys.exit(conferir())
        else:
            sys.exit(__doc__)
    except CotaEsgotada as e:
        sys.exit(f"warehouse indisponível (cota diária do Free Edition): {e}")
