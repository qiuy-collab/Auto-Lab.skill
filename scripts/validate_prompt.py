"""
Prompt JSON Validator for auto-lab.

Validates prompt_config.json using the Agnes AI validation agent.
Checks for consistency, constraint compliance, and structural issues.

Usage:
    # Validate and output report only
    python validate_prompt.py --config path/to/prompt_config.json

    # Validate and auto-fix (writes corrections to prompt_config.json)
    python validate_prompt.py --config path/to/prompt_config.json --fix

    # Validate with custom output
    python validate_prompt.py --config path/to/prompt_config.json --output validation_report.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_env_file() -> dict:
    """Load .env from skill root."""
    env_path = skill_root() / ".env"
    env_vars: dict = {}
    if not env_path.exists():
        return env_vars

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        delimiter = "=" if "=" in line else ":" if ":" in line else None
        if delimiter is None:
            continue
        key, value = line.split(delimiter, 1)
        env_vars[key.strip()] = value.strip()
    return env_vars


def build_validation_prompt(config_json: str) -> str:
    """Build a comprehensive validation prompt for the Agnes AI validator."""
    return f"""你是一个 JSON 提示词一致性校验专家。请严格校验以下 prompt_config.json 文件。

## 校验规则（逐条检查，每条给出通过/不通过/修改建议）

### 规则1: global_prompt 与 images[].prompt 语义一致性
- global_prompt 定义了统一的视觉环境（桌面环境、终端主题、窗口风格等）
- 每个 image.prompt 的描述必须与 global_prompt 完全兼容，不能自相矛盾
- 例如：global_prompt 说"深色终端主题"，某个 image 不能说"白色背景"
- 例如：global_prompt 说"不出现额外解释文字"，image.prompt 不能包含"显示说明文字"

### 规则2: 禁止词检查
- 检查 global_prompt 和每个 image.prompt 是否包含以下禁止词：
  流程图、架构图、讲解板、说明面板、悬浮标注、箭头标注、海报、AI生成、示意图、
  poster、callout、annotation、flowchart、diagram
- 注意：如果在"不要"、"不能有"、"无"、"without"、"avoid"的否定上下文中出现，视为通过
- 禁止词出现在肯定/描述性上下文中 = 不通过

### 规则3: mode 字段正确性
- 截图类 prompt 的 mode 必须是 "screenshot_strict"
- 非截图类 prompt 的 mode 可以是 "generic"
- 如果 prompt 描述了UI、终端、窗口等，但 mode 不是 screenshot_strict = 警告

### 规则4: 图片间视觉一致性
- 如果多张图片声称在"同一环境"中，检查它们的 prompt 是否真的描述了相同的：
  - 桌面/操作系统环境
  - 配色方案（深色/浅色主题）
  - 字体风格
  - 窗口布局
- 发现矛盾 = 不通过

### 规则5: 分辨率合理性
- "2560x1440" 或 "2048x1152" 适合截图（16:9 宽屏）
- "1024x1024" 适合非截图类
- 如果所有图片都是截图但分辨率是 1024x1024 = 建议改为 2048x1152

### 规则6: image_policy 配置完整性
- forbidden_terms 列表是否完整
- default_mode 是否为 "screenshot_strict"（当所有图片都是截图时）
- ui_density 是否合理
- fail_on_prompt_risk 是否为 true

### 规则7: total_count 与 images 数组长度匹配
- total_count 必须等于 images 数组的长度
- 不匹配 = 不通过

### 规则8: 图片命名规范
- image.name 必须以 "img_" 开头
- 编号必须连续（img_01, img_02, img_03...）
- 名称不能包含特殊字符或空格

## 输出格式要求

你必须严格输出以下 JSON 格式（不要输出 Markdown 代码块，只输出纯 JSON）：

{{
  "overall_result": "pass|fail|warn",
  "summary": "一句话总结校验结果",
  "checks": [
    {{
      "rule": "规则名称",
      "result": "pass|fail|warn",
      "issue": "具体问题描述（pass时为空字符串）",
      "fix_suggestion": "具体的修改建议（pass时为空字符串）",
      "affected_field": "需要修改的字段路径，如 'images[0].prompt' 或 'global_prompt'（pass时为空字符串）"
    }}
  ],
  "required_changes": [
    {{
      "path": "JSON 字段路径，如 'images[2].prompt' 或 'global_prompt'",
      "current": "当前值（截取前100字符）",
      "suggested": "建议修改为",
      "reason": "修改原因"
    }}
  ]
}}

