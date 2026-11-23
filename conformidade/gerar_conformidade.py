"""Monitoramento de conformidade dos dados e do workspace no schema pos_venda.conformidade.

Mede, só com o information_schema do Unity Catalog e as tabelas de sistema, se os ativos seguem as regras do projeto:
- documentação: descrição em ativos, colunas e schemas (P13);
- tags governadas: domain, data_owner e subject_area, valores dentro da política, tags de schema (P14);
- dados pessoais (LGPD): coluna com nome de dado pessoal marcada, classificação automática revisada, tags de
  ativo coerentes com as de coluna (P15);
- confiança e estrutura: chave primária na gold (P08), certificação, legado marcado como deprecated, dono em grupo;
- atualização e uso: frescor declarado × última escrita, leitura nos últimos 30 dias, view que responde (P16, P28);
- otimização: Predictive Optimization nas tabelas gerenciadas;
- plataforma: jobs, warehouses e alertas SQL com tags, descrição, timeout, auto-stop e frequência. Estas regras foram internalizadas do
  bundle observabilidade-framework (notebooks policy_compliance_monitoring e materializa_dados_observabilidade).

Cada regra tem meta, severidade, origem e como corrigir (`config_regras`). Uma regra sem nenhum objeto para
verificar aparece como "sem dados", nunca como "atende".

Não altera nada fora de pos_venda.conformidade: só lê. Grava as visões, a sonda das views (`sonda_views`) e o
histórico diário (`historico`).

Uso:
    python3 conformidade/gerar_conformidade.py politicas   # atualiza politicas_tags.json (valores das tags governadas)
    python3 conformidade/gerar_conformidade.py alertas     # atualiza alertas.json (alertas SQL: agenda e disparos por dia)
    python3 conformidade/gerar_conformidade.py gerar       # escreve conformidade/conformidade.sql
    python3 conformidade/gerar_conformidade.py aplicar     # cria schema, tabelas e visões (só recria o que mudou)
    python3 conformidade/gerar_conformidade.py registrar   # sonda as views do workspace e grava o histórico do dia
    python3 conformidade/gerar_conformidade.py conferir    # cada visão responde + contagens batem -> conferencia.json
"""
import concurrent.futures as cf
import datetime
import json
import pathlib
import re
import subprocess
import sys

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ / "governanca"))
from sql_util import CotaEsgotada, executar  # noqa: E402

S = "pos_venda.conformidade"
PERFIL = "dbx-workshop"
DOMINIO = "pos_venda"                     # catálogo do domínio: recebe as regras de tags, LGPD e estrutura
EXCLUIDOS = ("system", "samples", "__databricks_internal")
JANELA = 30                               # dias de leitura (lineage) e de Predictive Optimization
FRESCOR_DIAS = 2                          # ativo com atualizacao=diaria precisa ter sido escrito neste prazo
MIN_DESC_ATIVO = 30                       # caracteres mínimos da descrição de um ativo (escolha do projeto)
MIN_DESC_COLUNA = 15                      # caracteres mínimos da descrição de uma coluna (escolha do projeto)
ALERTA_MAX_DIA = 4                        # disparos por dia de um alerta SQL: cada disparo acorda o warehouse (L79)
TAGS_ATIVO = ["domain", "data_owner", "subject_area"]
TAGS_SCHEMA = ["domain", "camada"]

# papel de cada schema do domínio: principal = fluxo diário (ontologia, Genie, painéis e Power BI leem daqui);
# legado = medalhão estático da primeira versão (SQL e Lakeflow), sem carga diária e só com tags de dado pessoal;
# apoio = monitoramento gerado por código (FinOps e esta conformidade)
CAMADAS = [
    ("landing", "landing", "principal"), ("fonte", "fonte", "principal"), ("bronze", "bronze", "principal"),
    ("silver", "silver", "principal"), ("gold", "gold", "principal"), ("dq", "qualidade", "principal"),
    ("ontologia", "ontologia", "principal"), ("regras", "regras", "principal"), ("bi", "bi", "principal"),
    ("bronze_sql", "bronze", "legado"), ("silver_sql", "silver", "legado"), ("gold_sql", "gold", "legado"),
    ("bronze_ldp", "bronze", "legado"), ("silver_ldp", "silver", "legado"), ("gold_ldp", "gold", "legado"),
    ("finops", "monitoramento", "apoio"), ("conformidade", "monitoramento", "apoio"),
]

# regra de governanca/auditar_metadados.py: nome de coluna que indica dado pessoal, e as exceções; aqui, mais as
# exceções dos nomes de métrica da ontologia ("CPF inválido", "CEP malformado", "Taxa de ...")
PII = (r"(cpf|(^|_)rg($|_)|email|celular|telefone|(^|_)nome($|_)|logradouro|endereco|bairro|cep|data_nascimento|"
       r"documento|numero$|complemento)")
NAO_PII = (r"(produto_nome|ponto_venda_nome|_valido$|_ausente$|_invalido$|numero_apolice|numero_parcela|"
           r"_malformado$|^pct_|^taxa_|cobertura_|^nome_mes$|^nome_dia_semana$|numero_ultimo_endosso|cpf_valido|"
           r"malformado$|inv.lido$|^taxa )")
# tabelas de apoio que o Lakeflow cria sozinho: não são ativos de negócio e ficam fora das regras
INTERNO = "(startswith({n}, '__materialization') OR startswith({n}, 'event_log_'))"

DOC = "https://docs.databricks.com/aws/en"
L_COMENT = f"{DOC}/comments/"
L_TAGS = f"{DOC}/admin/governed-tags/"
L_CLASS = f"{DOC}/data-governance/unity-catalog/data-classification"
L_LGPD = "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm"
L_PK = f"{DOC}/tables/constraints"
L_UCBP = f"{DOC}/data-governance/unity-catalog/best-practices"
L_LIN = f"{DOC}/data-governance/unity-catalog/data-lineage"
L_PO = f"{DOC}/optimizations/predictive-optimization"
L_JOB = f"{DOC}/jobs/settings"
L_WH = f"{DOC}/compute/sql-warehouse/create"
L_CUSTO = f"{DOC}/lakehouse-architecture/cost-optimization/best-practices"
L_ALERTA = f"{DOC}/sql/user/alerts/"
OBS = "bundle observabilidade-framework"

