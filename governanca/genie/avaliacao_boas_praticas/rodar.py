"""Uso: rodar.py <repo> <base> <endpoint> <espaco>:<bench 0|1> [...]"""
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])          # pasta do repositório genie-best-practices-agent
from genie_validator.graph import run_validator
import genie_validator.nodes as N
_orig = N._make_llm
def _limitado(endpoint, **kw):          # endpoints do Free Edition aceitam no máximo 8.192 tokens de saída
    if kw.get("max_tokens", 0) > 8192:
        kw["max_tokens"] = 8192
    return _orig(endpoint, **kw)
N._make_llm = _limitado
base, endpoint = Path(sys.argv[2]), sys.argv[3]
IDS = {"analista": "01f1e4772cf610a8baf0c236595c284b", "diretor": "01f1e477314b1903a4212843cf0dabf1"}
(base / "reports").mkdir(exist_ok=True)
for item in sys.argv[4:]:
    nome, bench = item.split(":")
    t = time.time()
    try:
        md = run_validator(space_config_path=str(base / "space_configs" / f"{nome}_space_config.json"),
                           data_context_path=str(base / "space_configs" / f"{nome}_data_context.json"),
                           space_id=IDS[nome], space_name=nome, llm_endpoint=endpoint,
                           skip_fetch_best_practices=True, max_view_def_tokens=6000,
                           run_benchmarks=bench == "1", max_benchmark_questions=None)
        (base / "reports" / f"{nome}_evaluation.md").write_text(md)
        print(f"== {nome} OK em {time.time()-t:.0f}s", flush=True)
    except Exception as e:
        print(f"== {nome} FALHOU em {time.time()-t:.0f}s: {str(e)[:300]}", flush=True)
