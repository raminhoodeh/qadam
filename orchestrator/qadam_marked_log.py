"""Safe updates for generated Markdown sections identified by HTML markers."""

from __future__ import annotations


def upsert_marked_section(existing: str, marker: str, entry: str) -> str:
    """Replace one marked section without truncating sections that follow it."""

    normalized_entry = entry.strip()
    if marker not in existing:
        prefix = existing.rstrip()
        return f"{prefix}\n\n{normalized_entry}\n" if prefix else f"{normalized_entry}\n"

    start = existing.index(marker)
    next_marker = existing.find("\n<!-- ", start + len(marker))
    prefix = existing[:start].rstrip()
    suffix = existing[next_marker + 1 :].strip() if next_marker >= 0 else ""
    sections = [section for section in (prefix, normalized_entry, suffix) if section]
    return "\n\n".join(sections) + "\n"


__all__ = ["upsert_marked_section"]
