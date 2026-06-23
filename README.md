# Auto Lab

Template-preserving lab report workflow for:
- extracting scoring targets before writing
- finishing requirement-dependent pre-tasks before report drafting
- planning figures before copywriting
- generating AI screenshot-style experiment images for terminal/configuration content
- capturing real local screenshots for self-built frontend/app pages
- generating diagram assets for function diagrams, flowcharts, data flow diagrams, and ER diagrams
- analyzing operation videos and recording short local screen evidence clips
- converting already-filled reference DOCX files into blank templates
- packaging final submission contents into `submit.zip` from the assignment prompt
- creating task-specific DOCX scripts per template
- validating both structure and scoring-evidence coverage before delivery

The executable path currently expects a `.docx` template. If the source template is `.doc`, convert it first.

Scripts execute. The agent decides requirement-dependent meaning.

## Workflow

1. Run environment check:
   - `powershell -ExecutionPolicy Bypass -File scripts/env_check.ps1`
2. Initialize a task run directory:
   - `python scripts/init_run.py --requirements <requirements> --template <template.docx> --output-dir <output_dir> --output-docx-name <result.docx>`
3. Review generated task files:
   - `workflow.json`
   - `template_manifest.json`
   - `requirement_checklist.json`
   - `requirement_analysis.json`
   - `pre_task_plan.json`
   - `配文.md`
   - `prompt_config.json`
   - `browser_capture_plan.json`
   - `diagram_plan.json`
   - `video_plan.json`
   - `reference_template_cleanup.json`
   - `submission_package.json`
   - `insert_config.json`
   - `task_scripts/fill_template.py`
   - `task_scripts/insert_images.py`
   - `task_scripts/verify_template.py`
4. Fill `requirement_analysis.json` first.
   - this is the agent's requirement understanding record
5. Reflect those decisions into `requirement_checklist.json`.
   - the default initialized state is `planning_only`
   - change `run_mode` from `planning_only` to a descriptive label that matches the actual assignment plan
6. Decide whether the assignment requires a pre-task such as building a system, implementing pages, preparing data, or generating intermediate deliverables.
   - make this judgment by reading the requirement document, not by script keyword extraction
7. If yes, complete that pre-task first and record its outputs in `pre_task_plan.json`.
8. Plan figure count, figure anchors, figure purpose, and image routes.
9. Fill `配文.md`, `prompt_config.json`, `browser_capture_plan.json`, `diagram_plan.json`, `video_plan.json`, `reference_template_cleanup.json`, `submission_package.json`, and `insert_config.json`.
   - use `docs/prompts/prompt_driven_decisions.md` to decide what really belongs to the current assignment
   - for `ai_simulated`, keep only necessary information and a believable background
   - avoid high-density UI and hidden `localhost` or dev URLs
   - high-resolution image generation uses `2048x1152` for 2K 16:9 and `3840x2160` for 4K 16:9
   - find the highest stable batch worker count with `python scripts/test_image_concurrency.py --resolutions 2k_16_9,4k_16_9`
   - keep `prompt_config.json -> max_workers` at a conservative value until the probe result is available, then promote it to the highest passing worker count
   - for `diagram_assets`, you can start from:
   - `examples/diagram_plan.example.json`
   - `examples/diagram_plan.database_course_design.example.json`
   - `examples/diagram_plan.web_system.example.json`
   - for pre-tasked assignments, also review:
   - `examples/pre_task_plan.example.json`
10. Visually review generated AI screenshots and diagrams before validation.
   - use `docs/prompts/visual_review_rules.md`
   - only after review should `ai_visual_review_completed` and `diagram_visual_review_completed` be marked true
11. Validate:
   - `python scripts/run_workflow.py validate --workflow <workflow.json>`
12. Generate enabled visual routes:
   - `python scripts/run_workflow.py images --workflow <workflow.json>`
13. Process enabled video evidence:
   - `python scripts/run_workflow.py video --workflow <workflow.json>`
14. Build the prompt-driven submission package when required:
   - `python scripts/run_workflow.py package --workflow <workflow.json>`
15. Run:
   - `python scripts/run_workflow.py run --workflow <workflow.json>`

## Route boundary

- `ai_simulated`:
  - terminal screenshots
  - command output
  - software/system configuration screenshots

- `browser_capture`:
  - local frontend pages
  - self-built app/web screenshots
  - development software practice screenshots for the user's own app/web flow

- `diagram_assets`:
  - function diagrams
  - flowcharts
  - data flow diagrams
  - ER diagrams

- `video_analysis`:
  - existing operation videos
  - representative frame extraction
  - metadata and stream inspection

- `screen_recording`:
  - short local operation clips
  - screenshot evidence that needs temporal context

## DOCX tool policy

- For DOCX creation, filling, formatting, template application, or structural cleanup, first read and prefer `vendor/minimax-docx/SKILL.md`.
- Use `python-docx` only for simple paragraph/table fills, simple body cleanup, inspection, or when minimax-docx is unavailable.
- Record the fallback reason in `reference_template_cleanup.json` or the run notes.

## Notes

- Default target is the best grading tier unless the user says otherwise.
- If the requirement depends on a prior deliverable, do that pre-task first and then write the report from both the requirement and the pre-task outputs.
- Do not produce a pure-text report when the assignment expects screenshots or evidence figures.
- Before a browser-capture run, verify local screenshot capability.
- Use `diagram_assets` for database/system-design figures rather than screenshot routes.
- When the assignment requires a hand-in archive, derive the exact included files from the prompt/requirement and package them as `submit.zip`.
- `.env` is only required for runs that actually use `ai_simulated`.
- Packaging guidance lives in `docs/prompts/submission_package_rules.md`.
- Prompt-versus-script decision guidance lives in `docs/prompts/prompt_driven_decisions.md`.
- The agent decision record lives in `requirement_analysis.json`; the checklist is the execution-facing summary.
