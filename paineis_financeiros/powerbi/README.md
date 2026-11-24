# Painéis financeiros do Pós-venda · opção Power BI

Equivalente em Power BI dos painéis AI/BI `pos_venda · KPIs financeiros` (Diretoria e Analista/time de negócio), para
avaliar as duas ferramentas lado a lado. São as mesmas páginas por fato (carteira em aberto, recuperação, safras e
qualidade dos dados), os mesmos títulos e os **mesmos números**.

```
pos_venda.ontologia.mv_*  (metric views: a regra de negócio, num lugar só)
   ├── painéis AI/BI do Databricks  → consultam as metric views ao vivo
   └── pos_venda.bi.*  (visões agregadas a partir das metric views)
          └── Power BI (importação) → modelo pos_venda + 2 relatórios
```

## O que tem aqui

| Arquivo | Para quê |
|---|---|
| `gerar_powerbi.py` | Gera tudo: visões `pos_venda.bi`, modelo semântico (TMDL), relatórios (PBIR) e valores de referência |
| `projeto/pos_venda_negocio.pbip` | Relatório do **time de negócio**: Carteira em aberto, Recuperação, Safras, Qualidade dos dados (+ filtros de produto, canal e forma no painel de filtros) |
| `projeto/pos_venda_diretoria.pbip` | Relatório da **diretoria**: Visão executiva + uma página por fato |
| `projeto/pos_venda.SemanticModel/` | Modelo compartilhado pelos dois relatórios: 8 tabelas, 47 medidas DAX, 12 relações |
| `VALORES_DE_REFERENCIA.md` | O que cada cartão deve mostrar (= painel do Databricks), para conferir na avaliação |

**Modelo:** fatos `Carteira diária` (942 mil linhas), `Recuperação` (62 mil), `Safras` (1,1 mil) e `Qualidade` (221);
dimensões `Calendário`, `Produto`, `Canal de venda` e `Forma de pagamento`, compartilhadas pelos fatos (um filtro de produto
vale para carteira, recuperação e safras ao mesmo tempo). O saldo é **semiaditivo**: as medidas pegam o último dia com foto
no contexto (`[Data da foto]`), como a metric view; nunca somam dias.

## Abrir e atualizar

1. **Power BI Desktop no Windows** (o Desktop não existe para Mac), versão de 2025 ou mais nova. O projeto usa o formato
   PBIR (relatório em pastas). Se o Desktop for antigo, ative em *Opções > Recursos em versão prévia* a opção do formato PBIR.
2. Abra `projeto/pos_venda_negocio.pbip` (ou o da diretoria). Os dois usam o mesmo modelo.
3. **Atualizar**. Na primeira vez o Desktop pede a credencial do conector **Databricks**: use um *token de acesso pessoal*
   (Databricks: *Configurações > Desenvolvedor > Tokens de acesso*) ou OAuth, se oferecido. A carga leva por volta de
   1 a 2 minutos (o warehouse sem servidor pode precisar acordar).
4. Confira os cartões com `VALORES_DE_REFERENCIA.md` (sem filtro, devem ser idênticos).

O servidor e o caminho do warehouse ficam nos parâmetros `Host` e `HttpPath` (*Transformar dados > Gerenciar parâmetros*).
Workspace no Azure: troque `DatabricksMultiCloud.Catalogs` por `Databricks.Catalogs` nas consultas.

**Sem Windows (Mac):** publique pelo Fabric: um workspace com capacidade Fabric (ou avaliação) ligado ao Git (GitHub ou
Azure DevOps) importa a pasta `projeto/` como modelo e relatórios; depois informe a credencial nas configurações do modelo
semântico e atualize, tudo pelo navegador.

**Compartilhar:** publique no serviço do Power BI (licença Pro, PPU ou capacidade Fabric) e agende a atualização; o
Databricks é nuvem, não precisa de gateway.

## Gerar de novo

```bash
cd pos_venda/paineis_financeiros/powerbi
../../regras/.venv/bin/python gerar_powerbi.py visoes       # cria pos_venda.bi; só recria a visão cuja definição mudou
python3 ../../governanca/aplicar_semantica.py --so-tags      # só se alguma visão foi recriada (recriar apaga as tags)
python3 gerar_powerbi.py                                     # projeto/ + conferência contra os esquemas oficiais
../../regras/.venv/bin/python gerar_powerbi.py referencia   # paridade Databricks x lógica DAX; grava VALORES_DE_REFERENCIA.md
python3 gerar_powerbi.py bim                                 # model.bim (TMSL) só para a auditoria do pba; ver auditoria/README.md
```

A conferência valida os 102 arquivos JSON contra os esquemas oficiais da Microsoft (relatório 3.0.0, página 2.0.0,
visual 2.2.0), checa o layout de cada página, se cada medida citada no DAX existe e se as colunas do modelo existem nas
visões. Os esquemas são baixados para `.esquemas/` na primeira vez.

## O que foi e o que não foi verificado (22/11/2026)

| Verificação | Resultado |
|---|---|
| Esquemas oficiais (PBIP, PBIR) | 102 arquivos válidos; o teste negativo (campo faltando, propriedade inventada, medida inexistente) é detectado |
| Visões `pos_venda.bi` | criadas; 0 chave de fato sem dimensão (produto, canal, forma, calendário) |
| Paridade na reconferência (24/11) | **20/21** na foto de 09/01/2027. "Crescimento da carteira no mês": painel R$ 1.403.002,55; lógica DAX R$ 1.405.736,27. O painel soma o início do mês de cada grupo produto × canal, e 17 grupos nasceram depois de 01/01; o total certo é o da lógica DAX (L86) |
| Paridade dos números | **21/21** indicadores iguais ao painel do Databricks (foto de 25/12/2026), calculando em SQL a mesma lógica das medidas DAX |
| Auditoria Power BI on Databricks (`pba`) | modelo **80/100** (2 achados informativos, 1 falso positivo); lado Databricks **75/100** (limites do warehouse do Free Edition). As regras que dependem de visuais (RD-001, RD-010) e as de preparo de dados não foram avaliadas de fato: ver [auditoria/README.md](auditoria/README.md) |
| Abrir no Power BI Desktop | **não feito aqui** (não há Windows nesta máquina): a sintaxe TMDL e o DAX só são executados de verdade no Desktop ou no Fabric |

Se o Desktop apontar erro ao abrir, a mensagem diz o arquivo e a linha; corrija em `gerar_powerbi.py` (não no arquivo
gerado) e gere de novo.

## Para a avaliação: Databricks AI/BI x Power BI

| Critério | Databricks AI/BI | Power BI |
|---|---|---|
| Onde fica a regra | Metric views no Unity Catalog, consultadas ao vivo | As mesmas metric views (via `pos_venda.bi`) + 47 medidas DAX que repetem a lógica de saldo semiaditivo e comparação de períodos |
| Dados | Ao vivo no warehouse | Importação: atualização manual ou agendada |
| Quem pode ver | Usuários do workspace; o painel publicado usa a credencial do autor | Licença Pro/PPU ou capacidade Fabric para compartilhar |
| Governança | Permissões, linhagem e tags do Unity Catalog até o painel | Unity Catalog até `pos_venda.bi`; dali em diante, permissões do Power BI |
| Perguntas em linguagem natural | Genie embutido (espaços analista e diretoria) | Copilot (exige capacidade Fabric paga) |
| Versionamento | JSON gerado por script + bundle (`databricks bundle deploy`) | PBIP em texto (TMDL + PBIR) no Git |
| Edição no Mac | Navegador | Desktop só no Windows; no Mac, pelo Fabric |
