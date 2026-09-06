"""Offline subprocess fixture; never imports a broker, state store or provider."""

import os
import sys

from orchestrator.runtime.command import report_work_result

if "--missing-receipt" in sys.argv:
    os._exit(0)
if "--missing-work" in sys.argv:
    raise SystemExit(0)
if "--sibling-import" in sys.argv:
    from refactor_sibling_helper import VALUE
    assert VALUE == "sibling-import-ok"
report_work_result({"status": "passed", "material_change_detected": True})
print("material_change_detected=False\n" + "diagnostic\n" * 1000)
