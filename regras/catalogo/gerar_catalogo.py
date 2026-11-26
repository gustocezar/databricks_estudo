"""Catálogo de regras com versão e vigência (P41): valida, gera o YAML do DQX e os objetos de triagem, aplica e confere.

  python3 regras/catalogo/gerar_catalogo.py validar          # confere o catálogo e o YAML do DQX (sem rede)
  python3 regras/catalogo/gerar_catalogo.py testar           # testes da vigência e do gerador com catálogos de exemplo (sem rede)
  python3 regras/catalogo/gerar_catalogo.py gerar            # escreve o YAML do DQX, o YAML do ensaio e catalogo_regras.sql
  python3 regras/catalogo/gerar_catalogo.py aplicar          # cria ou atualiza tabelas, função e visões em pos_venda.regras
  python3 regras/catalogo/gerar_catalogo.py conferir         # no Databricks: catálogo = YAML, uma versão por dia, visões respondem
  python3 regras/catalogo/gerar_catalogo.py ensaio <run_id>  # compara a execução de ensaio do DQX com a verdade em SQL

Fonte única: catalogo_regras.yml. O YAML do DQX como código (dqx_codigo/checks_pendencias.yml) é gerado daqui.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

import yaml

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]                                     # pos_venda/
sys.path.insert(0, str(RAIZ / "governanca"))
from sql_util import CotaEsgotada, executar, executar_lista  # noqa: E402

CATALOGO = AQUI / "catalogo_regras.yml"
ENSAIO = AQUI / "ensaio" / "vigencia_periodicidade.yml"     # ensaio fictício: QUINZENAL aprovada a partir de 05/01/2027
DQX_YAML = RAIZ / "dqx_codigo" / "checks_pendencias.yml"
DQX_ENSAIO = RAIZ / "dqx_codigo" / "ensaio" / "checks_ensaio_vigencia.yml"
SQL = AQUI / "catalogo_regras.sql"
BARREIRA = RAIZ / "carga_diaria" / "gerar_carga.py"         # MOTIVO_REJEICAO: os nomes das regras de erro da barreira
JANELA_ENSAIO = ("2026-12-27", "2027-01-09")                # 14 dias que cruzam a troca de versão do ensaio

S = "pos_venda.regras"
BRONZE = "pos_venda.bronze.pagamentos_pendentes_eventos"
QUARENTENA = "pos_venda.silver.pendencia_evento_quarentena"
DQX_DESTINO = "pos_venda.dqx_codigo"                        # resultado da última execução do DQX como código (prefixo eventos)
PERFIL = "dbx-workshop"

TIPOS = {"erro": "error", "aviso": "warn"}
AREAS = {"cobranca", "carteira", "qualidade"}               # valores da tag governada subject_area
STATUS = {"proposta", "aprovada", "recusada"}
CLASSIFICACOES = ("dado_ruim", "regra_errada", "fora_da_vigencia", "esperado")
INICIO, FIM = "DATE'0001-01-01'", "DATE'9999-12-31'"


# ------------------------------------------------------------------------------------------------ catálogo e vigência
def data(x):
    if x is None or isinstance(x, dt.date):
        return x
    return dt.date.fromisoformat(str(x))


def carregar(caminho=CATALOGO, sobrepor=None):
    """Lê o catálogo; `sobrepor` troca as versões das regras listadas (usado só no ensaio)."""
    cat = yaml.safe_load(pathlib.Path(caminho).read_text(encoding="utf-8"))
    if sobrepor:
        ov = yaml.safe_load(pathlib.Path(sobrepor).read_text(encoding="utf-8"))
        por_id = {r["regra_id"]: r for r in cat["regras"]}
        for r in ov["regras"]:
            if r["regra_id"] not in por_id:
                raise ValueError(f"ensaio cita regra que não existe: {r['regra_id']}")
            por_id[r["regra_id"]]["versoes"] = r["versoes"]
    for r in cat["regras"]:
        for v in r["versoes"]:
            v["vigente_de"], v["vigente_ate"], v["aprovado_em"] = data(v.get("vigente_de")), data(v.get("vigente_ate")), data(v.get("aprovado_em"))
    return cat


def predicado(coluna, de, ate):
    """Filtro SQL da vigência pela data do dado: de inclusive, até exclusive; vazio quando vale sempre."""
    p = []
    if de:
        p.append(f"{coluna} >= DATE'{de.isoformat()}'")
    if ate:
        p.append(f"{coluna} < DATE'{ate.isoformat()}'")
    return " AND ".join(p)


def aprovadas(regra):
    return sorted((v for v in regra["versoes"] if v.get("status") == "aprovada"), key=lambda v: v["versao"])


def nomes_da_barreira(caminho=BARREIRA):
    texto = pathlib.Path(caminho).read_text(encoding="utf-8")
    bloco = texto.split('MOTIVO_REJEICAO = f"""CASE', 1)[1].split("END\"\"\"", 1)[0]
    return set(re.findall(r"THEN '([a-z_]+)'", bloco))


