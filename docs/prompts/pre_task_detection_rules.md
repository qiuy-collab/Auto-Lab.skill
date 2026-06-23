# Pre-Task Detection Rules

This document defines how `auto-lab` should decide whether a requirement document implies a mandatory pre-task.

## Decision owner

- Pre-task detection is an agent reasoning step, not a keyword-extraction script.
- The agent must read the requirement document itself before deciding `pre_task_required`.
- `init_run.py` only creates `pre_task_plan.json`; it does not decide whether a pre-task exists.

## Detection order

Before filling `pre_task_plan.json`:
1. Read the full requirement document.
2. Identify the final deliverable.
3. Identify whether the report depends on an earlier deliverable being produced first.
4. If yes, mark `requirement_checklist.json -> pre_task_required = true`.
5. Record the pre-task objective, outputs, and later report dependencies in `pre_task_plan.json`.

## Positive signals

Treat the requirement as pre-task-dependent when it clearly asks for work such as:
- designing and implementing a system before writing the report
- building frontend pages, app flows, or a local demo before documenting them
- completing a database design, schema, or course-design artifact before the write-up
- preparing experimental outputs, intermediate files, or runnable artifacts that the report must analyze
- producing real code, scripts, datasets, trained models, processed data, or packaged project deliverables that are explicitly named in the requirement

## Negative signals

Do not mark a pre-task as required when the document only asks for:
- literature review
- concept explanation
- security analysis with no prior build requirement
- pure reporting on already-provided materials
- generic "it would be nice to have a demo" ideas that are not explicit deliverable requirements
- work that the agent invents for convenience but the assignment never requested

## Quality bar when a pre-task exists

- A pre-task is not complete just because some files were created.
- If the requirement asks for code, the code must implement the requested scope instead of a toy demo.
- If the requirement asks for a runnable project, the handoff must include startup instructions or a README that explains how to run it.
- If the requirement asks for a dataset or generated data, the produced data must match the requested format and purpose.
- For frontend/web-app implementation pre-tasks:
  - initialize git before coding if the workspace is not already a git repository
  - read and apply `vendor/baseline-ui/SKILL.md`
  - read and apply `vendor/frontend-design/SKILL.md`
  - verify with `vendor/webapp-testing/SKILL.md` before claiming completion

## Output contract

When a pre-task is required:
- `pre_task_plan.json.enabled` must be `true`
- `pre_task_plan.json.completed` must only become `true` after the pre-task is actually done
- the final report must use both the original requirement and the pre-task outputs
- `pre_task_plan.json` should record the concrete deliverables, where they live, and what verification was performed
