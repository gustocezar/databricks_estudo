"""Descrição das colunas das views do painel de qualidade (pos_venda.dq.v_painel_*).

Essas views calculam as colunas (CTE, aliases, JSON do Studio), então não herdam a descrição da origem como um
SELECT * herdaria. Colunas repassadas sem mudança copiam a descrição da tabela de origem; as calculadas estão abaixo.
Usado por aplicar_e_testar.py depois de criar ou conferir as views.
"""

# view -> tabela de onde vêm as colunas repassadas com o mesmo nome
ORIGEM = {
    "v_painel_diario": "pos_venda.gold.dq_qualidade_diaria",
    "v_painel_barrados": "pos_venda.gold.dq_barrados_por_motivo_dia",
    "v_painel_quarentena": "pos_venda.silver.pendencia_evento_quarentena",
}

SEMANA = {
    "dia": "Dia de extração dos eventos.",
    "semana_n": "Número da semana da simulação (1 = 20/11 a 26/11/2026; 5 = 18/12 a 24/12/2026).",
    "semana": "Rótulo da semana da simulação, ex.: Semana 1 · 20/11–26/11.",
}
STUDIO = {
    "run_id": "Identificador da execução no DQX Studio.",
    "camada": "Camada avaliada, com ordem e rótulo (ex.: 1 · Bronze (tudo que chegou)).",
    "camada_curta": "Camada avaliada: bronze, quarentena, silver, silver hist ou fato.",
}

EXPLICITAS = {
    "v_painel_diario": {
        "taxa_barrados": "Eventos barrados divididos pelos recebidos, de 0 a 1.",
        "taxa_duplicados": "Eventos duplicados divididos pelos recebidos, de 0 a 1.",
        "taxa_cpf_invalido": "Eventos aptos com CPF inválido divididos pelos eventos aptos, de 0 a 1.",
        "taxa_email_ausente": "Eventos aptos sem e-mail divididos pelos eventos aptos, de 0 a 1.",
        "taxa_cep_malformado": "Eventos aptos com CEP malformado divididos pelos eventos aptos, de 0 a 1.",
        "fato_linhas_orfas": "Linhas da foto do dia na fato sem dimensão de forma de pagamento (chave órfã).",
        "fato_linhas_na_foto": "Linhas da foto do dia na fato histórica.",
    },
    "v_painel_quarentena": {
        "dia": "Dia de extração do evento barrado.",
    },
    "v_painel_studio_execucoes": {
        "destino": "View de janela avaliada pelo Studio (pos_venda.dq.v_*_janela).",
        "created_at": "Momento da execução no DQX Studio.",
        "total_rows": "Linhas avaliadas (todas as linhas da janela).",
        "error_rows": "Linhas reprovadas por regra de erro.",
        "warning_rows": "Linhas com aviso (regra de aviso).",
        "taxa_erro": "Linhas com erro divididas pelas linhas avaliadas, de 0 a 1.",
        "taxa_aviso": "Linhas com aviso divididas pelas linhas avaliadas, de 0 a 1.",
        "error_summary_json": "Resumo do Studio por regra: JSON com o nome da regra e as contagens de erro e aviso.",
    },
    "v_painel_studio_regras": {
        "regra": "Nome da regra do DQX violada.",
        "criticidade": "erro ou aviso.",
        "regra_rotulo": "Camada, regra e criticidade num rótulo para os gráficos.",
        "linhas": "Linhas que violaram a regra na execução.",
        "linhas_erro": "Linhas que violaram a regra como erro.",
        "linhas_aviso": "Linhas que violaram a regra como aviso.",
    },
    "v_painel_studio_reprovadas": {
        "regra": "Nome da regra do DQX que reprovou a linha.",
        "mensagem": "Mensagem do DQX Studio para a violação.",
        "referencia": "Data da linha reprovada (data_extracao ou data_referencia_sk da origem).",
        "pendencia_id": "Identificador da pendência da linha reprovada.",
        "numero_apolice": "Número da apólice da linha reprovada.",
        "cliente_nome": "Nome do cliente da linha reprovada (dado pessoal).",
        "valor_total_pendente": "Valor total pendente da linha reprovada, como texto (vem do JSON do Studio).",
        "created_at": "Momento em que o Studio gravou a linha reprovada.",
    },
}


def descricoes(nome, sql):
    """Dicionário coluna -> descrição para a view `nome` (catálogo.schema.view)."""
    view = nome.split(".")[-1]
    out = {}
    origem = ORIGEM.get(view)
    if origem:
        cat, sch, tab = origem.split(".")
        out.update({r["column_name"]: r["comment"] for r in sql(
            f"SELECT column_name, comment FROM {cat}.information_schema.columns "
            f"WHERE table_schema = '{sch}' AND table_name = '{tab}' AND comment IS NOT NULL")})
    out.update(SEMANA)
    if view.startswith("v_painel_studio"):
        out.update(STUDIO)
    out.update(EXPLICITAS.get(view, {}))
    return out
