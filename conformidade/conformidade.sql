CREATE SCHEMA IF NOT EXISTS pos_venda.conformidade COMMENT 'Conformidade dos dados e do workspace: descrições, tags governadas, dados pessoais (LGPD), estrutura, atualização e uso, otimização e plataforma, com meta e histórico. Gerado por conformidade/gerar_conformidade.py.';

CREATE TABLE IF NOT EXISTS pos_venda.conformidade.sonda_views (
  sondado_em TIMESTAMP COMMENT 'Momento da sonda (UTC).',
  catalogo STRING COMMENT 'Catálogo do Unity Catalog.',
  esquema STRING COMMENT 'Schema do Unity Catalog.',
  ativo STRING COMMENT 'Tabela, view, metric view, materialized view ou streaming table (ou o nome do job ou warehouse).',
  tipo STRING COMMENT 'Tipo do objeto no Unity Catalog (MANAGED, VIEW, METRIC_VIEW, MATERIALIZED_VIEW, STREAMING_TABLE...) ou tipo do warehouse.',
  responde BOOLEAN COMMENT 'Verdadeiro quando DESCRIBE QUERY na view funcionou.',
  erro STRING COMMENT 'Mensagem de erro da sonda, quando a view não responde.'
)
COMMENT 'Resultado da sonda diária: cada view, metric view e materialized view do workspace testada com DESCRIBE QUERY (analisa sem executar). Gravado por gerar_conformidade.py registrar.';

CREATE TABLE IF NOT EXISTS pos_venda.conformidade.historico (
  registrado_em DATE COMMENT 'Dia do registro no histórico.',
  regra_id STRING COMMENT 'Código da regra de conformidade (DOC, TAG, LGPD, EST, USO, OTM, PLT).',
  dimensao STRING COMMENT 'Dimensão da regra: documentação, tags governadas, dados pessoais (LGPD), confiança e estrutura, atualização e uso, otimização ou plataforma.',
  regra STRING COMMENT 'O que a regra exige.',
  aplicavel BIGINT COMMENT 'Objetos verificados pela regra.',
  conformes BIGINT COMMENT 'Objetos que atendem à regra.',
  falhas BIGINT COMMENT 'Objetos que não atendem à regra.',
  pct_conforme DOUBLE COMMENT 'Porcentagem dos objetos verificados que atendem.',
  meta_pct DOUBLE COMMENT 'Meta de conformidade, em porcentagem dos objetos verificados.',
  situacao STRING COMMENT 'atende (na meta), atenção (abaixo da meta), crítico (severidade alta abaixo da meta) ou sem dados (nenhum objeto verificado).'
)
COMMENT 'Histórico diário de boas_praticas_dados (uma linha por regra e dia). Gravado por gerar_conformidade.py registrar.';

CREATE OR REPLACE VIEW pos_venda.conformidade.config_camadas (
  esquema COMMENT 'Schema do Unity Catalog.',
  camada COMMENT 'Camada do fluxo (landing, fonte, bronze, silver, gold, qualidade, ontologia, regras, bi ou monitoramento).',
  papel COMMENT 'principal (fluxo diário), legado (medalhão da primeira versão), apoio (monitoramento), interno (tabela de apoio que o Lakeflow cria: __materialization_*, event_log_*; fica fora das regras), não classificado, fora do domínio (outro catálogo) ou plataforma (job ou warehouse).'
)
COMMENT 'Papel de cada schema do catálogo pos_venda: principal (fluxo diário), legado (medalhão da primeira versão) ou apoio (monitoramento). Editado em conformidade/gerar_conformidade.py.'
AS SELECT * FROM VALUES
    ('landing', 'landing', 'principal'),
    ('fonte', 'fonte', 'principal'),
    ('bronze', 'bronze', 'principal'),
    ('silver', 'silver', 'principal'),
    ('gold', 'gold', 'principal'),
    ('dq', 'qualidade', 'principal'),
    ('ontologia', 'ontologia', 'principal'),
    ('regras', 'regras', 'principal'),
    ('bi', 'bi', 'principal'),
    ('bronze_sql', 'bronze', 'legado'),
    ('silver_sql', 'silver', 'legado'),
    ('gold_sql', 'gold', 'legado'),
    ('bronze_ldp', 'bronze', 'legado'),
    ('silver_ldp', 'silver', 'legado'),
    ('gold_ldp', 'gold', 'legado'),
    ('finops', 'monitoramento', 'apoio'),
    ('conformidade', 'monitoramento', 'apoio'),
    ('dqx_codigo', 'qualidade', 'apoio'),
    ('sustentacao', 'monitoramento', 'apoio')
  AS t(esquema, camada, papel);

