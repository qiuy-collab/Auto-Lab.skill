# Auto Lab

Template-preserving lab report workflow. For full details, see `SKILL.md`.

## Quick start

1. `powershell -ExecutionPolicy Bypass -File scripts/env_check.ps1`
2. `python scripts/init_run.py --requirements <req> --template <tpl.docx> --output-dir <dir> --output-docx-name <result.docx>`
3. Fill `requirement_analysis.json` → update `requirement_checklist.json`
4. Plan figures → write `copywriting.md` + `prompt_config.json` + `insert_config.json`
5. `python scripts/run_workflow.py gate --workflow <workflow.json>`
6. `python scripts/run_workflow.py images --workflow <workflow.json>`
7. `python scripts/run_workflow.py run --workflow <workflow.json>`

## Image routes

| Route | Scope |
|-------|-------|
| `ai_simulated` | terminal, command output, software configuration, IDE screenshots |
| `browser_capture` | local frontend pages, self-built app/web screenshots |
| `diagram_assets` | function diagrams, flowcharts, data flow diagrams, ER diagrams |

## Notes

- Default target is the best grading tier unless the user says otherwise.
- Scripts execute; the agent decides requirement-dependent meaning.
- `.env` is only required for runs that use `ai_simulated`.
- Packaging guidance: `docs/prompts/submission_package_rules.md`
- Decision guidance: `docs/prompts/prompt_driven_decisions.md`
