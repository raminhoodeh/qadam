"""Operational health and bounded analysis cycle for Qadam's hedge-fund team.

This module verifies work, not declarations. The Local Research Analyst and
Frontier Strategy Lead are healthy only after accepted model inference receipts
exist for the current cycle. The Head of Quant can be healthy-idle between
review jobs; hardware is never invoked merely to satisfy a health check.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Callable
import urllib.error
import urllib.request
from urllib.parse import urlparse

from orchestrator.config import Settings
from orchestrator.intelligence import (
    gemini_credential_probe,
    lm_studio_models_probe,
    run_local_research_analyst_inference,
)
from orchestrator.qadam_operator_ready_common import (
    append_jsonl_durable,
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    sha256_text,
    write_json_atomic,
)
from orchestrator.secrets import secret_value

SCHEMA_VERSION = "qadam_hedge_fund_team_health.v1"
STATUS_ARTIFACT = "qadam_hedge_fund_team_health.json"
CHECK_ARTIFACT = "qadam_hedge_fund_team_health_checks.json"
HISTORY_ARTIFACT = "qadam_hedge_fund_team_health_history.jsonl"
FRONTIER_HISTORY_ARTIFACT = "qadam_frontier_strategy_lead_assessments.jsonl"
TELEGRAM_STATUS_ARTIFACT = "qadam_team_health_telegram_status.json"
TELEGRAM_HISTORY_ARTIFACT = "qadam_team_health_telegram_history.jsonl"

CYCLE_SECONDS = 3 * 60 * 60
HEALTH_MAX_AGE_SECONDS = 4 * 60 * 60
MAX_HISTORY_BYTES = 2_000_000

CommandRunner = Callable[[tuple[str, ...], int], dict[str, Any]]
JsonRequester = Callable[[str, dict[str, Any], int], dict[str, Any]]

PIPELINE_STAGE_SERVICES: tuple[tuple[int, str, tuple[str, ...]], ...] = (
    (1, "Observe", ("source_ingestion",)),
    (
        2,
        "Qualify Evidence",
        ("historical_source_worker", "market_price_refresh", "execution_context"),
    ),
    (3, "Discover Patterns", ("pattern_scoring", "power_market_research")),
    (
        4,
        "Form Strategies",
        ("qeg_evidence_cycle", "qualitative_evidence_cycle", "open_market_conversion"),
    ),
    (
        5,
        "Validate Edge",
        ("research_evidence_validation", "forward_shadow", "active_discovery_trial"),
    ),
    (6, "Akber's Filter", ("akber_review", "canonical_tradeability")),
    (7, "Govern Decision", ("portfolio_router_review",)),
    (8, "Paper Trade", ("guarded_paperops", "paper_lifecycle_poll")),
    (9, "Learn", ("learning_attribution",)),
    (10, "Improve", ("challenger_research",)),
)

FRONTIER_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "summary",
        "challenges",
        "alternative_explanations",
        "evidence_gaps",
        "next_research_questions",
        "recommendation",
        "confidence",
    ],
    "properties": {
        "summary": {"type": "string"},
        "challenges": {
            "type": "array",
            "maxItems": 4,
            "items": {"type": "string"},
        },
        "alternative_explanations": {
            "type": "array",
            "maxItems": 4,
            "items": {"type": "string"},
        },
        "evidence_gaps": {
            "type": "array",
            "maxItems": 4,
            "items": {"type": "string"},
        },
        "next_research_questions": {
            "type": "array",
            "maxItems": 4,
            "items": {"type": "string"},
        },
        "recommendation": {
            "type": "string",
            "enum": [
                "continue_observation",
                "hold_for_more_evidence",
                "challenge_hypothesis",
                "no_material_change",
            ],
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _parse_timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_seconds(reference: datetime, value: Any) -> float | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return max(0.0, (reference - parsed).total_seconds())


def _team_authority() -> dict[str, Any]:
    return {
        **authority_flags(),
        "local_service_restart_allowed": True,
        "model_inference_allowed": True,
        "research_advisory_only": True,
        "strategy_admission_allowed": False,
        "risk_threshold_mutation_allowed": False,
        "paperops_invocation_allowed": False,
        "quantum_job_submission_allowed": False,
        "autonomous_code_edit_allowed": False,
    }


def _bounded_append(path: Path, payload: dict[str, Any]) -> None:
    append_jsonl_durable(path, payload)
    try:
        if path.stat().st_size <= MAX_HISTORY_BYTES:
            return
    except OSError:
        return
    rows = read_jsonl(path, limit=1_000)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _default_command_runner(command: tuple[str, ...], timeout_seconds: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "returncode": None,
            "status": "failed",
            "error_class": error.__class__.__name__,
            "duration_seconds": round(time.monotonic() - started, 3),
        }
    return {
        "returncode": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "duration_seconds": round(time.monotonic() - started, 3),
    }


def _lms_executable() -> str | None:
    discovered = shutil.which("lms")
    if discovered:
        return discovered
    candidate = Path.home() / ".lmstudio" / "bin" / "lms"
    return str(candidate) if candidate.is_file() else None


def ensure_local_research_analyst_ready(
    settings: Settings | None = None,
    *,
    repair: bool,
    command_runner: CommandRunner | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    inference_failed: bool = False,
) -> dict[str, Any]:
    """Probe LM Studio and perform only the reviewed server/model recovery."""

    active = settings or Settings.from_env()
    if not repair:
        return _ensure_local_research_analyst_ready(
            active, repair=repair, command_runner=command_runner, sleep_fn=sleep_fn,
        )
    from orchestrator.qadam_local_model_lock import local_model_lock

    runtime = runtime_dir(active)
    endpoint = urlparse(secret_value("LM_STUDIO_BASE_URL", active) or "http://127.0.0.1:1234/v1")
    if endpoint.hostname not in {"localhost", "127.0.0.1", "::1"}:
        return {"status": "degraded", "reason": "remote_model_reload_not_permitted"}
    with local_model_lock(runtime) as acquired:
        if not acquired:
            return {"status": "degraded", "reason": "local_inference_busy"}
        if not inference_failed:
            return _ensure_local_research_analyst_ready(
                active, repair=True, command_runner=command_runner, sleep_fn=sleep_fn,
            )
        receipt_path = runtime / "qadam_local_model_recovery.json"
        previous = read_json(receipt_path)
        age = _age_seconds(datetime.now(timezone.utc), previous.get("generated_at"))
        if age is not None and age < 900:
            return {"status": "degraded", "reason": "local_model_reload_cooldown",
                    "repair_attempted": False}
        receipt = {"generated_at": now_iso(), "status": "attempting", "broker_write_count": 0}
        write_json_atomic(receipt_path, receipt)
        result = _ensure_local_research_analyst_ready(
            active, repair=True, command_runner=command_runner, sleep_fn=sleep_fn,
            reload_model=True,
        )
        write_json_atomic(receipt_path, {**receipt, "status": result.get("status"),
                                        "repair_actions": result.get("repair_actions", [])})
        return result


def _ensure_local_research_analyst_ready(
    active: Settings, *, repair: bool, command_runner: CommandRunner | None,
    sleep_fn: Callable[[float], None], reload_model: bool = False,
) -> dict[str, Any]:

    probe = lm_studio_models_probe(active, live=True, timeout_seconds=2.0)
    actions: list[dict[str, Any]] = []
    if probe.get("probe_status") == "ok" and probe.get("model_available") is True and not reload_model:
        return {
            "status": "ready",
            "probe": probe,
            "repair_attempted": False,
            "repair_actions": actions,
        }
    if not repair:
        return {
            "status": "degraded",
            "probe": probe,
            "repair_attempted": False,
            "repair_actions": actions,
            "reason": "local_llm_not_ready",
        }

    executable = _lms_executable()
    if not executable:
        return {
            "status": "degraded",
            "probe": probe,
            "repair_attempted": True,
            "repair_actions": actions,
            "reason": "lm_studio_cli_missing",
        }
    run = command_runner or _default_command_runner
    if reload_model and probe.get("model_available") is True:
        model = str(probe.get("resolved_model") or "").strip()
        if not model or model.startswith("-") or not re.fullmatch(r"[A-Za-z0-9._:/@-]+", model):
            return {"status": "degraded", "reason": "local_model_identifier_missing"}
        result = run((executable, "unload", model), 30)
        actions.append({"action": "unload_unresponsive_configured_model", **result})
        if result.get("returncode") != 0:
            return {"status": "degraded", "reason": "local_model_unload_failed",
                    "repair_attempted": True, "repair_actions": actions}
        probe = {**probe, "model_available": False}
    if probe.get("probe_status") != "ok":
        result = run((executable, "server", "start"), 30)
        actions.append({"action": "start_lm_studio_server", **result})
        sleep_fn(1.0)
        probe = lm_studio_models_probe(active, live=True, timeout_seconds=3.0)

    if probe.get("probe_status") == "ok" and probe.get("model_available") is not True:
        model = str(secret_value("LM_STUDIO_MODEL", active) or "").strip()
        if model:
            identifier = model.rsplit("/", 1)[-1]
            result = run(
                (executable, "load", model, "--identifier", identifier, "-y"),
                90,
            )
            actions.append({"action": "load_configured_local_model", **result})
            sleep_fn(1.0)
            probe = lm_studio_models_probe(active, live=True, timeout_seconds=3.0)

    ready = probe.get("probe_status") == "ok" and probe.get("model_available") is True
    return {
        "status": "ready" if ready else "degraded",
        "probe": probe,
        "repair_attempted": True,
        "repair_actions": actions,
        "reason": None if ready else "local_llm_repair_did_not_restore_readiness",
    }


def _extract_json_object(value: str) -> dict[str, Any]:
    text = str(value or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("frontier_response_not_object")
    return parsed


def _default_json_request(
    url: str, payload: dict[str, Any], timeout_seconds: int
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "qadam-strategy-lead/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
            return {"status": "ok", "http_status": response.status, "payload": body}
    except urllib.error.HTTPError as error:
        return {
            "status": "http_error",
            "http_status": error.code,
            "error_class": error.__class__.__name__,
        }
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        return {
            "status": "provider_error",
            "http_status": None,
            "error_class": error.__class__.__name__,
        }


def _gemini_model(settings: Settings, probe: dict[str, Any]) -> str:
    configured = str(
        secret_value("GEMINI_STRATEGY_MODEL", settings)
        or secret_value("GEMINI_MODEL", settings)
        or ""
    ).strip()
    if configured:
        return configured.removeprefix("models/")
    # The availability probe confirms the API before this bounded default is used.
    if probe.get("probe_status") == "ok":
        return "gemini-3.5-flash"
    return "gemini-2.5-flash"


def _frontier_context(runtime: Path, local_assessment: dict[str, Any]) -> dict[str, Any]:
    pattern_rows = read_jsonl(runtime / "qadam_pattern_score_v3_records.jsonl", limit=400)
    latest_generation = max(
        (str(row.get("generated_at") or "") for row in pattern_rows), default=""
    )
    current_patterns = [
        {
            "strategy_label": row.get("strategy_label"),
            "instrument": row.get("instrument"),
            "research_score": row.get("raw_pattern_score"),
            "confidence_state": row.get("confidence_state"),
        }
        for row in pattern_rows
        if str(row.get("generated_at") or "") == latest_generation
    ]
    current_patterns.sort(key=lambda row: _as_float(row.get("research_score")), reverse=True)
    router = read_json(runtime / "qadam_router_v3_why_not_trading_now.json")
    qeg = read_json(runtime / "qadam_qeg_cycle_summary.json")
    return {
        "local_research_assessment": {
            key: local_assessment.get(key)
            for key in (
                "summary",
                "watch_focus",
                "anomalies",
                "missing_correlations",
                "next_questions",
                "escalation_recommendation",
                "confidence",
            )
        },
        "highest_ranked_patterns": current_patterns[:5],
        "graph_research": {
            "status": qeg.get("status"),
            "candidate_count": qeg.get("candidate_count"),
            "strategy_hypothesis_count": qeg.get("strategy_hypothesis_count"),
        },
        "current_router_explanation": router.get("primary_reason")
        or router.get("why_not_trading_now")
        or router.get("reason"),
    }


def run_frontier_strategy_lead_assessment(
    local_assessment: dict[str, Any],
    settings: Settings | None = None,
    *,
    requester: JsonRequester | None = None,
) -> dict[str, Any]:
    """Run one bounded Gemini challenge with no downstream decision authority."""

    active = settings or Settings.from_env()
    runtime = runtime_dir(active)
    generated_at = now_iso()
    probe = gemini_credential_probe(active, live=True, timeout_seconds=5.0)
    api_key = secret_value("GEMINI_API_KEY", active) or secret_value("GOOGLE_API_KEY", active)
    context = _frontier_context(runtime, local_assessment)
    input_digest = sha256_json(context)
    base = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_frontier_strategy_lead_assessment",
        "generated_at": generated_at,
        "provider": "gemini",
        "input_digest": input_digest,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "strategy_admission_allowed": False,
        "live_capital_enabled": False,
        "authority": _team_authority(),
        "boundary": (
            "Gemini challenges research reasoning only. It cannot admit a strategy, approve risk, "
            "invoke PaperOps, write to a broker, or enable live capital."
        ),
    }
    if not api_key or probe.get("probe_status") != "ok":
        record = {
            **base,
            "status": "degraded",
            "model": None,
            "probe_status": probe.get("probe_status"),
            "reason": "gemini_provider_unavailable",
        }
        _bounded_append(runtime / FRONTIER_HISTORY_ARTIFACT, record)
        return record

    model = _gemini_model(active, probe)
    prompt = {
        "instruction": (
            "Act as Qadam's Strategy Lead. Challenge the Local Research Analyst using only the "
            "supplied evidence. Return JSON only. Do not recommend an order, position size, risk "
            "approval, strategy admission, or live-capital action. Separate facts, inferences, "
            "alternative explanations, missing evidence, and the next research questions."
        ),
        "required_schema": {
            "summary": "string",
            "challenges": ["string"],
            "alternative_explanations": ["string"],
            "evidence_gaps": ["string"],
            "next_research_questions": ["string"],
            "recommendation": (
                "continue_observation | hold_for_more_evidence | challenge_hypothesis | "
                "no_material_change"
            ),
            "confidence": "number from 0 to 1",
        },
        "evidence": context,
    }
    payload = {
        "contents": [{"role": "user", "parts": [{"text": json.dumps(prompt, sort_keys=True)}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1600,
            "responseMimeType": "application/json",
            "responseJsonSchema": FRONTIER_RESPONSE_SCHEMA,
            "thinkingConfig": {"thinkingLevel": "LOW"},
        },
    }
    request = requester or _default_json_request
    response = request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        payload,
        45,
    )
    if response.get("status") != "ok":
        record = {
            **base,
            "status": "degraded",
            "model": model,
            "probe_status": probe.get("probe_status"),
            "reason": "gemini_generation_failed",
            "provider_error_class": response.get("error_class"),
            "http_status": response.get("http_status"),
        }
        _bounded_append(runtime / FRONTIER_HISTORY_ARTIFACT, record)
        return record

    candidates = _safe_list(_safe_dict(response.get("payload")).get("candidates"))
    candidate = _safe_dict(candidates[0]) if candidates else {}
    content = _safe_dict(candidate.get("content"))
    parts = _safe_list(content.get("parts"))
    text = "".join(str(_safe_dict(part).get("text") or "") for part in parts)
    try:
        parsed = _extract_json_object(text)
        recommendation = str(parsed.get("recommendation") or "")
        allowed = {
            "continue_observation",
            "hold_for_more_evidence",
            "challenge_hypothesis",
            "no_material_change",
        }
        if recommendation not in allowed:
            raise ValueError("frontier_recommendation_invalid")
        confidence = max(0.0, min(1.0, float(parsed.get("confidence") or 0.0)))
        assessment = {
            "summary": str(parsed.get("summary") or "")[:800],
            "challenges": [str(item)[:300] for item in _safe_list(parsed.get("challenges"))[:8]],
            "alternative_explanations": [
                str(item)[:300] for item in _safe_list(parsed.get("alternative_explanations"))[:8]
            ],
            "evidence_gaps": [
                str(item)[:300] for item in _safe_list(parsed.get("evidence_gaps"))[:8]
            ],
            "next_research_questions": [
                str(item)[:300] for item in _safe_list(parsed.get("next_research_questions"))[:8]
            ],
            "recommendation": recommendation,
            "confidence": round(confidence, 3),
        }
        if not assessment["summary"]:
            raise ValueError("frontier_summary_missing")
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        record = {
            **base,
            "status": "degraded",
            "model": model,
            "probe_status": probe.get("probe_status"),
            "reason": "gemini_output_contract_rejected",
            "output_error_class": error.__class__.__name__,
            "finish_reason": candidate.get("finishReason"),
        }
        _bounded_append(runtime / FRONTIER_HISTORY_ARTIFACT, record)
        return record

    record = {
        **base,
        "status": "accepted",
        "model": model,
        "probe_status": probe.get("probe_status"),
        "assessment": assessment,
    }
    _bounded_append(runtime / FRONTIER_HISTORY_ARTIFACT, record)
    return record


def _service_records(operator: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("service_id")): row
        for row in _safe_list(operator.get("services"))
        if isinstance(row, dict) and row.get("service_id")
    }


def build_pipeline_health(operator: dict[str, Any], circuits: dict[str, Any],
                          canonical_health: dict[str, Any] | None = None) -> dict[str, Any]:
    services = _service_records(operator)
    circuit_services = _safe_dict(circuits.get("services"))
    stages: list[dict[str, Any]] = []
    for number, name, service_ids in PIPELINE_STAGE_SERVICES:
        degraded_services: list[str] = []
        service_states: list[dict[str, Any]] = []
        for service_id in service_ids:
            row = _safe_dict(services.get(service_id))
            freshness = _safe_dict(row.get("freshness")).get("state")
            circuit = _safe_dict(circuit_services.get(service_id)).get("state")
            healthy = bool(row) and freshness == "fresh" and circuit not in {"open", "half_open"}
            if not healthy:
                degraded_services.append(service_id)
            service_states.append(
                {
                    "service_id": service_id,
                    "freshness": freshness or "missing",
                    "circuit": circuit or "closed",
                    "healthy": healthy,
                }
            )
        if number == 8 and canonical_health is not None and canonical_health.get("status") != "healthy":
            degraded_services.append("guarded_paperops")
            degraded_services = sorted(set(degraded_services))
        stages.append(
            {
                "stage": number,
                "name": name,
                "status": "healthy" if not degraded_services else "degraded",
                "services": service_states,
                "degraded_services": degraded_services,
            }
        )
    healthy_count = sum(row["status"] == "healthy" for row in stages)
    return {
        "status": "healthy" if healthy_count == len(stages) else "degraded",
        "healthy_stage_count": healthy_count,
        "stage_count": len(stages),
        "stages": stages,
        "canonical_execution": canonical_health,
    }


def _quant_health(runtime: Path, reference: datetime) -> dict[str, Any]:
    usefulness = read_json(runtime / "qadam_quantum_usefulness_summary.json")
    challenger = read_json(runtime / "qadam_graph_quantum_challenger.json")
    hardware = read_json(runtime / "qadam_ibm_full_history_experiment_status.json")
    current_at = usefulness.get("generated_at") or challenger.get("generated_at")
    age = _age_seconds(reference, current_at)
    current = age is not None and age <= 24 * 60 * 60
    hardware_completed = (
        hardware.get("status") == "completed" and hardware.get("hardware_job_submitted") is True
    )
    return {
        "role": "Head of Quant",
        "technology": "IBM Quantum, Q-CTRL and matched classical models",
        "status": "healthy_active"
        if current
        else "healthy_idle"
        if hardware_completed
        else "degraded",
        "current_review_at": current_at,
        "current_review_age_seconds": age,
        "current_review_status": usefulness.get("status") or challenger.get("status"),
        "quantum_contribution_verdict": usefulness.get("quantum_contribution_verdict"),
        "hardware_experiment_completed": hardware_completed,
        "hardware_job_started_by_health_check": False,
        "boundary": "Health checks never submit quantum hardware jobs.",
    }


def _input_digest(runtime: Path) -> str:
    names = (
        "qadam_pattern_score_v3.json",
        "qadam_qeg_cycle_summary.json",
        "qadam_router_v3_why_not_trading_now.json",
        "qadam_operator_service_status.json",
    )
    return sha256_json({name: read_json(runtime / name) for name in names})


def _cycle_slot(reference: datetime) -> int:
    return int(reference.timestamp()) // CYCLE_SECONDS


def run_hedge_fund_team_cycle(
    settings: Settings | None = None,
    *,
    repair_local: bool = True,
    force: bool = False,
    command_runner: CommandRunner | None = None,
    frontier_requester: JsonRequester | None = None,
    local_inference_runner: Callable[..., dict[str, Any]] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[dict[str, Any], list[str]]:
    active = settings or Settings.from_env()
    runtime = runtime_dir(active)
    reference = datetime.now(timezone.utc)
    slot = _cycle_slot(reference)
    digest = _input_digest(runtime)
    previous = read_json(runtime / STATUS_ARTIFACT)
    if (
        not force
        and previous.get("cycle_slot") == slot
        and previous.get("input_digest") == digest
        and previous.get("validation_error_count") == 0
        and previous.get("status") == "passed"
    ):
        return {**previous, "reused_current_slot": True}, []

    local_readiness = ensure_local_research_analyst_ready(
        active,
        repair=repair_local,
        command_runner=command_runner,
        sleep_fn=sleep_fn,
    )
    local_runner = local_inference_runner or run_local_research_analyst_inference
    local_attempt_count = 0
    if local_readiness.get("status") == "ready":
        # One newest packet stays inside the installed 4k local context while still
        # requiring a real model inference receipt every three-hour cycle.
        local_result = {}
        for _attempt in range(2):
            local_attempt_count += 1
            local_result = local_runner(limit=1, live=True, settings=active)
            assessment = _safe_dict(local_result.get("assessment"))
            if (
                local_result.get("status") == "ok"
                and str(assessment.get("mode") or "").startswith("live_local_llm")
                and assessment.get("raw_response_status") == "ok"
            ):
                break
            if _attempt == 0 and local_result.get("reason") == "connection_error":
                # A successful /models probe does not prove inference stayed up.
                sleep_fn(2.0)
                recovered = ensure_local_research_analyst_ready(
                    active, repair=repair_local, command_runner=command_runner,
                    sleep_fn=sleep_fn, inference_failed=True,
                )
                recovered["repair_actions"] = [
                    *(local_readiness.get("repair_actions") or []),
                    *(recovered.get("repair_actions") or []),
                ]
                recovered["repair_attempted"] = bool(
                    local_readiness.get("repair_attempted") or recovered.get("repair_attempted")
                )
                local_readiness = recovered
                if recovered.get("status") != "ready":
                    break
    else:
        local_attempt_count = 0
        local_result = {
            "status": "degraded",
            "mode": "live_local_llm",
            "reason": local_readiness.get("reason") or "local_llm_not_ready",
        }
    local_assessment = _safe_dict(local_result.get("assessment"))
    local_accepted = bool(
        local_result.get("status") == "ok"
        and str(local_assessment.get("mode") or "").startswith("live_local_llm")
        and local_assessment.get("raw_response_status") == "ok"
    )
    frontier_attempt_count = 0
    frontier: dict[str, Any] = {}
    for _attempt in range(2):
        frontier_attempt_count += 1
        frontier = run_frontier_strategy_lead_assessment(
            local_assessment,
            active,
            requester=frontier_requester,
        )
        if frontier.get("status") == "accepted":
            break
    operator = read_json(runtime / "qadam_operator_service_status.json")
    circuits = read_json(runtime / "qadam_operator_circuit_breakers.json")
    from orchestrator.qadam_operating_ledger import read_operating_health
    pipeline = build_pipeline_health(operator, circuits, read_operating_health(runtime))
    operator_age = _age_seconds(reference, operator.get("generated_at"))
    coo_healthy = bool(
        operator.get("service_running") is True
        and operator_age is not None
        and operator_age <= 30 * 60
    )
    roles = {
        "python_coo": {
            "role": "COO",
            "technology": "Python orchestration",
            "status": "healthy_active" if coo_healthy else "degraded",
            "last_operating_receipt_at": operator.get("generated_at"),
        },
        "local_research_analyst": {
            "role": "Research Analyst",
            "technology": "Local Gemma through LM Studio",
            "status": "healthy_active" if local_accepted else "degraded",
            "provider_status": _safe_dict(local_readiness.get("probe")).get("probe_status"),
            "model": local_assessment.get("model")
            or _safe_dict(local_readiness.get("probe")).get("resolved_model"),
            "assessment_id": local_assessment.get("assessment_id"),
            "inference_at": local_assessment.get("created_at"),
            "processed_packet_count": local_result.get("processed_packet_count", 0),
            "inference_attempt_count": local_attempt_count,
            "repair_attempted": local_readiness.get("repair_attempted") is True,
            "repair_actions": local_readiness.get("repair_actions") or [],
            "reason": None
            if local_accepted
            else local_result.get("reason") or "local_inference_output_not_accepted",
        },
        "frontier_strategy_lead": {
            "role": "Strategy Lead",
            "technology": "Google Gemini frontier model",
            "status": "healthy_active" if frontier.get("status") == "accepted" else "degraded",
            "provider_status": frontier.get("probe_status"),
            "model": frontier.get("model"),
            "inference_at": frontier.get("generated_at"),
            "input_digest": frontier.get("input_digest"),
            "inference_attempt_count": frontier_attempt_count,
            "reason": frontier.get("reason"),
        },
        "head_of_quant": _quant_health(runtime, reference),
        "fund_manager": {
            "role": "Fund Manager",
            "technology": "Human constitutional oversight",
            "status": "oversight_boundary_active",
            "automated_health_dependency": False,
        },
    }
    required_roles = (
        "python_coo",
        "local_research_analyst",
        "frontier_strategy_lead",
        "head_of_quant",
    )
    role_blockers = [
        role
        for role in required_roles
        if not str(_safe_dict(roles.get(role)).get("status")).startswith("healthy")
    ]
    blockers = [f"team_role_degraded:{role}" for role in role_blockers]
    if pipeline.get("status") != "healthy":
        blockers.append("trading_pipeline_stage_degraded")
    generated_at = now_iso()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_hedge_fund_team_health",
        "generated_at": generated_at,
        "cycle_slot": slot,
        "input_digest": digest,
        "status": "passed" if not blockers else "degraded",
        "team": roles,
        "required_role_count": len(required_roles),
        "healthy_required_role_count": len(required_roles) - len(role_blockers),
        "trading_pipeline": pipeline,
        "blockers": blockers,
        "repair_summary": {
            "local_repair_attempted": local_readiness.get("repair_attempted") is True,
            "local_repair_actions": local_readiness.get("repair_actions") or [],
            "operator_action_required": bool(blockers),
        },
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "quantum_job_submitted_count": 0,
        "live_capital_enabled": False,
        "authority": _team_authority(),
        "boundary": (
            "This cycle may restart the installed local inference service and run research-only "
            "model analysis. It cannot change code, secrets, risk, authority, strategies, orders, "
            "broker state, proof credit, quantum jobs, or live capital."
        ),
    }
    errors = validate_hedge_fund_team_health(payload)
    payload["validation_error_count"] = len(errors)
    payload["validation_errors"] = errors
    if errors:
        payload["status"] = "degraded"
    write_json_atomic(runtime / STATUS_ARTIFACT, payload)
    write_json_atomic(
        runtime / CHECK_ARTIFACT,
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_hedge_fund_team_health_checks",
            "generated_at": generated_at,
            "status": "passed" if not errors else "failed",
            "error_count": len(errors),
            "errors": errors,
            "authority": _team_authority(),
        },
    )
    _bounded_append(runtime / HISTORY_ARTIFACT, payload)
    return payload, errors


def validate_hedge_fund_team_health(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("team_health_schema_invalid")
    if payload.get("artifact_type") != "qadam_hedge_fund_team_health":
        errors.append("team_health_artifact_type_invalid")
    team = _safe_dict(payload.get("team"))
    required = {
        "python_coo",
        "local_research_analyst",
        "frontier_strategy_lead",
        "head_of_quant",
        "fund_manager",
    }
    if not required.issubset(team):
        errors.append("team_health_roles_incomplete")
    automated_roles = (
        "python_coo",
        "local_research_analyst",
        "frontier_strategy_lead",
        "head_of_quant",
    )
    healthy_roles = [
        role
        for role in automated_roles
        if str(_safe_dict(team.get(role)).get("status") or "").startswith("healthy")
    ]
    if int(payload.get("required_role_count") or 0) != len(automated_roles):
        errors.append("team_health_required_role_count_invalid")
    if int(payload.get("healthy_required_role_count") or 0) != len(healthy_roles):
        errors.append("team_health_healthy_role_count_invalid")
    local = _safe_dict(team.get("local_research_analyst"))
    if str(local.get("status") or "").startswith("healthy") and not all(
        local.get(field) for field in ("assessment_id", "inference_at", "model")
    ):
        errors.append("team_health_local_inference_receipt_incomplete")
    frontier = _safe_dict(team.get("frontier_strategy_lead"))
    if str(frontier.get("status") or "").startswith("healthy") and not all(
        frontier.get(field) for field in ("input_digest", "inference_at", "model")
    ):
        errors.append("team_health_frontier_inference_receipt_incomplete")
    pipeline = _safe_dict(payload.get("trading_pipeline"))
    stages = _safe_list(pipeline.get("stages"))
    if len(stages) != 10 or [row.get("stage") for row in stages] != list(range(1, 11)):
        errors.append("team_health_pipeline_stage_contract_invalid")
    if payload.get("status") == "passed":
        if len(healthy_roles) != len(automated_roles):
            errors.append("team_health_pass_with_degraded_role")
        if (
            pipeline.get("status") != "healthy"
            or int(pipeline.get("healthy_stage_count") or 0) != 10
            or int(pipeline.get("stage_count") or 0) != 10
        ):
            errors.append("team_health_pass_with_degraded_pipeline")
    if payload.get("paper_order_created_count") != 0:
        errors.append("team_health_created_paper_order")
    if payload.get("broker_write_count") != 0:
        errors.append("team_health_created_broker_write")
    if payload.get("quantum_job_submitted_count") != 0:
        errors.append("team_health_submitted_quantum_job")
    authority = _safe_dict(payload.get("authority"))
    for field in (
        "strategy_admission_allowed",
        "risk_threshold_mutation_allowed",
        "paperops_invocation_allowed",
        "quantum_job_submission_allowed",
        "autonomous_code_edit_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if authority.get(field) not in {False, 0, None}:
            errors.append(f"team_health_unsafe_authority:{field}")
    return sorted(set(errors))


def _health_message(team_health: dict[str, Any], critic: dict[str, Any]) -> str:
    team = _safe_dict(team_health.get("team"))
    local = _safe_dict(team.get("local_research_analyst"))
    frontier = _safe_dict(team.get("frontier_strategy_lead"))
    quant = _safe_dict(team.get("head_of_quant"))
    pipeline = _safe_dict(team_health.get("trading_pipeline"))
    repairs = _safe_dict(team_health.get("repair_summary"))
    repair_text = ""
    if repairs.get("local_repair_attempted"):
        repair_text = " LM Studio was restarted or reloaded, then checked again."
    local_text = (
        f"Gemma completed local analysis of {int(local.get('processed_packet_count') or 0)} research packets"
        if str(local.get("status") or "").startswith("healthy")
        else "Gemma needs attention"
    )
    frontier_text = (
        "Gemini completed its strategy challenge"
        if str(frontier.get("status") or "").startswith("healthy")
        else "Gemini needs attention"
    )
    quant_text = (
        "the quant review is current"
        if quant.get("status") == "healthy_active"
        else "the Head of Quant is healthy between scheduled reviews"
        if quant.get("status") == "healthy_idle"
        else "the Head of Quant needs attention"
    )
    critic_text = "healthy" if critic.get("status") == "passed" else "needs attention"
    return (
        "Qadam 3-hour health check\n"
        f"Team: Python COO is running; {local_text}; {frontier_text}; {quant_text}.\n"
        f"Trading pipeline: {int(pipeline.get('healthy_stage_count') or 0)}/10 stages healthy. "
        f"Self-healing: {critic_text}.\n"
        f"Current state: {critic.get('primary_reason') or 'No explanation reported.'}{repair_text}"
    )[:1_500]


def send_team_health_telegram_update(
    team_health: dict[str, Any],
    critic: dict[str, Any],
    settings: Settings | None = None,
    *,
    sender: Callable[[str, str, str, int | None], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Send one public-safe health report per three-hour slot, with retry semantics."""

    active = settings or Settings.from_env()
    runtime = runtime_dir(active)
    token = secret_value("TELEGRAM_BOT_TOKEN", active)
    target = secret_value("TELEGRAM_GROUP_CHAT_ID", active)
    generated_at = now_iso()
    slot = int(datetime.now(timezone.utc).timestamp()) // CYCLE_SECONDS
    from orchestrator.qadam_research_telegram import notification_health

    messaging_state, messaging_text = notification_health(runtime)
    pipeline = _safe_dict(team_health.get("trading_pipeline"))
    state_signature = ":".join(
        (
            str(team_health.get("status") or "unknown"),
            str(team_health.get("healthy_required_role_count") or 0),
            str(pipeline.get("healthy_stage_count") or 0),
            str(critic.get("status") or "unknown"),
            str(critic.get("operating_state") or "unknown"),
            messaging_state,
        )
    )
    # A degraded report and its recovered state may both be useful inside one
    # slot, while an unchanged state remains strictly deduplicated.
    response_key = sha256_text(f"{SCHEMA_VERSION}:team-health:{slot}:{state_signature}")
    previous = read_jsonl(runtime / TELEGRAM_HISTORY_ARTIFACT, limit=1_000)
    if any(
        row.get("response_key") == response_key and row.get("delivery_status") == "delivered"
        for row in previous
    ):
        return {"status": "already_sent", "sent": False, "response_key": response_key}
    if not token or not target:
        result = {
            "status": "missing_configuration",
            "sent": False,
            "response_key": response_key,
        }
        write_json_atomic(
            runtime / TELEGRAM_STATUS_ARTIFACT, {**result, "generated_at": generated_at}
        )
        return result

    if sender is None:
        from orchestrator.qadam_telegram_readonly_interface import send_readonly_response

        sender = send_readonly_response
    message = _health_message(team_health, critic) + "\n" + messaging_text
    try:
        provider = sender(str(token), str(target), message, None)
        delivered = provider.get("ok") is True
        error_class = None if delivered else provider.get("error_class") or "provider_error"
    except Exception as error:  # noqa: BLE001 - transport failure remains retryable
        delivered = False
        error_class = error.__class__.__name__
    event = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_team_health_telegram_event",
        "generated_at": generated_at,
        "response_key": response_key,
        "target_ref_hash": sha256_text(str(target))[:24],
        "delivery_status": "delivered" if delivered else "delivery_retry_pending",
        "provider_error_class": error_class,
        "message_digest": sha256_text(message),
        "message_char_count": len(message),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": _team_authority(),
    }
    _bounded_append(runtime / TELEGRAM_HISTORY_ARTIFACT, event)
    status = {
        **event,
        "artifact_type": "qadam_team_health_telegram_status",
        "status": "delivered" if delivered else "retry_pending",
        "sent": delivered,
    }
    write_json_atomic(runtime / TELEGRAM_STATUS_ARTIFACT, status)
    return status


__all__ = [
    "CHECK_ARTIFACT",
    "FRONTIER_HISTORY_ARTIFACT",
    "HEALTH_MAX_AGE_SECONDS",
    "HISTORY_ARTIFACT",
    "PIPELINE_STAGE_SERVICES",
    "SCHEMA_VERSION",
    "STATUS_ARTIFACT",
    "TELEGRAM_HISTORY_ARTIFACT",
    "TELEGRAM_STATUS_ARTIFACT",
    "build_pipeline_health",
    "ensure_local_research_analyst_ready",
    "run_frontier_strategy_lead_assessment",
    "run_hedge_fund_team_cycle",
    "send_team_health_telegram_update",
    "validate_hedge_fund_team_health",
]
