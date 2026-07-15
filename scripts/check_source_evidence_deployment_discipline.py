#!/usr/bin/env python3
"""Deployment-discipline gate for Qadam source/evidence runtime work.

This is a pre-deploy contract check. It does not call Vercel, providers,
brokers, LLMs, Q-CTRL, IBM, or any live source. It proves that the local
source/evidence acceptance gate is wired into production preflight and that the
public cockpit mirror/receipt remain public-safe, read-only, and authority-free.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data/runtime/source_evidence_deployment_discipline.json"
ACCEPTANCE_REPORT_PATH = ROOT / "data/runtime/source_evidence_acceptance.json"
COCKPIT_STATUS_PATH = ROOT / "landing-page-repo/status/cockpit-status.json"
COCKPIT_SIGNATURE_PATH = ROOT / "landing-page-repo/status/cockpit-status.signature.json"
DEPLOY_RECEIPT_PATH = ROOT / "data/runtime/dashboard-deployment-receipt.json"
DEPLOY_SCRIPT_PATH = ROOT / "landing-page-repo/scripts/deploy-vercel-production.sh"
PREFLIGHT_PATH = ROOT / "scripts/preflight_dashboard_deployment.sh"
INVENTORY_DOC_PATH = ROOT / "docs/api-source-inventory.md"
DISCIPLINE_DOC_PATH = ROOT / "docs/qadam-source-evidence-deployment-discipline-2026-06-14.md"

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bPVZ[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bQzJJC[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bVERCEL_TOKEN\s*=\s*[A-Za-z0-9_.-]{10,}\b"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text(path: Path, errors: list[str], label: str) -> str:
    if not path.exists():
        errors.append(f"{label}_missing:{path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    text = _read_text(path, errors, label)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{label}_invalid_json:{exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{label}_not_object")
        return {}
    return payload


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _expect_equal(
    errors: list[str],
    payload: dict[str, Any],
    path: tuple[str, ...],
    expected: Any,
    label: str,
) -> None:
    actual = _nested(payload, *path)
    if actual != expected:
        dotted = ".".join(path)
        errors.append(f"{label}_{dotted}_expected_{expected!r}_actual_{actual!r}")


def _expect_false(errors: list[str], payload: dict[str, Any], path: tuple[str, ...], label: str) -> None:
    _expect_equal(errors, payload, path, False, label)


def _expect_zero(errors: list[str], payload: dict[str, Any], path: tuple[str, ...], label: str) -> None:
    _expect_equal(errors, payload, path, 0, label)


def _includes(text: str, needles: tuple[str, ...], errors: list[str], label: str) -> None:
    for needle in needles:
        if needle not in text:
            errors.append(f"{label}_missing:{needle}")


def _in_order(text: str, needles: tuple[str, ...], errors: list[str], label: str) -> None:
    cursor = -1
    for needle in needles:
        index = text.find(needle)
        if index < 0:
            errors.append(f"{label}_missing_order_item:{needle}")
            continue
        if index <= cursor:
            errors.append(f"{label}_wrong_order:{needle}")
        cursor = index


def _assert_parseable_time(value: Any, errors: list[str], label: str) -> None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label}_missing")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label}_invalid:{value}")


def _assert_no_secret_material(text: str, errors: list[str], label: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            errors.append(f"{label}_secret_like_material:{pattern.pattern}")


def _check_acceptance_report(report: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    _expect_equal(errors, report, ("status",), "ok", "acceptance_report")
    _expect_equal(errors, report, ("dashboard_simplification_scope",), "excluded_by_request", "acceptance_report")
    _expect_zero(errors, report, ("failed_check_count",), "acceptance_report")
    _expect_zero(errors, report, ("cross_check_error_count",), "acceptance_report")
    _assert_parseable_time(report.get("generated_at"), errors, "acceptance_report_generated_at")

    check_count = report.get("check_count")
    passed_count = report.get("passed_check_count")
    if check_count != passed_count:
        errors.append(f"acceptance_report_passed_count_mismatch:{passed_count}/{check_count}")

    return {
        "status": report.get("status"),
        "generated_at": report.get("generated_at"),
        "check_count": check_count,
        "passed_check_count": passed_count,
        "failed_check_count": report.get("failed_check_count"),
        "cross_check_error_count": report.get("cross_check_error_count"),
    }


def _check_preflight(preflight: str, errors: list[str]) -> dict[str, Any]:
    _includes(
        preflight,
        (
            "\"$PYTHON_BIN\" scripts/check_source_evidence_acceptance.py",
            "\"$PYTHON_BIN\" scripts/check_source_evidence_deployment_discipline.py",
            "\"$PYTHON_BIN\" scripts/check_evidence_packet_runtime.py",
            "\"$PYTHON_BIN\" scripts/check_cockpit_status.py",
            "node scripts/check_dashboard_d11o_deployment_discipline.js",
        ),
        errors,
        "preflight",
    )
    _in_order(
        preflight,
        (
            "scripts/check_evidence_packet_runtime.py",
            "scripts/check_source_evidence_acceptance.py",
            "scripts/check_cockpit_status.py",
            "scripts/check_source_evidence_deployment_discipline.py",
            "node scripts/check_dashboard_acceptance.js",
        ),
        errors,
        "preflight_source_evidence_gate_order",
    )
    return {"wired": "scripts/check_source_evidence_acceptance.py" in preflight}


def _check_deploy_script(deploy_script: str, errors: list[str]) -> dict[str, Any]:
    _includes(
        deploy_script,
        (
            "bash \"${ROOT_DIR}/scripts/preflight_dashboard_deployment.sh\"",
            "PREFLIGHT_REFERENCE_ROOT=\"${QADAM_REFERENCE_ROOT:-${CREDENTIAL_ROOT}}\"",
            "QADAM_REFERENCE_ROOT=\"${PREFLIGHT_REFERENCE_ROOT}\"",
            "QADAM_SKIP_DEPLOY_PREFLIGHT",
            "\"qadam.trade\"",
            "\"www.qadam.trade\"",
            "dashboard-deployment-receipt.json",
            "preflight: \"passed\"",
            "Production preflight cannot be skipped for a dashboard integration release.",
            "Dashboard repository is dirty; production deployment is blocked.",
            "verify-dashboard-production-release.js",
            "Contains no Vercel token, session cookie, broker credential, or dashboard secret.",
            "send_codebase_upgrade_telegram_notification.py",
            "--source \"production_deploy\"",
        ),
        errors,
        "deploy_script",
    )
    _in_order(
        deploy_script,
        (
            "bash \"${ROOT_DIR}/scripts/preflight_dashboard_deployment.sh\"",
            "\"${vercel_cmd[@]}\" deploy",
            "\"${vercel_cmd[@]}\" alias set",
            "dashboard-deployment-receipt.json",
            "Production deployment:",
        ),
        errors,
        "deploy_script_order",
    )
    return {"preflight_required": "preflight_dashboard_deployment.sh" in deploy_script}


def _check_cockpit_status(status: dict[str, Any], signature: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    _assert_parseable_time(status.get("generated_at"), errors, "cockpit_status_generated_at")

    _expect_equal(errors, status, ("cognition", "evidence_packet_runtime", "status"), "ok", "cockpit_status")
    _expect_equal(
        errors,
        status,
        ("cognition", "evidence_packet_runtime", "replay_status"),
        "local_jsonl_replay_ready",
        "cockpit_status",
    )
    _expect_zero(errors, status, ("cognition", "evidence_packet_runtime", "authority_leak_count"), "cockpit_status")
    _expect_zero(errors, status, ("cognition", "evidence_packet_runtime", "raw_ref_leak_count"), "cockpit_status")
    _expect_false(errors, status, ("cognition", "evidence_packet_runtime", "broker_write_allowed"), "cockpit_status")
    _expect_false(errors, status, ("cognition", "evidence_packet_runtime", "paper_order_allowed"), "cockpit_status")
    _expect_false(errors, status, ("cognition", "evidence_packet_runtime", "live_capital_enabled"), "cockpit_status")

    _expect_equal(errors, status, ("tradingview_mcp", "status"), "connected", "cockpit_status")
    _expect_equal(errors, status, ("tradingview_mcp", "connected"), True, "cockpit_status")
    _expect_false(errors, status, ("tradingview_mcp", "execution_allowed"), "cockpit_status")
    _expect_false(errors, status, ("tradingview_mcp", "paper_order_allowed"), "cockpit_status")
    _expect_false(errors, status, ("tradingview_mcp", "broker_write_allowed"), "cockpit_status")

    _expect_equal(errors, status, ("bookmap_local_bridge", "status"), "sample_ready", "cockpit_status")
    _expect_false(errors, status, ("bookmap_local_bridge", "execution_allowed"), "cockpit_status")
    _expect_false(errors, status, ("bookmap_local_bridge", "paper_order_allowed"), "cockpit_status")
    _expect_false(errors, status, ("bookmap_local_bridge", "broker_write_allowed"), "cockpit_status")
    _expect_false(errors, status, ("bookmap_local_bridge", "bookmap_order_injection_allowed"), "cockpit_status")
    _expect_false(errors, status, ("bookmap_local_bridge", "bookmap_trading_mode_allowed"), "cockpit_status")

    _expect_zero(
        errors,
        status,
        ("paperops_source_gap_visibility", "trade_blocking_source_gap_count"),
        "cockpit_status",
    )
    _expect_zero(errors, status, ("paperops_source_gap_visibility", "silent_blocker_count"), "cockpit_status")
    _expect_zero(errors, status, ("paperops_source_gap_visibility", "broker_post_called_count"), "cockpit_status")
    _expect_zero(errors, status, ("paperops_source_gap_visibility", "broker_write_allowed_count"), "cockpit_status")
    _expect_zero(errors, status, ("paperops_source_gap_visibility", "live_endpoint_called_count"), "cockpit_status")
    _expect_false(errors, status, ("paperops_source_gap_visibility", "live_capital_enabled"), "cockpit_status")

    _expect_equal(errors, signature, ("status",), "digest_only", "cockpit_signature")
    _expect_equal(errors, signature, ("read_only",), True, "cockpit_signature")
    _expect_false(errors, signature, ("broker_write_route",), "cockpit_signature")
    _expect_equal(errors, signature, ("browser_authority",), "read_only", "cockpit_signature")
    _expect_equal(
        errors,
        signature,
        ("payload_generated_at",),
        status.get("generated_at"),
        "cockpit_signature",
    )

    return {
        "status_generated_at": status.get("generated_at"),
        "signature_status": signature.get("status"),
        "tradingview_mcp_status": _nested(status, "tradingview_mcp", "status"),
        "bookmap_local_bridge_status": _nested(status, "bookmap_local_bridge", "status"),
        "trade_blocking_source_gap_count": _nested(
            status, "paperops_source_gap_visibility", "trade_blocking_source_gap_count"
        ),
        "silent_blocker_count": _nested(status, "paperops_source_gap_visibility", "silent_blocker_count"),
    }


def _check_receipt(receipt: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    if not receipt:
        return {"present": False, "status": "not_yet_written"}

    previous_preflight = receipt.get("preflight")
    if previous_preflight not in {"passed", "skipped"}:
        errors.append(f"deployment_receipt_preflight_invalid:{previous_preflight!r}")
    _expect_equal(
        errors,
        receipt,
        ("boundary",),
        "Receipt only. Contains no Vercel token, session cookie, broker credential, or dashboard secret.",
        "deployment_receipt",
    )
    _assert_parseable_time(receipt.get("deployed_at"), errors, "deployment_receipt_deployed_at")

    deployment_url = receipt.get("deployment_url")
    if not isinstance(deployment_url, str) or not deployment_url.startswith("https://") or not deployment_url.endswith(
        ".vercel.app"
    ):
        errors.append(f"deployment_receipt_url_invalid:{deployment_url!r}")

    aliases = receipt.get("aliases")
    if aliases != ["qadam.trade", "www.qadam.trade"]:
        errors.append(f"deployment_receipt_aliases_invalid:{aliases!r}")

    return {
        "present": True,
        "status": "passed" if previous_preflight == "passed" else "historical_preflight_skipped",
        "preflight": previous_preflight,
        "deployment_url": deployment_url,
        "aliases": aliases,
        "deployed_at": receipt.get("deployed_at"),
    }


def _check_docs(inventory_doc: str, discipline_doc: str, errors: list[str]) -> dict[str, Any]:
    _includes(
        inventory_doc,
        (
            "## Deployment Discipline",
            "`scripts/check_source_evidence_deployment_discipline.py`",
            "`scripts/preflight_dashboard_deployment.sh`",
            "source/evidence/runtime acceptance",
        ),
        errors,
        "api_source_inventory",
    )
    _includes(
        discipline_doc,
        (
            "# Qadam Source/Evidence Deployment Discipline",
            "No dashboard simplification is included in this stage.",
            "No broker write authority",
            "No live capital",
        ),
        errors,
        "deployment_discipline_doc",
    )
    return {"inventory_doc_updated": True, "discipline_doc_exists": bool(discipline_doc)}


def _write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = REPORT_PATH.with_name(f".{REPORT_PATH.name}.tmp")
    temp_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(REPORT_PATH)


def main() -> int:
    errors: list[str] = []

    acceptance_report = _read_json(ACCEPTANCE_REPORT_PATH, errors, "acceptance_report")
    cockpit_status = _read_json(COCKPIT_STATUS_PATH, errors, "cockpit_status")
    cockpit_signature = _read_json(COCKPIT_SIGNATURE_PATH, errors, "cockpit_signature")
    deployment_receipt = _read_json(DEPLOY_RECEIPT_PATH, errors, "deployment_receipt") if DEPLOY_RECEIPT_PATH.exists() else {}
    deploy_script = _read_text(DEPLOY_SCRIPT_PATH, errors, "deploy_script")
    preflight = _read_text(PREFLIGHT_PATH, errors, "preflight")
    inventory_doc = _read_text(INVENTORY_DOC_PATH, errors, "api_source_inventory")
    discipline_doc = _read_text(DISCIPLINE_DOC_PATH, errors, "deployment_discipline_doc")

    public_texts = {
        "cockpit_status": COCKPIT_STATUS_PATH.read_text(encoding="utf-8") if COCKPIT_STATUS_PATH.exists() else "",
        "cockpit_signature": COCKPIT_SIGNATURE_PATH.read_text(encoding="utf-8") if COCKPIT_SIGNATURE_PATH.exists() else "",
        "deployment_receipt": DEPLOY_RECEIPT_PATH.read_text(encoding="utf-8") if DEPLOY_RECEIPT_PATH.exists() else "",
        "deploy_script": deploy_script,
        "preflight": preflight,
        "api_source_inventory": inventory_doc,
        "deployment_discipline_doc": discipline_doc,
    }
    for label, text in public_texts.items():
        _assert_no_secret_material(text, errors, label)

    acceptance_summary = _check_acceptance_report(acceptance_report, errors)
    preflight_summary = _check_preflight(preflight, errors)
    deploy_summary = _check_deploy_script(deploy_script, errors)
    cockpit_summary = _check_cockpit_status(cockpit_status, cockpit_signature, errors)
    receipt_summary = _check_receipt(deployment_receipt, errors)
    docs_summary = _check_docs(inventory_doc, discipline_doc, errors)

    report = {
        "schema_version": 1,
        "status": "ok" if not errors else "error",
        "generated_at": _now(),
        "stage": "source_evidence_deployment_discipline",
        "dashboard_simplification_scope": "excluded_by_request",
        "acceptance_report": acceptance_summary,
        "preflight": preflight_summary,
        "deploy_script": deploy_summary,
        "cockpit_status": cockpit_summary,
        "deployment_receipt": receipt_summary,
        "docs": docs_summary,
        "error_count": len(errors),
        "errors": errors,
        "boundary": (
            "Deployment discipline covers source/evidence/runtime production readiness only. "
            "It performs no dashboard simplification, no provider calls, no quantum jobs, "
            "no broker writes, no paper orders, no live endpoints, and no live capital."
        ),
    }
    _write_report(report)

    print("source_evidence_deployment_discipline_status=" + report["status"])
    print("source_evidence_deployment_acceptance_report_status=" + str(acceptance_summary.get("status")))
    print("source_evidence_deployment_preflight_wired=" + str(bool(preflight_summary.get("wired"))))
    print(
        "source_evidence_deployment_live_status_ready="
        + str(not any(error.startswith("cockpit_status") or error.startswith("cockpit_signature") for error in errors))
    )
    print("source_evidence_deployment_receipt_ready=" + str(bool(receipt_summary.get("present"))))
    print("source_evidence_deployment_dashboard_simplification_skipped=True")
    print(f"source_evidence_deployment_discipline_report={REPORT_PATH.relative_to(ROOT)}")
    print(
        "source_evidence_deployment_discipline_boundary="
        "source/evidence/runtime deployment discipline only; no dashboard simplification, trading authority, broker writes, or live capital"
    )
    for error in errors:
        print(f"source_evidence_deployment_discipline_error={error}")

    if errors:
        return 1
    print("source_evidence_deployment_discipline_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
