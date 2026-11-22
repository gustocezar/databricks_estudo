#!/usr/bin/env python3
"""Gera ontologia.sql: a camada de ontologia (pos_venda.ontologia) e as metric views financeiras.

  python3 gerar_ontologia_sql.py     -> grava ontologia.sql (rodar com aplicar_sql.py ontologia.sql)

Conteúdo:
  - entidades de negócio como views com descrição em cada coluna (sem identificadores pessoais);
  - tabelas `entidades`, `relacoes` e `glossario` (o glossário vem das Pages de ontologia.py);
  - 4 metric views (carteira em aberto, recuperação, safra de entrada e qualidade) com sinônimos para a Genie.
"""
import json
import pathlib

import descricoes_colunas as DC
import ontologia as O

AQUI = pathlib.Path(__file__).resolve().parent
C = O.CAT
S = f"{C}.ontologia"


def q(t):
    return "'" + str(t).replace("\\", "\\\\").replace("'", "\\'") + "'"


def view(nome, comentario, colunas, select):
    """colunas: lista de (nome, descrição|None). A descrição vem do dicionário quando None."""
    cols = ",\n  ".join(f"{c} COMMENT {q(d or DC.D.get(c) or c)}" for c, d in colunas)
    return f"CREATE OR REPLACE VIEW {S}.{nome} (\n  {cols}\n)\nCOMMENT {q(comentario)}\nAS\n{select.strip()}"


SQL = [f"CREATE SCHEMA IF NOT EXISTS {S} COMMENT {q('Pós-venda: camada de ontologia — entidades de negócio, relações, glossário e métricas governadas (metric views). Sem identificadores pessoais.')}"]

# ------------------------------------------------------------------------------------------------ entidades
SQL.append(view("cliente", "Entidade Cliente (segurado pagador), sem identificadores pessoais: use cliente_sk para ligar.",
                [("cliente_sk", None), ("faixa_etaria", "Faixa etária do cliente."),
                 ("uf", "UF do cliente."), ("cpf_valido", "Verdadeiro se o dígito verificador do CPF confere."),
                 ("data_cadastro", "Data de cadastro do cliente.")],
                f"SELECT cliente_sk, cliente_faixa_etaria, cliente_uf, cliente_cpf_valido, cliente_data_cadastro FROM {C}.gold.dim_cliente"))
SQL.append(view("apolice", "Entidade Apólice de seguro de vida (contrato): status, vigência, capital, prêmio, coberturas e endossos.",
                [(c, None) for c in ["apolice_sk", "numero_apolice", "status_apolice", "data_emissao", "data_inicio_vigencia",
                                      "data_fim_vigencia_atual", "dia_vencimento", "capital_segurado_principal", "capital_segurado_total",
                                      "valor_premio_periodico", "qtd_coberturas", "qtd_endossos", "tipo_ultimo_endosso",
                                      "data_ultimo_endosso", "qtd_beneficiarios"]],
                f"SELECT apolice_sk, numero_apolice, status_apolice, data_emissao, data_inicio_vigencia, data_fim_vigencia_atual, dia_vencimento, "
                f"capital_segurado_principal, capital_segurado_total, valor_premio_periodico, qtd_coberturas, qtd_endossos, tipo_ultimo_endosso, "
                f"data_ultimo_endosso, qtd_beneficiarios FROM {C}.gold.dim_apolice"))
SQL.append(view("produto", "Entidade Produto de seguro de vida (8 produtos) e cobertura principal.",
                [(c, None) for c in ["produto_sk", "produto_codigo", "produto_nome", "categoria_produto", "cobertura_principal_nome"]],
                f"SELECT produto_sk, produto_codigo, produto_nome, categoria_produto, cobertura_principal_nome FROM {C}.gold.dim_produto"))
SQL.append(view("apolice_cobertura", "Relação Apólice tem Cobertura (N:N), com papel PRINCIPAL/ADICIONAL e capital.",
                [("apolice_sk", None), ("cobertura_sk", None), ("cobertura_nome", None), ("grupo_cobertura", None),
                 ("papel_cobertura", None), ("capital_segurado_cobertura", None)],
                f"SELECT b.apolice_sk, b.cobertura_sk, c.cobertura_nome, c.grupo_cobertura, b.papel_cobertura, b.capital_segurado_cobertura "
                f"FROM {C}.gold.bridge_apolice_cobertura b JOIN {C}.gold.dim_cobertura c ON c.cobertura_sk = b.cobertura_sk"))
SQL.append(view("corretor", "Entidade Corretor (sem nome e documento): SUSEP, regional, comissão e status. NAO_INFORMADO = venda sem corretor.",
                [(c, None) for c in ["corretor_sk", "corretor_id", "corretor_tipo_pessoa", "corretor_registro_susep", "corretor_regional",
                                      "corretor_comissao_pct", "corretor_status"]],
                f"SELECT corretor_sk, corretor_id, corretor_tipo_pessoa, corretor_registro_susep, corretor_regional, corretor_comissao_pct, "
                f"corretor_status FROM {C}.gold.dim_corretor"))
SQL.append(view("ponto_venda", "Entidade Ponto de venda e canal de venda.",
                [(c, None) for c in ["ponto_venda_sk", "ponto_venda_codigo", "ponto_venda_nome", "ponto_venda_tipo", "canal_venda",
                                      "ponto_venda_cidade", "ponto_venda_uf", "ponto_venda_regional"]],
                f"SELECT ponto_venda_sk, ponto_venda_codigo, ponto_venda_nome, ponto_venda_tipo, canal_venda, ponto_venda_cidade, "
                f"ponto_venda_uf, ponto_venda_regional FROM {C}.gold.dim_ponto_venda"))
