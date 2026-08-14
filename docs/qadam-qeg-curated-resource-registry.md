# Qadam QEG Curated Resource Registry

**Registry version:** 2026-08-12

This document explains how the Qadam Evidence Graph classifies external
references. The machine-readable current registry is
`data/runtime/qadam_qeg_curated_resource_registry.json`.

References are research inputs, not market evidence. Listing a URL does not
verify its claims, satisfy source quorum, create a pattern, admit a strategy,
approve risk or permit a paper order. Full-text collection requires a separate
terms, provenance and relevance review.

## Registry Groups

| Group | Meaning | Permitted use |
| --- | --- | --- |
| **Primary references** | Official provider pages, repositories, papers or institutional sources that may be suitable for direct verification. | Create a verification task and compare the claim with current primary evidence. |
| **Implementation references** | Technical material that may inform architecture, testing or tooling. | Inspire a bounded implementation proposal; never inherit performance claims. |
| **Research leads** | Vendor, marketing, social or anecdotal material that may contain an idea worth testing. | Form a falsifiable research question only. |
| **Archived or superseded** | Material whose claim is rejected, out of scope or no longer describes current Qadam. | Historical context and duplicate avoidance only. |

## Current Intake State

The current attachment-backed registry contains 140 unique references. They
remain metadata-only and unreviewed until an explicit verification workflow
changes their state. The live JSON registry supplies the current group counts,
hosts, collection state and verification state; this document deliberately does
not duplicate that mutable inventory.

## Promotion Rule

A reference can influence Qadam only through the normal evidence lifecycle:

```text
Reference -> atomic claim -> primary verification -> point-in-time evidence
-> falsifiable hypothesis -> preregistered test -> governed result
```

The reference namespace is isolated from Qadam's provider-backed market
evidence namespace. A reference or claim cannot satisfy source quorum alone,
become a current catalyst by assertion, grant proof credit or reach PaperOps.
