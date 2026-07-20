#!/usr/bin/env python3
"""Bind published Qadam documentation pages to their canonical Markdown source.

The visual HTML remains deliberately hand-shaped for the public site. This
script records the exact canonical source hash in every published materialized
copy. Before it writes metadata, the structured semantic parity gate must pass;
afterward, any Markdown change fails closed until the public page is reviewed
and synchronized again.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "docs" / "qadam-documentation-contract.json"
META_NAMES = (
    "qadam-canonical-source",
    "qadam-canonical-sha256",
    "qadam-document-version",
    "qadam-reviewed-on",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_metadata(
    source_rel: str,
    document_version: str,
    reviewed_on: str,
) -> dict[str, str]:
    source_path = ROOT / source_rel
    if not source_path.is_file():
        raise FileNotFoundError(f"canonical documentation source is missing: {source_rel}")
    return {
        "qadam-canonical-source": source_rel,
        "qadam-canonical-sha256": sha256(source_path),
        "qadam-document-version": document_version,
        "qadam-reviewed-on": reviewed_on,
    }


def current_metadata(html: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in META_NAMES:
        matches = re.findall(
            rf'<meta\s+name=["\']{re.escape(name)}["\']\s+content=["\']([^"\']*)["\']\s*/?>',
            html,
            flags=re.IGNORECASE,
        )
        if len(matches) == 1:
            result[name] = matches[0]
        elif len(matches) > 1:
            result[name] = "__duplicate_metadata__"
    return result


def render_metadata(metadata: dict[str, str]) -> str:
    return "\n".join(
        f'    <meta name="{name}" content="{metadata[name]}">' for name in META_NAMES
    )


def synchronized_html(html: str, metadata: dict[str, str]) -> str:
    cleaned = html
    for name in META_NAMES:
        cleaned = re.sub(
            rf'^\s*<meta\s+name=["\']{re.escape(name)}["\']\s+content=["\'][^"\']*["\']\s*/?>\s*\n?',
            "",
            cleaned,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    charset = re.search(r'^\s*<meta\s+charset=[^>]+>\s*$', cleaned, flags=re.IGNORECASE | re.MULTILINE)
    if not charset:
        raise ValueError("published documentation page has no charset meta tag")
    insertion = f"{charset.group(0)}\n{render_metadata(metadata)}"
    return cleaned[: charset.start()] + insertion + cleaned[charset.end() :]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of updating when a published copy is not bound to the current source hash",
    )
    args = parser.parse_args()

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    reviewed_on = str(contract["reviewed_on"])
    failures: list[str] = []
    updated: list[str] = []

    content_check = subprocess.run(
        ["node", "scripts/check_qadam_documentation_parity.js", "--content-only"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if content_check.returncode != 0:
        print("qadam_documentation_metadata=failed")
        print("published documentation failed semantic parity before metadata synchronization")
        print((content_check.stdout + content_check.stderr).strip())
        return 1

    for document_id, source_rel in contract["canonical_sources"].items():
        document_version = str(contract["document_versions"][document_id])
        metadata = expected_metadata(source_rel, document_version, reviewed_on)
        for target_rel in contract["published_materializations"][document_id]:
            target = ROOT / target_rel
            if not target.is_file():
                failures.append(f"missing published documentation copy: {target_rel}")
                continue
            html = target.read_text(encoding="utf-8")
            if current_metadata(html) == metadata:
                continue
            if args.check:
                failures.append(
                    f"{target_rel} is not synchronized with {source_rel}; "
                    "run .venv/bin/python scripts/sync_qadam_documentation_metadata.py"
                )
                continue
            target.write_text(synchronized_html(html, metadata), encoding="utf-8")
            updated.append(target_rel)

    if failures:
        print("qadam_documentation_metadata=failed")
        for failure in failures:
            print(failure)
        return 1

    print("qadam_documentation_metadata=ok")
    print(f"updated_count={len(updated)}")
    for target_rel in updated:
        print(f"updated={target_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
