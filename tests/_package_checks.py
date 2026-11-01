"""Inspect the wheel and source archive used by the external consumer test."""

from __future__ import annotations

import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path


def inspect_distributions(dist: Path) -> None:
    (wheel,) = dist.glob("*.whl")
    (sdist,) = dist.glob("*.tar.gz")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert "keyedlock/py.typed" in names
        assert "keyedlock/__init__.py" in names
        assert any(name.endswith("/licenses/LICENSE") for name in names)
        assert all(name.startswith(("keyedlock/", "keyedlock-1.0.0.dist-info/")) for name in names)
        assert not any(name.endswith("entry_points.txt") for name in names)
        metadata = BytesParser().parsebytes(archive.read("keyedlock-1.0.0.dist-info/METADATA"))
        assert metadata["Version"] == "1.0.0"
        assert metadata["Requires-Python"] == ">=3.10"
        assert metadata["License-Expression"] == "MIT"
        assert "Development Status :: 5 - Production/Stable" in metadata.get_all("Classifier", [])
        assert all(
            'extra == "dev"' in dep.replace("'", '"')
            for dep in metadata.get_all("Requires-Dist", [])
        )
        assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
        for version in ("3.10", "3.11", "3.12", "3.13", "3.14"):
            assert f"Programming Language :: Python :: {version}" in metadata.get_all(
                "Classifier", []
            )
        for label in ("Homepage", "Source", "Issues", "Changelog"):
            assert any(
                url.startswith(label + ", https://") for url in metadata.get_all("Project-URL", [])
            )
    with tarfile.open(sdist) as archive:
        names = [name.partition("/")[2] for name in archive.getnames()]
        for required in (
            "LICENSE",
            "README.md",
            "GUIDE.md",
            "CHANGELOG.md",
            "src/keyedlock/py.typed",
        ):
            assert required in names
        assert "tests/upstream/MANIFEST.json" in names
        assert "scripts/fetch_upstream.py" in names
        assert not any("CERT-" in name or "IMPROVEMENTS" in name for name in names)
    assert not any(
        "__pycache__" in name or "scratch" in name or name.endswith(".pyc") for name in names
    )