# (id, dimensão, regra, objeto, escopo, meta %, severidade, origem, link, como corrigir)
REGRAS = [
    ("DOC01", "Documentação", "Ativo com descrição", "ativo", "todos os catálogos do workspace", 100, "alta",
     "Databricks: comentários no Unity Catalog; framework P13", L_COMENT,
     "COMMENT ON TABLE (ou aceitar a descrição gerada por IA no Catalog Explorer depois de revisar)."),
    ("DOC02", "Documentação", f"Descrição do ativo com ao menos {MIN_DESC_ATIVO} caracteres", "ativo", "catálogo pos_venda", 100, "média",
     "Prática do projeto: a descrição diz grão, conteúdo e uso (P13)", L_COMENT,
     "Reescrever a descrição dizendo o grão, o que tem e para que serve."),
    ("DOC03", "Documentação", "Coluna com descrição", "coluna", "catálogo pos_venda", 100, "alta",
     "Databricks: comentários no Unity Catalog; framework P13", L_COMENT,
     "ALTER TABLE ... ALTER COLUMN ... COMMENT (governanca/descricoes_colunas.py e aplicar_descricoes.py)."),
    ("DOC04", "Documentação", f"Descrição da coluna com ao menos {MIN_DESC_COLUNA} caracteres", "coluna", "catálogo pos_venda", 100, "baixa",
     "Prática do projeto (P13)", L_COMENT, "Completar a descrição: significado, unidade e origem."),
    ("DOC05", "Documentação", "Schema com descrição", "schema", "catálogo pos_venda", 100, "média",
     "Databricks: comentários no Unity Catalog", L_COMENT, "COMMENT ON SCHEMA."),
    ("TAG01", "Tags governadas", "Ativo da camada principal com domain, data_owner e subject_area", "ativo", "camada principal", 100, "alta",
     "Databricks: governed tags; framework P14", L_TAGS,
     "SET TAGS com os valores da política (governanca/aplicar_semantica.py)."),
    ("TAG02", "Tags governadas", "Ativo da camada principal com a tag atualizacao", "ativo", "camada principal", 100, "média",
     "Prática do projeto: frescor declarado (P16)", L_TAGS, "SET TAGS ('atualizacao' = 'diaria' ou 'carga_unica')."),
    ("TAG03", "Tags governadas", "Valor de tag governada dentro dos valores da política", "tag", "catálogo pos_venda", 100, "alta",
     "Databricks: governed tags (tag policies)", L_TAGS,
     "Corrigir o valor, ou incluir o novo valor na política (databricks tag-policies)."),
    ("TAG04", "Tags governadas", "Schema da camada principal com as tags domain e camada", "schema", "camada principal", 100, "média",
     "Prática do projeto (P14)", L_TAGS, "ALTER SCHEMA ... SET TAGS ('domain' = 'pos_venda', 'camada' = ...)."),
    ("LGPD01", "Dados pessoais (LGPD)", "Coluna com nome de dado pessoal tem a tag dado_pessoal", "coluna", "camadas principal e legado", 100, "alta",
     "LGPD, art. 5º, I; framework P15 (mesma regra de governanca/auditar_metadados.py)", L_LGPD,
     "SET TAGS ('dado_pessoal' = identificacao, contato, endereco, perfil ou sensivel)."),
    ("LGPD02", "Dados pessoais (LGPD)", "Coluna com classificação automática (class.*) revisada com dado_pessoal", "coluna", "camadas principal e legado", 100, "alta",
     "Databricks: data classification; framework P15", L_CLASS,
     "Revisar a classe: confirmar com dado_pessoal ou remover a tag class.* se for falso positivo."),
    ("LGPD03", "Dados pessoais (LGPD)", "Ativo com coluna dado_pessoal marcado com contem_dado_pessoal", "ativo", "camadas principal e legado", 100, "alta",
     "LGPD, art. 5º, I; framework P15", L_LGPD, "SET TAGS ('contem_dado_pessoal' = 'sim') no ativo."),
    ("LGPD04", "Dados pessoais (LGPD)", "Ativo marcado com contem_dado_pessoal tem coluna marcada", "ativo", "catálogo pos_venda", 100, "média",
     "Prática do projeto: tag de ativo sem coluna correspondente é órfã (P15)", L_LGPD,
     "Marcar as colunas com dado_pessoal ou retirar a tag do ativo."),
    ("LGPD05", "Dados pessoais (LGPD)", "Ativo com coluna sensível marcado com contem_dado_sensivel", "ativo", "camadas principal e legado", 100, "alta",
     "LGPD, art. 5º, II (dado pessoal sensível); framework P15", L_LGPD, "SET TAGS ('contem_dado_sensivel' = 'sim') no ativo."),
    ("EST01", "Confiança e estrutura", "Dimensão, fato e ponte da gold com chave primária", "ativo", "gold da camada principal", 100, "alta",
     "Databricks: constraints informativas; framework P08", L_PK,
     "ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY ... RELY (governanca/aplicar_rely.py)."),
    ("EST02", "Confiança e estrutura", "Ativo da gold e da ontologia certificado", "ativo", "gold e ontologia da camada principal", 100, "média",
     "Databricks: governed tags, tag de sistema system.certification_status", L_TAGS,
     "Depois da conferência: SET TAGS ('system.certification_status' = 'certified')."),
    ("EST03", "Confiança e estrutura", "Ativo legado marcado como deprecated", "ativo", "camada legado", 100, "média",
     "Databricks: governed tags (sinalizar o que não é mais mantido como deprecated)", L_TAGS,
     "SET TAGS ('system.certification_status' = 'deprecated'), ou apagar o schema legado se ninguém mais lê."),
    ("EST04", "Confiança e estrutura", "Dono do ativo é grupo ou service principal", "ativo", "catálogo pos_venda", 100, "baixa",
     "Databricks: boas práticas do Unity Catalog (dono em grupo, principalmente em produção)", L_UCBP,
     "ALTER TABLE ... OWNER TO `grupo` (o criador é o primeiro dono)."),
    ("USO01", "Atualização e uso", f"Ativo com atualizacao=diaria escrito nos últimos {FRESCOR_DIAS} dias", "ativo", "tabelas da camada principal", 100, "média",
     "Prática do projeto (P02 agendas pausadas, P28); Databricks: lineage", L_LIN,
     "Rodar a carga diária (as agendas ficam pausadas no Free Edition) ou corrigir a tag atualizacao."),
    ("USO02", "Atualização e uso", f"Ativo da camada principal lido nos últimos {JANELA} dias", "ativo", "camada principal", 90, "baixa",
     "Databricks: lineage nas tabelas de sistema", L_LIN,
     "Confirmar se o ativo ainda tem consumidor; sem consumidor, marcar como deprecated."),
    ("USO03", "Atualização e uso", "View responde (sonda diária com DESCRIBE QUERY)", "view", "todos os catálogos do workspace", 100, "alta",
     "Prática do projeto: view recriada ou fonte apagada quebra em silêncio (P16, P28)", L_COMENT,
     "Recriar a view a partir do código ou apagar a quebrada."),
    ("OTM01", "Otimização", f"Tabela gerenciada com Predictive Optimization nos últimos {JANELA} dias", "ativo", "tabelas gerenciadas do pos_venda", 90, "baixa",
     "Databricks: Predictive Optimization", L_PO,
     "ALTER CATALOG ou SCHEMA ... ENABLE PREDICTIVE OPTIMIZATION; tabela pequena ou parada pode não precisar."),
    ("PLT01", "Plataforma", "Job com as tags project e team", "job", "jobs do workspace", 100, "média",
     f"Well-Architected, custo CO-03 (P31); {OBS} (policy_compliance_monitoring)", L_CUSTO,
     "tags no job (no bundle: resources.jobs.<job>.tags)."),
    ("PLT02", "Plataforma", "Job com descrição", "job", "jobs do workspace", 100, "baixa",
     "Prática do projeto", L_JOB, "description no job (no bundle: resources.jobs.<job>.description)."),
    ("PLT03", "Plataforma", "Job com timeout definido", "job", "jobs do workspace", 100, "média",
     "Databricks: configurações de job (Timeout)", L_JOB, "timeout_seconds no job, acima da duração normal."),
    ("PLT04", "Plataforma", "Warehouse com auto-stop de até 30 minutos", "warehouse", "warehouses do workspace", 100, "média",
     f"{OBS} (workspace_health_summary); Well-Architected, custo", L_WH, "auto_stop_mins do warehouse."),
    ("PLT05", "Plataforma", "Warehouse com as tags project e team", "warehouse", "warehouses do workspace", 100, "baixa",
     "Well-Architected, custo CO-03 (P31)", L_CUSTO, "tags do warehouse (compartilhado: team = plataforma)."),
    ("PLT06", "Plataforma", f"Alerta SQL com até {ALERTA_MAX_DIA} disparos por dia", "alerta", "alertas SQL do workspace", 100, "média",
     "Prática do projeto: cada disparo acorda o warehouse; o alerta horário custou US$ 29,73 em 7 dias (L79)", L_ALERTA,
     "Espaçar a agenda do alerta (ou pausar no Free Edition); juntar condições parecidas num alerta só."),
]

# avaliação das ações de observabilidade que já rodam no workspace (23/11/2026); os números vivos vêm das visões
ACOES = [
    ("Materialização diária das tabelas de sistema", "job", "%Materializacao Diaria%",
     "Recria 10 tabelas em main.observabilidade_dev (clusters, policies, warehouses, custo) e o histórico de tamanho das tabelas, todo dia às 6h.",
     "Roda sem falha, mas 7 das 10 tabelas ficam vazias: tratam de clusters clássicos, spot e policies, que o Free Edition não tem. O histórico de tamanho funciona.",
     "internalizar",
     "As regras de warehouse e de tags viram PLT01 a PLT05 aqui; as de cluster não se aplicam ao Free Edition. É o job de observabilidade mais caro.",
     "pos_venda.conformidade (PLT01 a PLT05) e pos_venda.finops (armazenamento)"),
    ("Detecção de anomalias: auditoria e segurança", "job", "%Deteccao de Anomalias%",
     "Consulta clusters sem policy, warehouses e eventos de permissão no audit log, todo dia às 7h; o resultado fica só na saída do notebook.",
     "Roda sem falha; a parte de clusters volta vazia no Free Edition.",
     "internalizar",
     "Policies e auto-stop viram regras com meta e histórico; os eventos de permissão seguem no notebook até virarem regra.",
     "pos_venda.conformidade (PLT04)"),
    ("Triagem automática de falhas de job", "job", "%Auto-Triagem de Falhas%",
     "Classifica as execuções com falha e mantém a view vw_triagem_falhas_jobs, todo dia às 7h30.",
     "Roda sem falha e classifica as falhas recentes.",
     "manter",
     "É operação, não conformidade. O custo das falhas já aparece em pos_venda.finops.uso_jobs_diario.",
     "P28 (matriz de resiliência) consulta a triagem"),
    ("Relatório executivo semanal", "job", "%Relatorio Executivo Semanal%",
     "Monta um relatório e grava em arquivo no volume main.observabilidade_dev.relatorios, toda segunda às 7h.",
     "Roda sem falha; não envia nada para fora do workspace (o envio por webhook ficou para depois).",
     "manter",
     "Próximo passo natural: incluir o resumo de pos_venda.conformidade.boas_praticas_dados.",
     "nenhum por enquanto"),
    ("Alertas SQL do bundle (5)", "alertas", "%",
     "Cinco alertas SQL no warehouse: queries lentas (de hora em hora), jobs com falha (3 vezes ao dia), custo diário alto, recursos sem tag com custo alto e tráfego no AI Gateway (1 vez ao dia).",
     "Rodam como jobs ocultos, que não aparecem na lista de jobs. São a maior parte do custo de observabilidade: US$ 816,20 desde julho, quase tudo do alerta horário, porque cada disparo acorda o warehouse.",
     "consertar",
     "Espaçar o alerta de queries lentas (até 4 disparos por dia) ou pausá-lo no Free Edition; os outros quatro ficam como estão.",
     "pos_venda.conformidade (PLT06) e pos_venda.finops (custo por consulta)"),
    ("Rightsizing semanal de clusters", "job", "%Rightsizing Semanal%",
     "Sugere o tamanho de cluster a partir de system.compute.node_timeline, toda segunda às 8h.",
     "Falha em toda execução (NameError: name 'null' is not defined) e, no Free Edition, não há cluster clássico para dimensionar.",
     "aposentar",
     "Pausar no Free Edition; consertar o notebook só ao migrar para um workspace com clusters clássicos.",
     "nenhum"),
    ("Visões vw_* em main.observabilidade_dev", "visões", "main.observabilidade_dev",
     "17 visões sobre as tabelas de sistema (custo, jobs, consultas, Genie, tags, inventário), criadas por um job sem agenda.",
     "As de custo repetem pos_venda.finops sem a atribuição por projeto; vw_governanca_cobertura_tags conta registros, não custo; vw_inventario_tabelas não traz descrição, tags nem dono.",
     "internalizar",
     "pos_venda.finops cobre custo e uso com FOCUS e atribuição; pos_venda.conformidade.ativos substitui o inventário.",
     "pos_venda.finops e pos_venda.conformidade.ativos"),
    ("Framework FinOps antigo em finops.observability", "visões", "finops.observability",
     "28 visões FOCUS e de histórias executivas, de um framework anterior.",
     "Parte das visões não responde; a sonda diária mostra quantas.",
     "manter só leitura",
     "Decisão do dono: não alterar. A sonda mede as quebradas sem mexer nelas.",
     "pos_venda.conformidade (USO03)"),
]

