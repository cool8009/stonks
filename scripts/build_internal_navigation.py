from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_TOP_LEVEL = {"CKA-Notes"}
EXCLUDED_PARTS = {".git", ".obsidian", "scripts", "__pycache__"}
EXCLUDED_FILES = {
    "repo_audit_report.md",
    "final_repo_update_report.md",
    "context_refresh_log.md",
    "00 - מפת המסחר.md",
}
SKIPPED_NOTE_NAMES = {"Welcome.md"}
NAV_HEADING = "## קישורים פנימיים"


@dataclass(frozen=True)
class Module:
    section_index: int
    module_index: int
    section_dir: Path
    folder: Path
    section_hub: Path
    hub_note: Path
    notes: tuple[Path, ...]

    @property
    def title(self) -> str:
        return clean_label(self.folder.name)


def safe_display(value: str) -> str:
    return value.encode("unicode_escape").decode("ascii")


RELATED_MODULES = {
    (1, 1): [(3, 3), (2, 5)],
    (1, 2): [(3, 2), (3, 3)],
    (1, 3): [(3, 4), (2, 5)],
    (2, 1): [(2, 6), (2, 3)],
    (2, 2): [(3, 5), (2, 6)],
    (2, 3): [(2, 1), (2, 4), (2, 5)],
    (2, 4): [(3, 6), (2, 3)],
    (2, 5): [(1, 1), (3, 3)],
    (2, 6): [(2, 1), (2, 2), (3, 8)],
    (3, 1): [(2, 5), (3, 2)],
    (3, 2): [(1, 2), (3, 7)],
    (3, 3): [(1, 1), (2, 5), (3, 6)],
    (3, 4): [(1, 3)],
    (3, 5): [(2, 2), (2, 6)],
    (3, 6): [(3, 3), (2, 4)],
    (3, 7): [(3, 2)],
    (3, 8): [(2, 6)],
}


def clean_label(name: str) -> str:
    return re.sub(r"^\d+\s*-\s*", "", name).strip()


def natural_key(path: Path) -> tuple[int, str]:
    match = re.match(r"^(\d+)\s*-\s*(.*)$", path.stem)
    if match:
        return (int(match.group(1)), match.group(2))
    return (10_000, path.stem)


def natural_key_for_dir(path: Path) -> tuple[int, str]:
    match = re.match(r"^(\d+)\s*-\s*(.*)$", path.name)
    if match:
        return (int(match.group(1)), match.group(2))
    return (10_000, path.name)


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
        (
            path
            for path in REPO_ROOT.rglob("*.md")
            if path.is_file() and in_scope(path)
        ),
        key=lambda path: path.relative_to(REPO_ROOT).as_posix(),
    )


def existing_content_notes(notes: list[Path]) -> list[Path]:
    filtered: list[Path] = []
    for note in notes:
        if note.name.startswith("00 - מפת "):
            continue
        text = note.read_text(encoding="utf-8")
        if text.strip():
            filtered.append(note)
    return filtered


def note_ref(path: Path, stem_counts: dict[str, int], label: str | None = None) -> str:
    target = path.stem if stem_counts.get(path.stem, 0) == 1 else path.relative_to(REPO_ROOT).with_suffix("").as_posix()
    if label:
        return f"[[{target}|{label}]]"
    return f"[[{target}]]"