SQL.append(view("pendencia",
                "Entidade Pendência (1 linha por pendência, estado atual): entrada, status, baixa e safra. Base da taxa de recuperação.",
                [("pendencia_id", None), ("numero_apolice", None), ("numero_parcela", None),
                 ("produto_codigo", None), ("produto_nome", None), ("canal_venda", None), ("corretor_id", None),
                 ("forma_pagamento", None), ("periodicidade_pagamento", None), ("motivo_pendencia", None),
                 ("data_vencimento", None), ("data_entrada", "Dia em que a pendência entrou (dia seguinte ao vencimento)."),
                 ("safra_entrada", "Mês de entrada da pendência (safra), para a taxa de recuperação."),
                 ("status_cobranca", "Status atual da cobrança."), ("paga", "Verdadeiro se a pendência já foi paga (status PAGA)."),
                 ("data_baixa", None), ("valor_pago", None), ("dias_ate_baixa", "Dias entre o vencimento e a baixa (só pagas)."),
                 ("valor_parcela", None), ("data_ultimo_evento", "Dia do último evento recebido da pendência.")],
                f"""SELECT pendencia_id, numero_apolice, numero_parcela, produto_codigo, produto_nome, canal_venda, corretor_id,
       forma_pagamento, periodicidade_pagamento, motivo_pendencia, data_vencimento,
       date_add(data_vencimento, 1) AS data_entrada, CAST(date_trunc('MONTH', date_add(data_vencimento, 1)) AS DATE) AS safra_entrada,
       status_cobranca, status_cobranca = 'PAGA' AS paga, data_baixa, valor_pago,
       CASE WHEN status_cobranca = 'PAGA' THEN datediff(data_baixa, data_vencimento) END AS dias_ate_baixa,
       valor_parcela, data_extracao AS data_ultimo_evento
FROM {C}.silver.pendencia_atual"""))
SQL.append(view("pagamento", "Entidade Pagamento (baixa): 1 linha por pendência paga, eventos BAIXA deduplicados. Base do valor recuperado.",
                [("pendencia_id", None), ("numero_apolice", None), ("produto_codigo", None), ("produto_nome", None),
                 ("categoria_produto", None), ("canal_venda", None), ("forma_pagamento", None), ("motivo_pendencia", None),
                 ("data_vencimento", None), ("data_baixa", None), ("dias_atraso_na_baixa", "Dias de atraso no dia do pagamento."),
                 ("faixa_atraso_na_baixa", "Faixa de atraso no dia do pagamento."), ("valor_parcela", None), ("valor_multa", None),
                 ("valor_juros", None), ("valor_pago", None)],
                f"""SELECT pendencia_id, numero_apolice, produto_codigo, produto_nome, categoria_produto, canal_venda, forma_pagamento,
       motivo_pendencia, data_vencimento, data_baixa, dias_atraso, faixa_atraso, valor_parcela, valor_multa, valor_juros, valor_pago
FROM {C}.silver.pendencia_evento
WHERE tipo_evento = 'BAIXA'
QUALIFY row_number() OVER (PARTITION BY pendencia_id ORDER BY _silver_ts) = 1"""))
SQL.append(view("evento_cobranca", "Entidade Evento de cobrança (NOVA, ATUALIZACAO, BAIXA) apto, deduplicado por pendência, dia e tipo.",
                [(c, None) for c in ["pendencia_id", "data_extracao", "tipo_evento", "status_cobranca", "dias_atraso", "faixa_atraso",
                                      "valor_total_pendente", "canal_ultimo_contato", "tentativas_cobranca"]],
                f"""SELECT pendencia_id, data_extracao, tipo_evento, status_cobranca, dias_atraso, faixa_atraso, valor_total_pendente,
       canal_ultimo_contato, tentativas_cobranca
FROM {C}.silver.pendencia_evento
QUALIFY row_number() OVER (PARTITION BY pendencia_id, data_extracao, tipo_evento ORDER BY _silver_ts) = 1"""))
SQL.append(view("posicao_carteira",
                "Posição diária da carteira em aberto (fato snapshot com rótulos legíveis). SALDO É SEMIADITIVO: some só dentro de um mesmo dia.",
                [("data_referencia", "Dia da foto da carteira."), ("data_referencia_sk", None),
                 ("foto_mais_recente", "Verdadeiro na foto mais recente disponível."),
                 ("fim_de_mes", "Verdadeiro se o dia da foto é o último dia do mês."),
                 ("pendencia_id", None), ("cliente_sk", None), ("apolice_sk", None), ("status_cobranca", None), ("fase_cobranca", None),
                 ("faixa_atraso", "Faixa de atraso no dia da foto."), ("ordem_faixa", None), ("produto_nome", None), ("categoria_produto", None),
                 ("canal_venda", None), ("ponto_venda_regional", None), ("ponto_venda_uf", None),
                 ("forma_pagamento", "Forma de pagamento (NAO_CADASTRADA quando a forma não existe no catálogo)."),
                 ("grupo_forma_pagamento", None), ("motivo_pendencia", None), ("grupo_motivo", None), ("periodicidade_pagamento", None),
                 ("status_apolice", None), ("canal_ultimo_contato", None), ("dias_atraso", DC.descricao("gold.fact_pagamento_pendente_snapshot", "dias_atraso")),
                 ("tentativas_cobranca", None), ("valor_parcela", None), ("valor_multa", None), ("valor_juros", None),
                 ("valor_total_pendente", None)],
                f"""SELECT to_date(CAST(f.data_referencia_sk AS STRING), 'yyyyMMdd') AS data_referencia, f.data_referencia_sk,
       f.data_referencia_sk = (SELECT max(data_referencia_sk) FROM {C}.gold.fact_pagamento_pendente_snapshot) AS foto_mais_recente,
       coalesce(d.ultimo_dia_mes, false) AS fim_de_mes,
       f.pendencia_id, f.cliente_sk, f.apolice_sk, s.status_cobranca, s.fase_cobranca, fa.faixa_atraso, fa.ordem_faixa,
       p.produto_nome, p.categoria_produto, pv.canal_venda, pv.ponto_venda_regional, pv.ponto_venda_uf,
       coalesce(fp.forma_pagamento, 'NAO_CADASTRADA') AS forma_pagamento, coalesce(fp.grupo_forma_pagamento, 'NAO_CADASTRADA') AS grupo_forma_pagamento,
       m.motivo_pendencia, m.grupo_motivo, pe.periodicidade_pagamento, a.status_apolice, f.canal_ultimo_contato,
       f.dias_atraso, f.tentativas_cobranca, f.valor_parcela, f.valor_multa, f.valor_juros, f.valor_total_pendente
FROM {C}.gold.fact_pagamento_pendente_snapshot f
LEFT JOIN {C}.gold.dim_data d ON d.data_sk = f.data_referencia_sk
LEFT JOIN {C}.gold.dim_status_cobranca s ON s.status_cobranca_sk = f.status_cobranca_sk
LEFT JOIN {C}.gold.dim_faixa_atraso fa ON fa.faixa_atraso_sk = f.faixa_atraso_sk
LEFT JOIN {C}.gold.dim_produto p ON p.produto_sk = f.produto_sk
LEFT JOIN {C}.gold.dim_ponto_venda pv ON pv.ponto_venda_sk = f.ponto_venda_sk
LEFT JOIN {C}.gold.dim_forma_pagamento fp ON fp.forma_pagamento_sk = f.forma_pagamento_sk
LEFT JOIN {C}.gold.dim_motivo_pendencia m ON m.motivo_pendencia_sk = f.motivo_pendencia_sk
LEFT JOIN {C}.gold.dim_periodicidade pe ON pe.periodicidade_sk = f.periodicidade_sk
LEFT JOIN {C}.gold.dim_apolice a ON a.apolice_sk = f.apolice_sk"""))

