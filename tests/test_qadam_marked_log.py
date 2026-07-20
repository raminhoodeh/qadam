from orchestrator.qadam_marked_log import upsert_marked_section


def test_upsert_marked_section_preserves_later_sections() -> None:
    existing = """# Log

<!-- phase_1 -->
## Phase 1

Old

<!-- phase_2 -->
## Phase 2

Keep me
"""

    updated = upsert_marked_section(
        existing,
        "<!-- phase_1 -->",
        "<!-- phase_1 -->\n## Phase 1\n\nNew",
    )

    assert updated.count("<!-- phase_1 -->") == 1
    assert "New" in updated
    assert "Old" not in updated
    assert "<!-- phase_2 -->\n## Phase 2\n\nKeep me" in updated


def test_upsert_marked_section_appends_absent_marker() -> None:
    updated = upsert_marked_section(
        "# Log\n",
        "<!-- phase_1 -->",
        "<!-- phase_1 -->\n## Phase 1",
    )

    assert updated == "# Log\n\n<!-- phase_1 -->\n## Phase 1\n"