def build_modules(content_notes: list[Path]) -> list[Module]:
    by_section: dict[Path, list[Path]] = {}
    for note in content_notes:
        rel = note.relative_to(REPO_ROOT)
        section_dir = REPO_ROOT / rel.parts[0]
        by_section.setdefault(section_dir, []).append(note)

    modules: list[Module] = []
    sorted_sections = sorted(by_section, key=natural_key_for_dir)
    for section_index, section_dir in enumerate(sorted_sections, start=1):
        module_dirs = sorted(
            {
                note.parent
                for note in by_section[section_dir]
                if note.parent != section_dir
            },
            key=natural_key_for_dir,
        )
        section_hub = section_dir / f"00 - מפת {clean_label(section_dir.name)}.md"
        for module_index, folder in enumerate(module_dirs, start=1):
            notes_in_module = tuple(
                sorted(
                    (note for note in by_section[section_dir] if note.parent == folder),
                    key=natural_key,
                )
            )
            hub_note = folder / f"00 - מפת {clean_label(folder.name)}.md"
            modules.append(
                Module(
                    section_index=section_index,
                    module_index=module_index,
                    section_dir=section_dir,
                    folder=folder,
                    section_hub=section_hub,
                    hub_note=hub_note,
                    notes=notes_in_module,
                )
            )
    return modules


