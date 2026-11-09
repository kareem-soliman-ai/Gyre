"""Keep the five-minute path and local documentation graph executable."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _markdown_surfaces() -> list[Path]:
    surfaces = [ROOT / "README.md", ROOT / "CONTRIBUTING.md"]
    surfaces.extend((ROOT / "docs").glob("*.md"))
    surfaces.extend((ROOT / "loops").glob("*.md"))
    surfaces.append(ROOT / "experiments" / "INDEX.md")
    surfaces.append(ROOT / "scripts" / "README.md")
    surfaces.append(ROOT / "archive" / "INDEX.md")
    surfaces.append(ROOT / "videos" / "README.md")
    surfaces.append(ROOT / "videos" / "notebooklm" / "README.md")
    surfaces.append(ROOT / "videos" / "notebooklm" / "SOURCE_MANIFEST.md")
    surfaces.extend((ROOT / "videos" / "explainers").glob("*.md"))
    surfaces.extend((ROOT / "videos" / "promos").rglob("*.md"))
    return surfaces


def test_readme_is_a_compact_router_not_the_research_archive():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert len(readme.splitlines()) <= 180
    assert "python scripts/alien_factory.py" in readme
    assert "docs/START_HERE.md" in readme
    assert "docs/LESSONS.md" in readme
    assert "experiments/INDEX.md" in readme


def test_every_local_markdown_link_in_live_navigation_resolves():
    broken = []
    for source in _markdown_surfaces():
        text = source.read_text(encoding="utf-8")
        for raw_target in LOCAL_LINK.findall(text):
            target = raw_target.strip().strip("<>")
            if (
                not target
                or target.startswith(("http://", "https://", "mailto:", "#"))
            ):
                continue
            relative = target.split("#", 1)[0]
            if not relative:
                continue
            resolved = (source.parent / relative).resolve()
            if not resolved.exists():
                broken.append(f"{source.relative_to(ROOT)} -> {target}")
    assert broken == []


def test_five_minute_demo_runs_without_network_or_input():
    completed = subprocess.run(
        [sys.executable, "scripts/alien_factory.py", "--demo", "--seed", "419"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr
    assert "FACTORY KESTREL" in completed.stdout
    assert "STORM-LOCK RECEIPT" in completed.stdout
    assert "stability score:" in completed.stdout


def test_public_archive_index_does_not_link_internal_snapshots():
    index = ROOT / "archive" / "INDEX.md"
    assert index.is_file()
    text = index.read_text(encoding="utf-8")
    assert "No retired public artefacts" in text
    assert "README_pre-expedition" not in text
