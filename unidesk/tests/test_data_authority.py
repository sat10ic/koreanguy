from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from unidesk.checks.runner import CheckFailure, validate_data_authority


MANIFEST = Path(__file__).resolve().parents[1] / "design" / "DATA_AUTHORITY.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_current_data_authority_manifest_is_valid() -> None:
    stores, fields = validate_data_authority(_manifest())
    assert stores >= 20
    assert fields >= 12


def test_duplicate_field_authority_fails_closed() -> None:
    manifest = _manifest()
    manifest["field_authorities"].append(copy.deepcopy(manifest["field_authorities"][0]))
    with pytest.raises(CheckFailure, match="duplicate field authority"):
        validate_data_authority(manifest)


def test_quarantined_lifecycle_cannot_become_field_authority() -> None:
    manifest = _manifest()
    field = next(row for row in manifest["field_authorities"] if row["field"] == "trader_lifecycle")
    field["authority_store"] = "traderlog_legacy_lifecycle_quarantine"
    field["state"] = "accepted"
    with pytest.raises(CheckFailure, match="quarantined store cannot be an authority"):
        validate_data_authority(manifest)


def test_lifecycle_classification_cannot_be_omitted() -> None:
    manifest = _manifest()
    manifest["lifecycle_outputs"] = [
        row for row in manifest["lifecycle_outputs"] if row["classification"] != "quarantined"
    ]
    with pytest.raises(CheckFailure, match="must explicitly cover"):
        validate_data_authority(manifest)


def test_accepted_field_requires_accepted_store() -> None:
    manifest = _manifest()
    field = next(row for row in manifest["field_authorities"] if row["field"] == "intraday_quote_depth")
    field["state"] = "accepted"
    with pytest.raises(CheckFailure, match="accepted field points to provisional store"):
        validate_data_authority(manifest)


def test_classification_vocabulary_cannot_drift() -> None:
    manifest = _manifest()
    manifest["classifications"]["trusted"] = manifest["classifications"].pop("accepted")
    with pytest.raises(CheckFailure, match="exact allowed set"):
        validate_data_authority(manifest)