# ------------------------------------------------------------------------------------------------ entidades, relações, glossário
ENTIDADES = [
    ("Cliente", "cliente", "cliente_sk", "Segurado pagador (sem identificadores pessoais).", "gold.dim_cliente"),
    ("Apólice", "apolice", "apolice_sk", "Contrato de seguro de vida.", "gold.dim_apolice"),
    ("Produto", "produto", "produto_sk", "Produto de seguro de vida.", "gold.dim_produto"),
    ("Cobertura", "apolice_cobertura", "apolice_sk, cobertura_sk", "Coberturas de cada apólice.", "gold.bridge_apolice_cobertura"),
    ("Corretor", "corretor", "corretor_sk", "Corretor que vendeu a apólice.", "gold.dim_corretor"),
    ("Ponto de venda", "ponto_venda", "ponto_venda_sk", "Ponto e canal de venda.", "gold.dim_ponto_venda"),
    ("Pendência", "pendencia", "pendencia_id", "Parcela não paga no vencimento (estado atual).", "silver.pendencia_atual"),
    ("Evento de cobrança", "evento_cobranca", "pendencia_id, data_extracao, tipo_evento", "NOVA, ATUALIZACAO ou BAIXA.", "silver.pendencia_evento"),
    ("Pagamento", "pagamento", "pendencia_id", "Baixa da pendência.", "silver.pendencia_evento (BAIXA)"),
    ("Posição da carteira", "posicao_carteira", "data_referencia_sk, pendencia_id", "Foto diária das pendências em aberto.",
     "gold.fact_pagamento_pendente_snapshot"),
]
RELACOES = [
    ("Cliente", "possui", "Apólice", "1:N", "cliente_sk", "Um cliente pode ter várias apólices."),
    ("Apólice", "é do produto", "Produto", "N:1", "produto_codigo / produto_sk", "Cada apólice é de um produto."),
    ("Apólice", "tem cobertura", "Cobertura", "N:N", "apolice_sk + cobertura_sk", "Coberturas principal e adicionais da apólice."),
    ("Apólice", "foi vendida por", "Corretor", "N:0..1", "corretor_id / corretor_sk", "Vendas DIGITAL e TELEVENDAS não têm corretor."),
    ("Apólice", "foi vendida em", "Ponto de venda", "N:1", "ponto_venda_codigo / ponto_venda_sk", "Ponto e canal de venda."),
    ("Apólice", "gera", "Pendência", "1:N", "numero_apolice", "Cada parcela não paga no vencimento vira uma pendência."),
    ("Pendência", "tem", "Evento de cobrança", "1:N", "pendencia_id", "NOVA na entrada, ATUALIZACAO nas mudanças de fase, BAIXA no pagamento."),
    ("Pendência", "é quitada por", "Pagamento", "1:0..1", "pendencia_id", "Nem toda pendência é paga."),
    ("Pendência", "aparece na", "Posição da carteira", "1:N", "pendencia_id", "Uma linha por dia enquanto a pendência está em aberto."),
    ("Evento barrado", "é versão não apta de", "Evento de cobrança", "N:1", "pendencia_id", "Eventos da quarentena não entram na silver."),
]
SQL.append(f"CREATE OR REPLACE TABLE {S}.entidades (entidade STRING COMMENT 'Nome da entidade de negócio', "
           f"objeto STRING COMMENT 'View da entidade em pos_venda.ontologia', chave STRING COMMENT 'Chave da entidade', "
           f"descricao STRING COMMENT 'Definição curta', origem STRING COMMENT 'Tabela de origem') "
           f"COMMENT 'Catálogo das entidades da ontologia do Pós-venda.'")