def validar_catalogo(cat, nomes_barreira=None):
    """Lista de erros do catálogo (vazia = válido)."""
    e = []
    col = (cat.get("padrao") or {}).get("coluna_data")
    if not col or not re.fullmatch(r"[a-z_][a-z0-9_]*", col):
        e.append("padrao.coluna_data ausente ou inválida")
    vistos = set()
    for r in cat.get("regras") or []:
        rid = r.get("regra_id", "?")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", rid):
            e.append(f"{rid}: regra_id precisa ser snake_case (é o nome estável da regra)")
        if rid in vistos:
            e.append(f"{rid}: regra_id repetido")
        vistos.add(rid)
        if r.get("tipo") not in TIPOS:
            e.append(f"{rid}: tipo deve ser erro ou aviso")
        if r.get("area") not in AREAS:
            e.append(f"{rid}: area fora de {sorted(AREAS)}")
        if not (r.get("titulo") or "").strip():
            e.append(f"{rid}: titulo (a regra em linguagem de negócio) vazio")
        vs = r.get("versoes") or []
        if [v.get("versao") for v in vs] != list(range(1, len(vs) + 1)):
            e.append(f"{rid}: versões devem ser 1, 2, 3... em ordem")
        for v in vs:
            n = f"{rid} v{v.get('versao')}"
            if v.get("status") not in STATUS:
                e.append(f"{n}: status fora de {sorted(STATUS)}")
            ck = v.get("check") or {}
            if not isinstance(ck.get("function"), str) or not isinstance(ck.get("arguments"), dict):
                e.append(f"{n}: check precisa de function e arguments (formato do DQX)")
            elif ck["function"] == "sql_expression" and not (ck["arguments"].get("expression") or "").strip():
                e.append(f"{n}: sql_expression sem expression")
            de, ate = data(v.get("vigente_de")), data(v.get("vigente_ate"))
            if de and ate and not de < ate:
                e.append(f"{n}: vigente_de precisa ser antes de vigente_ate")
            lt = v.get("limite_taxa")
            if lt is not None and not (0 <= float(lt) <= 1):
                e.append(f"{n}: limite_taxa entre 0 e 1")
            if v.get("status") == "aprovada" and not (v.get("aprovado_por") and v.get("aprovado_em")):
                e.append(f"{n}: versão aprovada precisa de aprovado_por e aprovado_em")
            if (v.get("versao") or 0) > 1 and not (v.get("motivo") and v.get("origem")):
                e.append(f"{n}: versão nova precisa de motivo e origem (questionário, triagem ou decisão)")
        ap = aprovadas(r)
        if not ap:
            e.append(f"{rid}: nenhuma versão aprovada")
        for a, b in zip(ap, ap[1:]):
            if data(a.get("vigente_ate")) is None or data(b.get("vigente_de")) != data(a.get("vigente_ate")):
                e.append(f"{rid}: v{b['versao']} precisa começar exatamente onde v{a['versao']} termina "
                         f"(sem buraco e sem sobreposição): {a.get('vigente_ate')} → {b.get('vigente_de')}")
    if nomes_barreira is not None:
        erros_cat = {r["regra_id"] for r in cat.get("regras") or [] if r.get("tipo") == "erro"}
        if erros_cat != nomes_barreira:
            e.append(f"regras de erro do catálogo ≠ barreira: só no catálogo {sorted(erros_cat - nomes_barreira)}, "
                     f"só na barreira {sorted(nomes_barreira - erros_cat)}")
    return e


# ------------------------------------------------------------------------------------------------ YAML do DQX
CABECALHO_DQX = """# GERADO por regras/catalogo/gerar_catalogo.py a partir de regras/catalogo/catalogo_regras.yml ({origem}).
# Não edite aqui: edite o catálogo e rode `python3 regras/catalogo/gerar_catalogo.py gerar`.
#
# Checagens DQX (biblioteca databricks-labs-dqx) para eventos de pendências de pagamento. As 11 regras de erro são as
# da barreira do pipeline (carga_diaria/gerar_carga.py, MOTIVO_REJEICAO), com os mesmos nomes, mais 3 avisos. Erro
# (criticality: error) vai para a quarentena; aviso (warn) entra marcado.
# Formato: https://databrickslabs.github.io/dqx/docs/guide/quality_checks_definition/
#
# Vigência (P41): cada versão de uma regra vale só para o dado da sua vigência, pelo `filter` na data do dado. Duas
# versões da mesma regra têm o mesmo nome (o motivo estável) e se distinguem pelo user_metadata.versao.
# Toda expressão dá TRUE quando o dado está bom (o DQX registra erro quando dá FALSE). O coalesce repete o
# comportamento da barreira com valor nulo: true = deixa passar; false = barra.
# Domínio fechado com sql_expression e IN: na versão 0.17.2, o is_in_list leu os valores de texto como colunas (L88).
"""


def checks_dqx(cat):
    col, dono = cat["padrao"]["coluna_data"], cat["padrao"].get("dono", "")
    saida = []
    for r in cat["regras"]:
        for v in aprovadas(r):
            c = {"name": r["regra_id"], "criticality": TIPOS[r["tipo"]], "check": v["check"]}
            f = predicado(col, v.get("vigente_de"), v.get("vigente_ate"))
            if f:
                c["filter"] = f
            c["user_metadata"] = {
                "regra_id": r["regra_id"], "versao": str(v["versao"]), "titulo": r["titulo"], "dono": r.get("dono", dono),
                "vigente_de": v["vigente_de"].isoformat() if v.get("vigente_de") else "",
                "vigente_ate": v["vigente_ate"].isoformat() if v.get("vigente_ate") else "",
            }
            saida.append(c)
    return saida


