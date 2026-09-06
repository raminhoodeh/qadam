"""Compatibility import for orchestrator.storage.control_plane; one implementation only."""

from importlib import import_module
import sys

if __name__ == "__main__":
    import runpy

    runpy.run_module("orchestrator.storage.control_plane", run_name="__main__")
else:
    sys.modules[__name__] = import_module("orchestrator.storage.control_plane")
