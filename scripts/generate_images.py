import json
import os
import re
import sys
import time
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

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


def load_env_file():
    env_path = skill_root() / ".env"
    env_vars = {}
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
    last_error = None

    for attempt in range(max_retries):
        try:
            safe_print(f"[{index}/{total}] start: {name} (attempt {attempt + 1}/{max_retries})")
            result = generate_image_single(
                prompt=prompt,
                output_dir=output_dir,
                resolution=resolution,
                filename=name,
                silent=True
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
    if configured_output_dir:
        output_path = Path(configured_output_dir).expanduser()
        if not output_path.is_absolute():
            output_path = (config_path.parent / output_path).resolve()
        else:
            output_path = output_path.resolve()
        return output_path
    return (config_path.parent / "generated_images").resolve()


def generate_from_config(config_path="examples/prompt_config.example.json"):
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

    safe_print("=== batch image generation ===")
    safe_print(f"config: {config_path}")
    safe_print(f"count: {total_count}")
    safe_print(f"resolution: {resolution}")
    safe_print(f"workers: {max_workers}")
    safe_print(f"retries: {max_retries}")
    safe_print(f"output_dir: {output_dir}")
    safe_print("-" * 50)

    output_dir.mkdir(parents=True, exist_ok=True)

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
                "retry_delay": retry_delay
            }
        )

    if lint_errors and policy.get("fail_on_prompt_risk", True):
        raise SystemExit("Prompt lint failed:\n" + "\n".join(lint_errors))

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
    return results


def generate_image_single(prompt, output_dir=None, resolution="1024x1024", filename=None, silent=False):
    resolution = normalize_resolution(resolution)
    base_url = env_vars.get("BASEURL")
    api_key = env_vars.get("APIKEY")
    if not base_url or not api_key:
        if not silent:
            safe_print("Missing BASEURL or APIKEY in .env")
        return None

    output_path = Path(output_dir).expanduser().resolve() if output_dir else (Path.cwd() / "generated_images").resolve()
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

    response = requests.post(url, headers=headers, json=data, timeout=120)
    response.raise_for_status()
    result = response.json()

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
    chinese_chars = re.findall(r"[\u4e00-\u9fff]+", prompt)
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
    return f"{filename}_{int(time.time())}.png"


def check_upstream():
    """Test if the upstream image generation API is reachable."""
    safe_print("=== upstream probe ===")
    test_prompt = "generate a small dog image"
    safe_print(f"Testing upstream connectivity with prompt: {test_prompt}")
    result = generate_image_single(test_prompt, silent=True)
    if result:
        safe_print("[OK] Upstream image generation is available")
        return True
    else:
        safe_print("[FAIL] Upstream image generation is NOT available")
        return False


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description="GPT Image 2 batch generator for auto-lab.",
        epilog="If --config is omitted, uses examples/prompt_config.example.json or runs a single test prompt."
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
    return parser.parse_args()


def check_upstream():
    """Test if the upstream image generation API is reachable."""
    test_prompt = "generate a small dog image"
    safe_print(f"Testing upstream connectivity with prompt: {test_prompt}")
    result = generate_image_single(test_prompt, silent=True)
    if result:
        safe_print("[OK] Upstream image generation is available")
        return True
    else:
        safe_print("[FAIL] Upstream image generation is NOT available")
        return False


def main():
    safe_print("=== GPT Image 2 batch generator ===")
    args = parse_args()

    if args.check:
        ok = check_upstream()
        raise SystemExit(0 if ok else 1)

    if args.prompt:
        safe_print(f"Test prompt: {args.prompt}")
        result = generate_image_single(args.prompt)
        if result:
            safe_print(f"[SUCCESS] image saved: {result}")
        else:
            safe_print("[FAILED] image generation failed")
        return

    if args.config:
        config_path = args.config
        safe_print(f"Using config file: {config_path}")
        generate_from_config(config_path)
        return

    default_config = skill_root() / "examples" / "prompt_config.example.json"
    if default_config.exists():
        safe_print(f"Using config file: {default_config}")
        generate_from_config(str(default_config))
        return

    test_prompt = "generate a small dog image"
    safe_print(f"Test prompt: {test_prompt}")
    result = generate_image_single(test_prompt)
    if result:
        safe_print("[SUCCESS] image generation succeeded")
    else:
        safe_print("[FAILED] image generation failed")


if __name__ == "__main__":
    main()
