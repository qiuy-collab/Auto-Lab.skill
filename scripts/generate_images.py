import json
import os
import re
import sys
import time
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, List, Tuple

warnings.filterwarnings("ignore")

import requests
from requests.exceptions import RequestsDependencyWarning

warnings.filterwarnings("ignore", category=RequestsDependencyWarning)


print_lock = threading.Lock()


def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_env_file() -> dict:
    """Load .env from skill root. Supports both single and multi-upstream modes."""
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


env_vars = load_env_file()


def parse_upstreams() -> Tuple[List[str], List[str], int]:
    """
    Parse upstream API configurations from .env.
    Returns (baseurls, apikeys, count).

    Priority:
    1. BASEURLS + APIKEYS (comma-separated multi-upstream)
    2. BASEURL1/APIKEY1, BASEURL2/APIKEY2, ... (numbered multi-upstream)
    3. BASEURL + APIKEY (single upstream, backward compatible)
    """
    # Mode 1: comma-separated
    baseurls_csv = env_vars.get("BASEURLS", "").strip()
    apikeys_csv = env_vars.get("APIKEYS", "").strip()
    if baseurls_csv and apikeys_csv:
        baseurls = [u.strip() for u in baseurls_csv.split(",") if u.strip()]
        apikeys = [k.strip() for k in apikeys_csv.split(",") if k.strip()]
        count = min(len(baseurls), len(apikeys))
        if count > 0:
            return baseurls[:count], apikeys[:count], count

    # Mode 2: numbered (BASEURL1, APIKEY1, ...)
    idx = 1
    numbered_baseurls = []
    numbered_apikeys = []
    while True:
        bu = env_vars.get(f"BASEURL{idx}", "").strip()
        ak = env_vars.get(f"APIKEY{idx}", "").strip()
        if not bu or not ak:
            break
        numbered_baseurls.append(bu)
        numbered_apikeys.append(ak)
        idx += 1
    if numbered_baseurls:
        return numbered_baseurls, numbered_apikeys, len(numbered_baseurls)

    # Mode 3: single upstream (backward compatible)
    single_url = env_vars.get("BASEURL", "").strip()
    single_key = env_vars.get("APIKEY", "").strip()
    if single_url and single_key:
        return [single_url], [single_key], 1

    return [], [], 0


DEFAULT_POLICY = {
    "default_mode": "generic",
    "auto_append_negative": True,
    "fail_on_prompt_risk": True,
    "forbidden_terms": [
        "流程图",
        "架构图",
        "箭头标注",
        "讲解板",
        "说明面板",
        "悬浮标注",
        "poster",
        "callout",
        "annotation",
        "flowchart",
        "diagram"
    ],
    "ui_density": "low_information_density",
    "crop_browser_chrome": True,
    "forbid_localhost_or_dev_url": True
}

RESOLUTION_ALIASES = {
    "2k_16_9": "2048x1152",
    "2K 16:9": "2048x1152",
    "4k_16_9": "3840x2160",
    "4K 16:9": "3840x2160",
}

SCREENSHOT_NEGATIVE_PROMPT = (
    "Only show content that could naturally appear in a real screen capture. "
    "Do not add explanatory text panels, poster layouts, arrows, flowcharts, split-screen teaching boards, "
    "captions outside the program window, or decorative annotations. "
    "Text may appear only where a real operating system, terminal, IDE, or application would naturally render it. "
    "Show only the necessary information, keep a believable background, avoid high information density, avoid tiny unreadable text, "
    "avoid localhost, 127.0.0.1, dev server URLs, browser address bars, tabs, and malformed UI details."
)


def normalize_policy(config):
    policy = dict(DEFAULT_POLICY)
    policy.update(config.get("image_policy", {}))
    return policy


def normalize_resolution(value):
    return RESOLUTION_ALIASES.get(str(value).strip(), str(value).strip())


def lint_prompt(policy, image_name, prompt, mode):
    if mode != "screenshot_strict":
        return []
    lower_prompt = prompt.lower()
    hits = []
    for term in policy.get("forbidden_terms", []):
        lower_term = term.lower()
        if lower_term not in lower_prompt:
            continue
        idx = lower_prompt.find(lower_term)
        window_start = max(0, idx - 60)
        context_en = lower_prompt[window_start:idx]
        context_zh = prompt[max(0, idx - 12):idx]
        if any(marker in context_en for marker in [" no ", " not ", " without ", "do not add", "don't add", "avoid ", "avoid any "]):
            continue
        if any(marker in context_zh for marker in ["不要", "不要有", "不能有", "无"]):
            continue
        hits.append(term)
    return [f"{image_name}: screenshot_strict prompt contains forbidden term '{term}'" for term in hits]