def yaml_dqx(cat, origem):
    blocos = [CABECALHO_DQX.format(origem=origem)]
    for tipo, titulo in (("error", "erros (barram o evento)"), ("warn", "avisos (entram marcados)")):
        blocos.append(f"\n# {'-' * 64} {titulo}\n")
        for c in checks_dqx(cat):
            if c["criticality"] == tipo:
                blocos.append(yaml.safe_dump([c], sort_keys=False, allow_unicode=True, width=110) + "\n")
    return "".join(blocos)


# ------------------------------------------------------------------------------------------------ SQL (pos_venda.regras)
def q(s):
    return str(s).replace("\\", "\\\\").replace("'", "''")


def lit(x):
    if x is None:
        return "NULL"
    if isinstance(x, dt.date):
        return f"DATE'{x.isoformat()}'"
    if isinstance(x, (int, float)):
        return str(x)
    return f"'{q(x)}'"


def ddl(cat):
    col, dono = cat["padrao"]["coluna_data"], cat["padrao"].get("dono", "")
    linhas = []
    for r in cat["regras"]:
        for v in r["versoes"]:
            ck = v["check"]
            linhas.append("(" + ", ".join(lit(x) for x in (
                r["regra_id"], v["versao"], r["titulo"], r["tipo"], r["area"], r.get("dono", dono), col, v["status"],
                v.get("vigente_de"), v.get("vigente_ate"),
                None if v.get("limite_taxa") is None else float(v["limite_taxa"]),
                ck["function"], json.dumps(ck["arguments"], ensure_ascii=False), v.get("motivo"), v.get("origem"),
                v.get("aprovado_por"), v.get("aprovado_em"))) + ")")
    vig = f"c.status = 'aprovada' AND d.dia >= coalesce(c.vigente_de, {INICIO}) AND d.dia < coalesce(c.vigente_ate, {FIM})"
    classes = ", ".join(f"'{c}'" for c in CLASSIFICACOES)
    return [
        f"""CREATE OR REPLACE TABLE {S}.catalogo_regras (
  regra_id STRING NOT NULL COMMENT 'Nome estável da regra: é o motivo de rejeição na quarentena e o nome da checagem no DQX.',
  versao INT NOT NULL COMMENT 'Número da versão da regra (1, 2, ...). Versão aprovada nunca é reescrita nem apagada.',
  titulo STRING COMMENT 'A regra em linguagem de negócio, como respondida no questionário.',
  tipo STRING COMMENT 'erro (barra o evento e o manda para a quarentena) ou aviso (o evento entra marcado).',
  area STRING COMMENT 'Área de negócio da regra (mesmos valores de subject_area): cobranca, carteira ou qualidade.',
  dono STRING COMMENT 'Área dona da regra: aprova versões novas e responde pela triagem das falhas.',
  coluna_data STRING COMMENT 'Coluna do dado que decide a versão vigente (a data do dado, não a da execução).',
  status STRING COMMENT 'proposta (ainda não vale), aprovada (vale na sua vigência) ou recusada.',
  vigente_de DATE COMMENT 'Primeiro dia do dado em que a versão vale (inclusive); nulo = desde sempre.',
  vigente_ate DATE COMMENT 'Dia do dado em que a versão deixa de valer (exclusive); nulo = sem fim.',
  limite_taxa DOUBLE COMMENT 'Taxa de reprovação que o negócio aceita sem abrir ação; 0 = qualquer falha pede ação; nulo = ainda não definido.',
  funcao STRING COMMENT 'Função de checagem do DQX usada pela versão (is_not_null, sql_expression...).',
  argumentos STRING COMMENT 'Argumentos da checagem em JSON; em sql_expression, a expressão que dá TRUE no dado bom.',
  motivo STRING COMMENT 'Por que a versão existe ou o que mudou em relação à versão anterior.',
  origem STRING COMMENT 'De onde veio a versão: código, pergunta do questionário, triagem ou decisão registrada.',
  aprovado_por STRING COMMENT 'Papel de quem aprovou a versão (área ou cargo; nunca o e-mail da pessoa).',
  aprovado_em DATE COMMENT 'Dia em que a versão foi aprovada ou registrada no catálogo.',
  CONSTRAINT catalogo_regras_pk PRIMARY KEY (regra_id, versao)
)
COMMENT 'Catálogo das regras de qualidade do pos_venda, com versão e vigência pela data do dado (P41). Gerado por regras/catalogo/gerar_catalogo.py a partir de catalogo_regras.yml; não edite aqui.'""",
        f"INSERT INTO {S}.catalogo_regras VALUES\n" + ",\n".join(linhas),
        f"""CREATE TABLE IF NOT EXISTS {S}.triagem_regras (
  triagem_id STRING NOT NULL COMMENT 'Identificador da triagem, por exemplo T-2026-11-30-01.',
  regra_id STRING NOT NULL COMMENT 'Regra triada (regra_id do catálogo).',
  versao INT COMMENT 'Versão triada; nula vale para todas as versões no período.',
  periodo_de DATE NOT NULL COMMENT 'Primeiro dia do dado coberto pela triagem (inclusive).',
  periodo_ate DATE NOT NULL COMMENT 'Último dia do dado coberto pela triagem (inclusive).',
  classificacao STRING NOT NULL COMMENT 'dado_ruim (corrigir na origem), regra_errada (nova versão), fora_da_vigencia (versão errada aplicada) ou esperado (falha conhecida e aceita).',
  decisao STRING COMMENT 'O que foi decidido, em uma frase de negócio.',
  acao STRING COMMENT 'Ação do plano de ação, ou a pergunta do questionário que vai gerar a nova versão.',
  dono STRING COMMENT 'Área responsável pela ação (nunca o e-mail da pessoa).',
  registrado_em TIMESTAMP COMMENT 'Quando a triagem foi registrada.'
)
COMMENT 'Triagem das falhas de regra: cada semana com falha recebe uma classificação e uma ação. Fecha o ciclo de retroalimentação (P41): regra errada vira versão nova; dado ruim vira ação no plano.'""",
        f"ALTER TABLE {S}.triagem_regras DROP CONSTRAINT IF EXISTS classificacao_valida",
        f"ALTER TABLE {S}.triagem_regras ADD CONSTRAINT classificacao_valida CHECK (classificacao IN ({classes}))",
        f"""CREATE OR REPLACE FUNCTION {S}.versao_vigente(
  regra STRING COMMENT 'regra_id do catálogo, por exemplo uf_invalida',
  dia DATE COMMENT 'data do dado (data_extracao do evento)')
RETURNS INT
COMMENT 'Versão aprovada da regra que vale para o dado do dia informado (P41); nula quando a regra não vale nesse dia.'
RETURN (SELECT max(c.versao) FROM {S}.catalogo_regras c
        WHERE c.regra_id = regra AND c.status = 'aprovada'
          AND dia >= coalesce(c.vigente_de, {INICIO}) AND dia < coalesce(c.vigente_ate, {FIM}))""",
        f"""CREATE OR REPLACE VIEW {S}.v_falhas_regras (
  dia COMMENT 'Dia do dado (data_extracao do evento).',
  fonte COMMENT 'barreira (quarentena diária da silver, só erros) ou dqx_codigo (última execução do DQX como código, erros e avisos).',
  regra_id COMMENT 'Nome estável da regra.',
  versao COMMENT 'Versão vigente no dia do dado, pelo catálogo.',
  titulo COMMENT 'A regra em linguagem de negócio.',
  tipo COMMENT 'erro (barra o evento) ou aviso (o evento entra marcado).',
  dono COMMENT 'Área dona da regra.',
  limite_taxa COMMENT 'Taxa de reprovação aceita pelo negócio; nulo = ainda não definida.',
  avaliados COMMENT 'Eventos do dia avaliados pela fonte.',
  reprovados COMMENT 'Eventos do dia reprovados pela regra; zero aparece, para mostrar que a regra foi checada (L84).',
  taxa COMMENT 'Reprovados dividido por avaliados, entre 0 e 1.',
  acima_do_limite COMMENT 'Verdadeiro quando a taxa passa do limite aceito (limite nulo conta como zero).'
)
COMMENT 'Falhas por dia, fonte, regra e versão vigente (P41). Na barreira, cada evento barrado conta só no primeiro motivo; no DQX, em todas as regras que violou. Base da triagem e da retroalimentação.'
AS WITH dias AS (SELECT {col} AS dia, count(*) AS avaliados FROM {BRONZE} GROUP BY 1),
barreira AS (SELECT {col} AS dia, motivo_rejeicao AS regra_id, count(*) AS reprovados FROM {QUARENTENA} GROUP BY 1, 2),
dqx_linhas AS (   -- só o nome de cada regra violada: erros e avisos
  SELECT {col} AS dia, concat(coalesce(transform(_errors, v -> v.name), array()), coalesce(transform(_warnings, v -> v.name), array())) AS nomes
  FROM {DQX_DESTINO}.eventos_quarentena
  UNION ALL
  SELECT {col}, coalesce(transform(_warnings, v -> v.name), array()) FROM {DQX_DESTINO}.eventos_validos),
dqx_dias AS (SELECT dia, count(*) AS avaliados FROM dqx_linhas GROUP BY 1),
dqx AS (SELECT dia, regra_id, count(*) AS reprovados FROM (SELECT dia, explode(nomes) AS regra_id FROM dqx_linhas) GROUP BY 1, 2),
base AS (
  SELECT d.dia, 'barreira' AS fonte, c.regra_id, c.versao, c.titulo, c.tipo, c.dono, c.limite_taxa, d.avaliados,
         coalesce(b.reprovados, 0) AS reprovados
  FROM dias d JOIN {S}.catalogo_regras c ON c.tipo = 'erro' AND {vig}
  LEFT JOIN barreira b ON b.dia = d.dia AND b.regra_id = c.regra_id
  UNION ALL
  SELECT d.dia, 'dqx_codigo', c.regra_id, c.versao, c.titulo, c.tipo, c.dono, c.limite_taxa, d.avaliados,
         coalesce(x.reprovados, 0)
  FROM dqx_dias d JOIN {S}.catalogo_regras c ON {vig}
  LEFT JOIN dqx x ON x.dia = d.dia AND x.regra_id = c.regra_id)
SELECT dia, fonte, regra_id, versao, titulo, tipo, dono, limite_taxa, avaliados, reprovados,
       reprovados / avaliados AS taxa, reprovados / avaliados > coalesce(limite_taxa, 0) AS acima_do_limite
FROM base""",
        f"""CREATE OR REPLACE VIEW {S}.v_triagem_pendente (
  semana COMMENT 'Segunda-feira da semana do dado.',
  fonte COMMENT 'barreira ou dqx_codigo.',
  regra_id COMMENT 'Nome estável da regra.',
  versao COMMENT 'Versão vigente no dado da semana.',
  titulo COMMENT 'A regra em linguagem de negócio.',
  tipo COMMENT 'erro (barra o evento) ou aviso (o evento entra marcado).',
  dono COMMENT 'Área que precisa triar.',
  avaliados COMMENT 'Eventos da semana avaliados pela fonte.',
  reprovados COMMENT 'Eventos da semana reprovados pela regra.',
  taxa COMMENT 'Reprovados dividido por avaliados na semana.',
  limite_taxa COMMENT 'Taxa aceita pelo negócio; nulo = ainda não definida (pergunta B3 do questionário).',
  dias_com_falha COMMENT 'Dias da semana com ao menos uma reprovação.'
)
COMMENT 'O que falta triar (P41): semanas em que a regra passou do limite aceito e nenhuma triagem cobre o período. Cada linha pede uma classificação em triagem_regras.'
AS SELECT date_trunc('WEEK', f.dia)::DATE AS semana, f.fonte, f.regra_id, f.versao, f.titulo, f.tipo, f.dono,
       sum(f.avaliados) AS avaliados, sum(f.reprovados) AS reprovados, sum(f.reprovados) / sum(f.avaliados) AS taxa,
       max(f.limite_taxa) AS limite_taxa, count_if(f.reprovados > 0) AS dias_com_falha
FROM {S}.v_falhas_regras f
WHERE NOT EXISTS (SELECT 1 FROM {S}.triagem_regras t
                  WHERE t.regra_id = f.regra_id AND (t.versao IS NULL OR t.versao = f.versao)
                    AND f.dia BETWEEN t.periodo_de AND t.periodo_ate)
GROUP BY ALL
HAVING sum(f.reprovados) / sum(f.avaliados) > coalesce(max(f.limite_taxa), 0)""",
        f"""CREATE OR REPLACE VIEW {S}.v_mudancas_regras (
  regra_id COMMENT 'Nome estável da regra.',
  versao COMMENT 'Versão que começou a valer.',
  mudou_em COMMENT 'Primeiro dia do dado julgado pela versão nova: a marca no eixo do tempo dos painéis.',
  titulo COMMENT 'A regra em linguagem de negócio.',
  motivo COMMENT 'O que mudou em relação à versão anterior.',
  origem COMMENT 'De onde veio a mudança: pergunta do questionário, triagem ou decisão.',
  aprovado_por COMMENT 'Papel de quem aprovou a versão.',
  aprovado_em COMMENT 'Dia da aprovação.'
)
COMMENT 'Mudanças de regra no tempo (P41): uma linha por versão com início de vigência. Os painéis marcam essas datas para explicar saltos na taxa de reprovação.'
AS SELECT regra_id, versao, vigente_de AS mudou_em, titulo, motivo, origem, aprovado_por, aprovado_em
FROM {S}.catalogo_regras WHERE status = 'aprovada' AND vigente_de IS NOT NULL""",
        f"""CREATE OR REPLACE VIEW {S}.v_retroalimentacao (
  regra_id COMMENT 'Nome estável da regra.',
  titulo COMMENT 'A regra em linguagem de negócio.',
  tipo COMMENT 'erro (barra o evento) ou aviso (o evento entra marcado).',
  dono COMMENT 'Área dona da regra.',
  versoes COMMENT 'Versões aprovadas da regra até hoje.',
  versao_atual COMMENT 'Versão aprovada mais recente.',
  reprovados COMMENT 'Reprovações em todas as fontes e versões.',
  dias_com_falha COMMENT 'Dias do dado com ao menos uma reprovação.',
  semanas_pendentes COMMENT 'Semanas acima do limite que ainda não foram triadas.',
  triagens COMMENT 'Triagens registradas para a regra.',
  dado_ruim COMMENT 'Triagens que apontaram dado ruim (ação na origem).',
  regra_errada COMMENT 'Triagens que apontaram a regra errada (falso positivo; gera versão nova).',
  fora_da_vigencia COMMENT 'Triagens em que a versão aplicada não era a do período.',
  esperado COMMENT 'Triagens de falha conhecida e aceita.',
  taxa_falso_positivo COMMENT 'regra_errada dividido por triagens: quanto a regra acusa sem razão.',
  ultima_triagem COMMENT 'Quando a regra foi triada pela última vez.'
)
COMMENT 'Indicadores da retroalimentação por regra (P41): quanto falha, quanto falta triar, o que a triagem concluiu e a taxa de falso positivo. Uma regra com falso positivo alto volta para o questionário.'
AS WITH c AS (SELECT regra_id, max_by(titulo, versao) AS titulo, max_by(tipo, versao) AS tipo, max_by(dono, versao) AS dono,
                     count(*) AS versoes, max(versao) AS versao_atual
              FROM {S}.catalogo_regras WHERE status = 'aprovada' GROUP BY 1),
f AS (SELECT regra_id, sum(reprovados) AS reprovados, count(DISTINCT CASE WHEN reprovados > 0 THEN dia END) AS dias_com_falha
      FROM {S}.v_falhas_regras GROUP BY 1),
p AS (SELECT regra_id, count(*) AS semanas_pendentes FROM {S}.v_triagem_pendente GROUP BY 1),
t AS (SELECT regra_id, count(*) AS triagens, count_if(classificacao = 'dado_ruim') AS dado_ruim,
             count_if(classificacao = 'regra_errada') AS regra_errada, count_if(classificacao = 'fora_da_vigencia') AS fora_da_vigencia,
             count_if(classificacao = 'esperado') AS esperado, max(registrado_em) AS ultima_triagem
      FROM {S}.triagem_regras GROUP BY 1)
SELECT c.regra_id, c.titulo, c.tipo, c.dono, c.versoes, c.versao_atual, coalesce(f.reprovados, 0) AS reprovados,
       coalesce(f.dias_com_falha, 0) AS dias_com_falha, coalesce(p.semanas_pendentes, 0) AS semanas_pendentes,
       coalesce(t.triagens, 0) AS triagens, coalesce(t.dado_ruim, 0) AS dado_ruim, coalesce(t.regra_errada, 0) AS regra_errada,
       coalesce(t.fora_da_vigencia, 0) AS fora_da_vigencia, coalesce(t.esperado, 0) AS esperado,
       t.regra_errada / t.triagens AS taxa_falso_positivo, t.ultima_triagem
FROM c LEFT JOIN f USING (regra_id) LEFT JOIN p USING (regra_id) LEFT JOIN t USING (regra_id)""",
    ]


