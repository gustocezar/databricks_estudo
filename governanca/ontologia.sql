CREATE SCHEMA IF NOT EXISTS pos_venda.ontologia COMMENT 'Pós-venda: camada de ontologia — entidades de negócio, relações, glossário e métricas governadas (metric views). Sem identificadores pessoais.';

CREATE OR REPLACE VIEW pos_venda.ontologia.cliente (
  cliente_sk COMMENT 'Chave substituta do cliente (xxhash64 de cliente_id) para dim_cliente.',
  faixa_etaria COMMENT 'Faixa etária do cliente.',
  uf COMMENT 'UF do cliente.',
  cpf_valido COMMENT 'Verdadeiro se o dígito verificador do CPF confere.',
  data_cadastro COMMENT 'Data de cadastro do cliente.'
)
COMMENT 'Entidade Cliente (segurado pagador), sem identificadores pessoais: use cliente_sk para ligar.'
AS
SELECT cliente_sk, cliente_faixa_etaria, cliente_uf, cliente_cpf_valido, cliente_data_cadastro FROM pos_venda.gold.dim_cliente;

CREATE OR REPLACE VIEW pos_venda.ontologia.apolice (
  apolice_sk COMMENT 'Chave substituta da apólice (xxhash64 do número) para dim_apolice.',
  numero_apolice COMMENT 'Número da apólice de vida (ex.: VID000289125).',
  status_apolice COMMENT 'Status da apólice: ATIVA, SUSPENSA, REDUZIDA ou CANCELADA_INADIMPLENCIA.',
  data_emissao COMMENT 'Data de emissão da apólice.',
  data_inicio_vigencia COMMENT 'Início da vigência da apólice.',
  data_fim_vigencia_atual COMMENT 'Fim da vigência atual da apólice.',
  dia_vencimento COMMENT 'Dia do mês em que as parcelas da apólice vencem.',
  capital_segurado_principal COMMENT 'Capital segurado da cobertura principal em R$.',
  capital_segurado_total COMMENT 'Capital segurado somando todas as coberturas em R$.',
  valor_premio_periodico COMMENT 'Valor do prêmio por parcela em R$.',
  qtd_coberturas COMMENT 'Quantidade de coberturas da apólice.',
  qtd_endossos COMMENT 'Quantidade de endossos (alterações) da apólice.',
  tipo_ultimo_endosso COMMENT 'Tipo do último endosso (ex.: ALTERACAO_CAPITAL, REAJUSTE_ANUAL).',
  data_ultimo_endosso COMMENT 'Data do último endosso da apólice.',
  qtd_beneficiarios COMMENT 'Quantidade de beneficiários da apólice.'
)
COMMENT 'Entidade Apólice de seguro de vida (contrato): status, vigência, capital, prêmio, coberturas e endossos.'
AS
SELECT apolice_sk, numero_apolice, status_apolice, data_emissao, data_inicio_vigencia, data_fim_vigencia_atual, dia_vencimento, capital_segurado_principal, capital_segurado_total, valor_premio_periodico, qtd_coberturas, qtd_endossos, tipo_ultimo_endosso, data_ultimo_endosso, qtd_beneficiarios FROM pos_venda.gold.dim_apolice;

CREATE OR REPLACE VIEW pos_venda.ontologia.produto (
  produto_sk COMMENT 'Chave substituta do produto para dim_produto.',
  produto_codigo COMMENT 'Código do produto de vida (ex.: VID-ESS).',
  produto_nome COMMENT 'Nome do produto de vida (ex.: Vida Essencial).',
  categoria_produto COMMENT 'Categoria do produto: TEMPORARIO, VITALICIO, FAMILIAR, RENDA, DOENCAS_GRAVES, PREMIUM ou RESGATAVEL.',
  cobertura_principal_nome COMMENT 'Nome da cobertura principal do produto.'
)
COMMENT 'Entidade Produto de seguro de vida (8 produtos) e cobertura principal.'
AS
SELECT produto_sk, produto_codigo, produto_nome, categoria_produto, cobertura_principal_nome FROM pos_venda.gold.dim_produto;

CREATE OR REPLACE VIEW pos_venda.ontologia.apolice_cobertura (
  apolice_sk COMMENT 'Chave substituta da apólice (xxhash64 do número) para dim_apolice.',
  cobertura_sk COMMENT 'Chave substituta da cobertura para dim_cobertura.',
  cobertura_nome COMMENT 'Nome da cobertura.',
  grupo_cobertura COMMENT 'Grupo da cobertura (morte, invalidez, doença, renda, assistência).',
  papel_cobertura COMMENT 'Papel da cobertura na apólice: PRINCIPAL ou ADICIONAL.',
  capital_segurado_cobertura COMMENT 'Capital segurado desta cobertura na apólice em R$.'
)
COMMENT 'Relação Apólice tem Cobertura (N:N), com papel PRINCIPAL/ADICIONAL e capital.'
AS
SELECT b.apolice_sk, b.cobertura_sk, c.cobertura_nome, c.grupo_cobertura, b.papel_cobertura, b.capital_segurado_cobertura FROM pos_venda.gold.bridge_apolice_cobertura b JOIN pos_venda.gold.dim_cobertura c ON c.cobertura_sk = b.cobertura_sk;

CREATE OR REPLACE VIEW pos_venda.ontologia.corretor (
  corretor_sk COMMENT 'Chave substituta do corretor para dim_corretor (NAO_INFORMADO quando não há corretor).',
  corretor_id COMMENT 'Identificador do corretor (nulo em vendas DIGITAL e TELEVENDAS; NAO_INFORMADO na gold).',
  corretor_tipo_pessoa COMMENT 'Tipo de pessoa do corretor: PF ou PJ.',
  corretor_registro_susep COMMENT 'Registro do corretor na SUSEP.',
  corretor_regional COMMENT 'Regional do corretor.',
  corretor_comissao_pct COMMENT 'Percentual de comissão do corretor.',
  corretor_status COMMENT 'Situação do corretor no credenciamento.'
)
COMMENT 'Entidade Corretor (sem nome e documento): SUSEP, regional, comissão e status. NAO_INFORMADO = venda sem corretor.'
AS
SELECT corretor_sk, corretor_id, corretor_tipo_pessoa, corretor_registro_susep, corretor_regional, corretor_comissao_pct, corretor_status FROM pos_venda.gold.dim_corretor;