def build_full_prompt(global_prompt, image_prompt, policy, mode):
    parts = []
    if global_prompt:
        parts.append(global_prompt.strip())
    if image_prompt:
        parts.append(image_prompt.strip())
    if mode == "screenshot_strict" and policy.get("auto_append_negative", True):
        if policy.get("ui_density") == "low_information_density":
            parts.append("Keep the interface information density low. Show only necessary panels and a believable surrounding background.")
        if policy.get("crop_browser_chrome", False):
            parts.append("Do not show browser tabs, browser address bar, or system chrome unless absolutely necessary.")
        if policy.get("forbid_localhost_or_dev_url", False):
            parts.append("Do not show localhost, 127.0.0.1, dev server URLs, or temporary local addresses anywhere in the image.")
        parts.append(SCREENSHOT_NEGATIVE_PROMPT)
    return ", ".join(part for part in parts if part)


def generate_image_task(task_info):
    index = task_info["index"]
    total = task_info["total"]
    name = task_info["name"]
    prompt = task_info["prompt"]
    output_dir = task_info["output_dir"]
    resolution = task_info["resolution"]
    max_retries = task_info.get("max_retries", 3)
    retry_delay = task_info.get("retry_delay", 2)
    base_url = task_info.get("base_url")
    api_key = task_info.get("api_key")
    upstream_index = task_info.get("upstream_index")
    last_error = None

    for attempt in range(max_retries):
        try:
            safe_print(f"[{index}/{total}] start: {name} (attempt {attempt + 1}/{max_retries})")
            result = generate_image_single(
                prompt=prompt,
                output_dir=output_dir,
                resolution=resolution,
                filename=name,
                silent=True,
                base_url=base_url,
                api_key=api_key,
                upstream_index=upstream_index,
            )
            if result:
                safe_print(f"[{index}/{total}] [OK] {name}")
                return {"success": True, "name": name, "file": result, "error": None}
            safe_print(f"[{index}/{total}] [FAIL] {name}, retrying...")
            last_error = "empty image generation result"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            safe_print(f"[{index}/{total}] [ERROR] {name}: {last_error}")

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    safe_print(f"[{index}/{total}] [FAILED] {name} exhausted retries")
    return {"success": False, "name": name, "file": None, "error": last_error}


def resolve_output_dir(config_path: Path, configured_output_dir: Optional[str]) -> Path:
    """Resolve output directory for generated images.

    STRICT RULE: output_dir MUST be explicit in prompt_config.json.
    Falls back to config parent ONLY when config_path is inside an init_run output dir
    (i.e., when config is at <output_dir>/prompt_config.json).
    NEVER falls back to CWD — this prevents workspace scattering.
    """
    if configured_output_dir:
        output_path = Path(configured_output_dir).expanduser()
        if not output_path.is_absolute():
            output_path = (config_path.parent / output_path).resolve()
        else:
            output_path = output_path.resolve()
        return output_path

    # Config resides inside a project output dir (init_run.py created it there).
    # Use <output_dir>/generated_images as the default.
    output_dir = config_path.parent / "generated_images"
    # Verify this looks like a valid init_run output dir (has workflow.json alongside)
    if (config_path.parent / "workflow.json").exists():
        return output_dir.resolve()

    # Config is NOT inside a proper run directory — refuse to guess
    raise SystemExit(
        f"prompt_config.json must have an explicit 'output_dir' field.\n"
        f"Current config: {config_path}\n"
        f"Expected: inside an init_run.py output directory with workflow.json.\n"
        f"Fix: set 'output_dir' in prompt_config.json to the correct project images directory."
    )


def shard_tasks_for_upstream(tasks: list, upstream_index: int, upstream_count: int) -> list:
    """
    Distribute tasks across upstreams using modulo sharding.
    tasks[i]["index"] % upstream_count == upstream_index
    """
    return [t for t in tasks if t["index"] % upstream_count == upstream_index]