# ------------------------------------------------------------------------------------------------ comandos
def cmd_validar():
    cat = carregar()
    erros = validar_catalogo(cat, nomes_da_barreira())
    esperado = yaml_dqx(cat, "catalogo_regras.yml")
    if DQX_YAML.read_text(encoding="utf-8") != esperado:
        erros.append(f"{DQX_YAML.relative_to(RAIZ)} difere do catálogo: rode `gerar_catalogo.py gerar`")
    ens = carregar(sobrepor=ENSAIO)
    erros += [f"ensaio: {x}" for x in validar_catalogo(ens, nomes_da_barreira())]
    if erros:
        sys.exit("catálogo inválido:\n  - " + "\n  - ".join(erros))
    n = sum(len(r["versoes"]) for r in cat["regras"])
    print(f"catálogo válido: {len(cat['regras'])} regras, {n} versões; YAML do DQX em dia; ensaio válido")


def cmd_gerar():
    cat = carregar()
    erros = validar_catalogo(cat, nomes_da_barreira())
    if erros:
        sys.exit("catálogo inválido:\n  - " + "\n  - ".join(erros))
    DQX_YAML.write_text(yaml_dqx(cat, "catalogo_regras.yml"), encoding="utf-8")
    DQX_ENSAIO.parent.mkdir(exist_ok=True)
    DQX_ENSAIO.write_text(yaml_dqx(carregar(sobrepor=ENSAIO), "ENSAIO: catalogo_regras.yml + ensaio/vigencia_periodicidade.yml"),
                          encoding="utf-8")
    SQL.write_text("-- Gerado por regras/catalogo/gerar_catalogo.py a partir de catalogo_regras.yml. Não edite.\n\n"
                   + ";\n\n".join(ddl(cat)) + ";\n", encoding="utf-8")
    for p in (DQX_YAML, DQX_ENSAIO, SQL):
        print("escrito", p.relative_to(RAIZ))


