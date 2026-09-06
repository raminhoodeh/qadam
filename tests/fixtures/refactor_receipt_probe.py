"""Offline subprocess fixture; never imports a broker, state store or provider."""

import os
import sys

from orchestrator.runtime.command import report_work_result

if "--missing-receipt" in sys.argv:
    os._exit(0)
report_work_result({"status": "passed", "material_change_detected": True})
print("material_change_detected=False\n" + "diagnostic\n" * 1000)