CREATE OR REPLACE VIEW pos_venda.ontologia.ponto_venda (
  ponto_venda_sk COMMENT 'Chave substituta do ponto de venda para dim_ponto_venda.',
  ponto_venda_codigo COMMENT 'Código do ponto de venda.',
  ponto_venda_nome COMMENT 'Nome do ponto de venda (escritório, agência, plataforma ou central).',
  ponto_venda_tipo COMMENT 'Tipo do ponto de venda: ESCRITORIO_CORRETOR, AGENCIA_BANCARIA, plataforma digital ou televendas.',
  canal_venda COMMENT 'Canal de venda da apólice: CORRETOR, BANCASSURANCE, DIGITAL ou TELEVENDAS.',
  ponto_venda_cidade COMMENT 'Cidade do ponto de venda.',
  ponto_venda_uf COMMENT 'UF do ponto de venda.',
  ponto_venda_regional COMMENT 'Regional comercial do ponto de venda.'
)
COMMENT 'Entidade Ponto de venda e canal de venda.'
AS
SELECT ponto_venda_sk, ponto_venda_codigo, ponto_venda_nome, ponto_venda_tipo, canal_venda, ponto_venda_cidade, ponto_venda_uf, ponto_venda_regional FROM pos_venda.gold.dim_ponto_venda;

CREATE OR REPLACE VIEW pos_venda.ontologia.pendencia (
  pendencia_id COMMENT 'Identificador da pendência: PD + número da apólice sem prefixo + parcela com 3 dígitos.',
  numero_apolice COMMENT 'Número da apólice de vida (ex.: VID000289125).',
  numero_parcela COMMENT 'Número sequencial da parcela do prêmio dentro da apólice.',
  produto_codigo COMMENT 'Código do produto de vida (ex.: VID-ESS).',
  produto_nome COMMENT 'Nome do produto de vida (ex.: Vida Essencial).',
  canal_venda COMMENT 'Canal de venda da apólice: CORRETOR, BANCASSURANCE, DIGITAL ou TELEVENDAS.',
  corretor_id COMMENT 'Identificador do corretor (nulo em vendas DIGITAL e TELEVENDAS; NAO_INFORMADO na gold).',
  forma_pagamento COMMENT 'Forma de pagamento: DEBITO_CONTA, BOLETO, CARTAO_CREDITO ou PIX_AUTOMATICO (valores fora disso são inválidos).',
  periodicidade_pagamento COMMENT 'Periodicidade do prêmio: MENSAL, TRIMESTRAL, SEMESTRAL ou ANUAL.',
  motivo_pendencia COMMENT 'Motivo do não pagamento (depende da forma de pagamento). Ver dim_motivo_pendencia.',
  data_vencimento COMMENT 'Data de vencimento da parcela.',
  data_entrada COMMENT 'Dia em que a pendência entrou (dia seguinte ao vencimento).',
  safra_entrada COMMENT 'Mês de entrada da pendência (safra), para a taxa de recuperação.',
  status_cobranca COMMENT 'Status atual da cobrança.',
  paga COMMENT 'Verdadeiro se a pendência já foi paga (status PAGA).',
  data_baixa COMMENT 'Data do pagamento da pendência (só em eventos BAIXA).',
  valor_pago COMMENT 'Valor pago na baixa em R$ (valor total pendente no dia do pagamento; só em eventos BAIXA).',
  dias_ate_baixa COMMENT 'Dias entre o vencimento e a baixa (só pagas).',
  valor_parcela COMMENT 'Valor da parcela do prêmio em R$ (prêmio periódico).',
  data_ultimo_evento COMMENT 'Dia do último evento recebido da pendência.'
)
COMMENT 'Entidade Pendência (1 linha por pendência, estado atual): entrada, status, baixa e safra. Base da taxa de recuperação.'
AS
SELECT pendencia_id, numero_apolice, numero_parcela, produto_codigo, produto_nome, canal_venda, corretor_id,
       forma_pagamento, periodicidade_pagamento, motivo_pendencia, data_vencimento,
       date_add(data_vencimento, 1) AS data_entrada, CAST(date_trunc('MONTH', date_add(data_vencimento, 1)) AS DATE) AS safra_entrada,
       status_cobranca, status_cobranca = 'PAGA' AS paga, data_baixa, valor_pago,
       CASE WHEN status_cobranca = 'PAGA' THEN datediff(data_baixa, data_vencimento) END AS dias_ate_baixa,
       valor_parcela, data_extracao AS data_ultimo_evento
FROM pos_venda.silver.pendencia_atual;

CREATE OR REPLACE VIEW pos_venda.ontologia.pagamento (
  pendencia_id COMMENT 'Identificador da pendência: PD + número da apólice sem prefixo + parcela com 3 dígitos.',
  numero_apolice COMMENT 'Número da apólice de vida (ex.: VID000289125).',
  produto_codigo COMMENT 'Código do produto de vida (ex.: VID-ESS).',
  produto_nome COMMENT 'Nome do produto de vida (ex.: Vida Essencial).',
  categoria_produto COMMENT 'Categoria do produto: TEMPORARIO, VITALICIO, FAMILIAR, RENDA, DOENCAS_GRAVES, PREMIUM ou RESGATAVEL.',
  canal_venda COMMENT 'Canal de venda da apólice: CORRETOR, BANCASSURANCE, DIGITAL ou TELEVENDAS.',
  forma_pagamento COMMENT 'Forma de pagamento: DEBITO_CONTA, BOLETO, CARTAO_CREDITO ou PIX_AUTOMATICO (valores fora disso são inválidos).',
  motivo_pendencia COMMENT 'Motivo do não pagamento (depende da forma de pagamento). Ver dim_motivo_pendencia.',
  data_vencimento COMMENT 'Data de vencimento da parcela.',
  data_baixa COMMENT 'Data do pagamento da pendência (só em eventos BAIXA).',
  dias_atraso_na_baixa COMMENT 'Dias de atraso no dia do pagamento.',
  faixa_atraso_na_baixa COMMENT 'Faixa de atraso no dia do pagamento.',
  valor_parcela COMMENT 'Valor da parcela do prêmio em R$ (prêmio periódico).',
  valor_multa COMMENT 'Multa por atraso em R$: 2% da parcela.',
  valor_juros COMMENT 'Juros por atraso em R$: 1% ao mês pro rata dia sobre a parcela.',
  valor_pago COMMENT 'Valor pago na baixa em R$ (valor total pendente no dia do pagamento; só em eventos BAIXA).'
)
COMMENT 'Entidade Pagamento (baixa): 1 linha por pendência paga, eventos BAIXA deduplicados. Base do valor recuperado.'
AS
SELECT pendencia_id, numero_apolice, produto_codigo, produto_nome, categoria_produto, canal_venda, forma_pagamento,
       motivo_pendencia, data_vencimento, data_baixa, dias_atraso, faixa_atraso, valor_parcela, valor_multa, valor_juros, valor_pago