CREATE OR REPLACE VIEW pos_venda.conformidade.config_regras (
  regra_id COMMENT 'Código da regra de conformidade (DOC, TAG, LGPD, EST, USO, OTM, PLT).',
  dimensao COMMENT 'Dimensão da regra: documentação, tags governadas, dados pessoais (LGPD), confiança e estrutura, atualização e uso, otimização ou plataforma.',
  regra COMMENT 'O que a regra exige.',
  objeto COMMENT 'Tipo do objeto verificado: ativo, coluna, schema, tag, view, job, warehouse ou alerta.',
  escopo COMMENT 'Onde a regra se aplica.',
  meta_pct COMMENT 'Meta de conformidade, em porcentagem dos objetos verificados.',
  severidade COMMENT 'alta, média ou baixa. Alta abaixo da meta vira crítico.',
  origem COMMENT 'De onde vem a regra: documentação Databricks, Well-Architected, LGPD, bundle de observabilidade ou prática do projeto (Pxx do framework).',
  link COMMENT 'Link da fonte da regra.',
  como_corrigir COMMENT 'Como colocar o objeto em conformidade.'
)
COMMENT 'Catálogo de regras de conformidade: dimensão, meta, severidade, origem, link da fonte e como corrigir. Editado em conformidade/gerar_conformidade.py.'
AS SELECT regra_id, dimensao, regra, objeto, escopo, CAST(meta_pct AS DOUBLE) AS meta_pct, severidade, origem, link, como_corrigir FROM VALUES
    ('DOC01', 'Documentação', 'Ativo com descrição', 'ativo', 'todos os catálogos do workspace', 100, 'alta', 'Databricks: comentários no Unity Catalog; framework P13', 'https://docs.databricks.com/aws/en/comments/', 'COMMENT ON TABLE (ou aceitar a descrição gerada por IA no Catalog Explorer depois de revisar).'),
    ('DOC02', 'Documentação', 'Descrição do ativo com ao menos 30 caracteres', 'ativo', 'catálogo pos_venda', 100, 'média', 'Prática do projeto: a descrição diz grão, conteúdo e uso (P13)', 'https://docs.databricks.com/aws/en/comments/', 'Reescrever a descrição dizendo o grão, o que tem e para que serve.'),
    ('DOC03', 'Documentação', 'Coluna com descrição', 'coluna', 'catálogo pos_venda', 100, 'alta', 'Databricks: comentários no Unity Catalog; framework P13', 'https://docs.databricks.com/aws/en/comments/', 'ALTER TABLE ... ALTER COLUMN ... COMMENT (governanca/descricoes_colunas.py e aplicar_descricoes.py).'),
    ('DOC04', 'Documentação', 'Descrição da coluna com ao menos 15 caracteres', 'coluna', 'catálogo pos_venda', 100, 'baixa', 'Prática do projeto (P13)', 'https://docs.databricks.com/aws/en/comments/', 'Completar a descrição: significado, unidade e origem.'),
    ('DOC05', 'Documentação', 'Schema com descrição', 'schema', 'catálogo pos_venda', 100, 'média', 'Databricks: comentários no Unity Catalog', 'https://docs.databricks.com/aws/en/comments/', 'COMMENT ON SCHEMA.'),
    ('TAG01', 'Tags governadas', 'Ativo da camada principal com domain, data_owner e subject_area', 'ativo', 'camada principal', 100, 'alta', 'Databricks: governed tags; framework P14', 'https://docs.databricks.com/aws/en/admin/governed-tags/', 'SET TAGS com os valores da política (governanca/aplicar_semantica.py).'),
    ('TAG02', 'Tags governadas', 'Ativo da camada principal com a tag atualizacao', 'ativo', 'camada principal', 100, 'média', 'Prática do projeto: frescor declarado (P16)', 'https://docs.databricks.com/aws/en/admin/governed-tags/', 'SET TAGS (''atualizacao'' = ''diaria'', ''carga_unica'' ou ''sob_demanda'').'),
    ('TAG03', 'Tags governadas', 'Valor de tag governada dentro dos valores da política', 'tag', 'catálogo pos_venda', 100, 'alta', 'Databricks: governed tags (tag policies)', 'https://docs.databricks.com/aws/en/admin/governed-tags/', 'Corrigir o valor, ou incluir o novo valor na política (databricks tag-policies).'),
    ('TAG04', 'Tags governadas', 'Schema da camada principal com as tags domain e camada', 'schema', 'camada principal', 100, 'média', 'Prática do projeto (P14)', 'https://docs.databricks.com/aws/en/admin/governed-tags/', 'ALTER SCHEMA ... SET TAGS (''domain'' = ''pos_venda'', ''camada'' = ...).'),
    ('LGPD01', 'Dados pessoais (LGPD)', 'Coluna com nome de dado pessoal tem a tag dado_pessoal', 'coluna', 'camadas principal e legado', 100, 'alta', 'LGPD, art. 5º, I; framework P15 (mesma regra de governanca/auditar_metadados.py)', 'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm', 'SET TAGS (''dado_pessoal'' = identificacao, contato, endereco, perfil ou sensivel).'),
    ('LGPD02', 'Dados pessoais (LGPD)', 'Coluna com classificação automática (class.*) revisada com dado_pessoal', 'coluna', 'camadas principal e legado', 100, 'alta', 'Databricks: data classification; framework P15', 'https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-classification', 'Revisar a classe: confirmar com dado_pessoal ou remover a tag class.* se for falso positivo.'),
    ('LGPD03', 'Dados pessoais (LGPD)', 'Ativo com coluna dado_pessoal marcado com contem_dado_pessoal', 'ativo', 'camadas principal e legado', 100, 'alta', 'LGPD, art. 5º, I; framework P15', 'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm', 'SET TAGS (''contem_dado_pessoal'' = ''sim'') no ativo.'),
    ('LGPD04', 'Dados pessoais (LGPD)', 'Ativo marcado com contem_dado_pessoal tem coluna marcada', 'ativo', 'catálogo pos_venda', 100, 'média', 'Prática do projeto: tag de ativo sem coluna correspondente é órfã (P15)', 'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm', 'Marcar as colunas com dado_pessoal ou retirar a tag do ativo.'),
    ('LGPD05', 'Dados pessoais (LGPD)', 'Ativo com coluna sensível marcado com contem_dado_sensivel', 'ativo', 'camadas principal e legado', 100, 'alta', 'LGPD, art. 5º, II (dado pessoal sensível); framework P15', 'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm', 'SET TAGS (''contem_dado_sensivel'' = ''sim'') no ativo.'),
    ('EST01', 'Confiança e estrutura', 'Dimensão, fato e ponte da gold com chave primária', 'ativo', 'gold da camada principal', 100, 'alta', 'Databricks: constraints informativas; framework P08', 'https://docs.databricks.com/aws/en/tables/constraints', 'ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY ... RELY (governanca/aplicar_rely.py).'),
    ('EST02', 'Confiança e estrutura', 'Ativo da gold e da ontologia certificado', 'ativo', 'gold e ontologia da camada principal', 100, 'média', 'Databricks: governed tags, tag de sistema system.certification_status', 'https://docs.databricks.com/aws/en/admin/governed-tags/', 'Depois da conferência: SET TAGS (''system.certification_status'' = ''certified'').'),
    ('EST03', 'Confiança e estrutura', 'Ativo legado marcado como deprecated', 'ativo', 'camada legado', 100, 'média', 'Databricks: governed tags (sinalizar o que não é mais mantido como deprecated)', 'https://docs.databricks.com/aws/en/admin/governed-tags/', 'SET TAGS (''system.certification_status'' = ''deprecated''), ou apagar o schema legado se ninguém mais lê.'),
    ('EST04', 'Confiança e estrutura', 'Dono do ativo é grupo ou service principal', 'ativo', 'catálogo pos_venda', 100, 'baixa', 'Databricks: boas práticas do Unity Catalog (dono em grupo, principalmente em produção)', 'https://docs.databricks.com/aws/en/data-governance/unity-catalog/best-practices', 'ALTER TABLE ... OWNER TO `grupo` (o criador é o primeiro dono).'),
    ('USO01', 'Atualização e uso', 'Ativo com atualizacao=diaria escrito nos últimos 2 dias', 'ativo', 'tabelas da camada principal', 100, 'média', 'Prática do projeto (P02 agendas pausadas, P28); Databricks: lineage', 'https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage', 'Rodar a carga diária (as agendas ficam pausadas no Free Edition) ou corrigir a tag atualizacao.'),
    ('USO02', 'Atualização e uso', 'Ativo da camada principal lido nos últimos 30 dias', 'ativo', 'camada principal', 90, 'baixa', 'Databricks: lineage nas tabelas de sistema', 'https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage', 'Confirmar se o ativo ainda tem consumidor; sem consumidor, marcar como deprecated.'),
    ('USO03', 'Atualização e uso', 'View responde (sonda diária com DESCRIBE QUERY)', 'view', 'todos os catálogos do workspace', 100, 'alta', 'Prática do projeto: view recriada ou fonte apagada quebra em silêncio (P16, P28)', 'https://docs.databricks.com/aws/en/comments/', 'Recriar a view a partir do código ou apagar a quebrada.'),
    ('OTM01', 'Otimização', 'Tabela gerenciada com Predictive Optimization nos últimos 30 dias', 'ativo', 'tabelas gerenciadas do pos_venda, fora as sob demanda', 90, 'baixa', 'Databricks: Predictive Optimization', 'https://docs.databricks.com/aws/en/optimizations/predictive-optimization', 'ALTER CATALOG ou SCHEMA ... ENABLE PREDICTIVE OPTIMIZATION; tabela pequena ou parada pode não precisar.'),
    ('PLT01', 'Plataforma', 'Job com as tags project e team', 'job', 'jobs do workspace', 100, 'média', 'Well-Architected, custo CO-03 (P31); bundle observabilidade-framework (policy_compliance_monitoring)', 'https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices', 'tags no job (no bundle: resources.jobs.<job>.tags).'),
    ('PLT02', 'Plataforma', 'Job com descrição', 'job', 'jobs do workspace', 100, 'baixa', 'Prática do projeto', 'https://docs.databricks.com/aws/en/jobs/settings', 'description no job (no bundle: resources.jobs.<job>.description).'),
    ('PLT03', 'Plataforma', 'Job com timeout definido', 'job', 'jobs do workspace', 100, 'média', 'Databricks: configurações de job (Timeout)', 'https://docs.databricks.com/aws/en/jobs/settings', 'timeout_seconds no job, acima da duração normal.'),
    ('PLT04', 'Plataforma', 'Warehouse com auto-stop de até 30 minutos', 'warehouse', 'warehouses do workspace', 100, 'média', 'bundle observabilidade-framework (workspace_health_summary); Well-Architected, custo', 'https://docs.databricks.com/aws/en/compute/sql-warehouse/create', 'auto_stop_mins do warehouse.'),
    ('PLT05', 'Plataforma', 'Warehouse com as tags project e team', 'warehouse', 'warehouses do workspace', 100, 'baixa', 'Well-Architected, custo CO-03 (P31)', 'https://docs.databricks.com/aws/en/lakehouse-architecture/cost-optimization/best-practices', 'tags do warehouse (compartilhado: team = plataforma).'),
    ('PLT06', 'Plataforma', 'Alerta SQL com até 4 disparos por dia', 'alerta', 'alertas SQL do workspace', 100, 'média', 'Prática do projeto: cada disparo acorda o warehouse; o alerta horário custou US$ 29,73 em 7 dias (L79)', 'https://docs.databricks.com/aws/en/sql/user/alerts/', 'Espaçar a agenda do alerta (ou pausar no Free Edition); juntar condições parecidas num alerta só.')
  AS t(regra_id, dimensao, regra, objeto, escopo, meta_pct, severidade, origem, link, como_corrigir);