D = {
    "esquema": "Schema do Unity Catalog.",
    "camada": "Camada do fluxo (landing, fonte, bronze, silver, gold, qualidade, ontologia, regras, bi ou monitoramento).",
    "papel": "principal (fluxo diário), legado (medalhão da primeira versão), apoio (monitoramento), interno (tabela de apoio que o Lakeflow cria: __materialization_*, event_log_*; fica fora das regras), não classificado, fora do domínio (outro catálogo) ou plataforma (job ou warehouse).",
    "regra_id": "Código da regra de conformidade (DOC, TAG, LGPD, EST, USO, OTM, PLT).",
    "dimensao": "Dimensão da regra: documentação, tags governadas, dados pessoais (LGPD), confiança e estrutura, atualização e uso, otimização ou plataforma.",
    "regra": "O que a regra exige.",
    "objeto": "Tipo do objeto verificado: ativo, coluna, schema, tag, view, job, warehouse ou alerta.",
    "escopo": "Onde a regra se aplica.",
    "meta_pct": "Meta de conformidade, em porcentagem dos objetos verificados.",
    "severidade": "alta, média ou baixa. Alta abaixo da meta vira crítico.",
    "origem": "De onde vem a regra: documentação Databricks, Well-Architected, LGPD, bundle de observabilidade ou prática do projeto (Pxx do framework).",
    "link": "Link da fonte da regra.",
    "como_corrigir": "Como colocar o objeto em conformidade.",
    "tag": "Chave da tag governada.",
    "valores": "Valores permitidos pela política da tag.",
    "catalogo": "Catálogo do Unity Catalog.",
    "ativo": "Tabela, view, metric view, materialized view ou streaming table (ou o nome do job ou warehouse).",
    "tipo": "Tipo do objeto no Unity Catalog (MANAGED, VIEW, METRIC_VIEW, MATERIALIZED_VIEW, STREAMING_TABLE...) ou tipo do warehouse.",
    "tipo_dono": "pessoa, grupo ou service principal, ou sistema (objeto gerenciado por pipeline).",
    "dono": "Dono do objeto no Unity Catalog.",
    "descricao": "Descrição (comentário) do objeto no Unity Catalog.",
    "tamanho_descricao": "Número de caracteres da descrição, sem espaços nas pontas.",
    "colunas": "Número de colunas.",
    "colunas_sem_descricao": "Colunas sem descrição.",
    "tags": "Tags do objeto (chave e valor).",
    "certificacao": "Valor da tag de sistema system.certification_status (certified ou deprecated).",
    "atualizacao": "Frequência declarada na tag atualizacao (diaria ou carga_unica).",
    "colunas_dado_pessoal": "Colunas com a tag dado_pessoal.",
    "colunas_sensiveis": "Colunas com dado_pessoal = sensivel.",
    "tem_pk": "Verdadeiro quando o ativo tem chave primária.",
    "fks": "Número de chaves estrangeiras.",
    "criado_em": "Quando o objeto foi criado.",
    "alterado_em": "Última alteração registrada no information_schema (definição, dados ou metadados).",
    "ultima_escrita": "Última escrita no ativo registrada pelo lineage (90 dias).",
    "ultima_leitura": f"Última leitura do ativo registrada pelo lineage ({JANELA} dias).",
    "leituras_30d": f"Leituras do ativo registradas pelo lineage nos últimos {JANELA} dias.",
    "ultima_otimizacao": "Última operação bem-sucedida de Predictive Optimization.",
    "otimizacoes_30d": f"Operações bem-sucedidas de Predictive Optimization nos últimos {JANELA} dias.",
    "tipo_ativo": "Tipo do ativo que contém a coluna, no Unity Catalog.",
    "coluna": "Nome da coluna (vazio quando a verificação é do ativo, schema, job ou warehouse).",
    "posicao": "Posição da coluna no ativo.",
    "tipo_dado": "Tipo de dado da coluna.",
    "dado_pessoal": "Valor da tag dado_pessoal (identificacao, contato, endereco, perfil ou sensivel).",
    "classes_automaticas": "Classes da classificação automática do Databricks (tags class.*), sem o prefixo.",
    "nome_sugere_dado_pessoal": "Verdadeiro quando o nome da coluna indica dado pessoal (mesma regra de governanca/auditar_metadados.py).",
    "tipo_recurso": "job, warehouse ou alerta (alerta SQL).",
    "disparos_dia": "Disparos por dia de um alerta SQL, calculados da agenda (cron); vazio para jobs e warehouses.",
    "recurso_id": "Identificador do job, do warehouse ou do alerta.",
    "nome": "Nome do job, do warehouse ou do alerta (sem o prefixo de desenvolvimento do bundle).",
    "projeto": "Valor da tag project.",
    "time": "Valor da tag team.",
    "tem_descricao": "Verdadeiro quando o job tem descrição.",
    "timeout_segundos": "Timeout do job, em segundos (0 = sem timeout).",
    "pausado": "Verdadeiro quando a agenda do job ou do alerta está pausada.",
    "auto_stop_minutos": "Minutos de inatividade até o warehouse desligar.",
    "conforme": "Verdadeiro quando o objeto atende à regra.",
    "detalhe": "O que foi encontrado no objeto.",
    "aplicavel": "Objetos verificados pela regra.",
    "conformes": "Objetos que atendem à regra.",
    "falhas": "Objetos que não atendem à regra.",
    "pct_conforme": "Porcentagem dos objetos verificados que atendem.",
    "situacao": "atende (na meta), atenção (abaixo da meta), crítico (severidade alta abaixo da meta) ou sem dados (nenhum objeto verificado).",
    "verificacoes": "Verificações (objeto × regra).",
    "acao": "Ação de observabilidade que já roda no workspace.",
    "o_que_faz": "O que a ação faz.",
    "achado": "O que a avaliação encontrou (23/11/2026).",
    "veredito": "internalizar (a lógica passa a viver aqui), manter (segue no bundle), consertar, aposentar ou manter só leitura.",
    "motivo": "Por que o veredito.",
    "no_framework": "Onde a ação ficou no framework.",
    "execucoes_30d": "Execuções nos últimos 30 dias: do job (pos_venda.finops.uso_jobs_diario) ou consultas disparadas pelos alertas.",
    "falhas_30d": "Execuções com falha nos últimos 30 dias.",
    "custo_lista_usd_30d": "Custo a preço de lista nos últimos 30 dias, em USD.",
    "views_sondadas": "Views do schema verificadas na última sonda.",
    "views_respondem": "Views do schema que responderam na última sonda.",
    "sondado_em": "Momento da sonda (UTC).",
    "responde": "Verdadeiro quando DESCRIBE QUERY na view funcionou.",
    "erro": "Mensagem de erro da sonda, quando a view não responde.",
    "registrado_em": "Dia do registro no histórico.",
}


def q(s):
    return s.replace("\\", "\\\\").replace("'", "''")


def lista_sql(itens):
    return ", ".join(f"'{q(i)}'" for i in itens)


def cols(*nomes, extra=None):
    extra = extra or {}
    return [(n, extra.get(n, D[n])) for n in nomes]


def politicas():
    arq = AQUI / "politicas_tags.json"
    return json.loads(arq.read_text(encoding="utf-8"))["politicas"] if arq.exists() else []


def alertas():
    arq = AQUI / "alertas.json"
    return json.loads(arq.read_text(encoding="utf-8"))["alertas"] if arq.exists() else []


def disparos_por_dia(cron):
    """Disparos por dia de uma agenda Quartz (seg min hora dia mês dia-da-semana): minutos × horas."""
    def conta(campo, total):
        if campo in ("*", "?"):
            return total
        n = 0
        for parte in campo.split(","):
            if "/" in parte:
                ini, passo = parte.split("/")
                ini = 0 if ini in ("*", "") else int(ini.split("-")[0])
                n += len(range(ini, total, int(passo)))
            elif "-" in parte:
                a, b = parte.split("-")
                n += int(b) - int(a) + 1
            else:
                n += 1
        return n
    campos = cron.split()
    return conta(campos[1], 60) * conta(campos[2], 24)


