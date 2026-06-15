"""Public-safe quality checks for Telegram message text."""

from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Iterable


TELEGRAM_MESSAGE_MIN_SPECIFICITY_SCORE = 70

_VALUE_PATTERN = re.compile(
    r"\b(?:GBP|USD|\d+(?:\.\d+)?%?|\d{4}-\d{2}-\d{2}|[a-f0-9]{8,12})\b",
    re.IGNORECASE,
)

_GENERIC_FALLBACK_PHRASES = (
    "backend state changed.",
    "structured runtime state.",
    "structured candidate created",
    "evidence summary pending",
    "instrument watch",
    "paper lifecycle update",
    "not provided",
    "unknown",
)

_CONTEXT_MARKERS = (
    "What changed:",
    "Detected update areas:",
    "Why it matters:",
    "Why this matters:",
    "What to check:",
    "Current impact:",
    "Evidence:",
    "Trade:",
    "Portfolio:",
    "Performance:",
    "Trades made today:",
    "Open positions:",
    "Broker status:",
    "Date:",
    "Upgrade:",
)

_HUMAN_TECHNICAL_NOISE_PATTERNS = (
    re.compile(r"\b(?:commit|branch|git|vercel|deployment|delivery key|fingerprint|schema|artifact|runtime)\b", re.IGNORECASE),
    re.compile(r"\b(?:version control|pull request|diff|repo|repository|alias(?:es)?)\b", re.IGNORECASE),
    re.compile(r"\b(?:Upgrade|Evidence|Dashboard|PaperOps context|Broker status|Detected update areas|What changed|Status|Mode):", re.IGNORECASE),
    re.compile(r"\b[a-f0-9]{8,40}\b", re.IGNORECASE),
    re.compile(r"https?://|qadam\.trade/"),
)

_HUMAN_EXPLANATION_TERMS = (
    "this means",
    "in plain terms",
    "for now",
    "because",
    "so",
    "what happened",
    "what this means",
    "you can",
    "the important point",
    "nothing here",
    "paper trading",
)