CREATE OR REPLACE VIEW pos_venda.conformidade.config_tags_governadas (
  tag COMMENT 'Chave da tag governada.',
  valores COMMENT 'Valores permitidos pela política da tag.',
  descricao COMMENT 'Descrição da política da tag.'
)
COMMENT 'Tags governadas com valores permitidos (tag policies do workspace), lidas pela API em conformidade/politicas_tags.json.'
AS SELECT * FROM VALUES
    ('contem_dado_pessoal', array('sim'), 'A tabela ou view tem pelo menos uma coluna com dado pessoal (LGPD); veja a tag dado_pessoal nas colunas.'),
    ('contem_dado_sensivel', array('sim'), 'A tabela ou view tem dado pessoal sensível (LGPD, art. 5º, II), como dado de saúde.'),
    ('dado_pessoal', array('sensivel', 'identificacao', 'contato', 'endereco', 'perfil'), 'Coluna com dado pessoal (LGPD), por categoria: identificacao, contato, endereco, perfil ou sensivel (art. 5º, II: dado de saúde). Não mascarado: usado na validação de qualidade.'),
    ('data_owner', array('financeiro_pos_venda'), 'Responsável (papel) pelo ativo e pelo significado dos dados.'),
    ('domain', array('pos_venda'), 'Domínio de negócio do ativo (chave padrão, sem acento). pos_venda = Pós-venda de seguro de vida.'),
    ('subject_area', array('cobranca', 'carteira', 'qualidade'), 'Subdomínio do ativo: cobranca (Cobrança e inadimplência), carteira (Clientes e apólices) ou qualidade (Qualidade de dados).'),
    ('system.certification_status', array('certified', 'deprecated'), 'This tag can be used to show a Databricks object''s quality and lifecycle. Objects can be "certified" or "deprecated".')
  AS t(tag, valores, descricao);

CREATE OR REPLACE VIEW pos_venda.conformidade.ativos (
  catalogo COMMENT 'Catálogo do Unity Catalog.',
  esquema COMMENT 'Schema do Unity Catalog.',
  ativo COMMENT 'Tabela, view, metric view, materialized view ou streaming table (ou o nome do job ou warehouse).',
  tipo COMMENT 'Tipo do objeto no Unity Catalog (MANAGED, VIEW, METRIC_VIEW, MATERIALIZED_VIEW, STREAMING_TABLE...) ou tipo do warehouse.',
  papel COMMENT 'principal (fluxo diário), legado (medalhão da primeira versão), apoio (monitoramento), interno (tabela de apoio que o Lakeflow cria: __materialization_*, event_log_*; fica fora das regras), não classificado, fora do domínio (outro catálogo) ou plataforma (job ou warehouse).',
  camada COMMENT 'Camada do fluxo (landing, fonte, bronze, silver, gold, qualidade, ontologia, regras, bi ou monitoramento).',
  tipo_dono COMMENT 'pessoa, grupo ou service principal, ou sistema (objeto gerenciado por pipeline).',
  dono COMMENT 'Dono do objeto no Unity Catalog.',
  descricao COMMENT 'Descrição (comentário) do objeto no Unity Catalog.',
  tamanho_descricao COMMENT 'Número de caracteres da descrição, sem espaços nas pontas.',
  colunas COMMENT 'Número de colunas.',
  colunas_sem_descricao COMMENT 'Colunas sem descrição.',
  tags COMMENT 'Tags do objeto (chave e valor).',
  certificacao COMMENT 'Valor da tag de sistema system.certification_status (certified ou deprecated).',
  atualizacao COMMENT 'Frequência declarada na tag atualizacao (diaria, carga_unica ou sob_demanda).',
  colunas_dado_pessoal COMMENT 'Colunas com a tag dado_pessoal.',
  colunas_sensiveis COMMENT 'Colunas com dado_pessoal = sensivel.',
  tem_pk COMMENT 'Verdadeiro quando o ativo tem chave primária.',
  fks COMMENT 'Número de chaves estrangeiras.',
  criado_em COMMENT 'Quando o objeto foi criado.',
  alterado_em COMMENT 'Última alteração registrada no information_schema (definição, dados ou metadados).',
  ultima_escrita COMMENT 'Última escrita no ativo registrada pelo lineage (90 dias).',
  ultima_leitura COMMENT 'Última leitura do ativo registrada pelo lineage (30 dias).',
  leituras_30d COMMENT 'Leituras do ativo registradas pelo lineage nos últimos 30 dias.',
  ultima_otimizacao COMMENT 'Última operação bem-sucedida de Predictive Optimization.',
  otimizacoes_30d COMMENT 'Operações bem-sucedidas de Predictive Optimization nos últimos 30 dias.'
)
COMMENT 'Inventário de tabelas e views do workspace (menos system e samples) com o que a conformidade mede: descrição, colunas sem descrição, tags, dado pessoal, chave primária, dono, última escrita e leitura (lineage) e Predictive Optimization. Substitui main.observabilidade_dev.vw_inventario_tabelas.'
AS WITH cam AS (SELECT * FROM pos_venda.conformidade.config_camadas),
t AS (
  SELECT table_catalog, table_schema, table_name, table_type, table_owner, comment, created, last_altered
  FROM system.information_schema.tables
  WHERE table_catalog NOT IN ('system', 'samples', '__databricks_internal') AND table_schema <> 'information_schema'),
c AS (
  SELECT table_catalog, table_schema, table_name, count(*) AS colunas,
         count_if(comment IS NULL OR trim(comment) = '') AS colunas_sem_descricao
  FROM system.information_schema.columns
  WHERE table_catalog NOT IN ('system', 'samples', '__databricks_internal') AND table_schema <> 'information_schema'
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
  WHERE event_date >= current_date() - 30 AND source_table_name IS NOT NULL
  GROUP BY ALL),
esc AS (
  SELECT target_table_catalog AS cat, target_table_schema AS sch, target_table_name AS tab, max(event_time) AS ultima_escrita
  FROM system.access.table_lineage
  WHERE event_date >= current_date() - 90 AND target_table_name IS NOT NULL
  GROUP BY ALL),
po AS (
  SELECT catalog_name, schema_name, table_name, max(start_time) AS ultima_otimizacao, count(*) AS otimizacoes
  FROM system.storage.predictive_optimization_operations_history
  WHERE start_time >= current_date() - 30 AND operation_status = 'SUCCESSFUL'
  GROUP BY ALL)
