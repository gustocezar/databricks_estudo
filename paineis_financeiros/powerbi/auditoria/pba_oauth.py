"""Roda o powerbi-analyzer (pba) com um perfil OAuth do Databricks CLI.

O pba abre a conexão SQL com `cfg.token`, que só existe em perfis com token fixo (PAT). Com OAuth (login pelo
navegador, token no chaveiro do sistema) esse campo fica vazio e a conexão falha. Este invólucro troca só a abertura
da conexão: pede ao SDK o cabeçalho de autenticação do perfil e passa o token OAuth ao conector SQL. O resto do pba
roda sem alteração.

Uso (mesmos argumentos do pba):
    python pba_oauth.py databricks --profile dbx-workshop --warehouse-id <id> --catalog pos_venda.gold --out saida.md
"""
from databricks import sql as dbsql
from powerbi_analyzer import databricks_clients
from powerbi_analyzer.cli import app


def _conexao_oauth(self):
    if self._conn is None:
        cfg = self._wc.config
        token = cfg.authenticate()["Authorization"].split(" ", 1)[1]
        self._conn = dbsql.connect(server_hostname=cfg.host.replace("https://", "").rstrip("/"),
                                   http_path=self._http_path, access_token=token)
    return self._conn


databricks_clients.SdkSqlExecutor._connection = _conexao_oauth

if __name__ == "__main__":
    app()
