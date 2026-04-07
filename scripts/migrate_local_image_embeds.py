from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote


REPO_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_TOP_LEVEL = {"CKA-Notes"}
EXCLUDED_PARTS = {".git", ".obsidian", "scripts", "__pycache__"}
EXCLUDED_FILES = {
    "repo_audit_report.md",
    "final_repo_update_report.md",
    "context_refresh_log.md",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
IMAGE_EMBED_RE = re.compile(r"!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


@dataclass
class TransformResult:
    note: Path
    changed: bool
    embed_count: int
    unresolved: list[str]
    validation_errors: list[str]
    preview_lines: list[str]
    text: str


def safe_display(value: str) -> str:
    return value.encode("unicode_escape").decode("ascii")


def in_scope(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT)
    if not rel.parts:
        return False
    if rel.name in EXCLUDED_FILES:
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


def image_files() -> list[Path]:
    return sorted(
        path
        for path in REPO_ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
        and in_scope(path)
    )


def build_image_index(images: list[Path]) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = defaultdict(list)
    for image in images:
        index[image.name.lower()].append(image)
    return index


def note_display_title(note: Path) -> str:
    stem = re.sub(r"^\d+\s*-\s*", "", note.stem).strip()
    return stem or note.stem


def clean_alt_text(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", lambda m: Path(m.group(1).split("|", 1)[0]).stem, text)
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", "", text)
    text = text.replace('"', "").replace("'", "").replace("`", "")
    text = text.replace("*", "").replace("#", "").replace("!", "")
    text = text.replace("|", " ")
    text = re.sub(r"^\s*[-*]\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip(" :-\t")
    return text


def descriptive_filename(stem: str) -> bool:
    lowered = stem.lower().strip()
    if lowered.startswith("pasted image"):
        return False
    if re.fullmatch(r"img[_-]?\d+", lowered):
        return False
    return True


def choose_alt_text(
    note: Path,
    lines: list[str],
    line_index: int,
    raw_target: str,
    text_without_embed: str,
    label_override: str | None,
) -> str:
    if label_override:
        cleaned = clean_alt_text(label_override)
        if cleaned:
            return cleaned

    filename_stem = Path(raw_target).stem
    if descriptive_filename(filename_stem):
        cleaned = clean_alt_text(filename_stem.replace("_", " ").replace("-", " "))
        if cleaned:
            return cleaned

    candidates = [text_without_embed]
    if line_index > 0:
        candidates.append(lines[line_index - 1])
    if line_index + 1 < len(lines):
        candidates.append(lines[line_index + 1])
    candidates.append(note_display_title(note))

    for candidate in candidates:
        cleaned = clean_alt_text(candidate)
        if 4 <= len(cleaned) <= 90:
            return cleaned

    return note_display_title(note)


def encode_relative_path(path: Path) -> str:
    return "/".join(quote(part) for part in path.parts)


def resolve_image_target(
    raw_target: str,
    all_images: list[Path],
    by_name: dict[str, list[Path]],
) -> list[Path]:
    normalized = raw_target.replace("\\", "/").strip()
    path_like = Path(normalized)

    if path_like.suffix:
        if "/" in normalized:
            lowered = normalized.lower()
            return [
                image
                for image in all_images
                if image.relative_to(REPO_ROOT).as_posix().lower().endswith(lowered)
            ]
        return by_name.get(path_like.name.lower(), [])

    stem = path_like.name.lower()
    return [image for image in all_images if image.stem.lower() == stem]


def normalize_text_fragment(text: str) -> str:
    text = text.replace("\t", " ")
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def render_line(
    line: str,
    matches: list[re.Match[str]],
    replacements: list[str],
) -> list[str]:
    leading_ws = re.match(r"^(\s*)", line).group(1)
    parts: list[str] = []
    last = 0
    for match in matches:
        parts.append(line[last:match.start()])
        last = match.end()
    parts.append(line[last:])
    text_without_embeds = "".join(parts)

    bullet_match = re.match(r"^(\s*)([-*])\s*(.*)$", text_without_embeds)
    if bullet_match:
        indent, marker, rest = bullet_match.groups()
        rest = normalize_text_fragment(rest)
        if not rest:
            rendered = [f"{indent}{marker} {replacements[0]}"]
            rendered.extend(f"{indent}  {image}" for image in replacements[1:])
            return rendered

        rendered = [f"{indent}{marker} {rest}"]
        rendered.extend(f"{indent}  {image}" for image in replacements)
        return rendered

    cleaned = normalize_text_fragment(text_without_embeds)
    if not cleaned:
        return [f"{leading_ws}{image}" for image in replacements]

    rendered = [f"{leading_ws}{cleaned}"]
    rendered.extend(f"{leading_ws}{image}" for image in replacements)
    return rendered


def validate_markdown_images(note: Path, text: str) -> list[str]:
    errors: list[str] = []
    for match in MARKDOWN_IMAGE_RE.finditer(text):
        target = match.group(1).strip()
        if re.match(r"^[a-z]+://", target, flags=re.IGNORECASE):
            continue

        decoded = unquote(target)
        candidate = (note.parent / decoded).resolve()
        try:
            candidate.relative_to(REPO_ROOT.resolve())
        except ValueError:
            errors.append(f"path escapes repo root: {target}")
            continue

        if not candidate.exists():
            errors.append(f"missing file: {target}")
    return errors


def transform_note(
    note: Path,
    all_images: list[Path],
    by_name: dict[str, list[Path]],
) -> TransformResult:
    original = note.read_text(encoding="utf-8")
    lines = original.splitlines()
    preview_lines: list[str] = []
    unresolved: list[str] = []
    embed_count = 0
    changed = False
    new_lines: list[str] = []

    for index, line in enumerate(lines):
        matches = list(IMAGE_EMBED_RE.finditer(line))
        if not matches:
            new_lines.append(line)
            continue

        replacements: list[str] = []
        text_without_embeds = normalize_text_fragment(IMAGE_EMBED_RE.sub("", line))

        for match in matches:
            raw_target = match.group(1).strip()
            label_override = match.group(2)
            candidates = resolve_image_target(raw_target, all_images, by_name)

            if len(candidates) != 1:
                if not candidates:
                    unresolved.append(f"unresolved: {raw_target}")
                else:
                    unresolved.append(
                        "ambiguous: "
                        + raw_target
                        + " -> "
                        + ", ".join(
                            str(candidate.relative_to(REPO_ROOT).as_posix())
                            for candidate in candidates[:5]
                        )
                    )
                continue

            image_path = candidates[0]
            relative_path = Path(os.path.relpath(image_path, start=note.parent))
            alt_text = choose_alt_text(
                note=note,
                lines=lines,
                line_index=index,
                raw_target=raw_target,
                text_without_embed=text_without_embeds,
                label_override=label_override,
            )
            replacements.append(f"![{alt_text}]({encode_relative_path(relative_path)})")
            embed_count += 1

        if not replacements:
            new_lines.append(line)
            continue

        rendered_lines = render_line(line, matches, replacements)
        if rendered_lines != [line]:
            changed = True
            if len(preview_lines) < 3:
                preview_lines.extend(rendered_lines[:3])
        new_lines.extend(rendered_lines)

    new_text = "\n".join(new_lines)
    if original.endswith("\n"):
        new_text += "\n"

    validation_errors = validate_markdown_images(note, new_text)
    return TransformResult(
        note=note,
        changed=changed,
        embed_count=embed_count,
        unresolved=unresolved,
        validation_errors=validation_errors,
        preview_lines=preview_lines,
        text=new_text,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert local Obsidian image embeds to Markdown image links."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to disk instead of running in dry-run mode.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    notes = markdown_notes()
    images = image_files()
    by_name = build_image_index(images)
    results = [transform_note(note, images, by_name) for note in notes]

    notes_with_embeds = sum(1 for result in results if result.embed_count)
    notes_changed = sum(1 for result in results if result.changed)
    embeds_processed = sum(result.embed_count for result in results)
    unresolved = sum(len(result.unresolved) for result in results)
    validation_errors = sum(len(result.validation_errors) for result in results)

    print(f"mode: {'apply' if args.apply else 'dry-run'}")
    print(f"notes scanned: {len(notes)}")
    print(f"notes with local Obsidian image embeds: {notes_with_embeds}")
    print(f"notes changed: {notes_changed}")
    print(f"local Obsidian image embeds processed: {embeds_processed}")
    print(f"resolution failures: {unresolved}")
    print(f"validation errors: {validation_errors}")

    for result in results:
        if result.changed:
            print(
                f"- {safe_display(result.note.relative_to(REPO_ROOT).as_posix())} "
                f"({result.embed_count} embeds)"
            )
            for preview in result.preview_lines[:2]:
                print(f"  {safe_display(preview)}")
        for issue in result.unresolved:
            print(
                f"  ! {safe_display(result.note.relative_to(REPO_ROOT).as_posix())}: "
                f"{safe_display(issue)}"
            )
        for issue in result.validation_errors:
            print(
                f"  ! {safe_display(result.note.relative_to(REPO_ROOT).as_posix())}: "
                f"{safe_display(issue)}"
            )

    if args.apply:
        for result in results:
            if result.changed and not result.unresolved and not result.validation_errors:
                result.note.write_text(result.text, encoding="utf-8")

    return 0 if unresolved == 0 and validation_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