FROM pos_venda.silver.pendencia_evento
WHERE tipo_evento = 'BAIXA'
QUALIFY row_number() OVER (PARTITION BY pendencia_id ORDER BY _silver_ts) = 1;

CREATE OR REPLACE VIEW pos_venda.ontologia.evento_cobranca (
  pendencia_id COMMENT 'Identificador da pendência: PD + número da apólice sem prefixo + parcela com 3 dígitos.',
  data_extracao COMMENT 'Dia em que o evento foi extraído do sistema de origem (dia do evento).',
  tipo_evento COMMENT 'Tipo do evento da pendência: NOVA (entrada), ATUALIZACAO (mudança de fase) ou BAIXA (pagamento).',
  status_cobranca COMMENT 'Status da cobrança: PENDENTE, EM_COBRANCA, PROMESSA_PAGAMENTO, NEGOCIADO, COBRANCA_EXTERNA ou PAGA.',
  dias_atraso COMMENT 'Dias de atraso no dia do evento: data_extracao - data_vencimento.',
  faixa_atraso COMMENT 'Faixa de atraso (aging): 00_VENCE_HOJE, 01_1_A_15, 02_16_A_30, 03_31_A_60, 04_61_A_90, 05_91_A_120, 06_ACIMA_120.',
  valor_total_pendente COMMENT 'Valor atualizado em R$: parcela + multa + juros. Na fato, recalculado no dia da foto.',
  canal_ultimo_contato COMMENT 'Canal do último contato de cobrança: SMS, EMAIL, WHATSAPP, TELEFONE, CARTA ou NENHUM.',
  tentativas_cobranca COMMENT 'Tentativas de cobrança feitas (1 a 10): 1 + 1 a cada 10 dias de atraso + 1 se saiu de PENDENTE.'
)
COMMENT 'Entidade Evento de cobrança (NOVA, ATUALIZACAO, BAIXA) apto, deduplicado por pendência, dia e tipo.'
AS
SELECT pendencia_id, data_extracao, tipo_evento, status_cobranca, dias_atraso, faixa_atraso, valor_total_pendente,
       canal_ultimo_contato, tentativas_cobranca
FROM pos_venda.silver.pendencia_evento
QUALIFY row_number() OVER (PARTITION BY pendencia_id, data_extracao, tipo_evento ORDER BY _silver_ts) = 1;

CREATE OR REPLACE VIEW pos_venda.ontologia.posicao_carteira (
  data_referencia COMMENT 'Dia da foto da carteira.',
  data_referencia_sk COMMENT 'Dia da foto (yyyyMMdd). Filtre um único dia para saldos: o saldo é semiaditivo.',
  foto_mais_recente COMMENT 'Verdadeiro na foto mais recente disponível.',
  fim_de_mes COMMENT 'Verdadeiro se o dia da foto é o último dia do mês.',
  pendencia_id COMMENT 'Identificador da pendência: PD + número da apólice sem prefixo + parcela com 3 dígitos.',
  cliente_sk COMMENT 'Chave substituta do cliente (xxhash64 de cliente_id) para dim_cliente.',
  apolice_sk COMMENT 'Chave substituta da apólice (xxhash64 do número) para dim_apolice.',
  status_cobranca COMMENT 'Status da cobrança: PENDENTE, EM_COBRANCA, PROMESSA_PAGAMENTO, NEGOCIADO, COBRANCA_EXTERNA ou PAGA.',
  fase_cobranca COMMENT 'Fase da cobrança: INICIAL, INTERNA, NEGOCIACAO, EXTERNA ou ENCERRADA.',
  faixa_atraso COMMENT 'Faixa de atraso no dia da foto.',
  ordem_faixa COMMENT 'Ordem da faixa de atraso, para ordenar o aging.',
  produto_nome COMMENT 'Nome do produto de vida (ex.: Vida Essencial).',
  categoria_produto COMMENT 'Categoria do produto: TEMPORARIO, VITALICIO, FAMILIAR, RENDA, DOENCAS_GRAVES, PREMIUM ou RESGATAVEL.',
  canal_venda COMMENT 'Canal de venda da apólice: CORRETOR, BANCASSURANCE, DIGITAL ou TELEVENDAS.',
  ponto_venda_regional COMMENT 'Regional comercial do ponto de venda.',
  ponto_venda_uf COMMENT 'UF do ponto de venda.',
  forma_pagamento COMMENT 'Forma de pagamento (NAO_CADASTRADA quando a forma não existe no catálogo).',
  grupo_forma_pagamento COMMENT 'Grupo da forma de pagamento: AUTOMATICO, CARTAO ou BOLETO.',
  motivo_pendencia COMMENT 'Motivo do não pagamento (depende da forma de pagamento). Ver dim_motivo_pendencia.',
  grupo_motivo COMMENT 'Grupo do motivo: FINANCEIRO, CADASTRAL, AUTORIZACAO ou OPERACIONAL.',
  periodicidade_pagamento COMMENT 'Periodicidade do prêmio: MENSAL, TRIMESTRAL, SEMESTRAL ou ANUAL.',
  status_apolice COMMENT 'Status da apólice: ATIVA, SUSPENSA, REDUZIDA ou CANCELADA_INADIMPLENCIA.',
  canal_ultimo_contato COMMENT 'Canal do último contato de cobrança: SMS, EMAIL, WHATSAPP, TELEFONE, CARTA ou NENHUM.',
  dias_atraso COMMENT 'Dias de atraso no dia da foto: data de referência - data de vencimento (recalculado a cada dia).',
  tentativas_cobranca COMMENT 'Tentativas de cobrança feitas (1 a 10): 1 + 1 a cada 10 dias de atraso + 1 se saiu de PENDENTE.',
  valor_parcela COMMENT 'Valor da parcela do prêmio em R$ (prêmio periódico).',
  valor_multa COMMENT 'Multa por atraso em R$: 2% da parcela.',
  valor_juros COMMENT 'Juros por atraso em R$: 1% ao mês pro rata dia sobre a parcela.',
  valor_total_pendente COMMENT 'Valor atualizado em R$: parcela + multa + juros. Na fato, recalculado no dia da foto.'
)
COMMENT 'Posição diária da carteira em aberto (fato snapshot com rótulos legíveis). SALDO É SEMIADITIVO: some só dentro de um mesmo dia.'
AS
SELECT to_date(CAST(f.data_referencia_sk AS STRING), 'yyyyMMdd') AS data_referencia, f.data_referencia_sk,
       f.data_referencia_sk = (SELECT max(data_referencia_sk) FROM pos_venda.gold.fact_pagamento_pendente_snapshot) AS foto_mais_recente,
       coalesce(d.ultimo_dia_mes, false) AS fim_de_mes,
       f.pendencia_id, f.cliente_sk, f.apolice_sk, s.status_cobranca, s.fase_cobranca, fa.faixa_atraso, fa.ordem_faixa,
       p.produto_nome, p.categoria_produto, pv.canal_venda, pv.ponto_venda_regional, pv.ponto_venda_uf,
       coalesce(fp.forma_pagamento, 'NAO_CADASTRADA') AS forma_pagamento, coalesce(fp.grupo_forma_pagamento, 'NAO_CADASTRADA') AS grupo_forma_pagamento,
       m.motivo_pendencia, m.grupo_motivo, pe.periodicidade_pagamento, a.status_apolice, f.canal_ultimo_contato,
       f.dias_atraso, f.tentativas_cobranca, f.valor_parcela, f.valor_multa, f.valor_juros, f.valor_total_pendente