def generate_from_config(config_path="examples/prompt_config.example.json",
                         upstream_index: Optional[int] = None,
                         upstream_count: Optional[int] = None,
                         timeout: Optional[int] = None):
    config_path = Path(config_path).expanduser().resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    total_count = config.get("total_count", 1)
    resolution = normalize_resolution(config.get("resolution", "1024x1024"))
    global_prompt = config.get("global_prompt", "")
    output_dir = resolve_output_dir(config_path, config.get("output_dir"))
    images = config.get("images", [])
    max_workers = min(int(config.get("max_workers", 50)), 50, max(total_count, 1))
    max_retries = config.get("max_retries", 3)
    retry_delay = config.get("retry_delay", 2)
    policy = normalize_policy(config)
    config_timeout = config.get("timeout", 180)

    # Determine upstream configuration
    if upstream_count is None:
        upstream_count = config.get("upstream_count", 1)
    if upstream_index is None:
        upstream_index = config.get("upstream_index", 0)
    if timeout is None:
        timeout = config_timeout

    # Detect multi-upstream mode
    baseurls, apikeys, env_upstream_count = parse_upstreams()
    effective_upstream_count = max(upstream_count, env_upstream_count)

    safe_print("=== batch image generation ===")
    safe_print(f"config: {config_path}")
    safe_print(f"count: {total_count}")
    safe_print(f"resolution: {resolution}")
    safe_print(f"workers: {max_workers}")
    safe_print(f"retries: {max_retries}")
    safe_print(f"output_dir: {output_dir}")
    safe_print(f"upstream_mode: {'multi' if effective_upstream_count > 1 else 'single'}")
    safe_print(f"upstream_count: {effective_upstream_count}")
    if effective_upstream_count > 1:
        safe_print(f"upstream_index: {upstream_index} (responsible for images where index % {effective_upstream_count} == {upstream_index})")
    safe_print(f"timeout: {timeout}s")
    safe_print("-" * 50)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine the upstream for this process instance
    task_base_url = None
    task_api_key = None
    if baseurls and effective_upstream_count > 0:
        idx = upstream_index % len(baseurls)
        task_base_url = baseurls[idx]
        task_api_key = apikeys[idx]

    tasks = []
    lint_errors = []
    for i, image_config in enumerate(images[:total_count]):
        name = image_config.get("name", f"image_{i + 1}")
        prompt = image_config.get("prompt", "")
        mode = image_config.get("mode", policy.get("default_mode", "generic"))
        lint_errors.extend(lint_prompt(policy, name, prompt, mode))
        full_prompt = build_full_prompt(global_prompt, prompt, policy, mode)

        tasks.append(
            {
                "index": i + 1,
                "total": total_count,
                "name": name,
                "prompt": full_prompt,
                "output_dir": str(output_dir),
                "resolution": resolution,
                "max_retries": max_retries,
                "retry_delay": retry_delay,
                "base_url": task_base_url,
                "api_key": task_api_key,
                "upstream_index": upstream_index,
            }
        )

    if lint_errors and policy.get("fail_on_prompt_risk", True):
        raise SystemExit("Prompt lint failed:\n" + "\n".join(lint_errors))

    # Shard tasks for this upstream instance
    if effective_upstream_count > 1:
        tasks = shard_tasks_for_upstream(tasks, upstream_index, effective_upstream_count)
        safe_print(f"After sharding: {len(tasks)} task(s) assigned to upstream {upstream_index}")

    if not tasks:
        safe_print("No tasks assigned to this upstream instance. Exiting cleanly.")
        return []

    safe_print(f"starting {len(tasks)} task(s)...")
    start_time = time.time()
    results = []
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(generate_image_task, task): task for task in tasks}
        for future in as_completed(future_to_task):
            completed += 1
            try:
                results.append(future.result())
            except Exception as exc:
                task = future_to_task[future]
                safe_print(f"[ERROR] task {task['name']} failed: {exc}")
                results.append({"success": False, "name": task["name"], "file": None, "error": f"{type(exc).__name__}: {exc}"})

            elapsed = time.time() - start_time
            success_count = sum(1 for item in results if item["success"])
            failed_count = sum(1 for item in results if not item["success"])
            safe_print(
                f"progress {completed}/{len(tasks)} | success {success_count} | failed {failed_count} | elapsed {elapsed:.1f}s"
            )

    total_time = time.time() - start_time
    success_count = sum(1 for item in results if item["success"])
    failed_count = sum(1 for item in results if not item["success"])
    safe_print("=" * 50)
    safe_print("=== done ===")
    safe_print(f"time: {total_time:.2f}s")
    safe_print(f"success: {success_count}/{len(tasks)}")
    safe_print(f"failed: {failed_count}/{len(tasks)}")
    safe_print(f"output_dir: {output_dir}")

    # Strict mode: if ALL images failed, raise error instead of silently returning
    if failed_count == len(tasks) and len(tasks) > 0:
        safe_print("[FATAL] All image generation tasks failed — upstream is likely down.")
        safe_print("Do NOT silently fall back. Fix the upstream API configuration first.")
        raise SystemExit(f"All {failed_count} image generation tasks failed. Upstream API may be down.")

    return results