SELECT t.table_catalog, t.table_schema, t.table_name, t.table_type,
  CASE WHEN (startswith(t.table_name, '__materialization') OR startswith(t.table_name, 'event_log_')) THEN 'interno'
       WHEN t.table_catalog = 'pos_venda' THEN coalesce(cam.papel, 'não classificado') ELSE 'fora do domínio' END,
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
LEFT JOIN cam ON t.table_catalog = 'pos_venda' AND t.table_schema = cam.esquema
LEFT JOIN c ON t.table_catalog = c.table_catalog AND t.table_schema = c.table_schema AND t.table_name = c.table_name
LEFT JOIN tg ON t.table_catalog = tg.catalog_name AND t.table_schema = tg.schema_name AND t.table_name = tg.table_name
LEFT JOIN ct ON t.table_catalog = ct.catalog_name AND t.table_schema = ct.schema_name AND t.table_name = ct.table_name
LEFT JOIN pk ON t.table_catalog = pk.table_catalog AND t.table_schema = pk.table_schema AND t.table_name = pk.table_name
LEFT JOIN lin ON t.table_catalog = lin.cat AND t.table_schema = lin.sch AND t.table_name = lin.tab
LEFT JOIN esc ON t.table_catalog = esc.cat AND t.table_schema = esc.sch AND t.table_name = esc.tab
LEFT JOIN po ON t.table_catalog = po.catalog_name AND t.table_schema = po.schema_name AND t.table_name = po.table_name;

CREATE OR REPLACE VIEW pos_venda.conformidade.colunas (
  esquema COMMENT 'Schema do Unity Catalog.',
  ativo COMMENT 'Tabela, view, metric view, materialized view ou streaming table (ou o nome do job ou warehouse).',
  tipo_ativo COMMENT 'Tipo do ativo que contém a coluna, no Unity Catalog.',
  papel COMMENT 'principal (fluxo diário), legado (medalhão da primeira versão), apoio (monitoramento), interno (tabela de apoio que o Lakeflow cria: __materialization_*, event_log_*; fica fora das regras), não classificado, fora do domínio (outro catálogo) ou plataforma (job ou warehouse).',
  camada COMMENT 'Camada do fluxo (landing, fonte, bronze, silver, gold, qualidade, ontologia, regras, bi ou monitoramento).',
  coluna COMMENT 'Nome da coluna (vazio quando a verificação é do ativo, schema, job ou warehouse).',
  posicao COMMENT 'Posição da coluna no ativo.',
  tipo_dado COMMENT 'Tipo de dado da coluna.',
  descricao COMMENT 'Descrição (comentário) do objeto no Unity Catalog.',
  tamanho_descricao COMMENT 'Número de caracteres da descrição, sem espaços nas pontas.',
  dado_pessoal COMMENT 'Valor da tag dado_pessoal (identificacao, contato, endereco, perfil ou sensivel).',
  classes_automaticas COMMENT 'Classes da classificação automática do Databricks (tags class.*), sem o prefixo.',
  nome_sugere_dado_pessoal COMMENT 'Verdadeiro quando o nome da coluna indica dado pessoal (mesma regra de governanca/auditar_metadados.py).'
)
COMMENT 'Colunas do catálogo pos_venda com descrição, tag dado_pessoal, classes da classificação automática (class.*) e se o nome indica dado pessoal.'
AS WITH cam AS (SELECT * FROM pos_venda.conformidade.config_camadas),
col AS (
  SELECT table_schema, table_name, column_name, ordinal_position, full_data_type, comment
  FROM system.information_schema.columns
  WHERE table_catalog = 'pos_venda' AND table_schema <> 'information_schema'),
t AS (SELECT table_schema, table_name, table_type FROM system.information_schema.tables WHERE table_catalog = 'pos_venda'),
ct AS (
  SELECT schema_name, table_name, column_name,
         max(CASE WHEN tag_name = 'dado_pessoal' THEN tag_value END) AS dado_pessoal,
         array_sort(collect_set(CASE WHEN tag_name LIKE 'class.%' THEN substr(tag_name, 7) END)) AS classes
  FROM system.information_schema.column_tags
  WHERE catalog_name = 'pos_venda'
  GROUP BY ALL)
SELECT col.table_schema, col.table_name, t.table_type,
  CASE WHEN (startswith(col.table_name, '__materialization') OR startswith(col.table_name, 'event_log_')) THEN 'interno' ELSE coalesce(cam.papel, 'não classificado') END, cam.camada,
  col.column_name, col.ordinal_position, col.full_data_type, col.comment, length(trim(coalesce(col.comment, ''))),
  ct.dado_pessoal, coalesce(ct.classes, CAST(array() AS ARRAY<STRING>)),
  (lower(col.column_name) RLIKE '(cpf|(^|_)rg($|_)|email|celular|telefone|(^|_)nome($|_)|logradouro|endereco|bairro|cep|data_nascimento|documento|numero$|complemento)' AND NOT lower(col.column_name) RLIKE '(produto_nome|ponto_venda_nome|_valido$|_ausente$|_invalido$|numero_apolice|numero_parcela|_malformado$|^pct_|^taxa_|cobertura_|^nome_mes$|^nome_dia_semana$|numero_ultimo_endosso|cpf_valido|malformado$|inv.lido$|^taxa )')
FROM col
LEFT JOIN t ON col.table_schema = t.table_schema AND col.table_name = t.table_name
LEFT JOIN cam ON col.table_schema = cam.esquema
LEFT JOIN ct ON col.table_schema = ct.schema_name AND col.table_name = ct.table_name AND col.column_name = ct.column_name;

