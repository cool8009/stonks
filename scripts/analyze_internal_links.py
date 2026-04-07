from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_TOP_LEVEL = {"CKA-Notes"}
EXCLUDED_PARTS = {".git", ".obsidian", "scripts", "__pycache__"}
EXCLUDED_FILES = {
    "repo_audit_report.md",
    "final_repo_update_report.md",
    "context_refresh_log.md",
}
SKIPPED_NOTE_NAMES = {"Welcome.md"}
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")


@dataclass
class LinkStats:
    resolved: int = 0
    unresolved: int = 0
    ambiguous: int = 0


def safe_display(value: str) -> str:
    return value.encode("unicode_escape").decode("ascii")


def in_scope(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT)
    if not rel.parts:
        return False
    if rel.name in EXCLUDED_FILES or rel.name in SKIPPED_NOTE_NAMES:
        return False
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    if rel.parts[0] in EXCLUDED_TOP_LEVEL:
        return False
    return True


def markdown_notes() -> list[Path]:
    return sorted(
        path
        for path in REPO_ROOT.rglob("*.md")
        if path.is_file() and in_scope(path)
    )


def build_stem_index(notes: list[Path]) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = defaultdict(list)
    for note in notes:
        index[note.stem].append(note)
    return index


def resolve_target(raw_target: str, stem_index: dict[str, list[Path]]) -> tuple[str, Path | None]:
    target = raw_target.split("|", 1)[0].strip()
    if not target:
        return ("unresolved", None)

    if "/" in target or "\\" in target:
        normalized = target.replace("\\", "/")
        candidate = REPO_ROOT / (normalized + ("" if normalized.endswith(".md") else ".md"))
        if candidate.exists():
            return ("resolved", candidate)
        return ("unresolved", None)

    matches = stem_index.get(target, [])
    if len(matches) == 1:
        return ("resolved", matches[0])
    if len(matches) > 1:
        return ("ambiguous", None)
    return ("unresolved", None)


def total_links(graph: dict[Path, set[Path]], inbound: dict[Path, set[Path]], note: Path) -> int:
    return len(graph[note]) + len(inbound[note])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze internal Obsidian wikilinks.")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="How many weak-note rows to print.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    notes = markdown_notes()
    stem_index = build_stem_index(notes)
    graph: dict[Path, set[Path]] = {note: set() for note in notes}
    inbound: dict[Path, set[Path]] = {note: set() for note in notes}
    stats = LinkStats()
    unresolved_samples: list[str] = []
    ambiguous_samples: list[str] = []

    for note in notes:
        text = note.read_text(encoding="utf-8")
        for match in WIKILINK_RE.finditer(text):
            raw_target = match.group(1)
            status, target_note = resolve_target(raw_target, stem_index)
            if status == "resolved" and target_note is not None:
                stats.resolved += 1
                graph[note].add(target_note)
                inbound[target_note].add(note)
            elif status == "ambiguous":
                stats.ambiguous += 1
                if len(ambiguous_samples) < 20:
                    ambiguous_samples.append(
                        f"{safe_display(note.relative_to(REPO_ROOT).as_posix())}: {safe_display(raw_target)}"
                    )
            else:
                stats.unresolved += 1
                if len(unresolved_samples) < 20:
                    unresolved_samples.append(
                        f"{safe_display(note.relative_to(REPO_ROOT).as_posix())}: {safe_display(raw_target)}"
                    )

    weak_notes = sorted(
        notes,
        key=lambda note: (total_links(graph, inbound, note), note.relative_to(REPO_ROOT).as_posix()),
    )

    print(f"notes scanned: {len(notes)}")
    print(f"wikilinks found: {stats.resolved + stats.unresolved + stats.ambiguous}")
    print(f"resolved wikilinks: {stats.resolved}")
    print(f"unresolved wikilinks: {stats.unresolved}")
    print(f"ambiguous wikilinks: {stats.ambiguous}")
    print("weak-note candidates:")
    for note in weak_notes[: args.limit]:
        print(
            f"- {safe_display(note.relative_to(REPO_ROOT).as_posix())} "
            f"(outbound={len(graph[note])}, inbound={len(inbound[note])}, total={total_links(graph, inbound, note)})"
        )

    if unresolved_samples:
        print("sample unresolved:")
        for sample in unresolved_samples:
            print(f"- {sample}")

    if ambiguous_samples:
        print("sample ambiguous:")
        for sample in ambiguous_samples:
            print(f"- {sample}")

    return 0 if stats.unresolved == 0 and stats.ambiguous == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
