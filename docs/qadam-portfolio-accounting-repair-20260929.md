# Portfolio accounting repair

## Confirmed defects

- The allocation pie normalized cash plus absolute short value. It therefore
  portrayed a liability as a positive investment and understated cash weight.
- Each mirror sync reset peak equity to the larger of current and initial
  equity. This understated drawdown in both reporting and portfolio risk.
- The chart imposed account-size padding, obscured small movements, overlapped
  endpoint labels, and did not distinguish recent history from inception return.
- Cross-artifact consistency checks did not independently test these semantics.
- The dashboard inferred missing exposure from equity minus cash, allowing a
  small asynchronous mark residual to hide otherwise-known signed net exposure.

## Repair contract

History is isolated by paper epoch, broker-account fingerprint, currency and
record origin. Future observations are excluded. Retained observations repair
the high-water mark; persisted peak and maximum drawdown survive retention and
restart. Zero equity means 100% drawdown, not missing history. Portfolio risk
uses the same historical calculation. Existing risk thresholds are unchanged.

Broker equity remains authoritative. Cash plus signed positions is reconciled
separately. Differences up to one cent match; a disclosed difference up to the
larger of USD 1 and one basis point of gross exposure is within mark tolerance.
A larger difference triggers one bounded account/positions re-read. If still
unresolved it blocks new-entry risk approval and degrades accounting health.
Separate read timestamps are recorded; timing is not asserted as the proven
cause of a difference. Exit processing and paper-only boundaries are unchanged.

Short or leveraged portfolios use a signed table rather than a normalized pie.
Cash can exceed 100% of equity or be negative. Gross and net exposure are
distinct. Short proceeds are not described as profit or available buying power.
Recent chart dates and zoomed scale are explicit; inception return is separate.

The reliability critic independently checks retained-history drawdown and the
stored reconciliation arithmetic. Failures request the existing singleton
operator's bounded GET-only broker mirror refresh and downstream publication,
not a second broker writer. Lifecycle polling alone is not an account refresh.
This allowlisted recovery can run after hours; normal price-refresh scheduling
and all execution session boundaries remain unchanged.

## Verification and release

The focused suite covers history isolation, decline/recovery, restart/retention,
zero/nonfinite values, longs/shorts/borrowing, bounded retry, risk vetoes, and
health-to-repair integration and GET-only after-hours recovery. Existing
Qiskit deprecation warnings remain unrelated. Renderer checks cover the full
canonical model, signed allocations, residual disclosure, and chart periods.

Frontend release: `qadam-dashboard-20260929-portfolio-accounting-v2`, commit
`62dfd1e2503beab0a5252bcc372b7009630c4f92`. Approved asset hashes remain enforced.

Release validation must observe a fresh mirror with accounting version 1,
run `scripts/check_dashboard_portfolio_consistency.py`, verify the reliability
critic and signed public bridge, pass mandatory deployment preflight, and
inspect production at desktop and mobile widths. A passing test suite alone is
not runtime sign-off. This repair makes no claim of guaranteed trades, profit,
complete historical drawdown beyond retained observations, or perpetual uptime.

Production preflight also exposed a stale source-acceptance assertion requiring
TradingView to remain sample-only. The aggregate gate now validates the same
truthful connection states as the adapter, forbids samples in canonical context,
and retains all no-quorum/no-execution/no-broker-write assertions. Live read-only
provider access is not trading authority. Tests cover every state and reject
contradictory connection flags, canonical sample leakage and authority changes.
