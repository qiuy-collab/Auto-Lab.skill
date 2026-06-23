# DOCX Fill Rules

This document defines how `auto-lab` should fill the report template while preserving the template shell.

## Core policy

- Preserve the template structure and styling intent.
- Save to a new output file, never overwrite the source template.
- For structural DOCX work, read and prefer `vendor/minimax-docx/SKILL.md` before writing scripts.
- Use `python-docx` only for simple paragraph/table fills, simple body cleanup, inspection, or when minimax-docx is unavailable; record the fallback reason.
- Plan figures before writing report text.
- Default target tier is `excellent`.
- Default report style is figure-supported, not pure-text.
- Write from the perspective of a student submitting completed coursework, not from the perspective of an agent describing actions.

## Route boundary

Three figure routes may appear in the same report:

- `ai_simulated`
  - terminal screenshots
  - command output screenshots
  - software/system configuration screenshots

- `browser_capture`
  - local frontend page screenshots
  - self-built app/web screenshots
  - development software practice screenshots for the user's own app/web flow

- `diagram_assets`
  - function diagrams
  - flowcharts
  - data flow diagrams
  - ER diagrams

- `video_analysis` / `screen_recording`
  - existing operation videos
  - short local operation recordings
  - representative frame evidence

## Mandatory pre-work

Before editing the document:
1. Read the template and identify headings, body zones, tables, and figure anchors.
2. Read `requirement_checklist.json` and confirm:
   - target tier
   - whether a pre-task is required
   - whether images are required
   - which routes are required
   - minimum image count
3. If a pre-task is required, complete it first and read `pre_task_plan.json`.
4. If browser capture is required, read `browser_capture_plan.json`.
5. If diagram assets are required, read `diagram_plan.json`.
6. If video evidence is required, read `video_plan.json`.
7. If a filled reference document must become a blank template, read `reference_template_cleanup.json` and `reference_template_cleanup_rules.md`.
8. Ensure `copywriting.md`, `prompt_config.json`, `browser_capture_plan.json`, `diagram_plan.json`, `video_plan.json`, `reference_template_cleanup.json`, and `insert_config.json` are mutually consistent.
9. When a pre-task exists, the report text must combine the original assignment requirements with the pre-task outputs rather than treating them separately.
10. Before final validation, verify that AI screenshots, diagram assets, and video evidence have passed the visual review checklist.
11. Review the template for directories, field-based tables of contents, sample text, formatting instructions, and reference wording that must be replaced or removed in the final output.

## Figure rules

- If the template already contains image placeholders, reuse them.
- If not, place figures at planned semantic anchors.
- Each figure should have:
  - a lead-in sentence
  - the image
  - a caption
  - a short analysis paragraph

## Verification expectations

The template-specific verify script should check at least:
- no unresolved placeholders remain unless intentionally documented
- the planned figure count is satisfied
- route coverage is satisfied when multiple routes are required
- video analysis/recording outputs exist when the checklist requires video evidence
- filled-reference cleanup preserved cover/front matter and retained level-1/level-2 headings when required
- pre-task results are reflected when the assignment depends on them
- captions exist
- figures are not dumped at the end without context
- placeholder/sample text is removed
- template formatting instructions and reference wording are removed when they are not part of the final report content
- table-of-contents or directory areas are not silently left broken when the template expects them to be filled or updated
- report narration stays in student voice instead of tool/agent voice
- the template shell remains stable
