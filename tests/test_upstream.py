"""Check provenance of optional fetched specifications, without shipping their text."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest


def test_fetched_specifications_match_the_manifest() -> None:
    folder = os.environ.get("KEYEDLOCK_UPSTREAM")
    if folder is None:
        pytest.skip("set KEYEDLOCK_UPSTREAM to the fetched specifications directory")
    manifest = Path(__file__).parent / "upstream/MANIFEST.json"
    for source in json.loads(manifest.read_text(encoding="utf-8")):
        data = (Path(folder) / source["file"]).read_bytes()
        assert len(data) == source["size"]
        assert hashlib.sha256(data).hexdigest() == source["sha256"]
