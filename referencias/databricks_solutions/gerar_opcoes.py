"""Guia de opções databricks-solutions para uma LLM escolher a melhor para o projeto.

Lê `catalogo.json` (gerado por `catalogo.py`, com a revisão de 22/11 já aplicada) e escreve:

- `OPCOES_PARA_LLM.md`: contexto do projeto, regras de escolha, ranking e um bloco por repositório, com campos fixos;
- `opcoes.json`: o mesmo conteúdo, estruturado, para ferramentas e agentes.

Cada repositório ganha o que o catálogo não tinha: a camada e as práticas do framework (`docs/04_FRAMEWORK.md`) que
ele ajuda, uma recomendação (já aplicado, aplicar a seguir, candidato, adiado...) e uma prioridade. Fonte única: para
mudar uma opção, edite `catalogo.py`, rode-o e rode este script.

Uso: python3 catalogo.py && python3 gerar_opcoes.py
"""
import json
import pathlib

AQUI = pathlib.Path(__file__).resolve().parent
DATA = "2026-11-23"

CATEGORIA = {
    "SEM": "Genie e camada semântica", "GOV": "Qualidade, governança e segurança", "ENG": "Pipelines e engenharia de dados",
    "ING": "Ingestão e streaming", "LKB": "Lakebase (Postgres)", "APP": "Apps e ferramentas de app",
    "AGT": "Agentes e IA generativa", "MLO": "Avaliação, MLOps e modelos", "MIG": "Migração",
    "PLT": "Plataforma, infraestrutura e custos", "BI": "BI externo (Power BI, Grafana)",
    "DEV": "Ferramentas para coding agents", "EDU": "Workshops, demos e coleções", "IND": "Soluções de indústria",
    "VAZ": "Modelo vazio ou arquivado",
}
# camada do framework e práticas (P##) que cada categoria toca; os repositórios avaliados de perto têm a sua
CAMADA = {
    "SEM": ("Semântica e Consumo", "P18, P19, P21"), "GOV": ("Qualidade e Governança", "P09 a P16"),
    "ENG": ("Fundação e Dados", "P02, P05 a P08"), "ING": ("Dados", "P06"), "LKB": ("Consumo (apps com Postgres)", "—"),
    "APP": ("Consumo (apps)", "P22"), "AGT": ("Consumo (agentes e IA generativa)", "—"),
    "MLO": ("Avaliação e modelos", "P24"), "MIG": ("Dados (migração)", "—"), "PLT": ("Fundação e Operação", "P01, P28"),
    "BI": ("Consumo (BI externo)", "P23"), "DEV": ("Fundação (ferramentas)", "P02"),
    "EDU": ("Referência (workshops e demos)", "—"), "IND": ("Referência (soluções de indústria)", "—"), "VAZ": ("Nenhuma", "—"),
}
CAMADA_REPO = {
    "uc-semantics-patterns": ("Semântica", "P19"),
    "genie-ontology-readiness": ("Avaliação", "P25"),
    "genie-best-practices-agent": ("Avaliação", "P24"),
    "agentic-bdd-uc-functions": ("Semântica", "P20"),
    "powerbi-analyzer": ("Consumo e Avaliação", "P08, P26"),
    "technical-services-solutions": ("Avaliação", "P26"),
    "power-bi-on-databricks-quickstarts": ("Consumo", "P23"),
    "regulatory_data_governance": ("Qualidade e Governança", "P11, P14"),
    "dbx-adoption-monitor": ("Avaliação", "P26"),
    "databricks-genie-workbench": ("Consumo e Avaliação", "P21, P26"),
    "uc-declarative-abac": ("Governança", "P15"),
    "genierails": ("Governança", "P15"),
    "data-classification-review-app": ("Governança", "P15"),
    "databricks-dab-examples": ("Fundação", "P02, P03"),
    "lakeflow_framework": ("Dados e Qualidade", "P06, P09"),
    "ingestion-workbench": ("Dados", "P06"),
    "caspers": ("Dados e Qualidade", "P04, P10"),
    "ai-dev-kit": ("Fundação", "P02"),
    "databricks-aibi-design-first-accelerator": ("Semântica", "P18"),
    "databricks-forge": ("Governança e Semântica", "P14, P18"),
    "aibi-dashboard-wanderbricks": ("Consumo", "P22"),
    "mlops-quickstart": ("Avaliação e modelos", "— (capacidade nova: modelo de propensão)"),
    "advance-document-processing": ("Consumo (agentes e IA generativa)", "— (capacidade nova: leitura de documentos)"),
}
RELEVANCIA = {"A": "Alta", "M": "Média", "B": "Baixa", "N": "Nenhuma"}
FREE = {"S": "Sim", "C": "Com ressalvas", "N": "Não"}
ORDEM_REC = ["Aplicar a seguir", "Candidato", "Já aplicado", "Adiado", "Só se a necessidade mudar", "Fora do escopo",
             "Não roda no Free Edition"]

