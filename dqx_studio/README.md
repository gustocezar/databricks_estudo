# DQX Studio no workspace Free Edition

Instalação do **DQX Studio** (Databricks Labs, versão `studio-v0.1.2`, DQX 0.17.x) como Databricks App, pelo bundle oficial
(`databrickslabs/dqx`, pasta `app/`, target `release` com o artefato pronto, sem build local).

- App: <https://dqx-studio-7474645927052439.aws.databricksapps.com>
- Perfil do CLI: `dbx-workshop`

## O que foi criado

| Recurso | Nome / onde |
|---|---|
| App | `dqx-studio` |
| Job (roda no serverless) | `dqx-studio-task-runner`, executa como o service principal `dqx-task-runner-sp` |
| Service principal | `dqx-task-runner-sp` (application id `5f3d5f9d-53f1-463f-acfe-f41dc872bf21`) |
| Projeto Lakebase | `dqx-studio-db` (estado do app: regras, permissões, agendas) |
| Schemas em `main` | `dqx_studio`, `dqx_studio_tmp`, `dqx_studio_genie`, `dqx_studio_demo` + volume `dqx_studio.wheels` |
| Tabelas Delta | `main.dqx_studio.dq_*` (execuções, métricas, quarentena, perfis), criadas pelas migrações do app |
| Grants em `main` | app: `USE CATALOG` + `CREATE SCHEMA`; service principal do job: `USE CATALOG`; `account users`: `USE CATALOG` (modo amplo) |
| Papel no service principal | seu usuário com `servicePrincipal.manager` e `servicePrincipal.user` (o job exige o segundo) |

## Diferença em relação ao bundle oficial

O bundle oficial **sempre cria um SQL warehouse próprio**, mas a Free Edition permite 1 só. A instalação usa o
`Serverless Starter Warehouse` que já existia (id `5f010b8396e591fb`). A mudança está em `warehouse-existente.patch`
(variável `sql_warehouse_id`; o recurso `sql_warehouses` foi removido do bundle). O app ganha `CAN_MANAGE` nesse warehouse pela
própria ligação de recurso do app, como na instalação pelo Marketplace.

## Operação

```bash
# o app para sozinho 24 h depois de iniciado na Free Edition; para religar:
databricks apps start dqx-studio --profile dbx-workshop

# estado do app e log
databricks apps get dqx-studio --profile dbx-workshop
databricks apps logs dqx-studio --tail-lines 100 --profile dbx-workshop
```

O primeiro acesso no navegador pede para autorizar o app a agir em seu nome (escopos de SQL, catálogo e IA).
Seu usuário é administrador (`admins`) e já tem o papel `ADMIN` dentro do Studio; os outros papéis (Author, Approver,
Viewer) são atribuídos em **Admin Settings → Entitlements**.

## Reinstalar ou atualizar (a partir do zero)

```bash
git clone --depth 1 --branch studio-v0.1.2 https://github.com/databrickslabs/dqx.git
cd dqx && patch -p1 < /caminho/para/warehouse-existente.patch
cd app
databricks bundle deploy -t release --profile dbx-workshop \
  --var catalog_name=main \
  --var dqx_service_principal_application_id=5f3d5f9d-53f1-463f-acfe-f41dc872bf21 \
  --var studio_user_group=users --var "studio_uc_principal=account users"
databricks bundle run dqx-studio -t release --profile dbx-workshop <mesmas --var>
```

Depois do primeiro deploy, se o app pedir, rode **Verify again** na tela de setup do Studio (equivale a `POST /api/v1/setup/reconcile`).

## Limites da Free Edition que importam

Até 3 apps por workspace (para caber o Studio foi apagado o app `dbx-community-rj`; o código dele continua em
`/Workspace/Users/<seu-usuario>/.bundle/dbx-community-rj/default/files`), 1 SQL warehouse 2X-Small, 1 projeto Lakebase,
só computação serverless.

## Remover

Veja `app/DEPLOYMENT.md` do repositório (seção "Removing a previous installation"). Os schemas, o volume e o projeto Lakebase têm
`prevent_destroy`, então `databricks bundle destroy` não os apaga sozinho.