def visoes():
    V = []
    excl = lista_sql(EXCLUIDOS)

    V.append(("config_camadas", "Papel de cada schema do catálogo pos_venda: principal (fluxo diário), legado (medalhão da primeira versão) ou apoio (monitoramento). Editado em conformidade/gerar_conformidade.py.",
              cols("esquema", "camada", "papel"),
              "SELECT * FROM VALUES\n    " + ",\n    ".join(f"('{e}', '{c}', '{p}')" for e, c, p in CAMADAS) + "\n  AS t(esquema, camada, papel)"))

    linhas = ",\n    ".join(
        f"('{i}', '{q(d)}', '{q(r)}', '{o}', '{q(e)}', {m}, '{s}', '{q(org)}', '{l}', '{q(c)}')"
        for i, d, r, o, e, m, s, org, l, c in REGRAS)
    V.append(("config_regras", "Catálogo de regras de conformidade: dimensão, meta, severidade, origem, link da fonte e como corrigir. Editado em conformidade/gerar_conformidade.py.",
              cols("regra_id", "dimensao", "regra", "objeto", "escopo", "meta_pct", "severidade", "origem", "link", "como_corrigir"),
              f"SELECT regra_id, dimensao, regra, objeto, escopo, CAST(meta_pct AS DOUBLE) AS meta_pct, severidade, origem, link, como_corrigir FROM VALUES\n    {linhas}\n"
              "  AS t(regra_id, dimensao, regra, objeto, escopo, meta_pct, severidade, origem, link, como_corrigir)"))

    pol = politicas()
    pol_sql = ",\n    ".join(f"('{q(p['tag'])}', array({lista_sql(p['valores'])}), '{q(p['descricao'])}')" for p in pol) \
        or "('sem_politica', array('x'), 'rode a ação politicas')"
    V.append(("config_tags_governadas", "Tags governadas com valores permitidos (tag policies do workspace), lidas pela API em conformidade/politicas_tags.json.",
              cols("tag", "valores", "descricao", extra={"descricao": "Descrição da política da tag."}),
              f"SELECT * FROM VALUES\n    {pol_sql}\n  AS t(tag, valores, descricao)"))

    V.append(("ativos", "Inventário de tabelas e views do workspace (menos system e samples) com o que a conformidade mede: descrição, colunas sem descrição, tags, dado pessoal, chave primária, dono, última escrita e leitura (lineage) e Predictive Optimization. Substitui main.observabilidade_dev.vw_inventario_tabelas.",
              cols("catalogo", "esquema", "ativo", "tipo", "papel", "camada", "tipo_dono", "dono", "descricao", "tamanho_descricao",
                   "colunas", "colunas_sem_descricao", "tags", "certificacao", "atualizacao", "colunas_dado_pessoal", "colunas_sensiveis",
                   "tem_pk", "fks", "criado_em", "alterado_em", "ultima_escrita", "ultima_leitura", "leituras_30d",
                   "ultima_otimizacao", "otimizacoes_30d"),
              f"""WITH cam AS (SELECT * FROM {S}.config_camadas),
t AS (
  SELECT table_catalog, table_schema, table_name, table_type, table_owner, comment, created, last_altered
  FROM system.information_schema.tables
  WHERE table_catalog NOT IN ({excl}) AND table_schema <> 'information_schema'),
c AS (
  SELECT table_catalog, table_schema, table_name, count(*) AS colunas,
         count_if(comment IS NULL OR trim(comment) = '') AS colunas_sem_descricao
  FROM system.information_schema.columns
  WHERE table_catalog NOT IN ({excl}) AND table_schema <> 'information_schema'
  GROUP BY ALL),
tg AS (
  SELECT catalog_name, schema_name, table_name, map_from_entries(collect_list(struct(tag_name, tag_value))) AS tags
  FROM system.information_schema.table_tags
  GROUP BY ALL),
ct AS (
  SELECT catalog_name, schema_name, table_name,
         count_if(tag_name = 'dado_pessoal') AS colunas_dado_pessoal,
         count_if(tag_name = 'dado_pessoal' AND tag_value = 'sensivel') AS colunas_sensiveis
  FROM system.information_schema.column_tags
  GROUP BY ALL),
pk AS (
  SELECT table_catalog, table_schema, table_name,
         bool_or(constraint_type = 'PRIMARY KEY') AS tem_pk, count_if(constraint_type = 'FOREIGN KEY') AS fks
  FROM system.information_schema.table_constraints
  GROUP BY ALL),
lin AS (
  SELECT source_table_catalog AS cat, source_table_schema AS sch, source_table_name AS tab,
         max(event_time) AS ultima_leitura, count(*) AS leituras
  FROM system.access.table_lineage
  WHERE event_date >= current_date() - {JANELA} AND source_table_name IS NOT NULL
  GROUP BY ALL),
esc AS (
  SELECT target_table_catalog AS cat, target_table_schema AS sch, target_table_name AS tab, max(event_time) AS ultima_escrita
  FROM system.access.table_lineage
  WHERE event_date >= current_date() - 90 AND target_table_name IS NOT NULL
  GROUP BY ALL),
po AS (
  SELECT catalog_name, schema_name, table_name, max(start_time) AS ultima_otimizacao, count(*) AS otimizacoes
  FROM system.storage.predictive_optimization_operations_history
  WHERE start_time >= current_date() - {JANELA} AND operation_status = 'SUCCESSFUL'
  GROUP BY ALL)
SELECT t.table_catalog, t.table_schema, t.table_name, t.table_type,
  CASE WHEN {INTERNO.format(n="t.table_name")} THEN 'interno'
       WHEN t.table_catalog = '{DOMINIO}' THEN coalesce(cam.papel, 'não classificado') ELSE 'fora do domínio' END,
  cam.camada,
  CASE WHEN t.table_owner = 'System user' THEN 'sistema' WHEN t.table_owner LIKE '%@%' THEN 'pessoa' ELSE 'grupo ou service principal' END,
  t.table_owner, t.comment, length(trim(coalesce(t.comment, ''))),
  coalesce(c.colunas, 0), coalesce(c.colunas_sem_descricao, 0),
  coalesce(tg.tags, map_from_arrays(CAST(array() AS ARRAY<STRING>), CAST(array() AS ARRAY<STRING>))),
  try_element_at(tg.tags, 'system.certification_status'), try_element_at(tg.tags, 'atualizacao'),
  coalesce(ct.colunas_dado_pessoal, 0), coalesce(ct.colunas_sensiveis, 0),
  coalesce(pk.tem_pk, false), coalesce(pk.fks, 0),
  t.created, t.last_altered, esc.ultima_escrita, lin.ultima_leitura, coalesce(lin.leituras, 0),
  po.ultima_otimizacao, coalesce(po.otimizacoes, 0)
FROM t
LEFT JOIN cam ON t.table_catalog = '{DOMINIO}' AND t.table_schema = cam.esquema
LEFT JOIN c ON t.table_catalog = c.table_catalog AND t.table_schema = c.table_schema AND t.table_name = c.table_name
LEFT JOIN tg ON t.table_catalog = tg.catalog_name AND t.table_schema = tg.schema_name AND t.table_name = tg.table_name
LEFT JOIN ct ON t.table_catalog = ct.catalog_name AND t.table_schema = ct.schema_name AND t.table_name = ct.table_name
LEFT JOIN pk ON t.table_catalog = pk.table_catalog AND t.table_schema = pk.table_schema AND t.table_name = pk.table_name
LEFT JOIN lin ON t.table_catalog = lin.cat AND t.table_schema = lin.sch AND t.table_name = lin.tab
LEFT JOIN esc ON t.table_catalog = esc.cat AND t.table_schema = esc.sch AND t.table_name = esc.tab
LEFT JOIN po ON t.table_catalog = po.catalog_name AND t.table_schema = po.schema_name AND t.table_name = po.table_name"""))

    V.append(("colunas", "Colunas do catálogo pos_venda com descrição, tag dado_pessoal, classes da classificação automática (class.*) e se o nome indica dado pessoal.",
              cols("esquema", "ativo", "tipo_ativo", "papel", "camada", "coluna", "posicao", "tipo_dado", "descricao", "tamanho_descricao",
                   "dado_pessoal", "classes_automaticas", "nome_sugere_dado_pessoal"),
              f"""WITH cam AS (SELECT * FROM {S}.config_camadas),
col AS (
  SELECT table_schema, table_name, column_name, ordinal_position, full_data_type, comment
  FROM system.information_schema.columns
  WHERE table_catalog = '{DOMINIO}' AND table_schema <> 'information_schema'),
t AS (SELECT table_schema, table_name, table_type FROM system.information_schema.tables WHERE table_catalog = '{DOMINIO}'),
ct AS (
  SELECT schema_name, table_name, column_name,
         max(CASE WHEN tag_name = 'dado_pessoal' THEN tag_value END) AS dado_pessoal,
         array_sort(collect_set(CASE WHEN tag_name LIKE 'class.%' THEN substr(tag_name, 7) END)) AS classes
  FROM system.information_schema.column_tags
  WHERE catalog_name = '{DOMINIO}'
  GROUP BY ALL)
SELECT col.table_schema, col.table_name, t.table_type,
  CASE WHEN {INTERNO.format(n="col.table_name")} THEN 'interno' ELSE coalesce(cam.papel, 'não classificado') END, cam.camada,
  col.column_name, col.ordinal_position, col.full_data_type, col.comment, length(trim(coalesce(col.comment, ''))),
  ct.dado_pessoal, coalesce(ct.classes, CAST(array() AS ARRAY<STRING>)),
  (lower(col.column_name) RLIKE '{PII}' AND NOT lower(col.column_name) RLIKE '{NAO_PII}')
FROM col
LEFT JOIN t ON col.table_schema = t.table_schema AND col.table_name = t.table_name
LEFT JOIN cam ON col.table_schema = cam.esquema
LEFT JOIN ct ON col.table_schema = ct.schema_name AND col.table_name = ct.table_name AND col.column_name = ct.column_name"""))

    V.append(("recursos", "Jobs e warehouses ativos do workspace (versão mais recente em system.lakeflow.jobs e system.compute.warehouses) com tags, descrição, timeout, agenda e auto-stop. Regras internalizadas do bundle observabilidade-framework.",
              cols("tipo_recurso", "recurso_id", "nome", "tags", "projeto", "time", "tem_descricao", "timeout_segundos", "pausado",
                   "auto_stop_minutos", "disparos_dia", "tipo", "alterado_em"),
              """WITH j AS (
  SELECT * FROM (
    SELECT job_id, name, tags, description, timeout_seconds, paused, change_time, delete_time,
           row_number() OVER (PARTITION BY workspace_id, job_id ORDER BY change_time DESC) AS rn
    FROM system.lakeflow.jobs)
  WHERE rn = 1 AND delete_time IS NULL),
w AS (
  SELECT * FROM (
    SELECT warehouse_id, warehouse_name, warehouse_type, auto_stop_minutes, tags, change_time, delete_time,
           row_number() OVER (PARTITION BY workspace_id, warehouse_id ORDER BY change_time DESC) AS rn
    FROM system.compute.warehouses)
  WHERE rn = 1 AND delete_time IS NULL)
SELECT 'job', CAST(job_id AS STRING), name, tags, try_element_at(tags, 'project'), try_element_at(tags, 'team'),
  length(trim(coalesce(description, ''))) > 0, timeout_seconds, paused, CAST(NULL AS INT), CAST(NULL AS INT), 'job', change_time
FROM j
UNION ALL
SELECT 'warehouse', warehouse_id, warehouse_name, tags, try_element_at(tags, 'project'), try_element_at(tags, 'team'),
  NULL, NULL, NULL, auto_stop_minutes, NULL, warehouse_type, change_time
FROM w""" + "".join(
        f"""
UNION ALL
SELECT 'alerta', '{a['id']}', '{q(a['nome'])}', NULL, NULL, NULL, {str(bool(a['descricao'])).lower()}, NULL, {str(a['pausado']).lower()}, NULL,
  {a['disparos_dia']}, 'alerta SQL', {f"TIMESTAMP '{a['atualizado_em']}'" if a['atualizado_em'] else 'NULL'}""" for a in alertas())))

    gov_pol = ", ".join(f"'{q(p['tag'])}'" for p in pol) or "''"
    V.append(("achados", "Uma linha por verificação (objeto × regra): conforme ou não, com o detalhe e como corrigir. Base de pendencias, boas_praticas_dados, squad_por_schema, plataforma_por_catalogo e da metric view mv_conformidade.",
              cols("regra_id", "dimensao", "regra", "severidade", "objeto", "catalogo", "esquema", "ativo", "coluna", "papel",
                   "conforme", "detalhe", "como_corrigir"),
              f"""WITH a AS (SELECT * FROM {S}.ativos),
c AS (SELECT * FROM {S}.colunas),
r AS (SELECT * FROM {S}.recursos),
cam AS (SELECT * FROM {S}.config_camadas),
gov AS (SELECT tag, valores FROM {S}.config_tags_governadas WHERE size(valores) > 0),
stg AS (
  SELECT schema_name, collect_set(tag_name) AS tags
  FROM system.information_schema.schema_tags WHERE catalog_name = '{DOMINIO}' GROUP BY ALL),
sch AS (
  SELECT s.catalog_name AS catalogo, s.schema_name AS esquema, coalesce(cam.papel, 'não classificado') AS papel,
         length(trim(coalesce(s.comment, ''))) AS tamanho_descricao, coalesce(stg.tags, CAST(array() AS ARRAY<STRING>)) AS tags
  FROM system.information_schema.schemata s
  LEFT JOIN cam ON s.schema_name = cam.esquema
  LEFT JOIN stg ON s.schema_name = stg.schema_name
  WHERE s.catalog_name = '{DOMINIO}' AND s.schema_name NOT IN ('information_schema', 'default')),
tt AS (
  SELECT 'tag de ativo' AS objeto, schema_name, table_name, CAST(NULL AS STRING) AS column_name, tag_name, tag_value
  FROM system.information_schema.table_tags WHERE catalog_name = '{DOMINIO}' AND tag_name IN ({gov_pol})
  UNION ALL
  SELECT 'tag de coluna', schema_name, table_name, column_name, tag_name, tag_value
  FROM system.information_schema.column_tags WHERE catalog_name = '{DOMINIO}' AND tag_name IN ({gov_pol})
  UNION ALL
  SELECT 'tag de schema', schema_name, NULL, NULL, tag_name, tag_value
  FROM system.information_schema.schema_tags WHERE catalog_name = '{DOMINIO}' AND tag_name IN ({gov_pol})),
sonda AS (SELECT * FROM {S}.sonda_views WHERE sondado_em = (SELECT max(sondado_em) FROM {S}.sonda_views)),
base AS (
  SELECT 'DOC01' AS regra_id, 'ativo' AS objeto, catalogo, esquema, ativo, CAST(NULL AS STRING) AS coluna, papel,
         tamanho_descricao > 0 AS conforme, CASE WHEN tamanho_descricao > 0 THEN 'tem descrição' ELSE 'sem descrição' END AS detalhe
  FROM a WHERE papel <> 'interno'
  UNION ALL
  SELECT 'DOC02', 'ativo', catalogo, esquema, ativo, NULL, papel, tamanho_descricao >= {MIN_DESC_ATIVO}, concat(tamanho_descricao, ' caracteres')
  FROM a WHERE catalogo = '{DOMINIO}' AND papel <> 'interno' AND tamanho_descricao > 0
  UNION ALL
  SELECT 'DOC03', 'coluna', '{DOMINIO}', esquema, ativo, coluna, papel, tamanho_descricao > 0,
         CASE WHEN tamanho_descricao > 0 THEN 'tem descrição' ELSE 'sem descrição' END
  FROM c WHERE papel <> 'interno'
  UNION ALL
  SELECT 'DOC04', 'coluna', '{DOMINIO}', esquema, ativo, coluna, papel, tamanho_descricao >= {MIN_DESC_COLUNA}, concat(tamanho_descricao, ' caracteres')
  FROM c WHERE papel <> 'interno' AND tamanho_descricao > 0
  UNION ALL
  SELECT 'DOC05', 'schema', catalogo, esquema, NULL, NULL, papel, tamanho_descricao > 0,
         CASE WHEN tamanho_descricao > 0 THEN 'tem descrição' ELSE 'sem descrição' END
  FROM sch
  UNION ALL
  SELECT 'TAG01', 'ativo', catalogo, esquema, ativo, NULL, papel,
         size(array_except(array({lista_sql(TAGS_ATIVO)}), map_keys(tags))) = 0,
         CASE WHEN size(array_except(array({lista_sql(TAGS_ATIVO)}), map_keys(tags))) = 0 THEN 'tem as três'
              ELSE concat('faltam: ', array_join(array_except(array({lista_sql(TAGS_ATIVO)}), map_keys(tags)), ', ')) END
  FROM a WHERE papel = 'principal'
  UNION ALL
  SELECT 'TAG02', 'ativo', catalogo, esquema, ativo, NULL, papel, atualizacao IS NOT NULL,
         coalesce(concat('atualizacao = ', atualizacao), 'sem a tag')
  FROM a WHERE papel = 'principal'
  UNION ALL
  SELECT 'TAG03', tt.objeto, '{DOMINIO}', tt.schema_name, tt.table_name, tt.column_name, coalesce(cam.papel, 'não classificado'),
         array_contains(gov.valores, tt.tag_value), concat(tt.tag_name, ' = ', coalesce(tt.tag_value, '(vazio)'))
  FROM tt JOIN gov ON tt.tag_name = gov.tag LEFT JOIN cam ON tt.schema_name = cam.esquema
  UNION ALL
  SELECT 'TAG04', 'schema', catalogo, esquema, NULL, NULL, papel,
         size(array_except(array({lista_sql(TAGS_SCHEMA)}), tags)) = 0,
         CASE WHEN size(array_except(array({lista_sql(TAGS_SCHEMA)}), tags)) = 0 THEN 'tem domain e camada'
              ELSE concat('faltam: ', array_join(array_except(array({lista_sql(TAGS_SCHEMA)}), tags), ', ')) END
  FROM sch WHERE papel = 'principal'
  UNION ALL
  SELECT 'LGPD01', 'coluna', '{DOMINIO}', esquema, ativo, coluna, papel, dado_pessoal IS NOT NULL,
         coalesce(concat('dado_pessoal = ', dado_pessoal), 'o nome indica dado pessoal e não há a tag')
  FROM c WHERE papel IN ('principal', 'legado') AND nome_sugere_dado_pessoal
  UNION ALL
  SELECT 'LGPD02', 'coluna', '{DOMINIO}', esquema, ativo, coluna, papel, dado_pessoal IS NOT NULL,
         concat('classes: ', array_join(classes_automaticas, ', '), CASE WHEN dado_pessoal IS NULL THEN ' (sem dado_pessoal)' ELSE '' END)
  FROM c WHERE papel IN ('principal', 'legado') AND size(classes_automaticas) > 0
  UNION ALL
  SELECT 'LGPD03', 'ativo', catalogo, esquema, ativo, NULL, papel, coalesce(try_element_at(tags, 'contem_dado_pessoal') = 'sim', false),
         concat(colunas_dado_pessoal, ' coluna(s) com dado_pessoal')
  FROM a WHERE catalogo = '{DOMINIO}' AND papel IN ('principal', 'legado') AND colunas_dado_pessoal > 0
  UNION ALL
  SELECT 'LGPD04', 'ativo', catalogo, esquema, ativo, NULL, papel, colunas_dado_pessoal > 0,
         concat(colunas_dado_pessoal, ' coluna(s) com dado_pessoal')
  FROM a WHERE catalogo = '{DOMINIO}' AND try_element_at(tags, 'contem_dado_pessoal') = 'sim'
  UNION ALL
  SELECT 'LGPD05', 'ativo', catalogo, esquema, ativo, NULL, papel, coalesce(try_element_at(tags, 'contem_dado_sensivel') = 'sim', false),
         concat(colunas_sensiveis, ' coluna(s) sensível(is)')
  FROM a WHERE catalogo = '{DOMINIO}' AND papel IN ('principal', 'legado') AND colunas_sensiveis > 0
  UNION ALL
  SELECT 'EST01', 'ativo', catalogo, esquema, ativo, NULL, papel, tem_pk,
         concat(try_element_at(tags, 'tipo_ativo'), CASE WHEN tem_pk THEN ' com chave primária' ELSE ' sem chave primária' END)
  FROM a WHERE catalogo = '{DOMINIO}' AND papel = 'principal' AND esquema = 'gold' AND tipo = 'MANAGED'
    AND try_element_at(tags, 'tipo_ativo') IN ('dimensao', 'fato', 'ponte')
  UNION ALL
  SELECT 'EST02', 'ativo', catalogo, esquema, ativo, NULL, papel, coalesce(certificacao = 'certified', false), coalesce(certificacao, 'sem certificação')
  FROM a WHERE catalogo = '{DOMINIO}' AND papel = 'principal' AND esquema IN ('gold', 'ontologia')
  UNION ALL
  SELECT 'EST03', 'ativo', catalogo, esquema, ativo, NULL, papel, coalesce(certificacao = 'deprecated', false), coalesce(certificacao, 'sem certificação')
  FROM a WHERE catalogo = '{DOMINIO}' AND papel = 'legado'
  UNION ALL
  SELECT 'EST04', 'ativo', catalogo, esquema, ativo, NULL, papel, tipo_dono <> 'pessoa', tipo_dono
  FROM a WHERE catalogo = '{DOMINIO}' AND papel <> 'interno'
  UNION ALL
  SELECT 'USO01', 'ativo', catalogo, esquema, ativo, NULL, papel,
         coalesce(ultima_escrita, alterado_em) >= current_timestamp() - INTERVAL {FRESCOR_DIAS} DAYS,
         concat('última escrita: ', date_format(coalesce(ultima_escrita, alterado_em), 'yyyy-MM-dd HH:mm'))
  FROM a WHERE catalogo = '{DOMINIO}' AND papel = 'principal' AND atualizacao = 'diaria'
    AND tipo IN ('MANAGED', 'STREAMING_TABLE', 'MATERIALIZED_VIEW')
  UNION ALL
  SELECT 'USO02', 'ativo', catalogo, esquema, ativo, NULL, papel, leituras_30d > 0, concat(leituras_30d, ' leitura(s) em {JANELA} dias')
  FROM a WHERE catalogo = '{DOMINIO}' AND papel = 'principal'
  UNION ALL
  SELECT 'USO03', 'view', sonda.catalogo, sonda.esquema, sonda.ativo, NULL, coalesce(a.papel, 'fora do domínio'), sonda.responde,
         CASE WHEN sonda.responde THEN 'responde' ELSE substr(coalesce(sonda.erro, 'erro'), 1, 300) END
  FROM sonda LEFT JOIN a ON sonda.catalogo = a.catalogo AND sonda.esquema = a.esquema AND sonda.ativo = a.ativo
  UNION ALL
  SELECT 'OTM01', 'ativo', catalogo, esquema, ativo, NULL, papel, otimizacoes_30d > 0, concat(otimizacoes_30d, ' operação(ões) em {JANELA} dias')
  FROM a WHERE catalogo = '{DOMINIO}' AND papel <> 'interno' AND tipo = 'MANAGED'
  UNION ALL
  SELECT 'PLT01', 'job', NULL, NULL, nome, NULL, 'plataforma', projeto IS NOT NULL AND time IS NOT NULL,
         concat('project = ', coalesce(projeto, '(sem)'), ', team = ', coalesce(time, '(sem)'))
  FROM r WHERE tipo_recurso = 'job'
  UNION ALL
  SELECT 'PLT02', 'job', NULL, NULL, nome, NULL, 'plataforma', tem_descricao, CASE WHEN tem_descricao THEN 'tem descrição' ELSE 'sem descrição' END
  FROM r WHERE tipo_recurso = 'job'
  UNION ALL
  SELECT 'PLT03', 'job', NULL, NULL, nome, NULL, 'plataforma', coalesce(timeout_segundos, 0) > 0, concat('timeout = ', coalesce(timeout_segundos, 0), ' s')
  FROM r WHERE tipo_recurso = 'job'
  UNION ALL
  SELECT 'PLT04', 'warehouse', NULL, NULL, nome, NULL, 'plataforma', coalesce(auto_stop_minutos, 0) BETWEEN 1 AND 30,
         concat('auto-stop = ', coalesce(auto_stop_minutos, 0), ' min')
  FROM r WHERE tipo_recurso = 'warehouse'
  UNION ALL
  SELECT 'PLT05', 'warehouse', NULL, NULL, nome, NULL, 'plataforma', projeto IS NOT NULL AND time IS NOT NULL,
         concat('project = ', coalesce(projeto, '(sem)'), ', team = ', coalesce(time, '(sem)'))
  FROM r WHERE tipo_recurso = 'warehouse'
  UNION ALL
  SELECT 'PLT06', 'alerta', NULL, NULL, nome, NULL, 'plataforma', pausado OR disparos_dia <= {ALERTA_MAX_DIA},
         concat(disparos_dia, ' disparo(s) por dia', CASE WHEN pausado THEN ' (pausado)' ELSE '' END)
  FROM r WHERE tipo_recurso = 'alerta')
SELECT b.regra_id, g.dimensao, g.regra, g.severidade, b.objeto, b.catalogo, b.esquema, b.ativo, b.coluna, b.papel,
  b.conforme, b.detalhe, g.como_corrigir
FROM base b JOIN {S}.config_regras g ON b.regra_id = g.regra_id"""))

    V.append(("pendencias", "Só as verificações que não atendem: a lista de correções, com severidade e como corrigir.",
              cols("regra_id", "severidade", "dimensao", "regra", "objeto", "catalogo", "esquema", "ativo", "coluna", "papel", "detalhe", "como_corrigir"),
              f"""SELECT regra_id, severidade, dimensao, regra, objeto, catalogo, esquema, ativo, coluna, papel, detalhe, como_corrigir
FROM {S}.achados WHERE NOT conforme"""))

    V.append(("boas_praticas_dados", "Uma linha por regra: objetos verificados, conformes, falhas, porcentagem, meta e situação, com origem e como corrigir. Regra sem objeto verificado fica 'sem dados', nunca 'atende'.",
              cols("regra_id", "dimensao", "regra", "escopo", "severidade", "aplicavel", "conformes", "falhas", "pct_conforme", "meta_pct",
                   "situacao", "origem", "link", "como_corrigir"),
              f"""WITH x AS (SELECT regra_id, count(*) AS aplicavel, count_if(conforme) AS conformes FROM {S}.achados GROUP BY regra_id)
SELECT g.regra_id, g.dimensao, g.regra, g.escopo, g.severidade, coalesce(x.aplicavel, 0), coalesce(x.conformes, 0),
  coalesce(x.aplicavel, 0) - coalesce(x.conformes, 0),
  round(100.0 * x.conformes / nullif(x.aplicavel, 0), 1), g.meta_pct,
  CASE WHEN coalesce(x.aplicavel, 0) = 0 THEN 'sem dados'
       WHEN 100.0 * x.conformes / x.aplicavel >= g.meta_pct THEN 'atende'
       WHEN g.severidade = 'alta' THEN 'crítico'
       ELSE 'atenção' END,
  g.origem, g.link, g.como_corrigir
FROM {S}.config_regras g LEFT JOIN x ON g.regra_id = x.regra_id"""))

    V.append(("squad_por_schema", "Visão do squad: conformidade de cada schema do catálogo pos_venda por dimensão.",
              cols("esquema", "papel", "dimensao", "verificacoes", "conformes", "falhas", "pct_conforme"),
              f"""SELECT esquema, papel, dimensao, count(*), count_if(conforme), count_if(NOT conforme), round(100.0 * count_if(conforme) / count(*), 1)
FROM {S}.achados WHERE catalogo = '{DOMINIO}' AND esquema IS NOT NULL
GROUP BY ALL"""))

    V.append(("plataforma_por_catalogo", "Visão da plataforma: conformidade de cada catálogo do workspace e dos recursos (jobs e warehouses) por dimensão.",
              cols("catalogo", "dimensao", "verificacoes", "conformes", "falhas", "pct_conforme",
                   extra={"catalogo": "Catálogo do Unity Catalog, ou 'recursos do workspace' para jobs e warehouses."}),
              f"""SELECT coalesce(catalogo, 'recursos do workspace'), dimensao, count(*), count_if(conforme), count_if(NOT conforme),
  round(100.0 * count_if(conforme) / count(*), 1)
FROM {S}.achados
GROUP BY ALL"""))

    acoes_sql = ",\n    ".join("(" + ", ".join(f"'{q(x)}'" for x in a) + ")" for a in ACOES)
    V.append(("acoes_observabilidade", "Avaliação das ações de observabilidade que já rodam no workspace (bundle observabilidade-framework e finops.observability): o que fazem, o que se encontrou, veredito e onde ficaram no framework, com execuções, falhas e custo dos últimos 30 dias e a última sonda das views.",
              cols("acao", "tipo", "o_que_faz", "achado", "veredito", "motivo", "no_framework", "execucoes_30d", "falhas_30d",
                   "custo_lista_usd_30d", "pausado", "views_sondadas", "views_respondem",
                   extra={"tipo": "job, alertas (alertas SQL) ou visões (um schema).", "pausado": "Verdadeiro quando a agenda está pausada (vazio para visões)."}),
              f"""WITH acoes AS (
  SELECT * FROM VALUES
    {acoes_sql}
  AS t(acao, tipo, padrao, o_que_faz, achado, veredito, motivo, no_framework)),
j AS (
  SELECT job, sum(execucoes) AS execucoes, sum(falhas) AS falhas, sum(custo_lista_usd) AS custo
  FROM pos_venda.finops.uso_jobs_diario WHERE dia >= current_date() - 30 GROUP BY job),
r AS (SELECT nome, pausado FROM {S}.recursos WHERE tipo_recurso = 'job'),
al AS (
  SELECT count(*) AS consultas, round(sum(c.custo_lista_usd), 2) AS custo
  FROM pos_venda.finops.custo_sql_por_consulta c JOIN system.query.history q ON c.statement_id = q.statement_id
  WHERE c.hora >= current_date() - 30 AND q.start_time >= current_date() - 31 AND q.query_source.alert_id IS NOT NULL),
ra AS (SELECT bool_and(pausado) AS pausados FROM {S}.recursos WHERE tipo_recurso = 'alerta'),
s AS (
  SELECT concat(catalogo, '.', esquema) AS alvo, count(*) AS views, count_if(responde) AS respondem
  FROM {S}.sonda_views WHERE sondado_em = (SELECT max(sondado_em) FROM {S}.sonda_views)
  GROUP BY 1)
SELECT a.acao, a.tipo, a.o_que_faz, a.achado, a.veredito, a.motivo, a.no_framework,
  CASE WHEN a.tipo = 'alertas' THEN (SELECT consultas FROM al) ELSE (SELECT sum(execucoes) FROM j WHERE a.tipo = 'job' AND j.job LIKE a.padrao) END,
  (SELECT sum(falhas) FROM j WHERE a.tipo = 'job' AND j.job LIKE a.padrao),
  CASE WHEN a.tipo = 'alertas' THEN (SELECT custo FROM al) ELSE (SELECT round(sum(custo), 2) FROM j WHERE a.tipo = 'job' AND j.job LIKE a.padrao) END,
  CASE WHEN a.tipo = 'alertas' THEN (SELECT pausados FROM ra) ELSE (SELECT bool_or(pausado) FROM r WHERE a.tipo = 'job' AND r.nome LIKE a.padrao) END,
  (SELECT sum(views) FROM s WHERE a.tipo = 'visões' AND s.alvo = a.padrao),
  (SELECT sum(respondem) FROM s WHERE a.tipo = 'visões' AND s.alvo = a.padrao)
FROM acoes a"""))
    return V