SQL.append(f"INSERT INTO {S}.entidades VALUES " + ", ".join(f"({q(a)}, {q(S + '.' + b)}, {q(c)}, {q(d)}, {q(C + '.' + e)})"
                                                            for a, b, c, d, e in ENTIDADES))
SQL.append(f"CREATE OR REPLACE TABLE {S}.relacoes (sujeito STRING COMMENT 'Entidade de origem', predicado STRING COMMENT 'Relação', "
           f"objeto STRING COMMENT 'Entidade de destino', cardinalidade STRING COMMENT 'Cardinalidade', chave STRING COMMENT 'Chave da ligação', "
           f"descricao STRING COMMENT 'Explicação') COMMENT 'Relações entre as entidades do Pós-venda (triplas sujeito-predicado-objeto).'")
SQL.append(f"INSERT INTO {S}.relacoes VALUES " + ", ".join("(" + ", ".join(q(x) for x in r) + ")" for r in RELACOES))
SQL.append(f"CREATE OR REPLACE TABLE {S}.glossario (termo STRING COMMENT 'Termo de negócio (título da Page)', "
           f"subdominio STRING COMMENT 'Subdomínio do Discover', definicao STRING COMMENT 'Definição curta', "
           f"sinonimos ARRAY<STRING> COMMENT 'Sinônimos usados pelas pessoas') "
           f"COMMENT 'Glossário do Pós-venda: mesmo conteúdo das Pages do Discover (domínio Pós-venda).'")
SQL.append(f"INSERT INTO {S}.glossario VALUES " + ", ".join(
    f"({q(p['titulo'])}, {q(O.SUB[p['sub']]['nome'])}, {q(p['descricao'])}, array({', '.join(q(s) for s in p['sinonimos'])}))"
    for p in O.PAGES))


