"""External-comparison evidence is archived, verified, and offline-only."""
import hashlib
import json
from datetime import datetime, timezone

from unidesk.momentum.validation.bananapatterns import archive_snapshot_bytes


UTC = timezone.utc


def test_archived_snapshot_keeps_exact_bytes_and_a_reproducible_manifest(tmp_path):
    payload = b'{"asOf":"2026-08-28","stocks":[{"sym":"DEMO"}]}'
    retrieved_at = datetime(2026, 8, 29, 18, 0, tzinfo=UTC)

    evidence = archive_snapshot_bytes(
        payload,
        root=tmp_path,
        source_url="https://bananapatterns.com/static/data/pub/universe.json",
        retrieved_at=retrieved_at,
    )

    assert evidence.snapshot_path.read_bytes() == payload
    manifest = json.loads(evidence.manifest_path.read_text(encoding="utf-8"))
    assert manifest["sha256"] == hashlib.sha256(payload).hexdigest()
    assert manifest["source_as_of"] == "2026-08-28"
    assert manifest["retrieved_at"] == retrieved_at.isoformat()
    assert manifest["runtime_use"] == "offline_comparison_only"
