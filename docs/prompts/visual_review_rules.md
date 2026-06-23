# Visual Review Rules

This document defines the mandatory visual acceptance pass for `auto-lab`.

## Decision owner

- Visual review is an agent reasoning step.
- The agent must inspect the generated images directly before marking review-complete fields.
- Script validation should fail if the checklist claims review is complete but the agent has not actually inspected the images.

## AI screenshot review

Before setting `ai_visual_review_completed = true`, check every `ai_simulated` image for:
- readable text at a normal report zoom level
- only necessary information, not a high-density wall of tiny UI
- a believable background instead of an empty cutout scene
- a consistent environment/background style across the full image set unless the requirement explicitly needs scene changes
- no `localhost`, `127.0.0.1`, dev URLs, tabs, or address bars unless explicitly required
- no malformed icons, twisted controls, broken charts, warped tables, or obviously fake UI details

If any item fails:
- revise the prompt
- regenerate the image
- review again

## Diagram review

Before setting `diagram_visual_review_completed = true`, check every `diagram_assets` image for:
- clean spacing
- no overlapping labels
- no modules, text blocks, or arrows colliding after final render
- no accidental line crossings unless intentionally unavoidable
- readable labels
- line routing that looks deliberate rather than tangled
- enough empty space around each node so the diagram still looks clean inside the report page

If any item fails:
- revise the node layout, explicit edge path, or canvas spacing
- regenerate the diagram
- review again

## Output contract

- `ai_visual_review_completed` may be `true` only after AI screenshot review passes
- `diagram_visual_review_completed` may be `true` only after diagram review passes
