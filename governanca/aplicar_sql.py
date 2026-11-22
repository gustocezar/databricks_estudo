#!/usr/bin/env python3
"""Executa uma lista de comandos SQL (arquivo .json com lista de strings) no warehouse do projeto.

  python3 aplicar_sql.py ontologia_sql.json
"""
import json
import pathlib
import sys

import sql_util

if __name__ == "__main__":
    arq = pathlib.Path(sys.argv[1])
    comandos = json.loads(arq.read_text(encoding="utf-8"))
    falhas = sql_util.executar_lista(comandos)
    print(f"RESULTADO: {len(comandos) - falhas}/{len(comandos)} comandos ok")
    sys.exit(1 if falhas else 0)