# ------------------------------------------------------------------------------------------------ metric views
DESCR_COMUM = {
    "Produto": "Nome do produto de seguro de vida (8 produtos, ex.: Vida Completo, Vida Essencial).",
    "Categoria do produto": "Categoria do produto: DOENCAS_GRAVES, FAMILIAR, PREMIUM, RENDA, RESGATAVEL, TEMPORARIO ou VITALICIO.",
    "Canal de venda": "Canal em que a apólice foi vendida: BANCASSURANCE, CORRETOR, DIGITAL ou TELEVENDAS.",
    "Forma de pagamento": "Forma de pagamento da parcela: BOLETO, CARTAO_CREDITO, DEBITO_CONTA ou PIX_AUTOMATICO. "
                          "NAO_CADASTRADA é dado que vazou da barreira de qualidade (dez/2026).",
    "Motivo da pendência": "Motivo pelo qual a parcela não foi paga no vencimento (10 motivos, agrupados em Grupo do motivo).",
    "Periodicidade": "Periodicidade de pagamento da apólice: MENSAL, TRIMESTRAL, SEMESTRAL ou ANUAL.",
}
# descrição dos campos sem comment no YAML (achado da avaliação com o genie-best-practices-agent, 20/11/2026)
DESCR = {
    "mv_carteira_em_aberto": {
        "Mês de referência": "Primeiro dia do mês da foto. Use com Saldo de fechamento e Variação mensal do saldo.",
        "Status de cobrança": "Status da cobrança no dia da foto: PENDENTE, EM_COBRANCA, PROMESSA_PAGAMENTO, NEGOCIADO ou COBRANCA_EXTERNA.",
        "Fase da cobrança": "Fase da régua de cobrança: INICIAL, INTERNA, NEGOCIACAO ou EXTERNA.",
        "Regional": "Regional comercial do ponto de venda: NORTE, NORDESTE, CENTRO-OESTE, SUDESTE ou SUL.",
        "UF do ponto de venda": "Sigla da UF do ponto de venda (23 UFs com pendências).",
        "Grupo da forma de pagamento": "Agrupamento da forma de pagamento: AUTOMATICO, BOLETO, CARTAO ou NAO_CADASTRADA.",
        "Grupo do motivo": "Agrupamento do motivo: AUTORIZACAO, CADASTRAL, FINANCEIRO ou OPERACIONAL. "
                           "Cadastral pede atualização de dados; financeiro pede negociação.",
        "Status da apólice": "Situação da apólice no dia: ATIVA, SUSPENSA, REDUZIDA ou CANCELADA_INADIMPLENCIA.",
        "Canal do último contato": "Último canal usado na cobrança: CARTA, EMAIL, SMS, TELEFONE, WHATSAPP ou NENHUM.",
        "Valor das parcelas em aberto": "Soma do valor original das parcelas em aberto, sem multa e juros. Semiaditivo: use com uma data.",
        "Multa e juros em aberto": "Multa e juros acumulados nas pendências em aberto. Semiaditivo: use com uma data.",
        "Ticket médio da pendência": "Saldo em aberto dividido pela quantidade de pendências em aberto.",
        "Atraso médio em dias": "Média de dias de atraso das pendências em aberto no dia da foto.",
        "Saldo acima de 60 dias": "Saldo em aberto das pendências com mais de 60 dias de atraso. Semiaditivo: use com uma data.",
        "Percentual do saldo acima de 60 dias": "Saldo acima de 60 dias dividido pelo saldo em aberto: indicador de risco da carteira.",
        "Saldo em cobrança externa": "Saldo em aberto das pendências em cobrança externa (status COBRANCA_EXTERNA). Semiaditivo: use com uma data.",
        "Clientes com pendência": "Quantidade de clientes distintos com pendência em aberto (contagem, sem dados pessoais).",
        "Apólices com pendência": "Quantidade de apólices distintas com pendência em aberto.",
    },
    "mv_recuperacao": {
        "Data da baixa": "Dia em que a pendência foi paga (baixa).",
        "Mês da baixa": "Primeiro dia do mês da baixa. Use com Variação mensal do valor recuperado e Valor recuperado acumulado no ano.",
        "Ano da baixa": "Primeiro dia do ano da baixa; base do acumulado no ano.",
        "Faixa de atraso na baixa": "Faixa de atraso no dia do pagamento (ex.: 01_1_A_15, 02_16_A_30, 03_31_A_60).",
        "Pendências pagas": "Quantidade de pendências pagas (baixas) no período.",
        "Multa e juros recebidos": "Multa e juros pagos nas baixas do período.",
        "Ticket médio recuperado": "Valor recuperado dividido pela quantidade de pendências pagas.",
    },
    "mv_safra_recuperacao": {
        "Data de entrada": "Dia em que a pendência entrou na carteira (dia seguinte ao vencimento).",
        "Status atual": "Status de cobrança atual da pendência, incluindo PAGA.",
        "Pendências que entraram": "Quantidade de pendências que entraram na safra.",
        "Pendências pagas da safra": "Quantidade de pendências da safra que já foram pagas.",
        "Valor das parcelas que entraram": "Soma do valor original das parcelas que entraram na safra.",
        "Valor recuperado da safra": "Soma do valor pago pelas pendências da safra.",
        "Dias até a baixa da safra": "Média de dias entre o vencimento e o pagamento das pendências pagas da safra.",
    },
    "mv_qualidade_dados": {
        "Dia": "Dia de extração dos eventos vindos do sistema de origem.",
        "Semana": "Primeiro dia (segunda-feira) da semana de extração. Para um período (ex.: semanas de dezembro), "
                  "filtre por Dia e agrupe por Semana: a semana de 30/11/2026 contém de 1º a 6/12.",
        "Mês": "Primeiro dia do mês de extração.",
        "Eventos recebidos": "Eventos de cobrança recebidos no bronze no período.",
        "Eventos aptos": "Eventos que passaram na barreira de qualidade e entraram na silver.",
        "Eventos barrados": "Eventos reprovados por regra de erro e mandados para a quarentena; não entram nos números.",
        "Taxa de barrados": "Eventos barrados divididos pelos eventos recebidos.",
        "Eventos duplicados": "Eventos repetidos (mesma pendência, dia e tipo) recebidos no período.",
        "Taxa de duplicatas": "Eventos duplicados divididos pelos eventos recebidos.",
        "E-mail ausente": "Eventos aptos com cliente sem e-mail (regra de aviso).",
        "Taxa de e-mail ausente": "E-mail ausente dividido pelos eventos aptos.",
        "CPF inválido": "Quantidade de eventos aptos cujo CPF não passa na validação (regra de aviso). É uma contagem: não contém CPF.",
        "Taxa de CPF inválido": "CPF inválido dividido pelos eventos aptos.",
        "CEP malformado": "Eventos aptos com CEP sem 8 dígitos (regra de aviso).",
        "Forma de pagamento não cadastrada": "Eventos aptos com forma de pagamento fora do catálogo que vazaram para a silver (incidente de dez/2026).",
    },
}


def com_descricoes(nome, yaml):
    """Insere `comment:` logo após `- name:` em todo campo do YAML que ainda não tem descrição."""
    import re
    linhas, saida = yaml.strip("\n").split("\n"), []
    for i, ln in enumerate(linhas):
        saida.append(ln)
        m = re.match(r"^  - name: (.+)$", ln)
        if not m:
            continue
        campo = m.group(1).strip()
        bloco = []
        for nxt in linhas[i + 1:]:
            if not nxt.startswith("    "):
                break
            bloco.append(nxt)
        if any(b.startswith("    comment:") for b in bloco):
            continue
        texto = DESCR.get(nome, {}).get(campo) or DESCR_COMUM.get(campo)
        if texto:
            saida.append(f'    comment: "{texto}"')
    return "\n".join(saida)


def mv(nome, yaml):
    return f"CREATE OR REPLACE VIEW {S}.{nome}\nWITH METRICS\nLANGUAGE YAML\nAS $$\n{com_descricoes(nome, yaml)}\n$$"


