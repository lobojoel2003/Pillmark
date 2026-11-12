#!/usr/bin/env python3
"""Pillmark release versioning.

One version number is shared by the API package, the web app, the Docker images
and the git tag. ``VERSION`` is the source of truth; this script keeps every other
place in step and pulls release notes out of ``CHANGELOG.md``.

    python scripts/version.py show              # print the current version
    python scripts/version.py check             # every file agrees (CI runs this)
    python scripts/version.py check --tag v1.2.3  # ... and matches a release tag
    python scripts/version.py bump patch        # 1.2.3 -> 1.2.4 (also minor, major, X.Y.Z)
    python scripts/version.py notes [1.2.3]     # release notes for a version

Build numbers are not stored in files: CI passes its run number to the images and
artifacts (PILLMARK_BUILD), so every build of a version is traceable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
CHANGELOG = ROOT / "CHANGELOG.md"
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
)

# (file, regex with one group around the version, replacement template)
TARGETS: list[tuple[Path, str, str]] = [
    (ROOT / "api/pyproject.toml", r'(?m)^version = "([^"]+)"', 'version = "{v}"'),
    (ROOT / "api/src/pillmark/__init__.py", r'(?m)^__version__ = "([^"]+)"', '__version__ = "{v}"'),
]
PACKAGE_JSON = ROOT / "web/package.json"
PACKAGE_LOCK = ROOT / "web/package-lock.json"


def read_version() -> str:
    version = VERSION_FILE.read_text().strip()
    if not SEMVER.match(version):
        sys.exit(f"VERSION is not semantic versioning: {version!r}")
    return version


def current_versions() -> dict[str, str]:
    found = {"VERSION": read_version()}
    for path, pattern, _ in TARGETS:
        match = re.search(pattern, path.read_text())
        found[str(path.relative_to(ROOT))] = match.group(1) if match else "<missing>"
    found["web/package.json"] = json.loads(PACKAGE_JSON.read_text())["version"]
    if PACKAGE_LOCK.exists():
        lock = json.loads(PACKAGE_LOCK.read_text())
        found["web/package-lock.json"] = lock.get("version", "<missing>")
        found["web/package-lock.json (root package)"] = (
            lock.get("packages", {}).get("", {}).get("version", "<missing>")
        )
    return found


def changelog_section(version: str) -> str | None:
    text = CHANGELOG.read_text()
    match = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]: |\Z)", text, re.S | re.M
    )
    return match.group(1).strip() if match else None


def cmd_show(_: argparse.Namespace) -> int:
    print(read_version())
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    versions = current_versions()
    expected = versions["VERSION"]
    problems = [f"{name} has {v}, expected {expected}" for name, v in versions.items() if v != expected]
    if changelog_section(expected) is None:
        problems.append(f"CHANGELOG.md has no section for [{expected}]")
    if args.tag and args.tag.removeprefix("v") != expected:
        problems.append(f"tag {args.tag} does not match VERSION {expected}")
    if problems:
        print("Version check failed:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    print(f"All versions agree: {expected}")
    return 0


def next_version(current: str, part: str) -> str:
    if SEMVER.match(part):
        return part
    major, minor, patch = (int(x) for x in SEMVER.match(current).groups()[:3])  # type: ignore[union-attr]
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    sys.exit(f"bump expects major, minor, patch or X.Y.Z, got {part!r}")


def cmd_bump(args: argparse.Namespace) -> int:
    old = read_version()
    new = next_version(old, args.part)
    VERSION_FILE.write_text(new + "\n")
    for path, pattern, template in TARGETS:
        text = path.read_text()
        path.write_text(re.sub(pattern, template.format(v=new), text, count=1))
    for path in (PACKAGE_JSON, PACKAGE_LOCK):
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        data["version"] = new
        if path is PACKAGE_LOCK and "" in data.get("packages", {}):
            data["packages"][""]["version"] = new
        path.write_text(json.dumps(data, indent="\t" if path is PACKAGE_JSON else 2) + "\n")

    text = CHANGELOG.read_text()
    today = datetime.now(UTC).date().isoformat()
    if f"## [{new}]" not in text:
        text = text.replace("## [Unreleased]", f"## [Unreleased]\n\n## [{new}] - {today}", 1)
        repo = "https://github.com/lobojoel2003/Pillmark"
        text = re.sub(
            r"(?m)^\[Unreleased\]: .*$",
            f"[Unreleased]: {repo}/compare/v{new}...HEAD\n[{new}]: {repo}/compare/v{old}...v{new}",
            text,
            count=1,
        )
        CHANGELOG.write_text(text)
    print(f"{old} -> {new}. Next: edit CHANGELOG.md, commit, then `git tag v{new} && git push --tags`.")
    return 0


def cmd_notes(args: argparse.Namespace) -> int:
    version = args.version or read_version()
    section = changelog_section(version)
    if section is None:
        print(f"CHANGELOG.md has no section for [{version}]", file=sys.stderr)
        return 1
    print(section)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show").set_defaults(func=cmd_show)
    check = sub.add_parser("check")
    check.add_argument("--tag", help="release tag to compare, e.g. v1.2.3")
    check.set_defaults(func=cmd_check)
    bump = sub.add_parser("bump")
    bump.add_argument("part", help="major, minor, patch or an explicit X.Y.Z")
    bump.set_defaults(func=cmd_bump)
    notes = sub.add_parser("notes")
    notes.add_argument("version", nargs="?")
    notes.set_defaults(func=cmd_notes)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