FROM pos_venda.gold.fact_pagamento_pendente_snapshot f
LEFT JOIN pos_venda.gold.dim_data d ON d.data_sk = f.data_referencia_sk
LEFT JOIN pos_venda.gold.dim_status_cobranca s ON s.status_cobranca_sk = f.status_cobranca_sk
LEFT JOIN pos_venda.gold.dim_faixa_atraso fa ON fa.faixa_atraso_sk = f.faixa_atraso_sk
LEFT JOIN pos_venda.gold.dim_produto p ON p.produto_sk = f.produto_sk
LEFT JOIN pos_venda.gold.dim_ponto_venda pv ON pv.ponto_venda_sk = f.ponto_venda_sk
LEFT JOIN pos_venda.gold.dim_forma_pagamento fp ON fp.forma_pagamento_sk = f.forma_pagamento_sk
LEFT JOIN pos_venda.gold.dim_motivo_pendencia m ON m.motivo_pendencia_sk = f.motivo_pendencia_sk
LEFT JOIN pos_venda.gold.dim_periodicidade pe ON pe.periodicidade_sk = f.periodicidade_sk
LEFT JOIN pos_venda.gold.dim_apolice a ON a.apolice_sk = f.apolice_sk;

CREATE OR REPLACE TABLE pos_venda.ontologia.entidades (entidade STRING COMMENT 'Nome da entidade de negócio', objeto STRING COMMENT 'View da entidade em pos_venda.ontologia', chave STRING COMMENT 'Chave da entidade', descricao STRING COMMENT 'Definição curta', origem STRING COMMENT 'Tabela de origem') COMMENT 'Catálogo das entidades da ontologia do Pós-venda.';

INSERT INTO pos_venda.ontologia.entidades VALUES ('Cliente', 'pos_venda.ontologia.cliente', 'cliente_sk', 'Segurado pagador (sem identificadores pessoais).', 'pos_venda.gold.dim_cliente'), ('Apólice', 'pos_venda.ontologia.apolice', 'apolice_sk', 'Contrato de seguro de vida.', 'pos_venda.gold.dim_apolice'), ('Produto', 'pos_venda.ontologia.produto', 'produto_sk', 'Produto de seguro de vida.', 'pos_venda.gold.dim_produto'), ('Cobertura', 'pos_venda.ontologia.apolice_cobertura', 'apolice_sk, cobertura_sk', 'Coberturas de cada apólice.', 'pos_venda.gold.bridge_apolice_cobertura'), ('Corretor', 'pos_venda.ontologia.corretor', 'corretor_sk', 'Corretor que vendeu a apólice.', 'pos_venda.gold.dim_corretor'), ('Ponto de venda', 'pos_venda.ontologia.ponto_venda', 'ponto_venda_sk', 'Ponto e canal de venda.', 'pos_venda.gold.dim_ponto_venda'), ('Pendência', 'pos_venda.ontologia.pendencia', 'pendencia_id', 'Parcela não paga no vencimento (estado atual).', 'pos_venda.silver.pendencia_atual'), ('Evento de cobrança', 'pos_venda.ontologia.evento_cobranca', 'pendencia_id, data_extracao, tipo_evento', 'NOVA, ATUALIZACAO ou BAIXA.', 'pos_venda.silver.pendencia_evento'), ('Pagamento', 'pos_venda.ontologia.pagamento', 'pendencia_id', 'Baixa da pendência.', 'pos_venda.silver.pendencia_evento (BAIXA)'), ('Posição da carteira', 'pos_venda.ontologia.posicao_carteira', 'data_referencia_sk, pendencia_id', 'Foto diária das pendências em aberto.', 'pos_venda.gold.fact_pagamento_pendente_snapshot');

CREATE OR REPLACE TABLE pos_venda.ontologia.relacoes (sujeito STRING COMMENT 'Entidade de origem', predicado STRING COMMENT 'Relação', objeto STRING COMMENT 'Entidade de destino', cardinalidade STRING COMMENT 'Cardinalidade', chave STRING COMMENT 'Chave da ligação', descricao STRING COMMENT 'Explicação') COMMENT 'Relações entre as entidades do Pós-venda (triplas sujeito-predicado-objeto).';

INSERT INTO pos_venda.ontologia.relacoes VALUES ('Cliente', 'possui', 'Apólice', '1:N', 'cliente_sk', 'Um cliente pode ter várias apólices.'), ('Apólice', 'é do produto', 'Produto', 'N:1', 'produto_codigo / produto_sk', 'Cada apólice é de um produto.'), ('Apólice', 'tem cobertura', 'Cobertura', 'N:N', 'apolice_sk + cobertura_sk', 'Coberturas principal e adicionais da apólice.'), ('Apólice', 'foi vendida por', 'Corretor', 'N:0..1', 'corretor_id / corretor_sk', 'Vendas DIGITAL e TELEVENDAS não têm corretor.'), ('Apólice', 'foi vendida em', 'Ponto de venda', 'N:1', 'ponto_venda_codigo / ponto_venda_sk', 'Ponto e canal de venda.'), ('Apólice', 'gera', 'Pendência', '1:N', 'numero_apolice', 'Cada parcela não paga no vencimento vira uma pendência.'), ('Pendência', 'tem', 'Evento de cobrança', '1:N', 'pendencia_id', 'NOVA na entrada, ATUALIZACAO nas mudanças de fase, BAIXA no pagamento.'), ('Pendência', 'é quitada por', 'Pagamento', '1:0..1', 'pendencia_id', 'Nem toda pendência é paga.'), ('Pendência', 'aparece na', 'Posição da carteira', '1:N', 'pendencia_id', 'Uma linha por dia enquanto a pendência está em aberto.'), ('Evento barrado', 'é versão não apta de', 'Evento de cobrança', 'N:1', 'pendencia_id', 'Eventos da quarentena não entram na silver.');

