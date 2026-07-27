from __future__ import annotations

from orchestrator.qadam_artifact_generations import (
    ArtifactGenerationStore,
    bootstrap_registered_generations,
)


def test_current_pointer_advances_only_to_complete_generation(tmp_path) -> None:
    source = tmp_path / "source.json"
    source.write_text('{"value":1}\n', encoding="utf-8")
    store = ArtifactGenerationStore(tmp_path, "score_plane")
    first = store.publish_files({"score.json": source}, producer="test")
    source.write_text('{"value":2}\n', encoding="utf-8")
    second = store.publish_files({"score.json": source}, producer="test")
    assert first.generation_id != second.generation_id
    assert store.resolve_current().generation_id == second.generation_id
    store.validate_reference(first)


def test_incomplete_staging_directory_is_never_current(tmp_path) -> None:
    source = tmp_path / "source.json"
    source.write_text('{"value":1}\n', encoding="utf-8")
    store = ArtifactGenerationStore(tmp_path, "label_plane")
    complete = store.publish_files({"labels.json": source}, producer="test")
    interrupted = store.staging / "interrupted"
    interrupted.mkdir()
    (interrupted / "labels.json").write_text("partial", encoding="utf-8")
    assert store.resolve_current().generation_id == complete.generation_id


def test_leased_generation_is_not_collected(tmp_path) -> None:
    source = tmp_path / "source.json"
    store = ArtifactGenerationStore(tmp_path, "edge_registry")
    references = []
    for value in range(5):
        source.write_text(f'{{"value":{value}}}\n', encoding="utf-8")
        references.append(store.publish_files({"edge.json": source}, producer="test"))
    with store.lease_current() as current:
        removed = store.collect(retain=3)
        assert current.generation_id not in removed
    assert store.resolve_current().generation_id == references[-1].generation_id


def test_bootstrap_registered_generations_preserves_bytes(tmp_path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_bytes(b'{"value":1}\n')
    second.write_bytes(b'{"value":2}\n')
    records = [
        {
            "artifact": first.name,
            "logical_resource": "source_lake",
            "producer": "source_ingestion",
        },
        {
            "artifact": second.name,
            "logical_resource": "price_lake",
            "producer": "market_price_refresh",
        },
    ]
    before = {path.name: path.read_bytes() for path in (first, second)}
    result = bootstrap_registered_generations(tmp_path, records)
    assert result["status"] == "passed"
    assert result["artifact_count"] == 2
    assert result["broker_write_count"] == 0
    assert {path.name: path.read_bytes() for path in (first, second)} == before
    assert ArtifactGenerationStore(tmp_path, "source_lake").resolve_current().manifest[
        "file_count"
    ] == 1
    assert ArtifactGenerationStore(tmp_path, "price_lake").resolve_current().manifest[
        "file_count"
    ] == 1