def cmd_aplicar():
    cmd_gerar()
    try:
        falhas = executar_lista(ddl(carregar()), rotulo=lambda s: " ".join(s.split()[:5])[:90])
    except CotaEsgotada as e:
        sys.exit(f"warehouse sem cota: {e}")
    if falhas:
        sys.exit(f"{falhas} comando(s) falharam")


def linhas(sql):
    estado, erro, ls = executar(sql)
    if estado != "SUCCEEDED":
        raise RuntimeError(f"{sql[:100]}... -> {estado}: {erro[:300]}")
    return ls


def cmd_conferir():
    cat = carregar()
    ok = True

    def check(nome, cond, detalhe):
        nonlocal ok
        ok &= bool(cond)
        print(f"{'ok   ' if cond else 'FALHA'} {nome}: {detalhe}")

    tab = {(r["regra_id"], int(r["versao"]), r["status"], r["vigente_de"], r["vigente_ate"])
           for r in linhas(f"SELECT regra_id, versao, status, vigente_de, vigente_ate FROM {S}.catalogo_regras")}
    yml = {(r["regra_id"], v["versao"], v["status"], v["vigente_de"].isoformat() if v["vigente_de"] else None,
            v["vigente_ate"].isoformat() if v["vigente_ate"] else None) for r in cat["regras"] for v in r["versoes"]}
    check("catálogo no Unity Catalog = YAML", tab == yml, f"{len(tab)} versões na tabela, {len(yml)} no YAML")
    buracos = linhas(f"""WITH dias AS (SELECT DISTINCT data_extracao AS dia FROM {BRONZE}),
r AS (SELECT DISTINCT regra_id FROM {S}.catalogo_regras)
SELECT d.dia, r.regra_id, count(c.versao) AS n FROM dias d CROSS JOIN r
LEFT JOIN {S}.catalogo_regras c ON c.regra_id = r.regra_id AND c.status = 'aprovada'
  AND d.dia >= coalesce(c.vigente_de, {INICIO}) AND d.dia < coalesce(c.vigente_ate, {FIM})
GROUP BY ALL HAVING count(c.versao) <> 1""")
    check("uma versão aprovada por regra em cada dia da base", not buracos, f"{len(buracos)} dia × regra fora disso")
    fora = linhas(f"""SELECT DISTINCT motivo_rejeicao FROM {QUARENTENA}
WHERE motivo_rejeicao NOT IN (SELECT regra_id FROM {S}.catalogo_regras WHERE tipo = 'erro')""")
    check("todo motivo da quarentena é regra de erro do catálogo", not fora, f"fora: {[r['motivo_rejeicao'] for r in fora]}")
    soma = linhas(f"""SELECT (SELECT sum(reprovados) FROM {S}.v_falhas_regras WHERE fonte = 'barreira') AS visao,
       (SELECT count(*) FROM {QUARENTENA}) AS quarentena""")[0]
    check("falhas da barreira na visão = linhas da quarentena", soma["visao"] == soma["quarentena"],
          f"{soma['visao']} = {soma['quarentena']}")
    dqx = linhas(f"""SELECT (SELECT sum(avaliados) FROM (SELECT DISTINCT dia, avaliados FROM {S}.v_falhas_regras WHERE fonte = 'dqx_codigo')) AS visao,
       (SELECT count(*) FROM {DQX_DESTINO}.eventos_quarentena) + (SELECT count(*) FROM {DQX_DESTINO}.eventos_validos) AS tabelas""")[0]
    check("linhas do DQX na visão = válidos + quarentena", dqx["visao"] == dqx["tabelas"], f"{dqx['visao']} = {dqx['tabelas']}")
    v = linhas(f"SELECT {S}.versao_vigente('uf_invalida', DATE'2026-06-01') AS v, {S}.versao_vigente('regra_que_nao_existe', current_date()) AS nada")[0]
    check("versao_vigente responde", v["v"] == "1" and v["nada"] is None, f"uf_invalida em 01/06/2026 = {v['v']}; regra inexistente = {v['nada']}")
    for nome in ("v_falhas_regras", "v_triagem_pendente", "v_mudancas_regras", "v_retroalimentacao", "triagem_regras"):
        n = linhas(f"SELECT count(*) AS n FROM {S}.{nome}")[0]["n"]
        check(f"{nome} responde", True, f"{n} linhas")
    if not ok:
        sys.exit(1)