CREATE OR REPLACE TABLE pos_venda.ontologia.glossario (termo STRING COMMENT 'Termo de negócio (título da Page)', subdominio STRING COMMENT 'Subdomínio do Discover', definicao STRING COMMENT 'Definição curta', sinonimos ARRAY<STRING> COMMENT 'Sinônimos usados pelas pessoas') COMMENT 'Glossário do Pós-venda: mesmo conteúdo das Pages do Discover (domínio Pós-venda).';

INSERT INTO pos_venda.ontologia.glossario VALUES ('Pendência de pagamento', 'Cobrança e inadimplência', 'Parcela do prêmio de uma apólice de vida que não foi paga até o vencimento. Existe do dia seguinte ao vencimento até a baixa (pagamento).', array('pendência', 'parcela em atraso', 'parcela vencida não paga', 'inadimplência', 'débito em aberto', 'delinquency', 'pending payment')), ('Status de cobrança', 'Cobrança e inadimplência', 'Situação da pendência no ciclo de cobrança: PENDENTE, EM_COBRANCA, PROMESSA_PAGAMENTO, NEGOCIADO, COBRANCA_EXTERNA ou PAGA.', array('status da pendência', 'fase de cobrança', 'situação da cobrança', 'collection status')), ('Dias de atraso e faixa de atraso (aging)', 'Cobrança e inadimplência', 'Dias entre o vencimento e a data de referência, agrupados em 7 faixas de 00_VENCE_HOJE a 06_ACIMA_120.', array('aging', 'atraso', 'faixa de atraso', 'bucket de atraso', 'envelhecimento da carteira', 'days past due', 'DPD')), ('Valor total pendente', 'Cobrança e inadimplência', 'Valor da parcela mais multa de 2% e juros de 1% ao mês pro rata dia, no dia de referência.', array('valor atualizado da parcela', 'saldo devedor da parcela', 'valor com encargos', 'parcela + multa + juros')), ('Saldo em aberto da carteira', 'Cobrança e inadimplência', 'Soma do valor total pendente de todas as pendências em aberto em UMA data de referência. Métrica semiaditiva: não se soma ao longo do tempo.', array('carteira em atraso', 'estoque de pendências', 'exposição', 'saldo pendente', 'valor em aberto', 'outstanding balance', 'receivables in arrears')), ('Baixa (pagamento da pendência)', 'Cobrança e inadimplência', 'Evento que encerra a pendência quando o cliente paga; registra data da baixa e valor pago.', array('baixa', 'pagamento', 'quitação', 'liquidação', 'pendência paga', 'settlement')), ('Valor recuperado e taxa de recuperação', 'Cobrança e inadimplência', 'Valor recuperado = soma dos valores pagos nas baixas. Taxa de recuperação = pendências pagas / pendências que entraram (por safra de entrada).', array('recuperação', 'valor recebido', 'taxa de recuperação', 'recovery rate', 'cobrança efetiva')), ('Motivo da pendência', 'Cobrança e inadimplência', 'Por que a parcela não foi paga; depende da forma de pagamento e se agrupa em FINANCEIRO, CADASTRAL, AUTORIZACAO e OPERACIONAL.', array('motivo do não pagamento', 'causa da inadimplência', 'motivo de recusa')), ('Foto diária da carteira (snapshot)', 'Cobrança e inadimplência', 'Fato com uma linha por pendência em aberto por dia (grão pendência × dia), com valores e atraso recalculados no dia da foto.', array('snapshot diário', 'fato histórica', 'posição diária', 'fotografia da carteira')), ('Tentativas e canal de contato da cobrança', 'Cobrança e inadimplência', 'Quantas tentativas de cobrança já foram feitas (1 a 10) e por qual canal foi o último contato.', array('tentativas de cobrança', 'canal de contato', 'régua de cobrança', 'contato com o cliente')), ('Cliente (segurado pagador)', 'Clientes e apólices', 'Pessoa física titular da apólice e responsável pelo pagamento do prêmio. Dados pessoais protegidos pela LGPD.', array('cliente', 'segurado', 'pagador', 'titular da apólice', 'policyholder')), ('Apólice de seguro de vida', 'Clientes e apólices', 'Contrato de seguro de vida do cliente: produto, vigência, capital segurado, prêmio periódico, coberturas, endossos e beneficiários.', array('apólice', 'contrato de seguro', 'policy')), ('Produto e coberturas de vida', 'Clientes e apólices', 'Oito produtos de vida (Essencial, Completo, Inteira, Família, Renda Protegida, Doenças Graves, Premium, Resgatável) e suas coberturas principal e adicionais.', array('produto', 'plano', 'cobertura', 'garantia', 'ramo vida')), ('Canal de venda, corretor e ponto de venda', 'Clientes e apólices', 'Por onde a apólice foi vendida: CORRETOR, BANCASSURANCE, DIGITAL ou TELEVENDAS, com o corretor (registro SUSEP, comissão) e o ponto de venda.', array('canal', 'corretor', 'corretora', 'ponto de venda', 'PDV', 'bancassurance', 'distribuição')), ('Forma de pagamento e periodicidade', 'Clientes e apólices', 'Como o prêmio é pago (DEBITO_CONTA, BOLETO, CARTAO_CREDITO, PIX_AUTOMATICO) e com que frequência (MENSAL, TRIMESTRAL, SEMESTRAL, ANUAL).', array('forma de pagamento', 'meio de pagamento', 'periodicidade', 'frequência de pagamento')), ('Quarentena (dado não apto)', 'Qualidade de dados', 'Eventos do bronze que violaram uma regra de erro e foram barrados antes da silver; guardam a linha original e o motivo da rejeição.', array('quarentena', 'dado não apto', 'evento barrado', 'rejeitado', 'quarantine')), ('Regra de erro e regra de aviso', 'Qualidade de dados', 'Erro barra a linha (não entra na silver); aviso deixa entrar sinalizada. As regras ficam no DQX Studio.', array('criticidade', 'error', 'warn', 'aviso de qualidade', 'regra DQX')), ('Janela de avaliação do DQX Studio', 'Qualidade de dados', 'Intervalo de dias que as views pos_venda.dq.v_*_janela expõem para o DQX Studio avaliar com todas as linhas.', array('janela', 'janela de 7 dias', 'avaliação semanal', 'dry run'));

