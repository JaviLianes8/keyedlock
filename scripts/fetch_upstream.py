"""Fetch the pinned Python documentation into a caller-selected scratch directory."""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path


def main() -> None:
    manifest = Path(__file__).resolve().parents[1] / "tests/upstream/MANIFEST.json"
    destination = Path(sys.argv[1]).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for source in json.loads(manifest.read_text(encoding="utf-8")):
        with urllib.request.urlopen(source["url"], timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError("upstream content changed")
        (destination / source["file"]).write_bytes(data)
        print(source["file"])


if __name__ == "__main__":
    main()
