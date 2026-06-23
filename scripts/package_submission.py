import argparse
import json
import os
import zipfile
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Package auto-lab submission contents into submit.zip.")
    parser.add_argument("--config", required=True, help="Path to submission_package.json")
    return parser.parse_args()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (root / path).resolve()
    else:
        path = path.resolve()
    return path


def should_exclude(rel_path: str, exclude_globs: list[str]) -> bool:
    normalized = rel_path.replace("\\", "/")
    return any(Path(normalized).match(pattern) for pattern in exclude_globs)


def collect_files(config_path: Path, config: dict):
    source_root = normalize_path(config_path.parent, config["source_root"])
    include_paths = config.get("include_paths", [])
    exclude_globs = config.get("exclude_globs", [])
    flatten = bool(config.get("flatten", False))

    selected = []
    seen_archives = set()

    for item in include_paths:
        source = normalize_path(source_root, item["path"])
        archive_root = item.get("archive_root", "")
        if not source.exists():
            raise SystemExit(f"Submission include path does not exist: {source}")

        if source.is_file():
            rel_name = source.name if flatten else str(Path(archive_root) / source.name)
            rel_name = rel_name.replace("\\", "/")
            if should_exclude(rel_name, exclude_globs):
                continue
            if rel_name not in seen_archives:
                seen_archives.add(rel_name)
                selected.append((source, rel_name))
            continue

        for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
            rel_tail = file_path.relative_to(source)
            rel_name = str(Path(archive_root) / rel_tail) if not flatten else file_path.name
            rel_name = rel_name.replace("\\", "/")
            if should_exclude(rel_name, exclude_globs):
                continue
            if rel_name not in seen_archives:
                seen_archives.add(rel_name)
                selected.append((file_path, rel_name))

    return source_root, selected


def package_submission(config_path: Path):
    config = load_json(config_path)
    if not config.get("enabled", False):
        raise SystemExit("submission_package.json is not enabled")

    output_zip = normalize_path(config_path.parent, config.get("output_zip", "submit.zip"))
    source_root, files = collect_files(config_path, config)
    if not files:
        raise SystemExit("submission_package.json did not resolve any files to package")

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for source, rel_name in files:
            zf.write(source, rel_name)

    manifest = {
        "source_root": str(source_root),
        "output_zip": str(output_zip),
        "file_count": len(files),
        "files": [{"source": str(source), "archive_path": rel_name, "size": os.path.getsize(source)} for source, rel_name in files],
    }
    manifest_path = output_zip.with_name(output_zip.stem + "_manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Submission package written: {output_zip}")
    print(f"Submission manifest written: {manifest_path}")


def main():
    args = parse_args()
    package_submission(Path(args.config).expanduser().resolve())


if __name__ == "__main__":
    main()