BRL = "format:\n      type: currency\n      currency_code: BRL\n      decimal_places:\n        type: exact\n        places: 2"
PCT = "format:\n      type: percentage\n      decimal_places:\n        type: max\n        places: 2"

SQL.append(mv("mv_carteira_em_aberto", f"""
version: 1.1
source: {S}.posicao_carteira
comment: "Carteira de pendências em aberto por dia (foto diária). O saldo é SEMIADITIVO: filtre UMA data de referência (ou a foto mais recente / fim de mês) ou agrupe por data; nunca some saldos de dias diferentes."
dimensions:
  - name: Data de referência
    expr: data_referencia
    comment: "Dia da foto da carteira."
    synonyms: [data, dia da foto, posição em, data da posição]
  - name: Mês de referência
    expr: "CAST(DATE_TRUNC('MONTH', data_referencia) AS DATE)"
    synonyms: [mês, competência da foto]
  - name: Foto mais recente
    expr: foto_mais_recente
    comment: "Verdadeiro na última foto disponível: use para 'hoje' ou 'atual'."
    synonyms: [hoje, atual, posição atual, último dia]
  - name: Fim de mês
    expr: fim_de_mes
    comment: "Verdadeiro no último dia do mês: use para saldos de fechamento."
    synonyms: [fechamento do mês, último dia do mês]
  - name: Status de cobrança
    expr: status_cobranca
    synonyms: [status, situação da cobrança]
  - name: Fase da cobrança
    expr: fase_cobranca
    synonyms: [fase]
  - name: Faixa de atraso
    expr: faixa_atraso
    comment: "Aging no dia da foto (00_VENCE_HOJE a 06_ACIMA_120)."
    synonyms: [aging, bucket de atraso, faixa de dias]
  - name: Produto
    expr: produto_nome
    synonyms: [plano, produto de vida]
  - name: Categoria do produto
    expr: categoria_produto
  - name: Canal de venda
    expr: canal_venda
    synonyms: [canal]
  - name: Regional
    expr: ponto_venda_regional
    synonyms: [regional comercial]
  - name: UF do ponto de venda
    expr: ponto_venda_uf
  - name: Forma de pagamento
    expr: forma_pagamento
    synonyms: [meio de pagamento]
  - name: Grupo da forma de pagamento
    expr: grupo_forma_pagamento
  - name: Motivo da pendência
    expr: motivo_pendencia
    synonyms: [motivo, causa]
  - name: Grupo do motivo
    expr: grupo_motivo
  - name: Periodicidade
    expr: periodicidade_pagamento
  - name: Status da apólice
    expr: status_apolice
  - name: Canal do último contato
    expr: canal_ultimo_contato
measures:
  - name: Saldo em aberto
    expr: SUM(valor_total_pendente)
    comment: "Soma do valor atualizado (parcela + multa + juros) das pendências em aberto. Semiaditivo: use com uma data."
    synonyms: [valor em aberto, carteira em atraso, exposição, saldo pendente, inadimplência em reais]
    {BRL}
  - name: Pendências em aberto
    expr: COUNT(1)
    comment: "Quantidade de pendências em aberto (semiaditivo: use com uma data)."
    synonyms: [quantidade de pendências, parcelas em atraso]
  - name: Valor das parcelas em aberto
    expr: SUM(valor_parcela)
    {BRL}
  - name: Multa e juros em aberto
    expr: SUM(valor_multa + valor_juros)
    synonyms: [encargos, acréscimos]
    {BRL}
  - name: Saldo médio diário
    expr: SUM(valor_total_pendente) / COUNT(DISTINCT data_referencia)
    comment: "Média dos saldos diários no período: forma correta de resumir o saldo de vários dias."
    synonyms: [saldo médio, média do saldo]
    {BRL}
  - name: Ticket médio da pendência
    expr: "MEASURE(`Saldo em aberto`) / MEASURE(`Pendências em aberto`)"
    synonyms: [valor médio por pendência]
    {BRL}
  - name: Atraso médio em dias
    expr: AVG(dias_atraso)
    synonyms: [dias de atraso médio, prazo médio de atraso]
  - name: Saldo acima de 60 dias
    expr: SUM(valor_total_pendente) FILTER (WHERE dias_atraso > 60)
    synonyms: [atraso longo, saldo crítico]
    {BRL}
  - name: Percentual do saldo acima de 60 dias
    expr: "MEASURE(`Saldo acima de 60 dias`) / MEASURE(`Saldo em aberto`)"
    {PCT}
  - name: Saldo em cobrança externa
    expr: SUM(valor_total_pendente) FILTER (WHERE status_cobranca = 'COBRANCA_EXTERNA')
    {BRL}
  - name: Clientes com pendência
    expr: COUNT(DISTINCT cliente_sk)
  - name: Apólices com pendência
    expr: COUNT(DISTINCT apolice_sk)
  # --- padrões semiaditivos e de comparação de períodos (databricks-solutions/uc-semantics-patterns)
  - name: Saldo de fechamento
    expr: SUM(valor_total_pendente)
    window:
      - order: Data de referência
        range: current
        semiadditive: last
    comment: "Saldo no último dia de cada período da consulta (por mês: o fim do mês; mês corrente: a foto mais recente). Sem data na consulta, é o saldo da foto mais recente. Nunca soma dias diferentes."
    synonyms: [saldo final, saldo no fim do período, saldo de encerramento, posição de fechamento]
    {BRL}
  - name: Pendências em aberto no fechamento
    expr: COUNT(1)
    window:
      - order: Data de referência
        range: current
        semiadditive: last
    comment: "Quantidade de pendências em aberto no último dia de cada período da consulta."
    synonyms: [pendências no fechamento, quantidade no fim do período]
  - name: Saldo no início do período
    expr: SUM(valor_total_pendente)
    window:
      - order: Data de referência
        range: current
        semiadditive: first
    comment: "Saldo no primeiro dia de cada período da consulta (por mês: dia 1; maio/2026 começa em 19/05)."
    synonyms: [saldo inicial, saldo no começo do período, saldo de abertura]
    {BRL}
  - name: Variação do saldo no período
    expr: "MEASURE(`Saldo de fechamento`) - MEASURE(`Saldo no início do período`)"
    comment: "Fechamento menos início DENTRO de um período de vários dias (ex.: agrupado por mês). Agrupado por data é sempre zero. Para comparar duas datas ou dois fins de mês, use Saldo em aberto em cada data ou Variação mensal do saldo."
    synonyms: [variação dentro do mês, crescimento da carteira dentro do período]
    {BRL}
  - name: Saldo de fechamento do mês anterior
    expr: SUM(valor_total_pendente) FILTER (WHERE fim_de_mes)
    window:
      - order: Mês de referência
        range: current
        semiadditive: last
        offset: -1 month
    comment: "Saldo no último dia do mês anterior ao mês de referência. Use agrupado por Mês de referência."
    synonyms: [fechamento do mês anterior, saldo do mês passado]
    {BRL}
  - name: Variação mensal do saldo
    expr: "(MEASURE(`Saldo de fechamento`) - MEASURE(`Saldo de fechamento do mês anterior`)) / MEASURE(`Saldo de fechamento do mês anterior`)"
    comment: "Variação percentual do saldo de fechamento sobre o fechamento do mês anterior (MoM). Use agrupado por Mês de referência."
    synonyms: [MoM, variação mês a mês, crescimento mensal do saldo]
    {PCT}
  - name: Posição no ranking do saldo
    expr: RANK() OVER (ORDER BY SUM(valor_total_pendente) / COUNT(DISTINCT data_referencia) DESC)
    comment: "Posição (1 = maior) pelo saldo médio diário do período filtrado; com uma única data é o ranking do saldo daquele dia. Não combine na mesma consulta com as medidas de fechamento, início ou mês anterior."
    synonyms: [ranking do saldo, posição no ranking, colocação]
"""))
SQL.append(mv("mv_recuperacao", f"""
version: 1.1
source: {S}.pagamento
comment: "Pagamentos (baixas) das pendências: valor recuperado por data da baixa. Aditivo no tempo."
dimensions:
  - name: Data da baixa
    expr: data_baixa
    synonyms: [data do pagamento, dia do pagamento]
  - name: Mês da baixa
    expr: "CAST(DATE_TRUNC('MONTH', data_baixa) AS DATE)"
    synonyms: [mês do pagamento]
  - name: Ano da baixa
    expr: "CAST(DATE_TRUNC('YEAR', data_baixa) AS DATE)"
    synonyms: [ano do pagamento]
  - name: Produto
    expr: produto_nome
  - name: Categoria do produto
    expr: categoria_produto
  - name: Canal de venda
    expr: canal_venda
  - name: Forma de pagamento
    expr: forma_pagamento
  - name: Motivo da pendência
    expr: motivo_pendencia
  - name: Faixa de atraso na baixa
    expr: faixa_atraso_na_baixa
measures:
  - name: Valor recuperado
    expr: SUM(valor_pago)
    comment: "Soma dos valores pagos nas baixas (parcela + multa + juros no dia do pagamento)."
    synonyms: [recebido, valor recebido, recuperação, arrecadação de atrasados]
    {BRL}
  - name: Pendências pagas
    expr: COUNT(1)
    synonyms: [baixas, quitações]
  - name: Multa e juros recebidos
    expr: SUM(valor_multa + valor_juros)
    {BRL}
  - name: Dias até a baixa
    expr: AVG(dias_atraso_na_baixa)
    comment: "Média de dias de atraso no momento do pagamento."
    synonyms: [tempo médio de recuperação, prazo de recuperação]
  - name: Ticket médio recuperado
    expr: "MEASURE(`Valor recuperado`) / MEASURE(`Pendências pagas`)"
    {BRL}
  # --- comparação de períodos, acumulados e ranking (databricks-solutions/uc-semantics-patterns)
  - name: Valor recuperado no mês
    expr: SUM(valor_pago)
    window:
      - order: Mês da baixa
        range: current
        semiadditive: last
    comment: "Valor recuperado no último mês do período da consulta; base da variação mensal."
    synonyms: [recuperado no mês corrente]
    {BRL}
  - name: Valor recuperado no mês anterior
    expr: SUM(valor_pago)
    window:
      - order: Mês da baixa
        range: current
        semiadditive: last
        offset: -1 month
    comment: "Valor recuperado no mês anterior ao mês da baixa. Use agrupado por Mês da baixa."
    synonyms: [recuperado no mês passado]
    {BRL}
  - name: Variação mensal do valor recuperado
    expr: "(MEASURE(`Valor recuperado no mês`) - MEASURE(`Valor recuperado no mês anterior`)) / MEASURE(`Valor recuperado no mês anterior`)"
    comment: "Variação percentual do valor recuperado sobre o mês anterior (MoM). Use agrupado por Mês da baixa."
    synonyms: [MoM da recuperação, variação mês a mês do recuperado]
    {PCT}
  - name: Valor recuperado acumulado no mês
    expr: SUM(valor_pago)
    window:
      - order: Data da baixa
        range: cumulative
        semiadditive: last
      - order: Mês da baixa
        range: current
        semiadditive: last
    comment: "Recuperado do dia 1 do mês até a data (MTD). Use agrupado por Data da baixa."
    synonyms: [MTD, acumulado do mês]
    {BRL}
  - name: Valor recuperado acumulado no ano
    expr: SUM(valor_pago)
    window:
      - order: Mês da baixa
        range: cumulative
        semiadditive: last
      - order: Ano da baixa
        range: current
        semiadditive: last
    comment: "Recuperado de 1º de janeiro até o fim do mês (YTD, grão mensal). Funciona agrupado por Mês da baixa ou filtrando um mês: o filtro de mês não corta os meses anteriores."
    synonyms: [YTD, acumulado do ano, recuperado no ano até agora]
    {BRL}
  - name: Posição no ranking de recuperação
    expr: RANK() OVER (ORDER BY SUM(valor_pago) DESC)
    comment: "Posição (1 = maior) pelo valor recuperado no período filtrado. Não combine na mesma consulta com as medidas de mês anterior ou acumuladas."
    synonyms: [ranking de recuperação, ranking do recuperado]
"""))
SQL.append(mv("mv_safra_recuperacao", f"""
version: 1.1
source: {S}.pendencia
comment: "Safras de entrada das pendências e quanto delas já foi pago. Compare safras de mesma idade (safras recentes tiveram menos tempo)."
dimensions:
  - name: Safra de entrada
    expr: safra_entrada
    comment: "Mês em que a pendência entrou (dia seguinte ao vencimento)."
    synonyms: [safra, mês de entrada, coorte]
  - name: Data de entrada
    expr: data_entrada
  - name: Produto
    expr: produto_nome
  - name: Canal de venda
    expr: canal_venda
  - name: Forma de pagamento
    expr: forma_pagamento
  - name: Motivo da pendência
    expr: motivo_pendencia
  - name: Periodicidade
    expr: periodicidade_pagamento
  - name: Status atual
    expr: status_cobranca
measures:
  - name: Pendências que entraram
    expr: COUNT(1)
    synonyms: [entradas, novas pendências]
  - name: Pendências pagas da safra
    expr: COUNT(1) FILTER (WHERE paga)
  - name: Taxa de recuperação
    expr: "MEASURE(`Pendências pagas da safra`) / MEASURE(`Pendências que entraram`)"
    comment: "Pendências pagas / pendências que entraram na safra."
    synonyms: [recovery rate, percentual recuperado, taxa de pagamento]
    {PCT}
  - name: Valor das parcelas que entraram
    expr: SUM(valor_parcela)
    {BRL}
  - name: Valor recuperado da safra
    expr: SUM(valor_pago)
    {BRL}
  - name: Dias até a baixa da safra
    expr: AVG(dias_ate_baixa)
"""))
SQL.append(mv("mv_qualidade_dados", f"""
version: 1.1
source: {C}.gold.dq_qualidade_diaria
comment: "Qualidade diária dos dados que chegam do sistema de origem: recebidos, barrados e avisos."
dimensions:
  - name: Dia
    expr: dia
    synonyms: [data, dia de extração]
  - name: Semana
    expr: "CAST(DATE_TRUNC('WEEK', dia) AS DATE)"
  - name: Mês
    expr: "CAST(DATE_TRUNC('MONTH', dia) AS DATE)"
measures:
  - name: Eventos recebidos
    expr: SUM(eventos_recebidos)
  - name: Eventos aptos
    expr: SUM(eventos_aptos)
  - name: Eventos barrados
    expr: SUM(eventos_barrados)
    synonyms: [quarentena, rejeitados, não aptos]
  - name: Taxa de barrados
    expr: "MEASURE(`Eventos barrados`) / MEASURE(`Eventos recebidos`)"
    synonyms: [percentual barrado, taxa de rejeição]
    {PCT}
  - name: Eventos duplicados
    expr: SUM(eventos_duplicados)
  - name: Taxa de duplicatas
    expr: "MEASURE(`Eventos duplicados`) / MEASURE(`Eventos recebidos`)"
    {PCT}
  - name: E-mail ausente
    expr: SUM(email_ausente)
  - name: Taxa de e-mail ausente
    expr: "MEASURE(`E-mail ausente`) / MEASURE(`Eventos aptos`)"
    {PCT}
  - name: CPF inválido
    expr: SUM(cpf_invalido)
  - name: Taxa de CPF inválido
    expr: "MEASURE(`CPF inválido`) / MEASURE(`Eventos aptos`)"
    {PCT}
  - name: CEP malformado
    expr: SUM(cep_malformado)
  - name: Forma de pagamento não cadastrada
    expr: SUM(forma_pagamento_nao_cadastrada)
    synonyms: [vazamento, forma inválida]
"""))

if __name__ == "__main__":
    (AQUI / "ontologia.sql").write_text(";\n\n".join(SQL) + ";\n", encoding="utf-8")          # para leitura
    (AQUI / "ontologia_sql.json").write_text(json.dumps(SQL, indent=1, ensure_ascii=False), encoding="utf-8")  # para executar
    print(f"ontologia.sql: {len(SQL)} comandos")