def build_stem_counts(paths: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in paths:
        counts[path.stem] = counts.get(path.stem, 0) + 1
    return counts


def module_lookup(modules: list[Module]) -> dict[tuple[int, int], Module]:
    return {(module.section_index, module.module_index): module for module in modules}


def related_modules_for(module: Module, lookup: dict[tuple[int, int], Module]) -> list[Module]:
    related = []
    for key in RELATED_MODULES.get((module.section_index, module.module_index), []):
        target = lookup.get(key)
        if target is not None:
            related.append(target)
    return related


def replace_nav_section(text: str, nav_block: str) -> str:
    body = text.rstrip()
    marker = f"\n{NAV_HEADING}\n"
    position = body.find(marker)
    if position != -1:
        body = body[:position].rstrip()
    elif body.startswith(f"{NAV_HEADING}\n"):
        body = ""

    if not body:
        return nav_block + "\n"
    return body + "\n\n" + nav_block + "\n"


def build_nav_block(
    module: Module,
    previous_note: Path | None,
    next_note: Path | None,
    related: list[Module],
    stem_counts: dict[str, int],
) -> str:
    nav_links = [note_ref(module.hub_note, stem_counts, "מפת הפרק")]
    if previous_note is not None:
        nav_links.append(note_ref(previous_note, stem_counts, "הקודם"))
    if next_note is not None:
        nav_links.append(note_ref(next_note, stem_counts, "הבא"))

    lines = [NAV_HEADING, "- ניווט בפרק: " + " | ".join(nav_links)]

    if related:
        lines.append(
            "- קשור במיוחד: "
            + ", ".join(
                note_ref(other.hub_note, stem_counts, other.title)
                for other in related
            )
        )

    lines.append(
        "- חזרה רחבה: "
        + note_ref(module.section_hub, stem_counts, clean_label(module.section_dir.name))
        + " | "
        + note_ref(REPO_ROOT / "00 - מפת המסחר.md", stem_counts, "מפת המסחר")
    )
    return "\n".join(lines)


def build_root_map(section_hubs: list[Path], stem_counts: dict[str, int]) -> str:
    lines = [
        "- המפה הזו מחברת בין שלושת חלקי הלימוד המרכזיים בוולט.",
        "- היא נוספה כדי לשפר ניווט בין נושאים בלי לשכתב את ההסברים המקוריים.",
        "",
        "## חלקי הלימוד",
    ]
    for section_hub in section_hubs:
        label = clean_label(section_hub.parent.name)
        lines.append(f"- {note_ref(section_hub, stem_counts, label)}")
    return "\n".join(lines) + "\n"


def build_section_hub(
    section_dir: Path,
    modules: list[Module],
    stem_counts: dict[str, int],
) -> str:
    lines = [
        f"- זו מפת הניווט של החלק \"{clean_label(section_dir.name)}\".",
        "- היא מרכזת את פרקי המשנה ואת הקשרים המרכזיים לכל פרק.",
        "",
        "## פרקי המשנה",
    ]
    for module in modules:
        lines.append(f"- {note_ref(module.hub_note, stem_counts, module.title)}")
    lines.extend(
        [
            "",
            "## חזרה למפה הראשית",
            f"- {note_ref(REPO_ROOT / '00 - מפת המסחר.md', stem_counts, 'מפת המסחר')}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_module_hub(
    module: Module,
    related: list[Module],
    stem_counts: dict[str, int],
) -> str:
    lines = [
        f"- זו מפת הניווט של הפרק \"{module.title}\".",
        "- היא שומרת על סדר הלימוד המקורי ומרכזת קפיצות שימושיות לפרקים קשורים.",
        "",
        "## סדר הקריאה",
    ]
    for note in module.notes:
        lines.append(f"- {note_ref(note, stem_counts, clean_label(note.stem))}")

    if related:
        lines.extend(["", "## פרקים קשורים במיוחד"])
        for other in related:
            lines.append(f"- {note_ref(other.hub_note, stem_counts, other.title)}")

    lines.extend(
        [
            "",
            "## חזרה לפרק העל",
            f"- {note_ref(module.section_hub, stem_counts, clean_label(module.section_dir.name))}",
            f"- {note_ref(REPO_ROOT / '00 - מפת המסחר.md', stem_counts, 'מפת המסחר')}",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create deterministic hub notes and internal navigation blocks."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write generated notes and navigation blocks to disk.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    notes = markdown_notes()
    content_notes = existing_content_notes(notes)
    modules = build_modules(content_notes)
    lookup = module_lookup(modules)

    generated_hubs = [REPO_ROOT / "00 - מפת המסחר.md"]
    generated_hubs.extend(sorted({module.section_hub for module in modules}))
    generated_hubs.extend(module.hub_note for module in modules)
    stem_counts = build_stem_counts(content_notes + generated_hubs)

    file_updates: list[tuple[Path, str]] = []

    section_hubs = sorted(
        {module.section_hub for module in modules},
        key=lambda path: natural_key_for_dir(path.parent),
    )
    file_updates.append((REPO_ROOT / "00 - מפת המסחר.md", build_root_map(section_hubs, stem_counts)))

    section_to_modules: dict[Path, list[Module]] = {}
    for module in modules:
        section_to_modules.setdefault(module.section_dir, []).append(module)

    for section_dir, section_modules in sorted(section_to_modules.items(), key=lambda item: natural_key_for_dir(item[0])):
        file_updates.append(
            (
                section_modules[0].section_hub,
                build_section_hub(section_dir, section_modules, stem_counts),
            )
        )

    for module in modules:
        related = related_modules_for(module, lookup)
        file_updates.append((module.hub_note, build_module_hub(module, related, stem_counts)))

    navigation_updates = 0
    skipped_empty = 0

    for module in modules:
        related = related_modules_for(module, lookup)
        for index, note in enumerate(module.notes):
            text = note.read_text(encoding="utf-8")
            if not text.strip():
                skipped_empty += 1
                continue

            previous_note = module.notes[index - 1] if index > 0 else None
            next_note = module.notes[index + 1] if index + 1 < len(module.notes) else None
            nav_block = build_nav_block(
                module=module,
                previous_note=previous_note,
                next_note=next_note,
                related=related,
                stem_counts=stem_counts,
            )
            new_text = replace_nav_section(text, nav_block)
            if new_text != text:
                navigation_updates += 1
                file_updates.append((note, new_text))

    print(f"mode: {'apply' if args.apply else 'dry-run'}")
    print(f"content notes considered: {len(content_notes)}")
    print(f"module hubs to manage: {len(modules)}")
    print(f"section hubs to manage: {len(section_hubs)}")
    print(f"navigation blocks to add/update: {navigation_updates}")
    print(f"empty notes skipped: {skipped_empty}")

    seen: set[Path] = set()
    for path, _ in file_updates[:25]:
        if path in seen:
            continue
        seen.add(path)
        print(f"- {safe_display(path.relative_to(REPO_ROOT).as_posix())}")

    if args.apply:
        written: set[Path] = set()
        for path, content in file_updates:
            if path in written:
                continue
            written.add(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