def _normalise(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def telegram_message_fingerprint(title: str, body: str) -> str:
    """Return a stable fingerprint for duplicate detection without storing secrets."""

    return sha256(_normalise(f"{title}\n{body}").encode("utf-8")).hexdigest()


def _lines(body: str) -> list[str]:
    return [line.strip() for line in str(body or "").splitlines() if line.strip()]


def _paragraphs(body: str) -> list[str]:
    raw = str(body or "").replace("\r\n", "\n")
    return [" ".join(part.split()) for part in raw.split("\n\n") if part.strip()]


def _sentence_count(text: str) -> int:
    return len([part for part in re.split(r"[.!?]+", str(text or "")) if part.strip()])


def _specific_value_line_count(lines: Iterable[str]) -> int:
    count = 0
    for line in lines:
        if ":" not in line:
            continue
        _, value = line.split(":", 1)
        normalised_value = _normalise(value)
        if len(normalised_value) < 8:
            continue
        if any(phrase in normalised_value for phrase in _GENERIC_FALLBACK_PHRASES):
            continue
        count += 1
    return count


def telegram_human_message_style(
    title: str,
    body: str,
    *,
    max_paragraphs: int = 2,
) -> dict[str, Any]:
    """Check that an outbound Telegram body reads like a human note.

    The title is still accepted for internal artifacts, but the body is what is
    intended to be sent to Telegram. This check rejects section headers, links,
    commit-like identifiers, and deployment/repo wording.
    """

    title_text = str(title or "")
    body_text = str(body or "")
    body_paragraphs = _paragraphs(body_text)
    body_lines = _lines(body_text)
    combined = f"{title_text}\n{body_text}"
    technical_hits = [
        pattern.pattern
        for pattern in _HUMAN_TECHNICAL_NOISE_PATTERNS
        if pattern.search(combined)
    ]
    colon_header_lines = [
        line
        for line in body_lines
        if re.match(r"^[A-Z][A-Za-z0-9 /-]{1,40}:", line)
    ]
    errors: list[str] = []
    if not body_text.strip():
        errors.append("body_empty")
    if len(body_paragraphs) < 1 or len(body_paragraphs) > max_paragraphs:
        errors.append("paragraph_count_outside_human_range")
    if len(body_text) > 900:
        errors.append("body_too_long_for_human_telegram")
    if len(body_lines) > max_paragraphs + 1:
        errors.append("too_many_line_breaks_for_human_telegram")
    if technical_hits:
        errors.append("technical_or_version_control_noise_present")
    if colon_header_lines:
        errors.append("section_header_lines_present")
    if _sentence_count(body_text) < 2:
        errors.append("not_enough_explanatory_sentences")

    return {
        "schema_version": 1,
        "status": "human" if not errors else "technical",
        "paragraph_count": len(body_paragraphs),
        "line_count": len(body_lines),
        "sentence_count": _sentence_count(body_text),
        "technical_noise_count": len(technical_hits),
        "section_header_count": len(colon_header_lines),
        "errors": sorted(set(errors)),
    }


def telegram_message_specificity(
    title: str,
    body: str,
    *,
    recent_bodies: Iterable[str] = (),
    minimum_score: int = TELEGRAM_MESSAGE_MIN_SPECIFICITY_SCORE,
) -> dict[str, Any]:
    """Score whether a Telegram message explains the actual event.

    This is intentionally heuristic. It is not a classifier for correctness; it
    is a guard against repeatedly sending safe but low-information templates.
    """

    title_text = str(title or "")
    body_text = str(body or "")
    combined = f"{title_text}\n{body_text}"
    normalised = _normalise(combined)
    message_lines = _lines(body_text)
    message_paragraphs = _paragraphs(body_text)
    paragraph_style_ok = 1 <= len(message_paragraphs) <= 2 and len(message_lines) <= 3
    human_style = telegram_human_message_style(title_text, body_text)
    score = 0
    reasons: list[str] = []

    if len(body_text) >= 220:
        score += 20
    else:
        reasons.append("body_too_short")
    if len(body_text) >= 450:
        score += 10
    if len(message_lines) >= 7:
        score += 12
    elif paragraph_style_ok and _sentence_count(body_text) >= 3:
        score += 12
    else:
        reasons.append("not_enough_lines")

    marker_hits = [marker for marker in _CONTEXT_MARKERS if marker in body_text]
    score += min(24, len(marker_hits) * 4)
    explanation_hits = [term for term in _HUMAN_EXPLANATION_TERMS if term in normalised]
    score += min(18, len(explanation_hits) * 4)
    if paragraph_style_ok:
        score += 14
    if human_style["status"] == "human":
        score += 18
    if (
        "Why it matters:" not in body_text
        and "Why this matters:" not in body_text
        and not explanation_hits
    ):
        reasons.append("missing_why_it_matters")
    if "Evidence:" not in body_text and not paragraph_style_ok:
        reasons.append("missing_evidence")
    if (
        not any(marker in body_text for marker in ("What changed:", "Trade:", "Portfolio:", "Trades made today:", "Current impact:"))
        and not paragraph_style_ok
    ):
        reasons.append("missing_event_specific_section")

    value_hits = _VALUE_PATTERN.findall(combined)
    score += min(18, len(value_hits) * 3)
    if not value_hits and not paragraph_style_ok:
        reasons.append("missing_numeric_or_identifier_context")

    specific_value_lines = _specific_value_line_count(message_lines)
    score += min(20, specific_value_lines * 4)
    if paragraph_style_ok and value_hits:
        score += 12
    elif paragraph_style_ok:
        score += 8
    elif specific_value_lines < 3:
        reasons.append("not_enough_specific_value_lines")

    if "Dashboard: qadam.trade/dashboard/" in body_text:
        score += 8
    elif paragraph_style_ok:
        score += 6
    else:
        reasons.append("missing_dashboard_link")

    generic_hits = [
        phrase for phrase in _GENERIC_FALLBACK_PHRASES if phrase in normalised
    ]
    score -= len(generic_hits) * 18
    if generic_hits:
        reasons.append("generic_fallback_text_present")

    fingerprint = telegram_message_fingerprint(title_text, body_text)
    duplicate_count = sum(
        1
        for recent_body in recent_bodies
        if telegram_message_fingerprint("", str(recent_body or "")) == telegram_message_fingerprint("", body_text)
    )
    if duplicate_count:
        score -= 35
        reasons.append("recent_duplicate_body")

    score = max(0, min(100, score))
    status = "specific" if score >= minimum_score and not duplicate_count else "generic"
    if score < minimum_score:
        reasons.append("specificity_score_below_threshold")

    return {
        "schema_version": 1,
        "status": status,
        "score": score,
        "minimum_score": minimum_score,
        "fingerprint": fingerprint,
        "line_count": len(message_lines),
        "specific_value_line_count": specific_value_lines,
        "context_marker_count": len(marker_hits),
        "numeric_or_identifier_count": len(value_hits),
        "recent_duplicate_count": duplicate_count,
        "reasons": sorted(set(reasons)),
    }


def assert_specific_telegram_message(
    title: str,
    body: str,
    *,
    minimum_score: int = TELEGRAM_MESSAGE_MIN_SPECIFICITY_SCORE,
) -> dict[str, Any]:
    quality = telegram_message_specificity(
        title,
        body,
        minimum_score=minimum_score,
    )
    if quality["status"] != "specific":
        raise ValueError("generic Telegram message text")
    return quality
