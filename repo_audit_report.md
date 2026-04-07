# Repository Audit Report

## Scope

- This audit is for the current Hebrew trading vault at `c:\Users\User\Desktop\obsidian\מניות`.
- The nested `CKA-Notes` folder is intentionally out of scope for this pass and is treated as reference material only.
- Hidden config folders and generated helper/report files should stay outside broad content automation:
  - `.obsidian/*`
  - `scripts/*`
  - `repo_audit_report.md`
  - `final_repo_update_report.md`
  - `context_refresh_log.md`
- `1 - צעדים ראשונים/Welcome.md` is the default Obsidian starter note and is not part of the actual course content.

## Repository Structure

- Main study sections:
  - `1 - צעדים ראשונים`
  - `2 - איתור מניה`
  - `3 - מסחר תאוריה`
- Scoped note count: `119` Markdown files.
- Scoped image count: `265` local image files.
- Local image storage is section-local rather than centralized:
  - `1 - צעדים ראשונים/images`
  - `2 - איתור מניה/images`
  - `3 - מסחר תאוריה/images`
- Current note distribution:
  - `20` notes under `1 - צעדים ראשונים`
  - `48` notes under `2 - איתור מניה`
  - `51` notes under `3 - מסחר תאוריה`

## Naming Conventions

- Folder names are structured as numbered course sections and sub-sections.
- Most note names begin with a sequence number and a descriptive Hebrew title.
- There is mild formatting inconsistency in filenames:
  - some files use `2 - ...`
  - some use `2- ...`
  - some subfolders are numbered while others are plain descriptive names
- Several folders clearly represent chapter-like learning sequences:
  - topic intro / introduction
  - ordered intermediate lessons
  - occasional summary note
- Placeholder / low-content items exist and should be handled carefully:
  - `3 - מסחר תאוריה/Untitled.md`
  - `3 - מסחר תאוריה/8 - פקודות מסחר/1 - סידור מערכת בקולמקס.md`
  - `3 - מסחר תאוריה/8 - פקודות מסחר/11 - פקודות לשעות המסחר המורחבות.md`
  - `3 - מסחר תאוריה/8 - פקודות מסחר/12 - סיכום.md`

## Writing Conventions

- The vault is course-note oriented rather than essay-like documentation.
- The dominant style is bullet-first prose.
- Most notes start immediately with bullet points instead of headings.
- `92` scoped notes start with a bullet list.
- Bold emphasis is common and used in `76` scoped notes.
- Headings exist but are rare:
  - only `3` notes contain `#`
  - only `3` notes contain `##`
- Tone is instructional, direct, and practical.
- Many notes read like concise lesson summaries or rule lists rather than polished long-form articles.
- There is no meaningful frontmatter convention in the scoped notes:
  - `0` files with YAML frontmatter

## Link Conventions

- The scoped vault currently has almost no intentional note-to-note linking.
- Non-image wikilinks found: `1`
  - that single example appears only in the default Obsidian starter note
- Standard Markdown links are almost absent:
  - `2` regular Markdown links total
  - `0` standard Markdown image links
- No consistent `See also`, `Related notes`, `Connections`, or MOC sections were found.
- This means the current knowledge graph is structurally weak even though the folder hierarchy is strong.

## Image / Embed Conventions

- Local images are embedded almost entirely with Obsidian-only syntax:
  - `![[Pasted image ...]]`
- Scoped audit result for local Obsidian image embeds:
  - `243` embeds found
  - `95` notes contain at least one local embed
  - `243 / 243` resolved uniquely to files on disk
  - `0` ambiguous matches
  - `0` missing matches
- No standard Markdown image syntax is currently used in the scoped notes.
- Real formatting edge cases are present:
  - image-only bullet lines
  - indented image lines under bullets
  - images glued directly to prose on the same line
  - multiple embeds within the same note block

## Likely Sources Of Broken GitHub Rendering

- `![[...]]` image embeds are Obsidian-specific and will not render on GitHub.
- The embeds rely on Obsidian attachment resolution instead of explicit relative paths.
- Filenames contain spaces and Hebrew characters, so safe relative-path generation matters.
- Because the repo uses almost no note-to-note links, GitHub rendering problems are less about broken links and more about missing explicit navigation and non-portable image syntax.

## Conventions To Preserve

- Keep the bullet-first lesson style.
- Keep the existing file and folder names.
- Keep notes concise and avoid broad rewriting.
- Preserve the course sequence implied by the folder layout.
- Avoid normalizing every numbering inconsistency just because it exists.

## Proposed Migration Rules

### Phase 2 Image Migration

- Convert only local Obsidian image embeds.
- Preserve existing regular Markdown links.
- Do not move or rename image files.
- Resolve every embed to a real file before replacing it.
- Generate standard Markdown image syntax with correct relative paths from each note.
- URL-encode path segments so spaces and Hebrew filenames remain GitHub-safe.
- Keep surrounding note layout readable:
  - if an image is glued to prose, separate it cleanly
  - if an image appears under a bullet, preserve that local structure
  - if multiple embeds appear together, keep them readable instead of inlining them mechanically

### Phase 3 Internal-Link Pass

- Use Obsidian wikilinks for note-to-note connectivity.
- Lean on the existing course hierarchy instead of inventing a new taxonomy.
- Prefer lightweight navigation and hub notes over rewriting large amounts of prose.
- Improve connectivity with:
  - section maps
  - chapter maps
  - conservative previous / next navigation inside sequential folders
  - a small number of cross-chapter related links where the folder structure strongly implies them
- Do not add fake content to placeholder notes.

## Recommended Implementation Approach

1. Add a dry-run/apply image migration script.
2. Validate the migrated Markdown image paths after apply mode.
3. Add a reproducible internal-link analyzer.
4. Generate a small set of hub notes and deterministic note-navigation blocks based on the actual chapter structure.
5. Re-run validation to measure:
   - broken local Markdown image links
   - unresolved internal wikilinks
   - weakly connected / still-empty notes

## Audit Conclusion

- The vault is structurally organized but graph-poor.
- The image migration is mechanically safe because all local embeds resolve uniquely.
- The internal-link phase should focus on turning the strong folder hierarchy into explicit in-note navigation, while keeping the study-note voice intact and avoiding noisy overlinking.