CREATE OR REPLACE VIEW pos_venda.ontologia.mv_carteira_em_aberto
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: pos_venda.ontologia.posicao_carteira
comment: "Carteira de pendências em aberto por dia (foto diária). O saldo é SEMIADITIVO: filtre UMA data de referência (ou a foto mais recente / fim de mês) ou agrupe por data; nunca some saldos de dias diferentes."
dimensions:
  - name: Data de referência
    expr: data_referencia
    comment: "Dia da foto da carteira."
    synonyms: [data, dia da foto, posição em, data da posição]
  - name: Mês de referência
    comment: "Primeiro dia do mês da foto. Use com Saldo de fechamento e Variação mensal do saldo."
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
    comment: "Status da cobrança no dia da foto: PENDENTE, EM_COBRANCA, PROMESSA_PAGAMENTO, NEGOCIADO ou COBRANCA_EXTERNA."
    expr: status_cobranca
    synonyms: [status, situação da cobrança]
  - name: Fase da cobrança
    comment: "Fase da régua de cobrança: INICIAL, INTERNA, NEGOCIACAO ou EXTERNA."
    expr: fase_cobranca
    synonyms: [fase]
  - name: Faixa de atraso
    expr: faixa_atraso
    comment: "Aging no dia da foto (00_VENCE_HOJE a 06_ACIMA_120)."
    synonyms: [aging, bucket de atraso, faixa de dias]
  - name: Produto
    comment: "Nome do produto de seguro de vida (8 produtos, ex.: Vida Completo, Vida Essencial)."
    expr: produto_nome
    synonyms: [plano, produto de vida]
  - name: Categoria do produto
    comment: "Categoria do produto: DOENCAS_GRAVES, FAMILIAR, PREMIUM, RENDA, RESGATAVEL, TEMPORARIO ou VITALICIO."
    expr: categoria_produto
  - name: Canal de venda
    comment: "Canal em que a apólice foi vendida: BANCASSURANCE, CORRETOR, DIGITAL ou TELEVENDAS."
    expr: canal_venda
    synonyms: [canal]
  - name: Regional
    comment: "Regional comercial do ponto de venda: NORTE, NORDESTE, CENTRO-OESTE, SUDESTE ou SUL."
    expr: ponto_venda_regional
    synonyms: [regional comercial]
  - name: UF do ponto de venda
    comment: "Sigla da UF do ponto de venda (23 UFs com pendências)."
    expr: ponto_venda_uf
  - name: Forma de pagamento
    comment: "Forma de pagamento da parcela: BOLETO, CARTAO_CREDITO, DEBITO_CONTA ou PIX_AUTOMATICO. NAO_CADASTRADA é dado que vazou da barreira de qualidade (dez/2026)."
    expr: forma_pagamento
    synonyms: [meio de pagamento]
  - name: Grupo da forma de pagamento
    comment: "Agrupamento da forma de pagamento: AUTOMATICO, BOLETO, CARTAO ou NAO_CADASTRADA."
    expr: grupo_forma_pagamento
  - name: Motivo da pendência
    comment: "Motivo pelo qual a parcela não foi paga no vencimento (10 motivos, agrupados em Grupo do motivo)."
    expr: motivo_pendencia
    synonyms: [motivo, causa]
  - name: Grupo do motivo
    comment: "Agrupamento do motivo: AUTORIZACAO, CADASTRAL, FINANCEIRO ou OPERACIONAL. Cadastral pede atualização de dados; financeiro pede negociação."
    expr: grupo_motivo
  - name: Periodicidade
    comment: "Periodicidade de pagamento da apólice: MENSAL, TRIMESTRAL, SEMESTRAL ou ANUAL."
    expr: periodicidade_pagamento
  - name: Status da apólice
    comment: "Situação da apólice no dia: ATIVA, SUSPENSA, REDUZIDA ou CANCELADA_INADIMPLENCIA."
    expr: status_apolice
  - name: Canal do último contato
    comment: "Último canal usado na cobrança: CARTA, EMAIL, SMS, TELEFONE, WHATSAPP ou NENHUM."
    expr: canal_ultimo_contato
measures:
  - name: Saldo em aberto
    expr: SUM(valor_total_pendente)
    comment: "Soma do valor atualizado (parcela + multa + juros) das pendências em aberto. Semiaditivo: use com uma data."
    synonyms: [valor em aberto, carteira em atraso, exposição, saldo pendente, inadimplência em reais]
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Pendências em aberto
    expr: COUNT(1)
    comment: "Quantidade de pendências em aberto (semiaditivo: use com uma data)."
    synonyms: [quantidade de pendências, parcelas em atraso]
  - name: Valor das parcelas em aberto
    comment: "Soma do valor original das parcelas em aberto, sem multa e juros. Semiaditivo: use com uma data."
    expr: SUM(valor_parcela)
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Multa e juros em aberto
    comment: "Multa e juros acumulados nas pendências em aberto. Semiaditivo: use com uma data."
    expr: SUM(valor_multa + valor_juros)
    synonyms: [encargos, acréscimos]
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Saldo médio diário
    expr: SUM(valor_total_pendente) / COUNT(DISTINCT data_referencia)
    comment: "Média dos saldos diários no período: forma correta de resumir o saldo de vários dias."
    synonyms: [saldo médio, média do saldo]
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Ticket médio da pendência
    comment: "Saldo em aberto dividido pela quantidade de pendências em aberto."
    expr: "MEASURE(`Saldo em aberto`) / MEASURE(`Pendências em aberto`)"
    synonyms: [valor médio por pendência]
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Atraso médio em dias
    comment: "Média de dias de atraso das pendências em aberto no dia da foto."
    expr: AVG(dias_atraso)
    synonyms: [dias de atraso médio, prazo médio de atraso]
  - name: Saldo acima de 60 dias
    comment: "Saldo em aberto das pendências com mais de 60 dias de atraso. Semiaditivo: use com uma data."
    expr: SUM(valor_total_pendente) FILTER (WHERE dias_atraso > 60)
    synonyms: [atraso longo, saldo crítico]
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Percentual do saldo acima de 60 dias
    comment: "Saldo acima de 60 dias dividido pelo saldo em aberto: indicador de risco da carteira."
    expr: "MEASURE(`Saldo acima de 60 dias`) / MEASURE(`Saldo em aberto`)"
    format:
      type: percentage
      decimal_places:
        type: max
        places: 2
  - name: Saldo em cobrança externa
    comment: "Saldo em aberto das pendências em cobrança externa (status COBRANCA_EXTERNA). Semiaditivo: use com uma data."
    expr: SUM(valor_total_pendente) FILTER (WHERE status_cobranca = 'COBRANCA_EXTERNA')
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Clientes com pendência
    comment: "Quantidade de clientes distintos com pendência em aberto (contagem, sem dados pessoais)."
    expr: COUNT(DISTINCT cliente_sk)
  - name: Apólices com pendência
    comment: "Quantidade de apólices distintas com pendência em aberto."
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
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
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
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Variação do saldo no período
    expr: "MEASURE(`Saldo de fechamento`) - MEASURE(`Saldo no início do período`)"
    comment: "Fechamento menos início DENTRO de um período de vários dias (ex.: agrupado por mês). Agrupado por data é sempre zero. Para comparar duas datas ou dois fins de mês, use Saldo em aberto em cada data ou Variação mensal do saldo."
    synonyms: [variação dentro do mês, crescimento da carteira dentro do período]
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Saldo de fechamento do mês anterior
    expr: SUM(valor_total_pendente) FILTER (WHERE fim_de_mes)
    window:
      - order: Mês de referência
        range: current
        semiadditive: last
        offset: -1 month
    comment: "Saldo no último dia do mês anterior ao mês de referência. Use agrupado por Mês de referência."
    synonyms: [fechamento do mês anterior, saldo do mês passado]
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Variação mensal do saldo
    expr: "(MEASURE(`Saldo de fechamento`) - MEASURE(`Saldo de fechamento do mês anterior`)) / MEASURE(`Saldo de fechamento do mês anterior`)"
    comment: "Variação percentual do saldo de fechamento sobre o fechamento do mês anterior (MoM). Use agrupado por Mês de referência."
    synonyms: [MoM, variação mês a mês, crescimento mensal do saldo]
    format:
      type: percentage
      decimal_places:
        type: max
        places: 2
  - name: Posição no ranking do saldo
    expr: RANK() OVER (ORDER BY SUM(valor_total_pendente) / COUNT(DISTINCT data_referencia) DESC)
    comment: "Posição (1 = maior) pelo saldo médio diário do período filtrado; com uma única data é o ranking do saldo daquele dia. Não combine na mesma consulta com as medidas de fechamento, início ou mês anterior."
    synonyms: [ranking do saldo, posição no ranking, colocação]