CONTEXTO = {
    "dominio": "Pós-venda de seguro de vida: parcelas pendentes de pagamento (carteira em aberto, recuperação, safras)",
    "plataforma": "Databricks Free Edition: 1 SQL warehouse 2X-Small, cota diária de computação, só serverless",
    "apps": "2 de 3 vagas em uso (dqx-studio e genie-ontology-readiness); resta 1",
    "lakebase": "1 projeto, já em uso (dqx-studio-db); um app novo que precise de Postgres usa uma database nesse projeto",
    "modelos": "Sem modelos Claude no Model Serving; llama-4-maverick testado para saída estruturada (até 8.192 tokens)",
    "dados": "Sintéticos (dbldatagen); dado pessoal marcado por tag e sem máscara, por decisão (a validação usa os valores)",
    "consumo": "2 espaços Genie (analista e diretor), painéis AI/BI, opção Power BI por importação (schema bi)",
    "versionamento": "Git no GitHub (gustocezar/databricks_estudo); ainda sem CI/CD",
    "framework": "docs/04_FRAMEWORK.md: 29 práticas (P01 a P29) em 8 camadas",
}
REGRAS = [
    "Identifique a necessidade e a camada do framework que ela toca (Fundação, Dados, Qualidade, Governança, "
    "Semântica, Consumo, Avaliação, Operação).",
    "Filtre as opções pela camada e pelas práticas (campos `camada` e `praticas`); confira o campo `escolha_quando`.",
    "Se uma opção `Já aplicado` cobre a necessidade, estenda-a antes de adotar outra (ela já está integrada e testada).",
    "Enquanto o projeto estiver no Free Edition, descarte `Não roda no Free Edition`; em `Com ressalvas`, leia a "
    "`nota_free_edition` e diga a ressalva.",
    "Prefira `Aplicar a seguir`, depois `Candidato`, em ordem de relevância (Alta antes de Média); o campo `prioridade` "
    "já ordena assim.",
    "Desempate: sem app novo (resta 1 vaga), sem modelo Claude, sem projeto Lakebase novo, menor esforço.",
    "`Adiado` só volta se o motivo do adiamento (campo `motivo_situacao`) deixou de valer.",
    "`Só se a necessidade mudar` e `Fora do escopo` não são recomendações para o pos_venda atual; cite-as só quando "
    "a necessidade nova bater com `escolha_quando`.",
    "Responda com: a opção escolhida, por quê (citando os campos), o que ela exige no Free Edition, a prática do "
    "framework que ela reforça e a alternativa descartada, com o motivo.",
]


def recomendacao(i):
    s = i.get("s") or ""
    if s == "aplicado":
        return "Já aplicado"
    if s == "proposto":
        return "Aplicar a seguir"
    if s == "adiado":
        return "Adiado"
    if i["fe"] == "N":
        return "Não roda no Free Edition"
    if i["r"] in "AM":
        return "Candidato"
    if i["r"] == "B":
        return "Só se a necessidade mudar"
    return "Fora do escopo"


def opcao(i):
    camada, praticas = CAMADA_REPO.get(i["n"], CAMADA[i["c"]])
    return {
        "nome": i["n"], "url": i["url"], "categoria": CATEGORIA[i["c"]], "camada": camada, "praticas": praticas,
        "o_que_e": i["f"], "como_usar": i["u"], "escolha_quando": i["k"], "como_ajuda_no_pos_venda": i["b"],
        "relevancia": RELEVANCIA[i["r"]], "free_edition": FREE[i["fe"]], "nota_free_edition": i.get("fn") or "",
        "situacao": i.get("s") or "não avaliado no projeto", "motivo_situacao": i.get("sn") or "",
        "recomendacao": recomendacao(i), "ultimo_commit": (i.get("push") or "")[:10], "arquivado": bool(i.get("arq")),
    }


def chave(o):
    return (ORDEM_REC.index(o["recomendacao"]), list(RELEVANCIA.values()).index(o["relevancia"]),
            list(FREE.values()).index(o["free_edition"]), o["nome"].lower())


def bloco(o):
    linhas = [f"#### {o['prioridade']}. {o['nome']}", "",
              f"- **Recomendação:** {o['recomendacao']}" + (f". {o['motivo_situacao']}" if o["motivo_situacao"] else ""),
              f"- **Relevância para o pos_venda:** {o['relevancia']} · **Free Edition:** {o['free_edition']}"
              + (f" ({o['nota_free_edition']})" if o["nota_free_edition"] else ""),
              f"- **Camada do framework:** {o['camada']} · **Práticas:** {o['praticas']} · **Categoria:** {o['categoria']}",
              f"- **O que é:** {o['o_que_e']}",
              f"- **Como ajudaria no pos_venda:** {o['como_ajuda_no_pos_venda']}",
              f"- **Escolha quando:** {o['escolha_quando']}",
              f"- **Como usar:** {o['como_usar']}",
              f"- **Repositório:** [{o['nome']}]({o['url']}) · último commit {o['ultimo_commit']}"
              + (" · **arquivado**" if o["arquivado"] else ""), ""]
    return "\n".join(linhas)


