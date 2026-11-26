-- Gerado por regras/catalogo/gerar_catalogo.py a partir de catalogo_regras.yml. Não edite.

CREATE OR REPLACE TABLE pos_venda.regras.catalogo_regras (
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
COMMENT 'Catálogo das regras de qualidade do pos_venda, com versão e vigência pela data do dado (P41). Gerado por regras/catalogo/gerar_catalogo.py a partir de catalogo_regras.yml; não edite aqui.';

INSERT INTO pos_venda.regras.catalogo_regras VALUES
('pendencia_id_nulo', 1, 'Toda pendência tem identificador', 'erro', 'cobranca', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, 0.0, 'is_not_null', '{"column": "pendencia_id"}', 'regra original da barreira da silver', 'carga_diaria/gerar_carga.py (MOTIVO_REJEICAO)', 'dono do projeto', DATE'2026-11-26'),
('tipo_evento_invalido', 1, 'O evento é NOVA, ATUALIZACAO ou BAIXA', 'erro', 'cobranca', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, 0.0, 'sql_expression', '{"expression": "coalesce(tipo_evento IN (''NOVA'', ''ATUALIZACAO'', ''BAIXA''), false)", "msg": "tipo_evento nulo ou fora de NOVA, ATUALIZACAO, BAIXA"}', 'regra original da barreira da silver', 'carga_diaria/gerar_carga.py (MOTIVO_REJEICAO)', 'dono do projeto', DATE'2026-11-26'),
('status_cobranca_invalido', 1, 'O status de cobrança é um dos 6 aceitos', 'erro', 'cobranca', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, 0.0, 'sql_expression', '{"expression": "coalesce(status_cobranca IN (''PENDENTE'', ''EM_COBRANCA'', ''PROMESSA_PAGAMENTO'', ''NEGOCIADO'', ''COBRANCA_EXTERNA'', ''PAGA''), false)", "msg": "status_cobranca nulo ou fora do domínio"}', 'regra original da barreira da silver', 'carga_diaria/gerar_carga.py (MOTIVO_REJEICAO)', 'dono do projeto', DATE'2026-11-26'),
('valor_parcela_nao_positivo', 1, 'A parcela tem valor maior que zero', 'erro', 'cobranca', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, 0.0, 'sql_expression', '{"expression": "coalesce(valor_parcela > 0, false)", "msg": "valor_parcela nulo, zero ou negativo"}', 'regra original da barreira da silver', 'carga_diaria/gerar_carga.py (MOTIVO_REJEICAO)', 'dono do projeto', DATE'2026-11-26'),
('valor_total_inconsistente', 1, 'O total pendente é parcela + multa + juros informados', 'erro', 'cobranca', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, 0.0, 'sql_expression', '{"expression": "coalesce(abs(valor_total_pendente - (valor_parcela + valor_multa + valor_juros)) < 0.01, true)", "msg": "valor_total_pendente diferente de parcela + multa + juros"}', 'regra original da barreira da silver', 'carga_diaria/gerar_carga.py (MOTIVO_REJEICAO)', 'dono do projeto', DATE'2026-11-26'),
('vencimento_nao_anterior_ao_evento', 1, 'O vencimento é anterior à data do evento', 'erro', 'cobranca', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, 0.0, 'sql_expression', '{"expression": "coalesce(data_vencimento < data_extracao, true)", "msg": "data_vencimento igual ou depois da data do evento"}', 'regra original da barreira da silver', 'carga_diaria/gerar_carga.py (MOTIVO_REJEICAO)', 'dono do projeto', DATE'2026-11-26'),
('atraso_nao_confere_com_as_datas', 1, 'Os dias de atraso batem com as datas', 'erro', 'cobranca', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, 0.0, 'sql_expression', '{"expression": "coalesce(dias_atraso = datediff(data_extracao, data_vencimento), true)", "msg": "dias_atraso não confere com as datas"}', 'regra original da barreira da silver', 'carga_diaria/gerar_carga.py (MOTIVO_REJEICAO)', 'dono do projeto', DATE'2026-11-26'),
('valores_fora_da_regra', 1, 'Multa, juros e total seguem a regra de cálculo', 'erro', 'cobranca', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, 0.0, 'sql_expression', '{"expression": "coalesce((valor_multa <=> pos_venda.regras.valor_multa(valor_parcela)) AND (valor_juros <=> pos_venda.regras.valor_juros(valor_parcela, dias_atraso)) AND (valor_total_pendente <=> pos_venda.regras.valor_total_pendente(valor_parcela, dias_atraso)), false)", "msg": "multa, juros ou total fora da regra de cálculo"}', 'regra original da barreira da silver', 'carga_diaria/gerar_carga.py (MOTIVO_REJEICAO)', 'dono do projeto', DATE'2026-11-26'),
('baixa_sem_data_ou_valor_pago', 1, 'Toda baixa tem data e valor pago', 'erro', 'cobranca', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, 0.0, 'sql_expression', '{"expression": "coalesce(NOT (tipo_evento = ''BAIXA'' AND (data_baixa IS NULL OR valor_pago IS NULL)), true)", "msg": "baixa sem data ou sem valor pago"}', 'regra original da barreira da silver', 'carga_diaria/gerar_carga.py (MOTIVO_REJEICAO)', 'dono do projeto', DATE'2026-11-26'),
('uf_invalida', 1, 'A UF do cliente é uma das 27', 'erro', 'carteira', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, 0.0, 'sql_expression', '{"expression": "coalesce(upper(trim(cliente_uf)) IN (''AC'', ''AL'', ''AP'', ''AM'', ''BA'', ''CE'', ''DF'', ''ES'', ''GO'', ''MA'', ''MT'', ''MS'', ''MG'', ''PA'', ''PB'', ''PR'', ''PE'', ''PI'', ''RJ'', ''RN'', ''RS'', ''RO'', ''RR'', ''SC'', ''SP'', ''SE'', ''TO''), true)", "msg": "UF do cliente fora das 27 UFs"}', 'regra original da barreira da silver', 'carga_diaria/gerar_carga.py (MOTIVO_REJEICAO)', 'dono do projeto', DATE'2026-11-26'),
('cliente_menor_de_idade', 1, 'O cliente tem 18 anos ou mais', 'erro', 'carteira', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, 0.0, 'sql_expression', '{"expression": "coalesce(cliente_idade >= 18, true)", "msg": "cliente com menos de 18 anos"}', 'regra original da barreira da silver', 'carga_diaria/gerar_carga.py (MOTIVO_REJEICAO)', 'dono do projeto', DATE'2026-11-26'),
('email_ausente', 1, 'O cliente tem e-mail cadastrado', 'aviso', 'carteira', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, NULL, 'is_not_null', '{"column": "cliente_email"}', 'aviso original do DQX como código', 'dqx_codigo/checks_pendencias.yml', 'dono do projeto', DATE'2026-11-26'),
('forma_pagamento_ausente', 1, 'A pendência tem forma de pagamento', 'aviso', 'cobranca', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, NULL, 'is_not_null', '{"column": "forma_pagamento"}', 'aviso original do DQX como código', 'dqx_codigo/checks_pendencias.yml', 'dono do projeto', DATE'2026-11-26'),
('periodicidade_fora_do_dominio', 1, 'A periodicidade é mensal, trimestral, semestral ou anual', 'aviso', 'carteira', 'financeiro_pos_venda', 'data_extracao', 'aprovada', NULL, NULL, NULL, 'sql_expression', '{"expression": "coalesce(periodicidade_pagamento IN (''MENSAL'', ''TRIMESTRAL'', ''SEMESTRAL'', ''ANUAL''), true)", "msg": "periodicidade fora do domínio (ex.: QUINZENAL, BIMESTRAL)"}', 'aviso original do DQX como código', 'dqx_codigo/checks_pendencias.yml', 'dono do projeto', DATE'2026-11-26');

CREATE TABLE IF NOT EXISTS pos_venda.regras.triagem_regras (
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
COMMENT 'Triagem das falhas de regra: cada semana com falha recebe uma classificação e uma ação. Fecha o ciclo de retroalimentação (P41): regra errada vira versão nova; dado ruim vira ação no plano.';

ALTER TABLE pos_venda.regras.triagem_regras DROP CONSTRAINT IF EXISTS classificacao_valida;

ALTER TABLE pos_venda.regras.triagem_regras ADD CONSTRAINT classificacao_valida CHECK (classificacao IN ('dado_ruim', 'regra_errada', 'fora_da_vigencia', 'esperado'));

CREATE OR REPLACE FUNCTION pos_venda.regras.versao_vigente(
  regra STRING COMMENT 'regra_id do catálogo, por exemplo uf_invalida',
  dia DATE COMMENT 'data do dado (data_extracao do evento)')
RETURNS INT
COMMENT 'Versão aprovada da regra que vale para o dado do dia informado (P41); nula quando a regra não vale nesse dia.'
RETURN (SELECT max(c.versao) FROM pos_venda.regras.catalogo_regras c
        WHERE c.regra_id = regra AND c.status = 'aprovada'
          AND dia >= coalesce(c.vigente_de, DATE'0001-01-01') AND dia < coalesce(c.vigente_ate, DATE'9999-12-31'));

CREATE OR REPLACE VIEW pos_venda.regras.v_falhas_regras (
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
AS WITH dias AS (SELECT data_extracao AS dia, count(*) AS avaliados FROM pos_venda.bronze.pagamentos_pendentes_eventos GROUP BY 1),
barreira AS (SELECT data_extracao AS dia, motivo_rejeicao AS regra_id, count(*) AS reprovados FROM pos_venda.silver.pendencia_evento_quarentena GROUP BY 1, 2),
dqx_linhas AS (   -- só o nome de cada regra violada: erros e avisos
  SELECT data_extracao AS dia, concat(coalesce(transform(_errors, v -> v.name), array()), coalesce(transform(_warnings, v -> v.name), array())) AS nomes
  FROM pos_venda.dqx_codigo.eventos_quarentena
  UNION ALL
  SELECT data_extracao, coalesce(transform(_warnings, v -> v.name), array()) FROM pos_venda.dqx_codigo.eventos_validos),
dqx_dias AS (SELECT dia, count(*) AS avaliados FROM dqx_linhas GROUP BY 1),
dqx AS (SELECT dia, regra_id, count(*) AS reprovados FROM (SELECT dia, explode(nomes) AS regra_id FROM dqx_linhas) GROUP BY 1, 2),
base AS (
  SELECT d.dia, 'barreira' AS fonte, c.regra_id, c.versao, c.titulo, c.tipo, c.dono, c.limite_taxa, d.avaliados,
         coalesce(b.reprovados, 0) AS reprovados
  FROM dias d JOIN pos_venda.regras.catalogo_regras c ON c.tipo = 'erro' AND c.status = 'aprovada' AND d.dia >= coalesce(c.vigente_de, DATE'0001-01-01') AND d.dia < coalesce(c.vigente_ate, DATE'9999-12-31')
  LEFT JOIN barreira b ON b.dia = d.dia AND b.regra_id = c.regra_id
  UNION ALL
  SELECT d.dia, 'dqx_codigo', c.regra_id, c.versao, c.titulo, c.tipo, c.dono, c.limite_taxa, d.avaliados,
         coalesce(x.reprovados, 0)
  FROM dqx_dias d JOIN pos_venda.regras.catalogo_regras c ON c.status = 'aprovada' AND d.dia >= coalesce(c.vigente_de, DATE'0001-01-01') AND d.dia < coalesce(c.vigente_ate, DATE'9999-12-31')
  LEFT JOIN dqx x ON x.dia = d.dia AND x.regra_id = c.regra_id)
SELECT dia, fonte, regra_id, versao, titulo, tipo, dono, limite_taxa, avaliados, reprovados,
       reprovados / avaliados AS taxa, reprovados / avaliados > coalesce(limite_taxa, 0) AS acima_do_limite
FROM base;

CREATE OR REPLACE VIEW pos_venda.regras.v_triagem_pendente (
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
FROM pos_venda.regras.v_falhas_regras f
WHERE NOT EXISTS (SELECT 1 FROM pos_venda.regras.triagem_regras t
                  WHERE t.regra_id = f.regra_id AND (t.versao IS NULL OR t.versao = f.versao)
                    AND f.dia BETWEEN t.periodo_de AND t.periodo_ate)
GROUP BY ALL
HAVING sum(f.reprovados) / sum(f.avaliados) > coalesce(max(f.limite_taxa), 0);

CREATE OR REPLACE VIEW pos_venda.regras.v_mudancas_regras (
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
FROM pos_venda.regras.catalogo_regras WHERE status = 'aprovada' AND vigente_de IS NOT NULL;

CREATE OR REPLACE VIEW pos_venda.regras.v_retroalimentacao (
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
              FROM pos_venda.regras.catalogo_regras WHERE status = 'aprovada' GROUP BY 1),
f AS (SELECT regra_id, sum(reprovados) AS reprovados, count(DISTINCT CASE WHEN reprovados > 0 THEN dia END) AS dias_com_falha
      FROM pos_venda.regras.v_falhas_regras GROUP BY 1),
p AS (SELECT regra_id, count(*) AS semanas_pendentes FROM pos_venda.regras.v_triagem_pendente GROUP BY 1),
t AS (SELECT regra_id, count(*) AS triagens, count_if(classificacao = 'dado_ruim') AS dado_ruim,
             count_if(classificacao = 'regra_errada') AS regra_errada, count_if(classificacao = 'fora_da_vigencia') AS fora_da_vigencia,
             count_if(classificacao = 'esperado') AS esperado, max(registrado_em) AS ultima_triagem
      FROM pos_venda.regras.triagem_regras GROUP BY 1)
SELECT c.regra_id, c.titulo, c.tipo, c.dono, c.versoes, c.versao_atual, coalesce(f.reprovados, 0) AS reprovados,
       coalesce(f.dias_com_falha, 0) AS dias_com_falha, coalesce(p.semanas_pendentes, 0) AS semanas_pendentes,
       coalesce(t.triagens, 0) AS triagens, coalesce(t.dado_ruim, 0) AS dado_ruim, coalesce(t.regra_errada, 0) AS regra_errada,
       coalesce(t.fora_da_vigencia, 0) AS fora_da_vigencia, coalesce(t.esperado, 0) AS esperado,
       t.regra_errada / t.triagens AS taxa_falso_positivo, t.ultima_triagem
FROM c LEFT JOIN f USING (regra_id) LEFT JOIN p USING (regra_id) LEFT JOIN t USING (regra_id);