$$;

CREATE OR REPLACE VIEW pos_venda.ontologia.mv_recuperacao
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: pos_venda.ontologia.pagamento
comment: "Pagamentos (baixas) das pendências: valor recuperado por data da baixa. Aditivo no tempo."
dimensions:
  - name: Data da baixa
    comment: "Dia em que a pendência foi paga (baixa)."
    expr: data_baixa
    synonyms: [data do pagamento, dia do pagamento]
  - name: Mês da baixa
    comment: "Primeiro dia do mês da baixa. Use com Variação mensal do valor recuperado e Valor recuperado acumulado no ano."
    expr: "CAST(DATE_TRUNC('MONTH', data_baixa) AS DATE)"
    synonyms: [mês do pagamento]
  - name: Ano da baixa
    comment: "Primeiro dia do ano da baixa; base do acumulado no ano."
    expr: "CAST(DATE_TRUNC('YEAR', data_baixa) AS DATE)"
    synonyms: [ano do pagamento]
  - name: Produto
    comment: "Nome do produto de seguro de vida (8 produtos, ex.: Vida Completo, Vida Essencial)."
    expr: produto_nome
  - name: Categoria do produto
    comment: "Categoria do produto: DOENCAS_GRAVES, FAMILIAR, PREMIUM, RENDA, RESGATAVEL, TEMPORARIO ou VITALICIO."
    expr: categoria_produto
  - name: Canal de venda
    comment: "Canal em que a apólice foi vendida: BANCASSURANCE, CORRETOR, DIGITAL ou TELEVENDAS."
    expr: canal_venda
  - name: Forma de pagamento
    comment: "Forma de pagamento da parcela: BOLETO, CARTAO_CREDITO, DEBITO_CONTA ou PIX_AUTOMATICO. NAO_CADASTRADA é dado que vazou da barreira de qualidade (dez/2026)."
    expr: forma_pagamento
  - name: Motivo da pendência
    comment: "Motivo pelo qual a parcela não foi paga no vencimento (10 motivos, agrupados em Grupo do motivo)."
    expr: motivo_pendencia
  - name: Faixa de atraso na baixa
    comment: "Faixa de atraso no dia do pagamento (ex.: 01_1_A_15, 02_16_A_30, 03_31_A_60)."
    expr: faixa_atraso_na_baixa
measures:
  - name: Valor recuperado
    expr: SUM(valor_pago)
    comment: "Soma dos valores pagos nas baixas (parcela + multa + juros no dia do pagamento)."
    synonyms: [recebido, valor recebido, recuperação, arrecadação de atrasados]
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Pendências pagas
    comment: "Quantidade de pendências pagas (baixas) no período."
    expr: COUNT(1)
    synonyms: [baixas, quitações]
  - name: Multa e juros recebidos
    comment: "Multa e juros pagos nas baixas do período."
    expr: SUM(valor_multa + valor_juros)
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Dias até a baixa
    expr: AVG(dias_atraso_na_baixa)
    comment: "Média de dias de atraso no momento do pagamento."
    synonyms: [tempo médio de recuperação, prazo de recuperação]
  - name: Ticket médio recuperado
    comment: "Valor recuperado dividido pela quantidade de pendências pagas."
    expr: "MEASURE(`Valor recuperado`) / MEASURE(`Pendências pagas`)"
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  # --- comparação de períodos, acumulados e ranking (databricks-solutions/uc-semantics-patterns)
  - name: Valor recuperado no mês
    expr: SUM(valor_pago)
    window:
      - order: Mês da baixa
        range: current
        semiadditive: last
    comment: "Valor recuperado no último mês do período da consulta; base da variação mensal."
    synonyms: [recuperado no mês corrente]
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Valor recuperado no mês anterior
    expr: SUM(valor_pago)
    window:
      - order: Mês da baixa
        range: current
        semiadditive: last
        offset: -1 month
    comment: "Valor recuperado no mês anterior ao mês da baixa. Use agrupado por Mês da baixa."
    synonyms: [recuperado no mês passado]
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Variação mensal do valor recuperado
    expr: "(MEASURE(`Valor recuperado no mês`) - MEASURE(`Valor recuperado no mês anterior`)) / MEASURE(`Valor recuperado no mês anterior`)"
    comment: "Variação percentual do valor recuperado sobre o mês anterior (MoM). Use agrupado por Mês da baixa."
    synonyms: [MoM da recuperação, variação mês a mês do recuperado]
    format:
      type: percentage
      decimal_places:
        type: max
        places: 2
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
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
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
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Posição no ranking de recuperação
    expr: RANK() OVER (ORDER BY SUM(valor_pago) DESC)
    comment: "Posição (1 = maior) pelo valor recuperado no período filtrado. Não combine na mesma consulta com as medidas de mês anterior ou acumuladas."
    synonyms: [ranking de recuperação, ranking do recuperado]
