"""Compatibility import for orchestrator.learning.forward_evaluation; one implementation only."""

from importlib import import_module
import sys

if __name__ == "__main__":
    import runpy

    runpy.run_module("orchestrator.learning.forward_evaluation", run_name="__main__")
else:
    sys.modules[__name__] = import_module("orchestrator.learning.forward_evaluation")