def generate_image_single(prompt, output_dir=None, resolution="1024x1024", filename=None, silent=False,
                          base_url=None, api_key=None, upstream_index=None, timeout=120):
    resolution = normalize_resolution(resolution)

    # Resolve upstream: explicit params > upstream_index from multi-upstream > .env single
    if not base_url or not api_key:
        baseurls, apikeys, count = parse_upstreams()
        if upstream_index is not None and upstream_index < count:
            base_url = baseurls[upstream_index]
            api_key = apikeys[upstream_index]
        elif count > 0:
            base_url = baseurls[0]
            api_key = apikeys[0]

    if not base_url or not api_key:
        if not silent:
            safe_print("Missing BASEURL or APIKEY in .env")
        return None

    if not output_dir:
        raise SystemExit("output_dir is required for image generation — refusing to use CWD as fallback.")
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    url = f"{base_url.rstrip('/')}/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "size": resolution,
        "quality": "high"
    }

    if not silent:
        safe_print(f"Generating image with prompt: {prompt}")
        safe_print(f"API endpoint: {url}")

    try:
        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.Timeout:
        if not silent:
            safe_print(f"[TIMEOUT] API request timed out after {timeout}s: {url}")
        return None
    except requests.exceptions.ConnectionError as exc:
        if not silent:
            safe_print(f"[CONNECT ERROR] Cannot reach API: {exc}")
        return None
    except requests.exceptions.HTTPError as exc:
        if not silent:
            safe_print(f"[HTTP ERROR] API returned error: {exc}")
        return None

    if "data" not in result or not result["data"]:
        if not silent:
            safe_print(f"Unexpected response: {result}")
        return None

    image_data = result["data"][0]
    file_path = output_path / f"{filename}.png" if filename else output_path / generate_filename_from_prompt(prompt)

    if "url" in image_data:
        image_response = requests.get(image_data["url"], timeout=30)
        image_response.raise_for_status()
        file_path.write_bytes(image_response.content)
        return str(file_path)

    if "b64_json" in image_data:
        import base64

        file_path.write_bytes(base64.b64decode(image_data["b64_json"]))
        return str(file_path)

    if not silent:
        safe_print("Response did not contain image data")
    return None


def generate_filename_from_prompt(prompt):
    stop_words = {
        "的",
        "了",
        "在",
        "是",
        "和",
        "与",
        "及",
        "或",
        "对",
        "把",
        "将",
        "用",
        "一个",
        "一种",
        "进行",
        "用于",
        "系统",
        "页面",
        "界面",
        "显示",
        "真实",
        "实验"
    }
    chinese_chars = re.findall(r"[一-鿿]+", prompt)
    english_words = re.findall(r"[a-zA-Z]+", prompt)

    keywords = []
    for word in chinese_chars:
        if word not in stop_words and len(word) >= 2:
            keywords.append(word)
    for word in english_words:
        if word.lower() not in stop_words and len(word) >= 2:
            keywords.append(word.lower())

    if not keywords:
        clean_prompt = re.sub(r"[^\w\s]", "", prompt)
        clean_prompt = re.sub(r"\s+", "_", clean_prompt.strip())
        keywords = [clean_prompt[:50]]

    filename = "_".join(keywords[:5])
    filename = re.sub(r"[^\w\-_]", "_", filename)
    filename = re.sub(r"_+", "_", filename).strip("_")
    # Limit length to avoid filesystem issues
    if len(filename) > 100:
        filename = filename[:100]
    return f"{filename}.png"