CREATE OR REPLACE VIEW pos_venda.conformidade.recursos (
  tipo_recurso COMMENT 'job, warehouse ou alerta (alerta SQL).',
  recurso_id COMMENT 'Identificador do job, do warehouse ou do alerta.',
  nome COMMENT 'Nome do job, do warehouse ou do alerta (sem o prefixo de desenvolvimento do bundle).',
  tags COMMENT 'Tags do objeto (chave e valor).',
  projeto COMMENT 'Valor da tag project.',
  time COMMENT 'Valor da tag team.',
  tem_descricao COMMENT 'Verdadeiro quando o job tem descrição.',
  timeout_segundos COMMENT 'Timeout do job, em segundos (0 = sem timeout).',
  pausado COMMENT 'Verdadeiro quando a agenda do job ou do alerta está pausada.',
  auto_stop_minutos COMMENT 'Minutos de inatividade até o warehouse desligar.',
  disparos_dia COMMENT 'Disparos por dia de um alerta SQL, calculados da agenda (cron); vazio para jobs e warehouses.',
  tipo COMMENT 'Tipo do objeto no Unity Catalog (MANAGED, VIEW, METRIC_VIEW, MATERIALIZED_VIEW, STREAMING_TABLE...) ou tipo do warehouse.',
  alterado_em COMMENT 'Última alteração registrada no information_schema (definição, dados ou metadados).'
)
COMMENT 'Jobs e warehouses ativos do workspace (versão mais recente em system.lakeflow.jobs e system.compute.warehouses) com tags, descrição, timeout, agenda e auto-stop. Regras internalizadas do bundle observabilidade-framework.'
AS WITH j AS (
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
FROM w
UNION ALL
SELECT 'alerta', '250698304652422', '[Observabilidade] Alerta - Custo Diario Alto (USD)', NULL, NULL, NULL, true, NULL, false, NULL,
  1, 'alerta SQL', TIMESTAMP '2026-07-03 23:43:35'
UNION ALL
SELECT 'alerta', '250698304652424', '[Observabilidade] Alerta - Jobs com Falha (mais de 3 por dia)', NULL, NULL, NULL, true, NULL, false, NULL,
  3, 'alerta SQL', TIMESTAMP '2026-07-03 23:43:35'
UNION ALL
SELECT 'alerta', '250698304652420', '[Observabilidade] Alerta - Queries Lentas (> 5 min)', NULL, NULL, NULL, true, NULL, false, NULL,
  24, 'alerta SQL', TIMESTAMP '2026-07-03 23:43:35'
UNION ALL
SELECT 'alerta', '250698304652421', '[Observabilidade] Alerta - Recursos sem Tag com Custo Alto', NULL, NULL, NULL, true, NULL, false, NULL,
  1, 'alerta SQL', TIMESTAMP '2026-07-03 23:43:35'
UNION ALL
SELECT 'alerta', '3609132029342407', '[Observabilidade] Alerta - Trafego Detectado no Unity AI Gateway', NULL, NULL, NULL, true, NULL, false, NULL,
  1, 'alerta SQL', TIMESTAMP '2026-07-30 19:54:16'
UNION ALL
SELECT 'alerta', '3507795912731880', 'pos_venda · Sustentação: SLA ou desvio da carga', NULL, NULL, NULL, true, NULL, true, NULL,
  1, 'alerta SQL', TIMESTAMP '2026-11-24 19:19:37';

CREATE OR REPLACE VIEW pos_venda.conformidade.achados (
  regra_id COMMENT 'Código da regra de conformidade (DOC, TAG, LGPD, EST, USO, OTM, PLT).',
  dimensao COMMENT 'Dimensão da regra: documentação, tags governadas, dados pessoais (LGPD), confiança e estrutura, atualização e uso, otimização ou plataforma.',
  regra COMMENT 'O que a regra exige.',
  severidade COMMENT 'alta, média ou baixa. Alta abaixo da meta vira crítico.',
  objeto COMMENT 'Tipo do objeto verificado: ativo, coluna, schema, tag, view, job, warehouse ou alerta.',
  catalogo COMMENT 'Catálogo do Unity Catalog.',
  esquema COMMENT 'Schema do Unity Catalog.',
  ativo COMMENT 'Tabela, view, metric view, materialized view ou streaming table (ou o nome do job ou warehouse).',
  coluna COMMENT 'Nome da coluna (vazio quando a verificação é do ativo, schema, job ou warehouse).',
  papel COMMENT 'principal (fluxo diário), legado (medalhão da primeira versão), apoio (monitoramento), interno (tabela de apoio que o Lakeflow cria: __materialization_*, event_log_*; fica fora das regras), não classificado, fora do domínio (outro catálogo) ou plataforma (job ou warehouse).',
  conforme COMMENT 'Verdadeiro quando o objeto atende à regra.',
  detalhe COMMENT 'O que foi encontrado no objeto.',
  como_corrigir COMMENT 'Como colocar o objeto em conformidade.'
)
COMMENT 'Uma linha por verificação (objeto × regra): conforme ou não, com o detalhe e como corrigir. Base de pendencias, boas_praticas_dados, squad_por_schema, plataforma_por_catalogo e da metric view mv_conformidade.'
AS WITH a AS (SELECT * FROM pos_venda.conformidade.ativos),
c AS (SELECT * FROM pos_venda.conformidade.colunas),
r AS (SELECT * FROM pos_venda.conformidade.recursos),
cam AS (SELECT * FROM pos_venda.conformidade.config_camadas),
gov AS (SELECT tag, valores FROM pos_venda.conformidade.config_tags_governadas WHERE size(valores) > 0),
stg AS (
  SELECT schema_name, collect_set(tag_name) AS tags
  FROM system.information_schema.schema_tags WHERE catalog_name = 'pos_venda' GROUP BY ALL),
sch AS (
  SELECT s.catalog_name AS catalogo, s.schema_name AS esquema, coalesce(cam.papel, 'não classificado') AS papel,
         length(trim(coalesce(s.comment, ''))) AS tamanho_descricao, coalesce(stg.tags, CAST(array() AS ARRAY<STRING>)) AS tags
  FROM system.information_schema.schemata s
  LEFT JOIN cam ON s.schema_name = cam.esquema
  LEFT JOIN stg ON s.schema_name = stg.schema_name
  WHERE s.catalog_name = 'pos_venda' AND s.schema_name NOT IN ('information_schema', 'default')),
tt AS (
  SELECT 'tag de ativo' AS objeto, schema_name, table_name, CAST(NULL AS STRING) AS column_name, tag_name, tag_value
  FROM system.information_schema.table_tags WHERE catalog_name = 'pos_venda' AND tag_name IN ('contem_dado_pessoal', 'contem_dado_sensivel', 'dado_pessoal', 'data_owner', 'domain', 'subject_area', 'system.certification_status')
  UNION ALL
  SELECT 'tag de coluna', schema_name, table_name, column_name, tag_name, tag_value
  FROM system.information_schema.column_tags WHERE catalog_name = 'pos_venda' AND tag_name IN ('contem_dado_pessoal', 'contem_dado_sensivel', 'dado_pessoal', 'data_owner', 'domain', 'subject_area', 'system.certification_status')
  UNION ALL
  SELECT 'tag de schema', schema_name, NULL, NULL, tag_name, tag_value
  FROM system.information_schema.schema_tags WHERE catalog_name = 'pos_venda' AND tag_name IN ('contem_dado_pessoal', 'contem_dado_sensivel', 'dado_pessoal', 'data_owner', 'domain', 'subject_area', 'system.certification_status')),
sonda AS (SELECT * FROM pos_venda.conformidade.sonda_views WHERE sondado_em = (SELECT max(sondado_em) FROM pos_venda.conformidade.sonda_views)),
base AS (
  SELECT 'DOC01' AS regra_id, 'ativo' AS objeto, catalogo, esquema, ativo, CAST(NULL AS STRING) AS coluna, papel,
         tamanho_descricao > 0 AS conforme, CASE WHEN tamanho_descricao > 0 THEN 'tem descrição' ELSE 'sem descrição' END AS detalhe
  FROM a WHERE papel <> 'interno'
  UNION ALL
  SELECT 'DOC02', 'ativo', catalogo, esquema, ativo, NULL, papel, tamanho_descricao >= 30, concat(tamanho_descricao, ' caracteres')
  FROM a WHERE catalogo = 'pos_venda' AND papel <> 'interno' AND tamanho_descricao > 0
  UNION ALL
  SELECT 'DOC03', 'coluna', 'pos_venda', esquema, ativo, coluna, papel, tamanho_descricao > 0,
         CASE WHEN tamanho_descricao > 0 THEN 'tem descrição' ELSE 'sem descrição' END
  FROM c WHERE papel <> 'interno'
  UNION ALL
  SELECT 'DOC04', 'coluna', 'pos_venda', esquema, ativo, coluna, papel, tamanho_descricao >= 15, concat(tamanho_descricao, ' caracteres')
  FROM c WHERE papel <> 'interno' AND tamanho_descricao > 0
  UNION ALL
  SELECT 'DOC05', 'schema', catalogo, esquema, NULL, NULL, papel, tamanho_descricao > 0,
         CASE WHEN tamanho_descricao > 0 THEN 'tem descrição' ELSE 'sem descrição' END
  FROM sch
  UNION ALL
  SELECT 'TAG01', 'ativo', catalogo, esquema, ativo, NULL, papel,
         size(array_except(array('domain', 'data_owner', 'subject_area'), map_keys(tags))) = 0,
         CASE WHEN size(array_except(array('domain', 'data_owner', 'subject_area'), map_keys(tags))) = 0 THEN 'tem as três'
              ELSE concat('faltam: ', array_join(array_except(array('domain', 'data_owner', 'subject_area'), map_keys(tags)), ', ')) END
  FROM a WHERE papel = 'principal'
  UNION ALL
  SELECT 'TAG02', 'ativo', catalogo, esquema, ativo, NULL, papel, atualizacao IS NOT NULL,
         coalesce(concat('atualizacao = ', atualizacao), 'sem a tag')
  FROM a WHERE papel = 'principal'
  UNION ALL
  SELECT 'TAG03', tt.objeto, 'pos_venda', tt.schema_name, tt.table_name, tt.column_name, coalesce(cam.papel, 'não classificado'),
         array_contains(gov.valores, tt.tag_value), concat(tt.tag_name, ' = ', coalesce(tt.tag_value, '(vazio)'))
  FROM tt JOIN gov ON tt.tag_name = gov.tag LEFT JOIN cam ON tt.schema_name = cam.esquema
  UNION ALL
  SELECT 'TAG04', 'schema', catalogo, esquema, NULL, NULL, papel,
         size(array_except(array('domain', 'camada'), tags)) = 0,
         CASE WHEN size(array_except(array('domain', 'camada'), tags)) = 0 THEN 'tem domain e camada'
              ELSE concat('faltam: ', array_join(array_except(array('domain', 'camada'), tags), ', ')) END
  FROM sch WHERE papel = 'principal'
  UNION ALL
  SELECT 'LGPD01', 'coluna', 'pos_venda', esquema, ativo, coluna, papel, dado_pessoal IS NOT NULL,
         coalesce(concat('dado_pessoal = ', dado_pessoal), 'o nome indica dado pessoal e não há a tag')
  FROM c WHERE papel IN ('principal', 'legado') AND nome_sugere_dado_pessoal
  UNION ALL
  SELECT 'LGPD02', 'coluna', 'pos_venda', esquema, ativo, coluna, papel, dado_pessoal IS NOT NULL,
         concat('classes: ', array_join(classes_automaticas, ', '), CASE WHEN dado_pessoal IS NULL THEN ' (sem dado_pessoal)' ELSE '' END)
  FROM c WHERE papel IN ('principal', 'legado') AND size(classes_automaticas) > 0
  UNION ALL
  SELECT 'LGPD03', 'ativo', catalogo, esquema, ativo, NULL, papel, coalesce(try_element_at(tags, 'contem_dado_pessoal') = 'sim', false),
         concat(colunas_dado_pessoal, ' coluna(s) com dado_pessoal')
  FROM a WHERE catalogo = 'pos_venda' AND papel IN ('principal', 'legado') AND colunas_dado_pessoal > 0
  UNION ALL
  SELECT 'LGPD04', 'ativo', catalogo, esquema, ativo, NULL, papel, colunas_dado_pessoal > 0,
         concat(colunas_dado_pessoal, ' coluna(s) com dado_pessoal')
  FROM a WHERE catalogo = 'pos_venda' AND try_element_at(tags, 'contem_dado_pessoal') = 'sim'
  UNION ALL
  SELECT 'LGPD05', 'ativo', catalogo, esquema, ativo, NULL, papel, coalesce(try_element_at(tags, 'contem_dado_sensivel') = 'sim', false),
         concat(colunas_sensiveis, ' coluna(s) sensível(is)')
  FROM a WHERE catalogo = 'pos_venda' AND papel IN ('principal', 'legado') AND colunas_sensiveis > 0
  UNION ALL
  SELECT 'EST01', 'ativo', catalogo, esquema, ativo, NULL, papel, tem_pk,
         concat(try_element_at(tags, 'tipo_ativo'), CASE WHEN tem_pk THEN ' com chave primária' ELSE ' sem chave primária' END)
  FROM a WHERE catalogo = 'pos_venda' AND papel = 'principal' AND esquema = 'gold' AND tipo = 'MANAGED'
    AND try_element_at(tags, 'tipo_ativo') IN ('dimensao', 'fato', 'ponte')
  UNION ALL
  SELECT 'EST02', 'ativo', catalogo, esquema, ativo, NULL, papel, coalesce(certificacao = 'certified', false), coalesce(certificacao, 'sem certificação')
  FROM a WHERE catalogo = 'pos_venda' AND papel = 'principal' AND esquema IN ('gold', 'ontologia')
  UNION ALL
  SELECT 'EST03', 'ativo', catalogo, esquema, ativo, NULL, papel, coalesce(certificacao = 'deprecated', false), coalesce(certificacao, 'sem certificação')
  FROM a WHERE catalogo = 'pos_venda' AND papel = 'legado'
  UNION ALL
  SELECT 'EST04', 'ativo', catalogo, esquema, ativo, NULL, papel, tipo_dono <> 'pessoa', tipo_dono
  FROM a WHERE catalogo = 'pos_venda' AND papel <> 'interno'
  UNION ALL
  SELECT 'USO01', 'ativo', catalogo, esquema, ativo, NULL, papel,
         coalesce(ultima_escrita, alterado_em) >= current_timestamp() - INTERVAL 2 DAYS,
         concat('última escrita: ', date_format(coalesce(ultima_escrita, alterado_em), 'yyyy-MM-dd HH:mm'))
  FROM a WHERE catalogo = 'pos_venda' AND papel = 'principal' AND atualizacao = 'diaria'
    AND tipo IN ('MANAGED', 'STREAMING_TABLE', 'MATERIALIZED_VIEW')
  UNION ALL
  SELECT 'USO02', 'ativo', catalogo, esquema, ativo, NULL, papel, leituras_30d > 0, concat(leituras_30d, ' leitura(s) em 30 dias')
  FROM a WHERE catalogo = 'pos_venda' AND papel = 'principal'
  UNION ALL
  SELECT 'USO03', 'view', sonda.catalogo, sonda.esquema, sonda.ativo, NULL, coalesce(a.papel, 'fora do domínio'), sonda.responde,
         CASE WHEN sonda.responde THEN 'responde' ELSE substr(coalesce(sonda.erro, 'erro'), 1, 300) END
  FROM sonda LEFT JOIN a ON sonda.catalogo = a.catalogo AND sonda.esquema = a.esquema AND sonda.ativo = a.ativo
  UNION ALL
  SELECT 'OTM01', 'ativo', catalogo, esquema, ativo, NULL, papel, otimizacoes_30d > 0, concat(otimizacoes_30d, ' operação(ões) em 30 dias')
  FROM a WHERE catalogo = 'pos_venda' AND papel <> 'interno' AND tipo = 'MANAGED'
    AND coalesce(atualizacao, '') <> 'sob_demanda'   -- tabela que só muda sob demanda não recebe operação (L96)
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
  SELECT 'PLT06', 'alerta', NULL, NULL, nome, NULL, 'plataforma', pausado OR disparos_dia <= 4,
         concat(disparos_dia, ' disparo(s) por dia', CASE WHEN pausado THEN ' (pausado)' ELSE '' END)
  FROM r WHERE tipo_recurso = 'alerta')
SELECT b.regra_id, g.dimensao, g.regra, g.severidade, b.objeto, b.catalogo, b.esquema, b.ativo, b.coluna, b.papel,
  b.conforme, b.detalhe, g.como_corrigir
FROM base b JOIN pos_venda.conformidade.config_regras g ON b.regra_id = g.regra_id;

CREATE OR REPLACE VIEW pos_venda.conformidade.pendencias (
  regra_id COMMENT 'Código da regra de conformidade (DOC, TAG, LGPD, EST, USO, OTM, PLT).',
  severidade COMMENT 'alta, média ou baixa. Alta abaixo da meta vira crítico.',
  dimensao COMMENT 'Dimensão da regra: documentação, tags governadas, dados pessoais (LGPD), confiança e estrutura, atualização e uso, otimização ou plataforma.',
  regra COMMENT 'O que a regra exige.',
  objeto COMMENT 'Tipo do objeto verificado: ativo, coluna, schema, tag, view, job, warehouse ou alerta.',
  catalogo COMMENT 'Catálogo do Unity Catalog.',
  esquema COMMENT 'Schema do Unity Catalog.',
  ativo COMMENT 'Tabela, view, metric view, materialized view ou streaming table (ou o nome do job ou warehouse).',
  coluna COMMENT 'Nome da coluna (vazio quando a verificação é do ativo, schema, job ou warehouse).',
  papel COMMENT 'principal (fluxo diário), legado (medalhão da primeira versão), apoio (monitoramento), interno (tabela de apoio que o Lakeflow cria: __materialization_*, event_log_*; fica fora das regras), não classificado, fora do domínio (outro catálogo) ou plataforma (job ou warehouse).',
  detalhe COMMENT 'O que foi encontrado no objeto.',
  como_corrigir COMMENT 'Como colocar o objeto em conformidade.'
)
COMMENT 'Só as verificações que não atendem: a lista de correções, com severidade e como corrigir.'
AS SELECT regra_id, severidade, dimensao, regra, objeto, catalogo, esquema, ativo, coluna, papel, detalhe, como_corrigir
FROM pos_venda.conformidade.achados WHERE NOT conforme;

CREATE OR REPLACE VIEW pos_venda.conformidade.boas_praticas_dados (
  regra_id COMMENT 'Código da regra de conformidade (DOC, TAG, LGPD, EST, USO, OTM, PLT).',
  dimensao COMMENT 'Dimensão da regra: documentação, tags governadas, dados pessoais (LGPD), confiança e estrutura, atualização e uso, otimização ou plataforma.',
  regra COMMENT 'O que a regra exige.',
  escopo COMMENT 'Onde a regra se aplica.',
  severidade COMMENT 'alta, média ou baixa. Alta abaixo da meta vira crítico.',
  aplicavel COMMENT 'Objetos verificados pela regra.',
  conformes COMMENT 'Objetos que atendem à regra.',
  falhas COMMENT 'Objetos que não atendem à regra.',
  pct_conforme COMMENT 'Porcentagem dos objetos verificados que atendem.',
  meta_pct COMMENT 'Meta de conformidade, em porcentagem dos objetos verificados.',
  situacao COMMENT 'atende (na meta), atenção (abaixo da meta), crítico (severidade alta abaixo da meta) ou sem dados (nenhum objeto verificado).',
  origem COMMENT 'De onde vem a regra: documentação Databricks, Well-Architected, LGPD, bundle de observabilidade ou prática do projeto (Pxx do framework).',
  link COMMENT 'Link da fonte da regra.',
  como_corrigir COMMENT 'Como colocar o objeto em conformidade.'
)
COMMENT 'Uma linha por regra: objetos verificados, conformes, falhas, porcentagem, meta e situação, com origem e como corrigir. Regra sem objeto verificado fica ''sem dados'', nunca ''atende''.'
AS WITH x AS (SELECT regra_id, count(*) AS aplicavel, count_if(conforme) AS conformes FROM pos_venda.conformidade.achados GROUP BY regra_id)
SELECT g.regra_id, g.dimensao, g.regra, g.escopo, g.severidade, coalesce(x.aplicavel, 0), coalesce(x.conformes, 0),
  coalesce(x.aplicavel, 0) - coalesce(x.conformes, 0),
  round(100.0 * x.conformes / nullif(x.aplicavel, 0), 1), g.meta_pct,
  CASE WHEN coalesce(x.aplicavel, 0) = 0 THEN 'sem dados'
       WHEN 100.0 * x.conformes / x.aplicavel >= g.meta_pct THEN 'atende'
       WHEN g.severidade = 'alta' THEN 'crítico'
       ELSE 'atenção' END,
  g.origem, g.link, g.como_corrigir
FROM pos_venda.conformidade.config_regras g LEFT JOIN x ON g.regra_id = x.regra_id;

CREATE OR REPLACE VIEW pos_venda.conformidade.squad_por_schema (
  esquema COMMENT 'Schema do Unity Catalog.',
  papel COMMENT 'principal (fluxo diário), legado (medalhão da primeira versão), apoio (monitoramento), interno (tabela de apoio que o Lakeflow cria: __materialization_*, event_log_*; fica fora das regras), não classificado, fora do domínio (outro catálogo) ou plataforma (job ou warehouse).',
  dimensao COMMENT 'Dimensão da regra: documentação, tags governadas, dados pessoais (LGPD), confiança e estrutura, atualização e uso, otimização ou plataforma.',
  verificacoes COMMENT 'Verificações (objeto × regra).',
  conformes COMMENT 'Objetos que atendem à regra.',
  falhas COMMENT 'Objetos que não atendem à regra.',
  pct_conforme COMMENT 'Porcentagem dos objetos verificados que atendem.'
)
COMMENT 'Visão do squad: conformidade de cada schema do catálogo pos_venda por dimensão.'
AS SELECT esquema, papel, dimensao, count(*), count_if(conforme), count_if(NOT conforme), round(100.0 * count_if(conforme) / count(*), 1)
FROM pos_venda.conformidade.achados WHERE catalogo = 'pos_venda' AND esquema IS NOT NULL
GROUP BY ALL;

CREATE OR REPLACE VIEW pos_venda.conformidade.plataforma_por_catalogo (
  catalogo COMMENT 'Catálogo do Unity Catalog, ou ''recursos do workspace'' para jobs e warehouses.',
  dimensao COMMENT 'Dimensão da regra: documentação, tags governadas, dados pessoais (LGPD), confiança e estrutura, atualização e uso, otimização ou plataforma.',
  verificacoes COMMENT 'Verificações (objeto × regra).',
  conformes COMMENT 'Objetos que atendem à regra.',
  falhas COMMENT 'Objetos que não atendem à regra.',
  pct_conforme COMMENT 'Porcentagem dos objetos verificados que atendem.'
)
COMMENT 'Visão da plataforma: conformidade de cada catálogo do workspace e dos recursos (jobs e warehouses) por dimensão.'
AS SELECT coalesce(catalogo, 'recursos do workspace'), dimensao, count(*), count_if(conforme), count_if(NOT conforme),
  round(100.0 * count_if(conforme) / count(*), 1)
FROM pos_venda.conformidade.achados
GROUP BY ALL;

CREATE OR REPLACE VIEW pos_venda.conformidade.acoes_observabilidade (
  acao COMMENT 'Ação de observabilidade que já roda no workspace.',
  tipo COMMENT 'job, alertas (alertas SQL) ou visões (um schema).',
  o_que_faz COMMENT 'O que a ação faz.',
  achado COMMENT 'O que a avaliação encontrou (23/11/2026).',
  veredito COMMENT 'internalizar (a lógica passa a viver aqui), manter (segue no bundle), consertar, aposentar ou manter só leitura.',
  motivo COMMENT 'Por que o veredito.',
  no_framework COMMENT 'Onde a ação ficou no framework.',
  execucoes_30d COMMENT 'Execuções nos últimos 30 dias: do job (pos_venda.finops.uso_jobs_diario) ou consultas disparadas pelos alertas.',
  falhas_30d COMMENT 'Execuções com falha nos últimos 30 dias.',
  custo_lista_usd_30d COMMENT 'Custo a preço de lista nos últimos 30 dias, em USD.',
  pausado COMMENT 'Verdadeiro quando a agenda está pausada (vazio para visões).',
  views_sondadas COMMENT 'Views do schema verificadas na última sonda.',
  views_respondem COMMENT 'Views do schema que responderam na última sonda.'
)
COMMENT 'Avaliação das ações de observabilidade que já rodam no workspace (bundle observabilidade-framework e finops.observability): o que fazem, o que se encontrou, veredito e onde ficaram no framework, com execuções, falhas e custo dos últimos 30 dias e a última sonda das views.'
AS WITH acoes AS (
  SELECT * FROM VALUES
    ('Materialização diária das tabelas de sistema', 'job', '%Materializacao Diaria%', 'Recria 10 tabelas em main.observabilidade_dev (clusters, policies, warehouses, custo) e o histórico de tamanho das tabelas, todo dia às 6h.', 'Roda sem falha, mas 7 das 10 tabelas ficam vazias: tratam de clusters clássicos, spot e policies, que o Free Edition não tem. O histórico de tamanho funciona.', 'internalizar', 'As regras de warehouse e de tags viram PLT01 a PLT05 aqui; as de cluster não se aplicam ao Free Edition. É o job de observabilidade mais caro.', 'pos_venda.conformidade (PLT01 a PLT05) e pos_venda.finops (armazenamento)'),
    ('Detecção de anomalias: auditoria e segurança', 'job', '%Deteccao de Anomalias%', 'Consulta clusters sem policy, warehouses e eventos de permissão no audit log, todo dia às 7h; o resultado fica só na saída do notebook.', 'Roda sem falha; a parte de clusters volta vazia no Free Edition.', 'internalizar', 'Policies e auto-stop viram regras com meta e histórico; os eventos de permissão seguem no notebook até virarem regra.', 'pos_venda.conformidade (PLT04)'),
    ('Triagem automática de falhas de job', 'job', '%Auto-Triagem de Falhas%', 'Classifica as execuções com falha e mantém a view vw_triagem_falhas_jobs, todo dia às 7h30.', 'Roda sem falha e classifica as falhas recentes.', 'manter', 'É operação, não conformidade. O custo das falhas já aparece em pos_venda.finops.uso_jobs_diario.', 'P28 (matriz de resiliência) consulta a triagem'),
    ('Relatório executivo semanal', 'job', '%Relatorio Executivo Semanal%', 'Monta um relatório e grava em arquivo no volume main.observabilidade_dev.relatorios, toda segunda às 7h.', 'Roda sem falha; não envia nada para fora do workspace (o envio por webhook ficou para depois).', 'manter', 'Próximo passo natural: incluir o resumo de pos_venda.conformidade.boas_praticas_dados.', 'nenhum por enquanto'),
    ('Alertas SQL do bundle (5)', 'alertas', '%', 'Cinco alertas SQL no warehouse: queries lentas (de hora em hora), jobs com falha (3 vezes ao dia), custo diário alto, recursos sem tag com custo alto e tráfego no AI Gateway (1 vez ao dia).', 'Rodam como jobs ocultos, que não aparecem na lista de jobs. São a maior parte do custo de observabilidade: US$ 816,20 desde julho, quase tudo do alerta horário, porque cada disparo acorda o warehouse.', 'consertar', 'Espaçar o alerta de queries lentas (até 4 disparos por dia) ou pausá-lo no Free Edition; os outros quatro ficam como estão.', 'pos_venda.conformidade (PLT06) e pos_venda.finops (custo por consulta)'),
    ('Rightsizing semanal de clusters', 'job', '%Rightsizing Semanal%', 'Sugere o tamanho de cluster a partir de system.compute.node_timeline, toda segunda às 8h.', 'Falha em toda execução (NameError: name ''null'' is not defined) e, no Free Edition, não há cluster clássico para dimensionar.', 'aposentar', 'Pausar no Free Edition; consertar o notebook só ao migrar para um workspace com clusters clássicos.', 'nenhum'),
    ('Visões vw_* em main.observabilidade_dev', 'visões', 'main.observabilidade_dev', '17 visões sobre as tabelas de sistema (custo, jobs, consultas, Genie, tags, inventário), criadas por um job sem agenda.', 'As de custo repetem pos_venda.finops sem a atribuição por projeto; vw_governanca_cobertura_tags conta registros, não custo; vw_inventario_tabelas não traz descrição, tags nem dono.', 'internalizar', 'pos_venda.finops cobre custo e uso com FOCUS e atribuição; pos_venda.conformidade.ativos substitui o inventário.', 'pos_venda.finops e pos_venda.conformidade.ativos'),
    ('Framework FinOps antigo em finops.observability', 'visões', 'finops.observability', '28 visões FOCUS e de histórias executivas, de um framework anterior.', 'Parte das visões não responde; a sonda diária mostra quantas.', 'manter só leitura', 'Decisão do dono: não alterar. A sonda mede as quebradas sem mexer nelas.', 'pos_venda.conformidade (USO03)')
  AS t(acao, tipo, padrao, o_que_faz, achado, veredito, motivo, no_framework)),
j AS (
  SELECT job, sum(execucoes) AS execucoes, sum(falhas) AS falhas, sum(custo_lista_usd) AS custo
  FROM pos_venda.finops.uso_jobs_diario WHERE dia >= current_date() - 30 GROUP BY job),
r AS (SELECT nome, pausado FROM pos_venda.conformidade.recursos WHERE tipo_recurso = 'job'),
al AS (
  SELECT count(*) AS consultas, round(sum(c.custo_lista_usd), 2) AS custo
  FROM pos_venda.finops.custo_sql_por_consulta c JOIN system.query.history q ON c.statement_id = q.statement_id
  WHERE c.hora >= current_date() - 30 AND q.start_time >= current_date() - 31 AND q.query_source.alert_id IS NOT NULL),
ra AS (SELECT bool_and(pausado) AS pausados FROM pos_venda.conformidade.recursos WHERE tipo_recurso = 'alerta'),
s AS (
  SELECT concat(catalogo, '.', esquema) AS alvo, count(*) AS views, count_if(responde) AS respondem
  FROM pos_venda.conformidade.sonda_views WHERE sondado_em = (SELECT max(sondado_em) FROM pos_venda.conformidade.sonda_views)
  GROUP BY 1)
SELECT a.acao, a.tipo, a.o_que_faz, a.achado, a.veredito, a.motivo, a.no_framework,
  CASE WHEN a.tipo = 'alertas' THEN (SELECT consultas FROM al) ELSE (SELECT sum(execucoes) FROM j WHERE a.tipo = 'job' AND j.job LIKE a.padrao) END,
  (SELECT sum(falhas) FROM j WHERE a.tipo = 'job' AND j.job LIKE a.padrao),
  CASE WHEN a.tipo = 'alertas' THEN (SELECT custo FROM al) ELSE (SELECT round(sum(custo), 2) FROM j WHERE a.tipo = 'job' AND j.job LIKE a.padrao) END,
  CASE WHEN a.tipo = 'alertas' THEN (SELECT pausados FROM ra) ELSE (SELECT bool_or(pausado) FROM r WHERE a.tipo = 'job' AND r.nome LIKE a.padrao) END,
  (SELECT sum(views) FROM s WHERE a.tipo = 'visões' AND s.alvo = a.padrao),
  (SELECT sum(respondem) FROM s WHERE a.tipo = 'visões' AND s.alvo = a.padrao)
FROM acoes a;

CREATE OR REPLACE VIEW pos_venda.conformidade.mv_conformidade
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: pos_venda.conformidade.achados
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
$$;