TABELAS = [
    ("sonda_views", "Resultado da sonda diária: cada view, metric view e materialized view do workspace testada com DESCRIBE QUERY (analisa sem executar). Gravado por gerar_conformidade.py registrar.",
     [("sondado_em", "TIMESTAMP"), ("catalogo", "STRING"), ("esquema", "STRING"), ("ativo", "STRING"), ("tipo", "STRING"),
      ("responde", "BOOLEAN"), ("erro", "STRING")]),
    ("historico", "Histórico diário de boas_praticas_dados (uma linha por regra e dia). Gravado por gerar_conformidade.py registrar.",
     [("registrado_em", "DATE"), ("regra_id", "STRING"), ("dimensao", "STRING"), ("regra", "STRING"), ("aplicavel", "BIGINT"),
      ("conformes", "BIGINT"), ("falhas", "BIGINT"), ("pct_conforme", "DOUBLE"), ("meta_pct", "DOUBLE"), ("situacao", "STRING")]),
]

MV = f"""CREATE OR REPLACE VIEW {S}.mv_conformidade
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: {S}.achados
comment: "Conformidade dos dados e do workspace: uma verificação por objeto e regra. Use Conformidade (%) por dimensão, schema ou regra; Pendências conta o que falta corrigir."
dimensions:
  - name: Regra
    expr: regra_id
    comment: "Código da regra (DOC, TAG, LGPD, EST, USO, OTM, PLT)."
  - name: Descrição da regra
    expr: regra
    comment: "O que a regra exige."
  - name: Dimensão
    expr: dimensao
    comment: "Documentação, tags governadas, dados pessoais (LGPD), confiança e estrutura, atualização e uso, otimização ou plataforma."
  - name: Severidade
    expr: severidade
    comment: "alta, média ou baixa."
  - name: Tipo de objeto
    expr: objeto
    comment: "ativo, coluna, schema, tag, view, job ou warehouse."
  - name: Catálogo
    expr: "coalesce(catalogo, 'recursos do workspace')"
    comment: "Catálogo do Unity Catalog, ou recursos do workspace para jobs e warehouses."
  - name: Schema
    expr: esquema
    comment: "Schema do Unity Catalog."
  - name: Papel
    expr: papel
    comment: "principal, legado, apoio, fora do domínio ou plataforma."
measures:
  - name: Verificações
    expr: COUNT(1)
    comment: "Verificações (objeto × regra)."
  - name: Conformes
    expr: "SUM(CASE WHEN conforme THEN 1 ELSE 0 END)"
    comment: "Verificações que atendem à regra."
  - name: Pendências
    expr: "SUM(CASE WHEN conforme THEN 0 ELSE 1 END)"
    comment: "Verificações que não atendem: o que falta corrigir."
  - name: Conformidade (%)
    expr: "ROUND(100.0 * SUM(CASE WHEN conforme THEN 1 ELSE 0 END) / COUNT(1), 1)"
    comment: "Porcentagem das verificações que atendem."
$$"""

