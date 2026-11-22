"""Injeta catalogo.json no template e gera catalogo_databricks_solutions.html."""
import json
from pathlib import Path
AQUI = Path(__file__).parent
dados = json.loads((AQUI / "catalogo.json").read_text())
js = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = (AQUI / "pagina.template.html").read_text().replace("/*DADOS*/", js)
(AQUI / "catalogo_databricks_solutions.html").write_text(html)
print(len(html), "bytes")
