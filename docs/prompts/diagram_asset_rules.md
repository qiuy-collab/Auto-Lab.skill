# Diagram Asset Rules

This document defines how `auto-lab` should write `diagram_plan.json`.

## Scope boundary

`diagram_plan.json` is only for the `diagram_assets` route.

Use it for:
- function diagrams
- flowcharts
- data flow diagrams
- ER diagrams

Do not use it for:
- terminal screenshots
- command output screenshots
- local frontend page screenshots
- third-party product screenshots

## Planning order

Before writing a diagram plan:
1. Read the requirement document.
2. Fill `requirement_checklist.json`.
3. If the assignment depends on a pre-task, complete it first and absorb the outputs.
4. Decide which figures belong to `diagram_assets`.
5. For each diagram, define:
   - `name`
   - `kind`
   - title
   - nodes / entities / stores / relations / edges as needed

## Diagram quality rules

- Use a clean academic layout with consistent spacing.
- Keep labels short and legible.
- Avoid overlapping labels and crossing lines when possible.
- Reserve enough horizontal and vertical spacing between modules so text and arrows do not collide after rendering.
- Prefer explicit edge paths for flowcharts when automatic routing would cause line crossings.
- Prefer standard course-design symbols for DFD and ER diagrams.
- Keep naming consistent with the report text and captions.
- When a diagram risks becoming crowded, split it into multiple simpler diagrams instead of forcing all content into one canvas.

## Output contract

`diagram_plan.json` should:
- match only the `diagram_assets` figures
- keep names aligned with `配文.md` placeholders
- never include AI screenshot figures or browser-capture figures
- stay free of comments and helper fields
