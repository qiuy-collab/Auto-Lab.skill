# Prompt-Driven Decisions

This file defines which parts of `auto-lab` must be decided by the agent from the requirement/prompt instead of by fixed script defaults.

## Principle

- Scripts are the execution layer.
- The agent is the decision layer.
- If a choice depends on assignment semantics, grading emphasis, deliverable wording, project reality, or template meaning, the agent must decide it from the requirement/prompt.

## Must be prompt-driven

- Whether a pre-task is required.
- Which requirement items demand real implementation deliverables such as code, datasets, scripts, or packaged project files.
- Which visual routes are actually needed: `ai_simulated`, `browser_capture`, `diagram_assets`, `video_analysis`, `screen_recording`.
- Which figures are needed, how many are needed, and where they belong in the report.
- Whether zero images is acceptable.
- Which local pages must be browser-captured, and what startup command/base URL are correct for the actual project.
- Which diagrams are required, and what their real labels/entities/flows should be.
- Whether video evidence is needed, and whether it should be analysis, recording, or both.
- Whether a filled reference document can be safely converted into a blank template, and what the real preserved/removed zones are.
- What the final submission should contain.
- Whether the output file names must follow assignment-specific naming.
- What `配文.md` should emphasize, including where figures belong and how pre-task outputs should be woven into the narrative.
- Which image concurrency level is actually safe for the current upstream provider and resolution mix after probing 2K/4K 16:9.
- Which template guidance text, placeholders, sample wording, TOC zones, and formatting reminders must be removed or retained in the final report.
- Whether the final delivery passes a requirement-by-requirement acceptance review instead of only a file-existence check.

## Should not be hard-coded by scripts

- Fixed image counts across all assignments.
- Fixed assumptions that every assignment needs screenshots.
- Fixed assumptions that every report uses the same route combination.
- Fixed assumptions that every cleanup keeps the same body boundary unless the template clearly supports that heuristic.
- Fixed assumptions that the whole project folder should always be zipped for submission.
- Fixed assumptions that a large default `max_workers` is always safe for image generation.
- Fixed assumptions that any generated code demo is "good enough" when the requirement asks for a real implementation.

## Safe for scripts to enforce

- Environment availability checks.
- File existence checks.
- Route-boundary validation after the agent has chosen a route.
- Prompt lint rules for screenshot-style image generation.
- Packaging output name `submit.zip` when the assignment requires a submission archive and the user did not override the name.
- Post-decision execution such as image generation, video analysis, template cleanup, and zip creation.