def check_upstream(upstream_index: int = 0, upstream_count: int = 1):
    """Test if the upstream image generation API is reachable."""
    baseurls, apikeys, count = parse_upstreams()
    if not baseurls:
        safe_print("[FAIL] No upstream configured in .env")
        return False

    # Use a temp output dir inside skill root for probe tests (auto-cleaned)
    probe_dir = skill_root() / ".probe_cache"
    probe_dir.mkdir(exist_ok=True)

    # Probe each upstream (or just the assigned one in multi mode)
    indices = range(min(upstream_count, count)) if upstream_count > 1 else [0]
    all_ok = True
    for i in indices:
        if i >= len(baseurls):
            break
        safe_print(f"Probing upstream {i}: {baseurls[i]}")
        test_prompt = "generate a small dog image"
        try:
            result = generate_image_single(
                test_prompt,
                silent=True,
                output_dir=str(probe_dir),
                base_url=baseurls[i],
                api_key=apikeys[i],
                timeout=30
            )
            if result:
                safe_print(f"  [OK] Upstream {i} is available")
                # Clean up probe image
                try:
                    Path(result).unlink(missing_ok=True)
                except Exception:
                    pass
            else:
                safe_print(f"  [FAIL] Upstream {i} returned empty result")
                all_ok = False
        except Exception as exc:
            safe_print(f"  [FAIL] Upstream {i} connection error: {exc}")
            all_ok = False

    return all_ok


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description="GPT Image 2 batch generator for auto-lab.",
        epilog=(
            "Multi-upstream mode:\n"
            "  python generate_images.py --config prompt_config.json --upstreams 3\n"
            "  python generate_images.py --config prompt_config.json --upstream 0\n"
            "  python generate_images.py --config prompt_config.json --upstream 1\n"
            "  python generate_images.py --config prompt_config.json --upstream 2\n"
        )
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to prompt_config.json (default: examples/prompt_config.example.json)"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Test upstream API connectivity without generating images"
    )
    parser.add_argument(
        "--prompt", "-p",
        help="Single test prompt (used with --check or standalone test)"
    )
    parser.add_argument(
        "--upstream", "-u", type=int, default=None,
        help="Specify which upstream to use (0-based index). Use with --upstreams for multi-upstream mode."
    )
    parser.add_argument(
        "--upstreams", "-U", type=int, default=None,
        help="Total number of upstreams for sharding. When > 1, tasks are distributed by index modulo upstreams."
    )
    parser.add_argument(
        "--timeout", "-t", type=int, default=None,
        help="Request timeout in seconds (default: 180 for multi-upstream, 120 for single)."
    )
    return parser.parse_args()


def main():
    safe_print("=== GPT Image 2 batch generator ===")
    args = parse_args()

    if args.check:
        ok = check_upstream(
            upstream_index=args.upstream or 0,
            upstream_count=args.upstreams or 1
        )
        raise SystemExit(0 if ok else 1)

    if args.prompt:
        safe_print(f"Test prompt: {args.prompt}")
        probe_dir = skill_root() / ".probe_cache"
        probe_dir.mkdir(exist_ok=True)
        result = generate_image_single(args.prompt, output_dir=str(probe_dir))
        if result:
            safe_print(f"[SUCCESS] image saved: {result}")
        else:
            safe_print("[FAILED] image generation failed")
        return

    # Determine upstream mode
    baseurls, apikeys, env_upstream_count = parse_upstreams()
    config_upstream_count = 1

    if args.upstreams is not None:
        config_upstream_count = args.upstreams
    elif env_upstream_count > 1:
        config_upstream_count = env_upstream_count
    elif args.upstream is not None:
        # User specified --upstream but not --upstreams, infer from config
        config_upstream_count = max(env_upstream_count, 1)

    # In multi-upstream mode, --upstream is required
    if config_upstream_count > 1 and args.upstream is None:
        # Auto-detect: if only one upstream is specified, use it
        if env_upstream_count == 1:
            args.upstream = 0
        else:
            safe_print(
                f"Multi-upstream mode detected ({config_upstream_count} upstreams). "
                f"Specify --upstream N to select which upstream to use.\n"
                f"Example: python generate_images.py --config prompt_config.json --upstreams {config_upstream_count} --upstream 0"
            )
            raise SystemExit(1)

    timeout = args.timeout or 180 if config_upstream_count > 1 else 120

    config_path = args.config
    if not config_path:
        # In batch mode, require explicit --config. Fall back to example ONLY for --check.
        if args.check or args.prompt:
            config_path = str(skill_root() / "examples" / "prompt_config.example.json")
        else:
            raise SystemExit(
                "Batch image generation requires --config <path/to/prompt_config.json>.\n"
                "The config should be in your init_run output directory.\n"
                "Example: python generate_images.py --config output/my_project/prompt_config.json"
            )
    if not Path(config_path).exists():
        default_config = skill_root() / "examples" / "prompt_config.example.json"
        if default_config.exists():
            config_path = str(default_config)
        else:
            test_prompt = "generate a small dog image"
            safe_print(f"No config found, running test prompt: {test_prompt}")
            result = generate_image_single(test_prompt)
            if result:
                safe_print("[SUCCESS] image generation succeeded")
            else:
                safe_print("[FAILED] image generation failed")
            return

    safe_print(f"Using config file: {config_path}")
    generate_from_config(
        config_path=config_path,
        upstream_index=args.upstream or 0,
        upstream_count=config_upstream_count,
        timeout=timeout
    )


if __name__ == "__main__":
    main()