def cmd_ensaio(run_id):
    """Compara a execução de ensaio do DQX (modo=ensaio) com a mesma conta feita em SQL, regra a regra e versão a versão."""
    run = json.loads(subprocess.run(["databricks", "jobs", "get-run", str(run_id), "--profile", PERFIL, "-o", "json"],
                                    capture_output=True, text=True, check=True).stdout)
    tarefa = run["tasks"][0]["run_id"]
    saida = json.loads(subprocess.run(["databricks", "jobs", "get-run-output", str(tarefa), "--profile", PERFIL, "-o", "json"],
                                      capture_output=True, text=True, check=True).stdout)
    dqx = json.loads(saida["notebook_output"]["result"])
    cat = carregar(sobrepor=ENSAIO) if "ensaio" in dqx["arquivo_checks"] else carregar()
    col = cat["padrao"]["coluna_data"]
    filtro = dqx["filtro"] or "TRUE"
    colunas, por_chave = [], {}
    for c in checks_dqx(cat):
        fn, args = c["check"]["function"], c["check"]["arguments"]
        falha = f"NOT ({args['expression']})" if fn == "sql_expression" else f"{args['column']} IS NULL" if fn == "is_not_null" else None
        if falha is None:
            sys.exit(f"sem verdade em SQL para a função {fn}")
        janela = c.get("filter") or "TRUE"
        i = len(colunas)
        colunas += [f"count_if(({janela}) AND {falha}) AS r{i}", f"count_if({janela}) AS a{i}"]
        por_chave[(c["name"], c["user_metadata"]["versao"])] = (i, c["criticality"], falha)
    erros_sql = " OR ".join(f"({c.get('filter') or 'TRUE'}) AND {f}" for (n, v), (i, crit, f) in por_chave.items()
                            for c in [next(x for x in checks_dqx(cat) if x["name"] == n and x["user_metadata"]["versao"] == v)]
                            if crit == "error")
    verdade = linhas(f"SELECT count(*) AS linhas, count_if({erros_sql}) AS linhas_com_erro, {', '.join(colunas)} "
                     f"FROM {BRONZE} WHERE {filtro}")[0]
    barreira = linhas(f"SELECT count(*) AS n FROM {QUARENTENA} WHERE {filtro}")[0]["n"]
    ok = True
    print(f"janela: {filtro}  ({col})")
    print(f"{'linhas':<46} DQX {dqx['linhas']:>8}  SQL {verdade['linhas']:>8}")
    print(f"{'linhas com erro (= quarentena da barreira ' + barreira + ')':<46} DQX {dqx['linhas_com_erro']:>8}  SQL {verdade['linhas_com_erro']:>8}")
    ok &= int(dqx["linhas"]) == int(verdade["linhas"]) and int(dqx["linhas_com_erro"]) == int(verdade["linhas_com_erro"]) == int(barreira)
    for r in dqx["regras"]:
        i, _, _ = por_chave[(r["regra"], r["versao"])]
        rs, av = int(verdade[f"r{i}"]), int(verdade[f"a{i}"])
        bate = int(r["reprovadas"]) == rs and int(r["avaliadas"]) == av
        ok &= bate
        print(f"{'ok   ' if bate else 'FALHA'} {r['regra']:<34} v{r['versao']}  reprovadas DQX {r['reprovadas']:>5} SQL {rs:>5}"
              f"  avaliadas DQX {r['avaliadas']:>6} SQL {av:>6}  {r['filtro'] or '(sempre)'}")
    ok &= len(dqx["regras"]) == len(por_chave)
    if not ok:
        sys.exit("ensaio NÃO bate com a verdade em SQL")
    print(f"ensaio ok: {len(por_chave)} checagens, DQX = SQL em todas")