def tabela(ops):
    L = ["| # | Opção | Recomendação | Camada · práticas | Relevância | Free Edition | Como ajudaria |", "|---|---|---|---|---|---|---|"]
    for o in ops:
        ajuda = o["como_ajuda_no_pos_venda"].replace("|", "/")
        ajuda = ajuda if len(ajuda) <= 160 else ajuda[:157].rsplit(" ", 1)[0] + "…"
        L.append(f"| {o['prioridade']} | [{o['nome']}]({o['url']}) | {o['recomendacao']} | {o['camada']} · {o['praticas']} | "
                 f"{o['relevancia']} | {o['free_edition']} | {ajuda} |")
    return "\n".join(L)


def gerar():
    cat = json.loads((AQUI / "catalogo.json").read_text(encoding="utf-8"))
    ops = sorted((opcao(i) for i in cat), key=chave)
    for n, o in enumerate(ops, 1):
        o["prioridade"] = n
    (AQUI / "opcoes.json").write_text(json.dumps({
        "gerado_em": DATA, "fonte": "referencias/databricks_solutions/catalogo.py (147 repositórios públicos da "
        "organização databricks-solutions, lidos em 20/11/2026 e revistos em 22/11/2026)",
        "contexto_do_projeto": CONTEXTO, "regras_de_escolha": REGRAS,
        "legenda": {"recomendacao": ORDEM_REC, "relevancia": list(RELEVANCIA.values()), "free_edition": list(FREE.values())},
        "opcoes": ops}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    contagem = {r: sum(1 for o in ops if o["recomendacao"] == r) for r in ORDEM_REC}
    md = [f"# Opções databricks-solutions para o pos_venda · guia para LLM",
          "",
          f"> Gerado por `gerar_opcoes.py` em {DATA}, a partir de `catalogo.py`. Não edite à mão. Versão estruturada: "
          "[`opcoes.json`](opcoes.json).",
          "",
          "Este guia lista os **147 repositórios públicos** da organização "
          "[databricks-solutions](https://github.com/databricks-solutions) como opções para o projeto. Cada opção diz o "
          "que é, como ajudaria no pos_venda, quando escolher, se cabe no Free Edition, a camada e as práticas do "
          "[framework](../../docs/04_FRAMEWORK.md) que ela reforça, e a recomendação para o projeto hoje.",
          "",
          "**Para uma LLM:** leia o contexto e as regras, depois use o ranking e os blocos. Pergunta de exemplo: "
          "*\"Quero medir quanto a Genie e os painéis são usados. Qual opção databricks-solutions usar no pos_venda?\"* "
          "A resposta esperada aplica as regras: a camada é Avaliação; `dbx-adoption-monitor` está em *Aplicar a seguir*, "
          "cabe no Free Edition e não ocupa vaga de app; o `databricks-genie-workbench` fica de fora porque gastaria a "
          "última vaga de app.",
          "",
          "## Contexto do projeto",
          "",
          "| Item | Situação |", "|---|---|"]
    md += [f"| {k.replace('_', ' ').capitalize()} | {v} |" for k, v in CONTEXTO.items()]
    md += ["", "## Regras de escolha", ""] + [f"{n}. {r}" for n, r in enumerate(REGRAS, 1)]
    md += ["", "## Recomendações, em números", "", "| Recomendação | Opções | O que significa |", "|---|---|---|"]
    sentido = {
        "Aplicar a seguir": "proposta da revisão de 22/11 ainda não aplicada",
        "Candidato": "relevância alta ou média, cabe no Free Edition, sem decisão ainda",
        "Já aplicado": "em uso no projeto; estenda antes de adotar outra",
        "Adiado": "avaliado e adiado, com o motivo; volta se o motivo deixar de valer",
        "Só se a necessidade mudar": "relevância baixa para o pos_venda atual",
        "Fora do escopo": "sem relação com o pos_venda atual",
        "Não roda no Free Edition": "exige recurso que o Free Edition não tem",
    }
    md += [f"| {r} | {contagem[r]} | {sentido[r]} |" for r in ORDEM_REC]
    md += ["", "## Ranking das opções que importam para o pos_venda", "",
           "Aplicar a seguir, candidatos, já aplicados e adiados, nessa ordem e por relevância.", ""]
    md.append(tabela([o for o in ops if o["recomendacao"] in ORDEM_REC[:4]]))
    md += ["", "## Todas as opções, em ordem de prioridade", ""]
    atual = None
    for o in ops:
        if o["recomendacao"] != atual:
            atual = o["recomendacao"]
            md += [f"### {atual} ({contagem[atual]})", ""]
        md.append(bloco(o))
    (AQUI / "OPCOES_PARA_LLM.md").write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
    print(f"{len(ops)} opções; " + "; ".join(f"{r}: {c}" for r, c in contagem.items()))


if __name__ == "__main__":
    gerar()
