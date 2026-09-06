import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "config/qadam_refactor_boundaries.json").read_text())


def test_retained_adapters_have_no_second_implementation():
    assert REGISTRY["review_owner"] and REGISTRY["next_review"]
    for adapter, destination in REGISTRY["adapters"].items():
        path = ROOT / "orchestrator" / (adapter + ".py")
        source = path.read_text()
        tree = ast.parse(source)
        assert not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                       for node in ast.walk(tree)), adapter
        assert "sys.modules[__name__]" in source
        assert "orchestrator." + destination in source
        assert (ROOT / "orchestrator" / (destination.replace(".", "/") + ".py")).exists()


def test_contracts_cannot_import_runtime_or_broker_implementations():
    prefixes = REGISTRY["blocked_import_prefixes_in_contracts"]
    for path in (ROOT / "orchestrator/contracts").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = ([node.module or ""] if isinstance(node, ast.ImportFrom)
                     else [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
            assert not any(name == prefix or name.startswith(prefix + ".")
                           for name in names for prefix in prefixes), path
