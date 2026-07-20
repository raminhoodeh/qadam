#!/usr/bin/env python3
"""Generate Qadam's operator-facing historical data sourcing brief."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "data" / "runtime"
OUTPUT = ROOT / "output" / "pdf" / "qadam-missing-backtesting-data-sourcing-brief.pdf"

CRIMSON = colors.HexColor("#B0003A")
INK = colors.HexColor("#302C33")
MUTED = colors.HexColor("#66616A")
RULE = colors.HexColor("#DDD7D2")
PALE = colors.HexColor("#F7F3F1")
PALE_BLUE = colors.HexColor("#EAF2F5")
PALE_GREEN = colors.HexColor("#EAF5EF")
PALE_GOLD = colors.HexColor("#FAF1DE")
WHITE = colors.white


def _read_json(name: str) -> dict[str, Any]:
    path = RUNTIME / name
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"required runtime artifact unavailable: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"runtime artifact is not an object: {path}")
    return payload


def _register_fonts() -> tuple[str, str, str]:
    sans = "Helvetica"
    sans_bold = "Helvetica-Bold"
    serif = "Times-Roman"
    candidates = {
        "QadamSans": "/System/Library/Fonts/SFNS.ttf",
        "QadamSansBold": "/System/Library/Fonts/SFNS.ttf",
        "QadamSerif": "/System/Library/Fonts/NewYork.ttf",
    }
    for name, path in candidates.items():
        try:
            pdfmetrics.registerFont(TTFont(name, path))
        except Exception:
            continue
    if "QadamSans" in pdfmetrics.getRegisteredFontNames():
        sans = "QadamSans"
        sans_bold = "QadamSansBold"
    if "QadamSerif" in pdfmetrics.getRegisteredFontNames():
        serif = "QadamSerif"
    return sans, sans_bold, serif


SANS, SANS_BOLD, SERIF = _register_fonts()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_eyebrow": ParagraphStyle(
            "cover_eyebrow",
            parent=base["Normal"],
            fontName=SANS_BOLD,
            fontSize=9,
            leading=12,
            textColor=CRIMSON,
            tracking=1.2,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontName=SERIF,
            fontSize=31,
            leading=34,
            textColor=INK,
            alignment=TA_CENTER,
            spaceAfter=13,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=base["Normal"],
            fontName=SANS,
            fontSize=11,
            leading=16,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=16,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName=SERIF,
            fontSize=23,
            leading=27,
            textColor=INK,
            spaceBefore=2,
            spaceAfter=9,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName=SANS_BOLD,
            fontSize=13,
            leading=17,
            textColor=CRIMSON,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base["Heading3"],
            fontName=SANS_BOLD,
            fontSize=10.5,
            leading=14,
            textColor=INK,
            spaceBefore=7,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName=SANS,
            fontSize=9.3,
            leading=13.5,
            textColor=INK,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["BodyText"],
            fontName=SANS,
            fontSize=7.6,
            leading=10.2,
            textColor=INK,
        ),
        "small_muted": ParagraphStyle(
            "small_muted",
            parent=base["BodyText"],
            fontName=SANS,
            fontSize=7.4,
            leading=10,
            textColor=MUTED,
        ),
        "metric": ParagraphStyle(
            "metric",
            parent=base["Normal"],
            fontName=SERIF,
            fontSize=20,
            leading=22,
            textColor=CRIMSON,
            alignment=TA_CENTER,
        ),
        "metric_label": ParagraphStyle(
            "metric_label",
            parent=base["Normal"],
            fontName=SANS_BOLD,
            fontSize=7.2,
            leading=9,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "callout": ParagraphStyle(
            "callout",
            parent=base["BodyText"],
            fontName=SANS,
            fontSize=9.5,
            leading=14,
            textColor=INK,
            leftIndent=5,
            rightIndent=5,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["BodyText"],
            fontName=SANS,
            fontSize=8.9,
            leading=13,
            textColor=INK,
            leftIndent=12,
            firstLineIndent=-7,
            bulletIndent=3,
            spaceAfter=3,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            parent=base["Normal"],
            fontName=SANS_BOLD,
            fontSize=7.2,
            leading=9,
            textColor=WHITE,
        ),
    }


STYLES = _styles()


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"- {text}", STYLES["bullet"])


def link(label: str, url: str) -> str:
    return f'<link href="{url}" color="#B0003A"><u>{label}</u></link>'


def callout(text: str, *, background: colors.Color = PALE_BLUE) -> Table:
    table = Table([[p(text, "callout")]], colWidths=[166 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def metric_strip(metrics: list[tuple[str, str]]) -> Table:
    cells = [
        [p(value, "metric") for value, _label in metrics],
        [p(label, "metric_label") for _value, label in metrics],
    ]
    table = Table(
        cells,
        colWidths=[166 * mm / len(metrics)] * len(metrics),
        rowHeights=[15 * mm, 10 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, RULE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def data_table(
    headers: list[str],
    rows: list[list[str | Paragraph]],
    widths: list[float],
    *,
    font_size: float = 7.6,
) -> Table:
    header = [p(value, "table_header") for value in headers]
    normalized: list[list[Paragraph]] = []
    style_name = "small" if font_size >= 7.5 else "small_muted"
    for row in rows:
        normalized.append(
            [value if isinstance(value, Paragraph) else p(str(value), style_name) for value in row]
        )
    table = Table([header, *normalized], colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for index in range(1, len(rows) + 1):
        if index % 2 == 0:
            commands.append(("BACKGROUND", (0, index), (-1, index), PALE))
    table.setStyle(TableStyle(commands))
    return table


def _priority_rows() -> list[list[str]]:
    return [
        [
            "1",
            "Unusual Whales historical flow",
            "Official export or licensed archive of options flow, interval flow, market tide, IV, Greeks, liquidity, corrections, and exact event timestamps.",
            "Tests whether flow confirms or rejects Qadam's macro signals. Current eligible historical rows: 0.",
        ],
        [
            "2",
            "STOCK Act transaction details",
            "House and Senate periodic transaction report rows, amendments, asset identity, amount range, transaction date, and public-availability timestamp.",
            "The filing index exists, but 29,824 index rows contain 0 normalized transaction-detail rows.",
        ],
        [
            "3",
            "Kalshi market microstructure",
            "Historical trades, bid/ask candlesticks, volume, open interest, lifecycle, settlement, fee and fill context for every mapped contract.",
            "5,034 identity records are usable as signals; direct contract backtesting remains incomplete.",
        ],
        [
            "4",
            "Polymarket CLOB history",
            "Token/condition identity, price history, orderbook or spread snapshots, trades, liquidity, lifecycle, resolution and fee context.",
            "28,275 identity records are usable as signals; direct contract execution evidence remains incomplete.",
        ],
        [
            "5",
            "Point-in-time macro and physical archives",
            "Vintage releases and exact availability timestamps for selected macro, geospatial, shipping, aviation, outage and conflict sources.",
            "Expands beyond the five historically scored source signals without introducing look-ahead leakage.",
        ],
    ]


def _source_action(row: dict[str, Any]) -> str:
    key = str(row.get("source_key") or "")
    priority = {
        "unusual_whales": "Source now - highest priority",
        "stock_act": "Complete transaction-detail plane",
        "kalshi": "Extend with market microstructure",
        "polymarket": "Extend with CLOB liquidity history",
        "acled": "License review before use",
        "fred": "Use ALFRED vintages only after written terms review",
        "un_comtrade": "Seek approved bulk archive terms",
        "bookmap": "Optional official export only",
    }
    if key in priority:
        return priority[key]
    status = row.get("status")
    if status == "pilot_ready":
        return "Covered - retain provenance and refresh"
    if status == "forward_only":
        return "Capture prospectively; seek archive only if official"
    return "Keep excluded unless an official licensed history is obtained"


def _page_header_footer(canvas, doc) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    width, height = A4
    canvas.setFont(SANS, 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(22 * mm, 12 * mm, "Paper-only research sourcing brief - no trading authority")
    canvas.drawRightString(width - 22 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf() -> Path:
    coverage = _read_json("qadam_backtest_completion_coverage.json")
    planes = _read_json("qadam_backtest_completion_source_planes.json").get("source_planes", {})
    gap = _read_json("qadam_historical_gap_resolution.json")
    labels = _read_json("qadam_label_coverage.json")
    matrix = _read_json("qadam_historical_source_coverage_matrix.json")
    rows = matrix.get("rows") if isinstance(matrix.get("rows"), list) else []
    partition = gap.get("provider_partition_state", {})
    alignment = gap.get("provider_alignment_state", {})
    legacy = gap.get("legacy_grid_state", {})

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=28 * mm,
        bottomMargin=24 * mm,
        title="Qadam Missing Backtesting Data Sourcing Brief",
        author="Qadam Research Operations",
        subject="Provider-backed historical data gaps and operator sourcing requirements",
    )
    story: list[Any] = []
    generated = datetime.now(timezone.utc).strftime("%d %B %Y")

    story.extend(
        [
            Spacer(1, 28 * mm),
            p("QADAM - OPERATOR SOURCING BRIEF", "cover_eyebrow"),
            p("Missing Backtesting Data", "cover_title"),
            p(
                "What is genuinely missing, what is already complete, and what to source next to expand Qadam's point-in-time research evidence.",
                "cover_subtitle",
            ),
            HRFlowable(width="55%", thickness=1.2, color=CRIMSON, spaceBefore=3, spaceAfter=16, hAlign="CENTER"),
            metric_strip(
                [
                    (str(coverage.get("source_count", 0)), "SOURCE UNIVERSE"),
                    (str(coverage.get("instrument_count", 0)), "WATCHED INSTRUMENTS"),
                    (f"{int(coverage.get('provider_backed_historical_rows') or 0):,}", "CURRENT CANONICAL ROWS"),
                    (str(coverage.get("historically_scored_source_count", 0)), "HISTORICALLY SCORED SOURCES"),
                ]
            ),
            Spacer(1, 12 * mm),
            callout(
                "<b>Current conclusion.</b> Qadam's available provider-backed acquisition is terminal and honestly classified. The important remaining gap is breadth and execution-quality evidence, especially Unusual Whales, STOCK Act transaction details, and prediction-market microstructure. More data can improve the search, but cannot guarantee an edge.",
                background=PALE_GREEN,
            ),
            Spacer(1, 15 * mm),
            p(f"Prepared from canonical runtime artifacts on {generated}.", "cover_subtitle"),
            p("Private internal research. Re-check provider terms before acquisition, redistribution, packaging, or commercial use.", "cover_subtitle"),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("1. Executive Answer", "h1"),
            p(
                "Qadam does not have an unfinished bulk download. It has a completed provider-backed baseline with uneven source depth. Ten source histories and 17 instrument histories were acquired; 15 sources are forward-only and 16 are terminally unavailable under the current frozen contracts. Only five source signals currently have enough point-in-time history to enter the canonical score-label dataset.",
            ),
            callout(
                "<b>The next useful acquisition is not more of the same price data.</b> It is timestamp-accurate, economically distinct evidence that can test a specific mechanism: prediction-market disagreement, congressional disclosures, and options-flow confirmation.",
                background=PALE_GOLD,
            ),
            p("What is already complete", "h2"),
            bullet(f"{int(partition.get('acquired') or 0)} provider partitions were acquired and {int(partition.get('classified_unavailable') or 0)} were classified unavailable. All {int(partition.get('total') or 0)} partitions are terminal."),
            bullet(f"The point-in-time alignment contains {int(alignment.get('alignment_record_count') or 0):,} records, {int(alignment.get('eligible_forward_window_count') or 0):,} eligible forward windows and {int(alignment.get('relationship_count') or 0)} relationships."),
            bullet(f"The current label plane contains {int(labels.get('label_count') or 0):,} labels. Its {int(labels.get('typed_missing_label_count') or 0)} missing labels are future windows that have not matured yet, not data Qadam should invent or backfill."),
            bullet("The clean Alpaca paper account, guarded PaperOps route and dashboard are operationally separate from this historical-data sourcing work."),
            p("What remains worth sourcing", "h2"),
            data_table(
                ["Priority", "Dataset", "Minimum acquisition", "Why it matters"],
                _priority_rows(),
                [12 * mm, 36 * mm, 64 * mm, 54 * mm],
            ),
            PageBreak(),
        ]
    )

    resolution = legacy.get("resolution_state_counts", {})
    story.extend(
        [
            p("2. The 6,150 Legacy Gaps Explained", "h1"),
            p(
                "The legacy whole-universe grid still displays 6,150 missing or ineligible cells. This is an audit trail, not an OR-3 download queue. The baseline intentionally did not mutate or backfill those cells, and the repairable count in the frozen baseline is zero.",
            ),
            data_table(
                ["Typed resolution", "Count", "Meaning", "Operator response"],
                [
                    ["No point-in-time overlap", f"{int(resolution.get('terminal_unavailable_no_point_in_time_overlap') or 0):,}", "The source and price windows do not overlap under the no-leakage clock.", "Do not fabricate. A genuinely older archive may create a new, versioned baseline."],
                    ["Intentionally excluded relationship", f"{int(resolution.get('intentionally_excluded_relationship') or 0):,}", "The pair has no defensible research mechanism or duplicates another source.", "Keep excluded unless a pre-registered mechanism is approved."],
                    ["Superseded by provider alignment", f"{int(resolution.get('superseded_by_provider_alignment') or 0):,}", "The legacy cell is obsolete because the canonical provider alignment now represents it.", "No action."],
                    ["Contract identity unavailable", f"{int(resolution.get('terminal_unavailable_contract_identity') or 0):,}", "An expired or historical contract cannot be mapped reliably.", "Source official contract identity and lifecycle history only."],
                    ["Descriptive, not forward label", f"{int(resolution.get('descriptive_non_forward_record') or 0):,}", "The record is useful context but is not a predictive forward-return observation.", "Retain as context; do not force a label."],
                ],
                [42 * mm, 18 * mm, 58 * mm, 48 * mm],
            ),
            Spacer(1, 7 * mm),
            callout(
                "<b>Do not set 6,150 to zero.</b> A zero forced by synthetic values would make Qadam look complete while weakening its point-in-time integrity. New licensed archives should enter as a new provider/version lineage and be evaluated against the frozen baseline.",
            ),
            p("Current forward-label maturity", "h2"),
            p(
                f"There are {int(labels.get('typed_missing_label_count') or 0)} labels with the typed reason <b>forward_window_not_yet_complete</b>. These close automatically only when real market time reaches their pre-defined horizon. They require waiting, not procurement.",
            ),
            PageBreak(),
        ]
    )

    uw = planes.get("unusual_whales", {})
    stock = planes.get("stock_act", {})
    story.extend(
        [
            p("3. Highest-Priority Source: Unusual Whales", "h1"),
            p(
                f"Current state: <b>{uw.get('status', 'unknown')}</b>. Eligible historical rows: <b>{int(uw.get('historical_backtest_eligible_record_count') or 0)}</b>. A current API response or 72-hour stream retention is useful for forward capture, but it is not a historical backtest.",
            ),
            p("Request this from the provider", "h2"),
            bullet("A licensed historical export for Qadam's 19 watched instruments and their option chains, ideally covering at least two years and preferably five years."),
            bullet("Five-minute interval flow, flow alerts, market tide or net flow, stock tape context, option-chain state, implied volatility, Greeks, open interest, premium and liquidity fields."),
            bullet("Exact executed_at, tape_time, start_time, provider publication/availability time, unique record IDs, cancellations/corrections and schema version."),
            bullet("Bid/ask or NBBO context, trade side, size, premium, sweep/multileg flags, option identity, expiry, strike, right and underlying price."),
            bullet("Written private-research retention rights and an explicit statement of whether derived backtest statistics may be retained."),
            p("Acceptance test", "h2"),
            bullet("Raw export checksum and immutable acquisition receipt."),
            bullet("No future open interest, end-of-day classifications or corrected values may leak backward to the event timestamp."),
            bullet("Run four pre-registered comparisons: core without Unusual Whales; core plus Unusual Whales; Unusual Whales-only diagnostic; shuffled and time-shifted controls."),
            bullet("Promote nothing unless the signal adds net-of-cost holdout value beyond the macro baseline."),
            callout(
                f"Official reference: {link('Unusual Whales API documentation', 'https://api.unusualwhales.com/docs')} and {link('Kafka retention and schemas', 'https://api.unusualwhales.com/docs/kafka')}. The official streaming documentation states 72-hour retention, which is why a bespoke historical export remains necessary.",
                background=PALE_GREEN,
            ),
            Spacer(1, 8 * mm),
            p("4. Highest-Priority Source: STOCK Act", "h1"),
            p(
                f"Current state: <b>{stock.get('status', 'unknown')}</b>. Qadam has {int(stock.get('filing_index_record_count') or 0):,} filing-index records but {int(stock.get('transaction_detail_record_count') or 0)} normalized transaction-detail records. The index proves a filing exists; it does not tell Qadam what was bought or sold.",
            ),
            p("Minimum normalized transaction schema", "h2"),
            bullet("Document ID, chamber, filer identity, owner, report type, source URL, amendment/correction lineage and raw document checksum."),
            bullet("Asset description, resolved ticker or stable asset identity, transaction type, transaction date and disclosed amount range. Never invent an exact notional."),
            bullet("Filed date and the exact public-availability timestamp. Backtests must score from public availability, not the earlier transaction date."),
            bullet("Committee, sector and strategy-basket mappings as derived features with parser version and confidence."),
            callout(
                f"Official sources: {link('House disclosure downloads', 'https://disclosures-clerk.house.gov/FinancialDisclosure/ViewReport')} and {link('Senate financial disclosure guidance', 'https://www.ethics.senate.gov/public/index.cfm/financialdisclosure')}. Store raw reports separately from parsed rows so amendments remain auditable.",
                background=PALE_GREEN,
            ),
            PageBreak(),
        ]
    )

    kalshi = planes.get("kalshi", {})
    poly = planes.get("polymarket", {})
    story.extend(
        [
            p("5. Prediction-Market Completion", "h1"),
            p(
                "Kalshi and Polymarket already contribute point-in-time signal identity. The missing layer is sufficient market microstructure to test disagreement as a tradeable instrument rather than only as a predictor of ETFs or futures.",
            ),
            p("Kalshi", "h2"),
            p(
                f"Qadam currently holds {int(kalshi.get('record_count') or 0):,} records across {int(kalshi.get('unique_counts', {}).get('event_ticker') or 0)} event tickers and {int(kalshi.get('unique_counts', {}).get('market_ticker') or 0)} market tickers. Direct-instrument state: <b>{kalshi.get('direct_instrument_reason', 'incomplete')}</b>.",
            ),
            bullet("Acquire the historical cutoff, markets, trades and market candlesticks; merge historical and live tiers without duplicates."),
            bullet("Retain event/series/market identity, open/close/settlement time, bid/ask OHLC, trade-price OHLC, volume, open interest, settlement result and lifecycle state."),
            bullet("Model fees, spread, fill probability and paperability separately. A price series alone is not execution evidence."),
            callout(
                f"Official references: {link('Kalshi historical data overview', 'https://docs.kalshi.com/getting_started/historical_data')}, {link('historical trades', 'https://docs.kalshi.com/api-reference/historical/get-historical-trades')} and {link('historical candlesticks', 'https://docs.kalshi.com/api-reference/historical/get-historical-market-candlesticks')}.",
                background=PALE_GREEN,
            ),
            p("Polymarket", "h2"),
            p(
                f"Qadam currently holds {int(poly.get('record_count') or 0):,} records across {int(poly.get('unique_counts', {}).get('market_id') or 0)} markets and {int(poly.get('unique_counts', {}).get('token_id') or 0)} tokens. Direct-instrument state: <b>{poly.get('direct_instrument_reason', 'incomplete')}</b>.",
            ),
            bullet("Acquire market, condition and token identities together with price history, trades, spread/liquidity observations, lifecycle, resolution and settlement."),
            bullet("Preserve outcome-token mapping and availability timestamps. Resolution values must never appear in pre-resolution features."),
            bullet("Treat Polymarket as a research signal until legal venue, execution and paperability review explicitly permits more."),
            callout(
                f"Official references: {link('Polymarket API introduction', 'https://docs.polymarket.com/api-reference/introduction')}, {link('batch price history', 'https://docs.polymarket.com/api-reference/markets/get-batch-prices-history')} and {link('CLOB orderbook overview', 'https://docs.polymarket.com/trading/orderbook')}.",
                background=PALE_GREEN,
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("6. Secondary Archive Opportunities", "h1"),
            p(
                "These sources can broaden Qadam's world model, but should be acquired only where an exact publication clock and written retention terms exist. A wider source count is not automatically a stronger signal set.",
            ),
            data_table(
                ["Programme", "Sources", "Minimum useful history", "Decision rule"],
                [
                    ["Macro vintages", "FRED/ALFRED, BLS, ECB, BIS, UN Comtrade", "Release vintage, originally published value, revision sequence, availability timestamp and calendar.", "Prefer official vintage APIs. Exclude revised-only series from point-in-time features."],
                    ["Conflict and disruption", "ACLED, UCDP, GDELT, NASA FIRMS", "Event identity, first-public timestamp, location, severity and subsequent correction lineage.", "Use only under explicit archive and retention rights. Never use later-coded severity early."],
                    ["Physical-world operations", "AIS/shipping, aviation, GPS jamming, IODA, ArcGIS/USACE, satellite/TLE", "Timestamped observations with coverage/outage metadata and provider availability time.", "Acquire only where the archive is stable enough to distinguish missing signal from missing coverage."],
                    ["Technical confirmation", "Bookmap, TradingView, order-flow providers", "Official exported bars, alerts or order-flow state with exact timestamps and symbol mapping.", "Supplemental confirmation only; do not scrape or treat local fixtures as provider-backed."],
                    ["Narrative history", "Reddit, RSS, Telegram, X", "Terms-compliant posts/messages with publication time, edits/deletions and stable source identity.", "Use as noisy narrative context; require corroboration and strong multiple-testing controls."],
                ],
                [34 * mm, 41 * mm, 56 * mm, 35 * mm],
            ),
            p("Recommended research programmes after ingestion", "h2"),
            bullet("Prediction-market disagreement preceding ETF or futures repricing."),
            bullet("STOCK Act public disclosures preceding defence or semiconductor basket movement."),
            bullet("Unusual Whales flow as confirmation that strengthens or rejects an existing macro signal."),
            bullet("For each programme, freeze the economic mechanism, instrument, horizon, costs, baseline and failure condition before testing."),
            PageBreak(),
        ]
    )

    source_rows: list[list[str]] = []
    for row in rows:
        source_rows.append(
            [
                str(row.get("source_name") or row.get("source_key") or "Unknown"),
                str(row.get("source_category") or "unknown").replace("_", " ").title(),
                str(row.get("status") or "unknown").replace("_", " "),
                str(row.get("classification_reason") or "No classification recorded."),
                _source_action(row),
            ]
        )
    source_headers = ["Source", "Category", "Current state", "Why", "Next action"]
    source_widths = [35 * mm, 27 * mm, 24 * mm, 45 * mm, 35 * mm]
    source_chunks = [source_rows[index : index + 14] for index in range(0, len(source_rows), 14)]
    for index, chunk in enumerate(source_chunks):
        if index == 0:
            story.extend(
                [
                    p("7. Entire 41-Source Acquisition Register", "h1"),
                    p(
                        "This register reflects the frozen historical-provider review. 'Forward only' means Qadam should capture new observations from now; 'excluded' means the current provider, terms or independent history is insufficient. It does not mean the source is useless forever.",
                    ),
                ]
            )
        else:
            story.append(p(f"7. Acquisition Register - continued ({index + 1} of {len(source_chunks)})", "h1"))
        story.append(
            data_table(
                source_headers,
                chunk,
                source_widths,
                font_size=7.2,
            )
        )
        story.append(PageBreak())

    story.extend(
        [
            p("8. Ingestion Acceptance Checklist", "h1"),
            p("A dataset should not enter Qadam's historical score-label plane until every applicable item below passes.", "body"),
            p("Provenance and rights", "h2"),
            bullet("Official provider, reviewed interface, private-research rights, retention rights and any redistribution restriction are recorded."),
            bullet("Raw payload or export, checksum, request parameters, provider cursor, acquisition time, parser version and immutable source URL are retained."),
            p("Point-in-time safety", "h2"),
            bullet("Event time, first-public time, Qadam availability time, revision time and market calendar are distinct fields."),
            bullet("Resolution, amendments, end-of-day totals, future open interest and revised macro values cannot leak backward."),
            bullet("A shuffled control and a time-shifted control remain non-predictive."),
            p("Identity and coverage", "h2"),
            bullet("Instrument, contract, token, option and filer identities resolve to stable canonical IDs with explicit unmapped states."),
            bullet("Coverage gaps, outages, pre-inception periods, closed markets and expired contracts receive typed reasons rather than zero-filled values."),
            p("Research admission", "h2"),
            bullet("The economic mechanism and expected horizon are pre-registered before testing."),
            bullet("Walk-forward and untouched holdouts include spread, slippage, fees, delay and proxy basis risk."),
            bullet("Multiple-testing and false-discovery controls cover the full search, not only the best result."),
            bullet("New evidence may propose changes to strategies. It cannot silently alter risk limits, create authority or bypass Akber's 6-Stage Filter and PaperOps."),
            callout(
                "<b>Most intelligent use of the completed backtest.</b> Freeze the platform, run the three focused programmes, collect 60-90 real market days of forward evidence, reject weak hypotheses quickly, and promote only net-of-cost holdout results that continue to work after the rules are frozen.",
                background=PALE_GOLD,
            ),
            PageBreak(),
            p("9. Operator Procurement Worksheet", "h1"),
            data_table(
                ["Dataset", "Operator request", "Evidence to obtain before import", "Ready when"],
                [
                    ["Unusual Whales", "Ask for private-research historical export and quote covering Qadam's 19 instruments.", "Field dictionary, date range, granularity, corrections, licensing, cost and sample file.", "Sample passes timestamp, identity, checksum and shuffled-control probes."],
                    ["House STOCK Act", "Download annual indexes and every linked PTR/amendment needed for the chosen date range.", "Official document URL, public availability, document checksum and transaction rows.", "Parser reproduces a reviewed sample and never invents exact notionals."],
                    ["Senate STOCK Act", "Acquire terms-compliant reports through the official disclosure system.", "Search/download receipt, report identity, public availability and transaction rows.", "House and Senate schemas reconcile without erasing chamber-specific provenance."],
                    ["Kalshi", "Backfill historical markets, trades and candlesticks for mapped event families.", "Cutoff receipts, pagination logs, rate-limit state, market lifecycle and fee assumptions.", "Historical and live tiers merge idempotently with no resolution leakage."],
                    ["Polymarket", "Backfill token price history and available CLOB/trade/liquidity context.", "Market-condition-token map, lifecycle, availability timestamps and terms record.", "Every price maps to the correct outcome token and pre-resolution clock."],
                    ["Optional archives", "Request only the sources tied to a pre-registered mechanism.", "Written rights, exact publication clock, sample export and cost ceiling.", "Expected information gain exceeds acquisition and engineering cost."],
                ],
                [31 * mm, 48 * mm, 52 * mm, 35 * mm],
            ),
            Spacer(1, 10 * mm),
            callout(
                "This brief is an acquisition map, not investment advice and not permission to trade. Qadam remains paper-only. Provider terms and data availability can change; verify them again immediately before acquisition.",
                background=PALE,
            ),
        ]
    )

    doc.build(story, onFirstPage=_page_header_footer, onLaterPages=_page_header_footer)
    return OUTPUT


def main() -> int:
    path = build_pdf()
    print(f"qadam_missing_backtesting_data_pdf={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