$$;

CREATE OR REPLACE VIEW pos_venda.ontologia.mv_safra_recuperacao
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: pos_venda.ontologia.pendencia
comment: "Safras de entrada das pendências e quanto delas já foi pago. Compare safras de mesma idade (safras recentes tiveram menos tempo)."
dimensions:
  - name: Safra de entrada
    expr: safra_entrada
    comment: "Mês em que a pendência entrou (dia seguinte ao vencimento)."
    synonyms: [safra, mês de entrada, coorte]
  - name: Data de entrada
    comment: "Dia em que a pendência entrou na carteira (dia seguinte ao vencimento)."
    expr: data_entrada
  - name: Produto
    comment: "Nome do produto de seguro de vida (8 produtos, ex.: Vida Completo, Vida Essencial)."
    expr: produto_nome
  - name: Canal de venda
    comment: "Canal em que a apólice foi vendida: BANCASSURANCE, CORRETOR, DIGITAL ou TELEVENDAS."
    expr: canal_venda
  - name: Forma de pagamento
    comment: "Forma de pagamento da parcela: BOLETO, CARTAO_CREDITO, DEBITO_CONTA ou PIX_AUTOMATICO. NAO_CADASTRADA é dado que vazou da barreira de qualidade (dez/2026)."
    expr: forma_pagamento
  - name: Motivo da pendência
    comment: "Motivo pelo qual a parcela não foi paga no vencimento (10 motivos, agrupados em Grupo do motivo)."
    expr: motivo_pendencia
  - name: Periodicidade
    comment: "Periodicidade de pagamento da apólice: MENSAL, TRIMESTRAL, SEMESTRAL ou ANUAL."
    expr: periodicidade_pagamento
  - name: Status atual
    comment: "Status de cobrança atual da pendência, incluindo PAGA."
    expr: status_cobranca
measures:
  - name: Pendências que entraram
    comment: "Quantidade de pendências que entraram na safra."
    expr: COUNT(1)
    synonyms: [entradas, novas pendências]
  - name: Pendências pagas da safra
    comment: "Quantidade de pendências da safra que já foram pagas."
    expr: COUNT(1) FILTER (WHERE paga)
  - name: Taxa de recuperação
    expr: "MEASURE(`Pendências pagas da safra`) / MEASURE(`Pendências que entraram`)"
    comment: "Pendências pagas / pendências que entraram na safra."
    synonyms: [recovery rate, percentual recuperado, taxa de pagamento]
    format:
      type: percentage
      decimal_places:
        type: max
        places: 2
  - name: Valor das parcelas que entraram
    comment: "Soma do valor original das parcelas que entraram na safra."
    expr: SUM(valor_parcela)
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Valor recuperado da safra
    comment: "Soma do valor pago pelas pendências da safra."
    expr: SUM(valor_pago)
    format:
      type: currency
      currency_code: BRL
      decimal_places:
        type: exact
        places: 2
  - name: Dias até a baixa da safra
    comment: "Média de dias entre o vencimento e o pagamento das pendências pagas da safra."
    expr: AVG(dias_ate_baixa)
$$;

CREATE OR REPLACE VIEW pos_venda.ontologia.mv_qualidade_dados
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: pos_venda.gold.dq_qualidade_diaria
comment: "Qualidade diária dos dados que chegam do sistema de origem: recebidos, barrados e avisos."
dimensions:
  - name: Dia
    comment: "Dia de extração dos eventos vindos do sistema de origem."
    expr: dia
    synonyms: [data, dia de extração]
  - name: Semana
    comment: "Primeiro dia (segunda-feira) da semana de extração. Para um período (ex.: semanas de dezembro), filtre por Dia e agrupe por Semana: a semana de 30/11/2026 contém de 1º a 6/12."
    expr: "CAST(DATE_TRUNC('WEEK', dia) AS DATE)"
  - name: Mês
    comment: "Primeiro dia do mês de extração."
    expr: "CAST(DATE_TRUNC('MONTH', dia) AS DATE)"
measures:
  - name: Eventos recebidos
    comment: "Eventos de cobrança recebidos no bronze no período."
    expr: SUM(eventos_recebidos)
  - name: Eventos aptos
    comment: "Eventos que passaram na barreira de qualidade e entraram na silver."
    expr: SUM(eventos_aptos)
  - name: Eventos barrados
    comment: "Eventos reprovados por regra de erro e mandados para a quarentena; não entram nos números."
    expr: SUM(eventos_barrados)
    synonyms: [quarentena, rejeitados, não aptos]
  - name: Taxa de barrados
    comment: "Eventos barrados divididos pelos eventos recebidos."
    expr: "MEASURE(`Eventos barrados`) / MEASURE(`Eventos recebidos`)"
    synonyms: [percentual barrado, taxa de rejeição]
    format:
      type: percentage
      decimal_places:
        type: max
        places: 2
  - name: Eventos duplicados
    comment: "Eventos repetidos (mesma pendência, dia e tipo) recebidos no período."
    expr: SUM(eventos_duplicados)
  - name: Taxa de duplicatas
    comment: "Eventos duplicados divididos pelos eventos recebidos."
    expr: "MEASURE(`Eventos duplicados`) / MEASURE(`Eventos recebidos`)"
    format:
      type: percentage
      decimal_places:
        type: max
        places: 2
  - name: E-mail ausente
    comment: "Eventos aptos com cliente sem e-mail (regra de aviso)."
    expr: SUM(email_ausente)
  - name: Taxa de e-mail ausente
    comment: "E-mail ausente dividido pelos eventos aptos."
    expr: "MEASURE(`E-mail ausente`) / MEASURE(`Eventos aptos`)"
    format:
      type: percentage
      decimal_places:
        type: max
        places: 2
  - name: CPF inválido
    comment: "Quantidade de eventos aptos cujo CPF não passa na validação (regra de aviso). É uma contagem: não contém CPF."
    expr: SUM(cpf_invalido)
  - name: Taxa de CPF inválido
    comment: "CPF inválido dividido pelos eventos aptos."
    expr: "MEASURE(`CPF inválido`) / MEASURE(`Eventos aptos`)"
    format:
      type: percentage
      decimal_places:
        type: max
        places: 2
  - name: CEP malformado
    comment: "Eventos aptos com CEP sem 8 dígitos (regra de aviso)."
    expr: SUM(cep_malformado)
  - name: Forma de pagamento não cadastrada
    comment: "Eventos aptos com forma de pagamento fora do catálogo que vazaram para a silver (incidente de dez/2026)."
    expr: SUM(forma_pagamento_nao_cadastrada)
    synonyms: [vazamento, forma inválida]
$$;