## 待校验的 prompt_config.json

```json
{config_json}
```

请严格按照上述规则和输出格式进行校验。只输出纯 JSON，不要输出任何解释文字。"""


VALIDATOR_SYSTEM_PROMPT = """你是一个专业的 JSON 配置校验引擎。你的唯一职责是对输入的 JSON 配置执行规则校验，并输出结构化的校验结果。

严格要求：
1. 只输出纯 JSON，不要包含 Markdown 代码块标记（不要 ```json）
2. 输出必须是可以直接 parse 的有效 JSON
3. 逐条规则检查，不要跳过
4. 对于每一条规则，明确给出 pass/fail/warn
5. required_changes 数组中的每一条必须是具体可执行的修改"""


def call_validator_api(prompt: str, base_url: str, api_key: str, model: str, timeout: int = 120) -> Optional[dict]:
    """Call the Agnes AI validation API."""
    url = f"{base_url.rstrip('/')}/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 4096
    }

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    result = response.json()

    if "choices" not in result or not result["choices"]:
        return None

    content = result["choices"][0].get("message", {}).get("content", "")
    if not content:
        return None

    # Try to parse the JSON response
    content = content.strip()
    # Remove markdown code block markers if present
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Warning: Validator returned non-JSON response: {e}")
        print(f"Raw response: {content[:500]}")
        return {"error": "JSON parse failed", "raw": content[:1000]}


def validate_config(config_path: Path, output_path: Optional[Path] = None, auto_fix: bool = False) -> dict:
    """Validate prompt_config.json using the Agnes AI validator."""
    env = load_env_file()

    base_url = env.get("AGNES_BASEURL", "").strip()
    api_key = env.get("AGNES_APIKEY", "").strip()
    model = env.get("AGNES_MODEL", "agnes-2.0-flash").strip()

    if not base_url or not api_key:
        raise SystemExit(
            "[ERROR] Agnes AI validator not configured.\n"
            "Add these to .env:\n"
            "  AGNES_BASEURL=https://apihub.agnes-ai.com\n"
            "  AGNES_APIKEY=sk-xxx...\n"
            "  AGNES_MODEL=agnes-2.0-flash"
        )

    if not config_path.exists():
        raise SystemExit(f"Config file not found: {config_path}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    config_json = json.dumps(config, ensure_ascii=False, indent=2)

    print(f"=== Prompt JSON Validation ===")
    print(f"Config: {config_path}")
    print(f"Validator: {model} @ {base_url}")
    print(f"Images: {config.get('total_count', 0)} entries")
    print(f"Mode: {'auto-fix' if auto_fix else 'report-only'}")
    print("-" * 50)

    validation_prompt = build_validation_prompt(config_json)

    print("Calling validation agent...")
    start_time = time.time()

    max_retries = 2
    result = None
    last_error = None

    for attempt in range(max_retries):
        try:
            result = call_validator_api(validation_prompt, base_url, api_key, model)
            if result and "error" not in result:
                break
            last_error = result.get("error") if result else "empty response"
        except Exception as exc:
            last_error = str(exc)
            print(f"  Attempt {attempt + 1} failed: {last_error}")
            if attempt < max_retries - 1:
                time.sleep(3)

    elapsed = time.time() - start_time

    if not result or "error" in result:
        raise SystemExit(
            f"[FAIL] Prompt validation failed after {max_retries} attempts.\n"
            f"Last error: {last_error}\n"
            f"Time: {elapsed:.1f}s\n"
            f"Check AGNES_BASEURL/AGNES_APIKEY/AGNES_MODEL in .env"
        )

    print(f"Validation completed in {elapsed:.1f}s")
    print(f"Overall result: {result.get('overall_result', 'unknown')}")
    print(f"Summary: {result.get('summary', 'N/A')}")

    # Count issues
    checks = result.get("checks", [])
    failed = [c for c in checks if c.get("result") == "fail"]
    warnings = [c for c in checks if c.get("result") == "warn"]
    passed = [c for c in checks if c.get("result") == "pass"]

    print(f"\nResults: {len(passed)} passed, {len(failed)} failed, {len(warnings)} warnings")
    print("-" * 50)

    for check in checks:
        status = check.get("result", "?")
        icon = {"pass": "[PASS]", "fail": "[FAIL]", "warn": "[WARN]"}.get(status, "[????]")
        rule = check.get("rule", "Unknown rule")
        issue = check.get("issue", "")
        if issue:
            print(f"{icon} {rule}: {issue}")
        else:
            print(f"{icon} {rule}")

    # Required changes
    required_changes = result.get("required_changes", [])
    if required_changes:
        print(f"\n=== Required Changes ({len(required_changes)}) ===")
        for i, change in enumerate(required_changes, 1):
            print(f"\n  #{i}: {change.get('path', 'unknown')}")
            print(f"      Reason: {change.get('reason', 'N/A')}")
            current = change.get("current", "")
            suggested = change.get("suggested", "")
            if current:
                print(f"      Current:  {current[:120]}")
            if suggested:
                print(f"      Suggest:  {suggested[:120]}")

    # Auto-fix
    if auto_fix and required_changes:
        print(f"\n=== Auto-fixing prompt_config.json ===")
        fixed_count = 0
        for change in required_changes:
            path_str = change.get("path", "")
            suggested = change.get("suggested", "")
            if not path_str or not suggested:
                continue

            try:
                apply_change(config, path_str, suggested)
                fixed_count += 1
                print(f"  Fixed: {path_str}")
            except Exception as exc:
                print(f"  Failed to fix {path_str}: {exc}")

        if fixed_count > 0:
            # Backup original
            backup_path = config_path.with_suffix(".json.bak")
            config_path.rename(backup_path)
            print(f"  Backup: {backup_path}")

            # Write fixed config
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  Written: {config_path} ({fixed_count} changes)")
            print(f"\n  Agent: review the changes and verify before proceeding.")
            result["auto_fix_applied"] = True
            result["auto_fix_count"] = fixed_count
    elif auto_fix:
        print(f"\nNo changes needed — config is clean.")

    # Save report
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nReport saved: {output_path}")

    return result


def apply_change(config: dict, path_str: str, suggested: str) -> None:
    """Apply a single change to the config dict using dot/bracket notation path."""
    # Parse path like "images[0].prompt" or "global_prompt"
    parts = []
    current = ""
    i = 0
    while i < len(path_str):
        ch = path_str[i]
        if ch == ".":
            if current:
                parts.append(current)
                current = ""
        elif ch == "[":
            if current:
                parts.append(current)
                current = ""
            # Find closing bracket
            j = path_str.index("]", i)
            idx = int(path_str[i+1:j])
            parts.append(idx)
            i = j
        else:
            current += ch
        i += 1
    if current:
        parts.append(current)

    # Navigate to the target
    target = config
    for part in parts[:-1]:
        if isinstance(part, int):
            target = target[part]
        else:
            target = target[part]

    # Set the value
    last = parts[-1]
    if isinstance(last, int):
        target[last] = suggested
    elif last == "prompt" or last == "global_prompt":
        # String fields
        target[last] = suggested
    elif last == "total_count":
        target[last] = int(suggested)
    elif last == "mode":
        target[last] = str(suggested)
    elif last == "resolution":
        target[last] = str(suggested)
    else:
        # Try best-effort
        try:
            target[last] = json.loads(suggested)
        except (json.JSONDecodeError, TypeError):
            target[last] = suggested


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate prompt_config.json using Agnes AI validation agent.",
        epilog=(
            "Examples:\n"
            "  python validate_prompt.py --config prompt_config.json\n"
            "  python validate_prompt.py --config prompt_config.json --fix\n"
            "  python validate_prompt.py --config prompt_config.json --output report.json"
        )
    )
    parser.add_argument("--config", "-c", required=True, help="Path to prompt_config.json")
    parser.add_argument("--output", "-o", help="Path to save validation report JSON")
    parser.add_argument("--fix", action="store_true", help="Auto-apply suggested fixes to prompt_config.json")
    parser.add_argument("--timeout", "-t", type=int, default=120, help="API timeout in seconds")
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve() if args.output else None

    try:
        result = validate_config(config_path, output_path, auto_fix=args.fix)

        overall = result.get("overall_result", "fail")
        if overall == "fail":
            print("\n[FAIL] Prompt validation found critical issues.")
            print("Fix the above issues in prompt_config.json before generating images.")
            sys.exit(1)
        elif overall == "warn":
            print("\n[WARN] Prompt validation found warnings. Review before proceeding.")
            sys.exit(0)
        else:
            print("\n[PASS] Prompt validation passed. Ready for image generation.")
            sys.exit(0)

    except SystemExit:
        raise
    except Exception as exc:
        print(f"\n[ERROR] Validation failed: {exc}")
        sys.exit(2)


if __name__ == "__main__":
    main()