# ------------------------------------------------------------------------------------------------ testes (sem rede)
def cmd_testar():
    import copy
    base = carregar()
    falhas = 0

    def caso(nome, cond):
        nonlocal falhas
        falhas += not cond
        print(f"{'ok   ' if cond else 'FALHA'} {nome}")

    D = dt.date
    caso("predicado sem limites = vazio", predicado("d", None, None) == "")
    caso("predicado com início", predicado("d", D(2027, 1, 5), None) == "d >= DATE'2027-01-05'")
    caso("predicado com fim exclusivo", predicado("d", None, D(2027, 1, 5)) == "d < DATE'2027-01-05'")
    caso("catálogo real válido e igual à barreira", validar_catalogo(base, nomes_da_barreira()) == [])

    ens = carregar(sobrepor=ENSAIO)
    per = [c for c in checks_dqx(ens) if c["name"] == "periodicidade_fora_do_dominio"]
    caso("ensaio: periodicidade com 2 versões e filtros complementares",
         [c.get("filter") for c in per] == ["data_extracao < DATE'2027-01-05'", "data_extracao >= DATE'2027-01-05'"])
    caso("ensaio: as outras 13 regras sem filtro", all("filter" not in c for c in checks_dqx(ens) if c["name"] != "periodicidade_fora_do_dominio"))
    caso("ensaio: user_metadata com versão em texto", [c["user_metadata"]["versao"] for c in per] == ["1", "2"])

    def com(alterar):
        c = copy.deepcopy(ens)
        alterar(next(r for r in c["regras"] if r["regra_id"] == "periodicidade_fora_do_dominio")["versoes"])
        return validar_catalogo(c)

    caso("reprova sobreposição de versões", any("sem buraco" in e for e in com(lambda vs: vs[1].update(vigente_de=D(2027, 1, 4)))))
    caso("reprova buraco entre versões", any("sem buraco" in e for e in com(lambda vs: vs[1].update(vigente_de=D(2027, 1, 6)))))
    caso("reprova versão aberta antes da seguinte", any("sem buraco" in e for e in com(lambda vs: vs[0].update(vigente_ate=None))))
    caso("reprova versão nova sem motivo", any("motivo" in e for e in com(lambda vs: vs[1].update(motivo=None))))
    caso("reprova aprovada sem aprovado_em", any("aprovado_em" in e for e in com(lambda vs: vs[1].update(aprovado_em=None))))
    caso("proposta não entra no DQX", (lambda c: (next(r for r in c["regras"] if r["regra_id"] == "periodicidade_fora_do_dominio")["versoes"][1].update(status="proposta"),
                                                  sum(1 for x in checks_dqx(c) if x["name"] == "periodicidade_fora_do_dominio"))[1])(copy.deepcopy(ens)) == 1)
    caso("reprova limite_taxa fora de 0 a 1", any("limite_taxa" in e for e in com(lambda vs: vs[0].update(limite_taxa=1.5))))
    caso("detecta regra de erro que a barreira não tem",
         any("só no catálogo" in e for e in validar_catalogo(base, nomes_da_barreira() - {"uf_invalida"})))
    caso("YAML do DQX gerado = arquivo em dqx_codigo", DQX_YAML.read_text(encoding="utf-8") == yaml_dqx(base, "catalogo_regras.yml"))
    antes = [{k: c[k] for k in ("name", "criticality", "check")} for c in checks_dqx(base)]
    caso("produção: 14 checagens, nenhuma com filtro", len(antes) == 14 and all("filter" not in c for c in checks_dqx(base)))
    if falhas:
        sys.exit(f"{falhas} teste(s) falharam")
    print("todos os testes passaram")


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else "validar"
    {"validar": cmd_validar, "testar": cmd_testar, "gerar": cmd_gerar, "aplicar": cmd_aplicar, "conferir": cmd_conferir,
     "ensaio": lambda: cmd_ensaio(sys.argv[2])}[acao]()