ESQUEMA = (f"CREATE SCHEMA IF NOT EXISTS {S} COMMENT 'Conformidade dos dados e do workspace: descrições, tags governadas, dados pessoais (LGPD), "
           f"estrutura, atualização e uso, otimização e plataforma, com meta e histórico. Gerado por conformidade/gerar_conformidade.py.'")


def ddl(nome, comentario, colunas, consulta):
    lista = ",\n  ".join(f"{c} COMMENT '{q(d)}'" for c, d in colunas)
    return f"CREATE OR REPLACE VIEW {S}.{nome} (\n  {lista}\n)\nCOMMENT '{q(comentario)}'\nAS {consulta}"


def ddl_tabela(nome, comentario, colunas):
    lista = ",\n  ".join(f"{c} {t} COMMENT '{q(D[c])}'" for c, t in colunas)
    return f"CREATE TABLE IF NOT EXISTS {S}.{nome} (\n  {lista}\n)\nCOMMENT '{q(comentario)}'"


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def sql(s, exigir=True):
    estado, erro, linhas = executar(s)
    if exigir and estado != "SUCCEEDED":
        raise RuntimeError(f"{s[:120]}... -> {estado}: {erro[:400]}")
    return linhas


def cmd_politicas():
    r = subprocess.run(["databricks", "tag-policies", "list-tag-policies", "--profile", PERFIL, "-o", "json"], capture_output=True, text=True)
    dados = json.loads(r.stdout or "[]")
    dados = dados if isinstance(dados, list) else dados.get("tag_policies", [])
    fora = ("ai.", "sap.", "class.", "system.system_tables")       # políticas de terceiros ou de sistema que não governam o domínio
    pol = sorted(({"tag": p["tag_key"], "valores": [v["name"] for v in p.get("values", [])], "descricao": p.get("description", "")}
                  for p in dados if p.get("values") and not p["tag_key"].startswith(fora)), key=lambda p: p["tag"])
    (AQUI / "politicas_tags.json").write_text(json.dumps({"gerado_em": datetime.date.today().isoformat(), "politicas": pol},
                                                         ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"politicas_tags.json: {len(pol)} tags governadas com valores permitidos: {', '.join(p['tag'] for p in pol)}")


def cmd_alertas():
    r = subprocess.run(["databricks", "alerts-v2", "list-alerts", "--profile", PERFIL, "-o", "json"], capture_output=True, text=True)
    dados = json.loads(r.stdout or "[]")
    dados = dados if isinstance(dados, list) else dados.get("alerts", [])
    lista = []
    for a in dados:
        ag = a.get("schedule") or {}
        cron = ag.get("quartz_cron_schedule") or "0 0 0 * * ?"
        lista.append({"id": a["id"], "nome": re.sub(r"^\[dev [^\]]+\]\s*", "", a.get("display_name", "")),   # sem o usuário
                      "agenda": cron, "fuso": ag.get("timezone_id", ""), "pausado": ag.get("pause_status") == "PAUSED",
                      "disparos_dia": disparos_por_dia(cron), "descricao": bool((a.get("custom_description") or "").strip()),
                      "estado": a.get("lifecycle_state", ""), "warehouse_id": a.get("warehouse_id", ""),
                      "atualizado_em": (a.get("update_time") or "")[:19].replace("T", " ")})
    lista.sort(key=lambda a: a["nome"])
    (AQUI / "alertas.json").write_text(json.dumps({"gerado_em": datetime.date.today().isoformat(), "alertas": lista},
                                                  ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"alertas.json: {len(lista)} alertas SQL; disparos por dia: {', '.join(str(a['disparos_dia']) for a in lista)}")


def cmd_gerar():
    V = visoes()
    partes = [ESQUEMA] + [ddl_tabela(*t) for t in TABELAS] + [ddl(*v) for v in V] + [MV]
    (AQUI / "conformidade.sql").write_text(";\n\n".join(partes) + ";\n", encoding="utf-8")
    print(f"conformidade/conformidade.sql: schema + {len(TABELAS)} tabelas + {len(V)} visões + 1 metric view, {len(REGRAS)} regras")
    return V


def cmd_aplicar():
    V = cmd_gerar()
    sql(ESQUEMA)
    for t in TABELAS:
        sql(ddl_tabela(*t))
        print(f"tabela    {t[0]}")
    atuais = {r["table_name"]: norm(r["view_definition"]) for r in
              sql("SELECT table_name, view_definition FROM pos_venda.information_schema.views WHERE table_schema = 'conformidade'")}
    coment = {}
    for r in sql("SELECT table_name, column_name, comment FROM pos_venda.information_schema.columns WHERE table_schema = 'conformidade'"):
        coment.setdefault(r["table_name"], {})[r["column_name"]] = r["comment"] or ""
    for nome, comentario, colunas, consulta in V:
        if atuais.get(nome) == norm(consulta) and coment.get(nome) == {c: d for c, d in colunas}:
            sql(f"COMMENT ON TABLE {S}.{nome} IS '{q(comentario)}'")
            print(f"igual     {nome}")
            continue
        sql(ddl(nome, comentario, colunas, consulta))
        print(f"{'recriada' if nome in atuais else 'criada  '}  {nome}")
    sql(MV)
    print("aplicada  mv_conformidade")


def cmd_registrar():
    agora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    views = sql(f"""SELECT table_catalog, table_schema, table_name, table_type FROM system.information_schema.tables
WHERE table_type IN ('VIEW', 'METRIC_VIEW', 'MATERIALIZED_VIEW') AND table_catalog NOT IN ({lista_sql(EXCLUIDOS)})
  AND table_schema <> 'information_schema'""")

    def sondar(v):
        nome = f"`{v['table_catalog']}`.`{v['table_schema']}`.`{v['table_name']}`"
        estado, erro, _ = executar(f"DESCRIBE QUERY /* sonda-conformidade */ SELECT * FROM {nome}")
        return v, estado == "SUCCEEDED", "" if estado == "SUCCEEDED" else (erro or estado)[:500]

    if not views:
        sys.exit("nenhuma view para sondar: confira o acesso ao information_schema")
    with cf.ThreadPoolExecutor(4) as ex:
        res = list(ex.map(sondar, views))
    valores = ",\n".join(
        f"(TIMESTAMP '{agora}', '{q(v['table_catalog'])}', '{q(v['table_schema'])}', '{q(v['table_name'])}', '{v['table_type']}', "
        f"{str(ok).lower()}, {'NULL' if ok else repr_sql(erro)})" for v, ok, erro in res)
    sql(f"INSERT INTO {S}.sonda_views VALUES\n{valores}")
    quebradas = [f"{v['table_catalog']}.{v['table_schema']}.{v['table_name']}" for v, ok, _ in res if not ok]
    print(f"sonda: {len(res)} views, {len(res) - len(quebradas)} respondem, {len(quebradas)} não respondem")
    sql(f"DELETE FROM {S}.historico WHERE registrado_em = current_date()")
    sql(f"""INSERT INTO {S}.historico
SELECT current_date(), regra_id, dimensao, regra, aplicavel, conformes, falhas, pct_conforme, meta_pct, situacao FROM {S}.boas_praticas_dados""")
    print("histórico do dia gravado")


def repr_sql(s):
    return f"'{q(s)}'"


def cmd_conferir():
    V = visoes()
    erros = 0
    contagem = {}
    print("== cada visão responde")
    for nome, *_ in V + [("mv_conformidade",)] + [(t[0],) for t in TABELAS]:
        consulta = (f"SELECT MEASURE(`Verificações`) AS n FROM {S}.{nome}" if nome.startswith("mv_") else f"SELECT count(*) AS n FROM {S}.{nome}")
        try:
            contagem[nome] = int(sql(consulta)[0]["n"] or 0)
            print(f"  ok    {nome:26} {contagem[nome]}")
        except RuntimeError as e:
            erros += 1
            print(f"  ERRO  {nome:26} {str(e)[-200:]}")
    print("== contagens")
    excl = lista_sql(EXCLUIDOS)
    r = sql(f"""SELECT
  (SELECT count(*) FROM system.information_schema.tables WHERE table_catalog NOT IN ({excl}) AND table_schema <> 'information_schema') AS tabelas_uc,
  (SELECT count(*) FROM system.information_schema.columns WHERE table_catalog = '{DOMINIO}' AND table_schema <> 'information_schema') AS colunas_uc,
  (SELECT count(*) FROM {S}.ativos) AS ativos,
  (SELECT count_if(papel = 'interno') FROM {S}.ativos) AS ativos_internos,
  (SELECT count(*) FROM {S}.colunas) AS colunas,
  (SELECT count_if(papel = 'interno') FROM {S}.colunas) AS colunas_internas,
  (SELECT aplicavel FROM {S}.boas_praticas_dados WHERE regra_id = 'DOC01') AS doc01,
  (SELECT aplicavel FROM {S}.boas_praticas_dados WHERE regra_id = 'DOC03') AS doc03,
  (SELECT sum(aplicavel) FROM {S}.boas_praticas_dados) AS soma_aplicavel,
  (SELECT count(*) FROM {S}.achados) AS achados,
  (SELECT count(*) FROM {S}.pendencias) AS pendencias,
  (SELECT count_if(NOT conforme) FROM {S}.achados) AS nao_conformes,
  (SELECT count(*) FROM {S}.config_regras) AS regras,
  (SELECT count_if(situacao = 'sem dados') FROM {S}.boas_praticas_dados) AS regras_sem_dados,
  (SELECT count(*) FROM {S}.historico WHERE registrado_em = current_date()) AS historico_hoje,
  (SELECT max(sondado_em) FROM {S}.sonda_views) AS ultima_sonda,
  (SELECT MEASURE(`Pendências`) FROM {S}.mv_conformidade) AS pendencias_mv""")[0]
    n = {k: (int(v) if v is not None and k != "ultima_sonda" else v) for k, v in r.items()}
    checks = [
        ("inventário tem todo ativo do workspace", n["ativos"] == n["tabelas_uc"], f"{n['ativos']} = {n['tabelas_uc']}"),
        ("DOC01 verifica todo ativo não interno", n["doc01"] == n["ativos"] - n["ativos_internos"],
         f"{n['doc01']} = {n['ativos']} - {n['ativos_internos']} internos"),
        ("colunas tem toda coluna do pos_venda", n["colunas"] == n["colunas_uc"], f"{n['colunas']} = {n['colunas_uc']}"),
        ("DOC03 verifica toda coluna não interna", n["doc03"] == n["colunas"] - n["colunas_internas"],
         f"{n['doc03']} = {n['colunas']} - {n['colunas_internas']} internas"),
        ("soma por regra = linhas de achados", n["soma_aplicavel"] == n["achados"], f"{n['soma_aplicavel']} = {n['achados']}"),
        ("pendências = achados não conformes", n["pendencias"] == n["nao_conformes"] == n["pendencias_mv"],
         f"{n['pendencias']} = {n['nao_conformes']} = {n['pendencias_mv']} (metric view)"),
        ("toda regra verificou algum objeto", n["regras_sem_dados"] == 0, f"{n['regras_sem_dados']} regra(s) sem dados"),
        ("histórico do dia com uma linha por regra", n["historico_hoje"] == n["regras"], f"{n['historico_hoje']} = {n['regras']}"),
        ("sonda das views gravada", n["ultima_sonda"] is not None, str(n["ultima_sonda"])),
    ]
    for nome, ok, det in checks:
        erros += not ok
        print(f"  {'ok  ' if ok else 'ERRO'}  {nome:42} {det}")
    regras = sql(f"SELECT regra_id, aplicavel, conformes, pct_conforme, meta_pct, situacao FROM {S}.boas_praticas_dados ORDER BY regra_id")
    (AQUI / "conferencia.json").write_text(json.dumps({
        "conferido_em": datetime.date.today().isoformat(), "contagens": {k: str(v) for k, v in n.items()},
        "checks": [{"check": c, "ok": bool(o), "detalhe": d} for c, o, d in checks], "regras": regras},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("conferência:", "ok" if not erros else f"{erros} problema(s)")
    return erros


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else "gerar"
    try:
        {"politicas": cmd_politicas, "alertas": cmd_alertas, "gerar": cmd_gerar, "aplicar": cmd_aplicar, "registrar": cmd_registrar}.get(acao, lambda: None)()
        if acao == "conferir":
            sys.exit(1 if cmd_conferir() else 0)
        if acao not in ("politicas", "alertas", "gerar", "aplicar", "registrar", "conferir"):
            sys.exit(__doc__)
    except CotaEsgotada as e:
        sys.exit(f"warehouse indisponível (cota diária do Free Edition): {e}")
