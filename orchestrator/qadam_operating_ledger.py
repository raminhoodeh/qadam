"""Compatibility import for orchestrator.execution.ledger; one implementation only."""

from importlib import import_module
import sys

if __name__ == "__main__":
    import runpy

    runpy.run_module("orchestrator.execution.ledger", run_name="__main__")
else:
    sys.modules[__name__] = import_module("orchestrator.execution.ledger")
