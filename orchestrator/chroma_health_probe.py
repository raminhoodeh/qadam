"""Isolated Chroma health probe used by cockpit publication."""

from __future__ import annotations

import json
import sys

from orchestrator.chroma_store import KNOWLEDGE_COLLECTION


def main() -> int:
    if len(sys.argv) != 2:
        return 2

    import chromadb

    persist_dir = sys.argv[1]
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(
        KNOWLEDGE_COLLECTION,
        metadata={
            "owner": "qadam",
            "phase": "foundation",
            "mode": "local_embedded",
        },
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "backend": "embedded_chroma",
                "collection": KNOWLEDGE_COLLECTION,
                "path": persist_dir,
                "count": collection.count(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
