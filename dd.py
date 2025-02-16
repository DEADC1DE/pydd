#!/usr/bin/env python3
import re
import shutil
import argparse
from pathlib import Path
from collections import defaultdict
try:
    import tomllib
except ImportError:
    import tomli as tomllib
import colorama
colorama.init()

def load_config(config_path: Path):
    with config_path.open("rb") as f:
        return tomllib.load(f)

def compile_score_patterns(patterns: list) -> dict:
    compiled = {}
    for item in patterns:
        compiled[re.compile(item["pattern"], re.IGNORECASE)] = item["score"]
    return compiled

def calculate_score(dir_name: str, compiled_patterns: dict) -> int:
    score = 0
    for regex, value in compiled_patterns.items():
        if regex.search(dir_name):
            score += value
    return score

def get_imdb_id_from_directory(dir_path: Path, debug: bool = False) -> str:
    nfo_files = list(dir_path.glob("*.nfo"))
    for nfo in nfo_files:
        try:
            content = nfo.read_text(errors="ignore")
            match = re.search(r"(tt\d{7,8})", content)
            if match:
                if debug:
                    print(f"Extracted IMDB id from {nfo}: {match.group(1)}")
                return match.group(1)
        except Exception as e:
            if debug:
                print(f"Error reading {nfo}: {e}")
    return None

def canonicalize_name(name: str, debug: bool = False) -> str:
    m = re.match(r"^(.*?)(\d{4})", name, re.IGNORECASE)
    if m:
        candidate_title = m.group(1).replace('.', ' ').strip()
        candidate_year = m.group(2)
        return f"{candidate_title.lower()} {candidate_year}"
    if debug:
        print(f"No valid candidate found in '{name}'. Using full name.")
    return name.lower()

def get_canonical_key(dir_path: Path, debug: bool = False) -> str:
    imdb_id = get_imdb_id_from_directory(dir_path, debug)
    if imdb_id:
        if debug:
            print(f"Using IMDB id for {dir_path}: {imdb_id}")
        return f"imdb:{imdb_id}"
    return canonicalize_name(dir_path.name, debug)

def process_base_dir(base_dir: Path, compiled_patterns: dict, delete: bool, dry_run: bool, debug: bool = False) -> None:
    if not base_dir.exists():
        print(f"Directory {base_dir} does not exist.")
        return
    directories = [d for d in base_dir.iterdir() if d.is_dir()]
    if debug:
        print(f"Found {len(directories)} directories in {base_dir}")
    dir_info = {}
    for d in directories:
        imdb_id = get_imdb_id_from_directory(d, debug)
        canonical = canonicalize_name(d.name, debug=debug)
        key = f"imdb:{imdb_id}" if imdb_id else canonical
        dir_info[d] = key
    grouped_dirs = defaultdict(list)
    for d, key in dir_info.items():
        grouped_dirs[key].append(d)
    if debug:
        print("Grouping results:")
        for key, group in grouped_dirs.items():
            print(f"  {key}: {len(group)} item(s)")
    for key in sorted(grouped_dirs.keys()):
        group = grouped_dirs[key]
        if len(group) > 1:
            best_dir = None
            max_score = float('-inf')
            scores = {}
            for d in group:
                score = calculate_score(d.name, compiled_patterns)
                scores[d] = score
                if score > max_score:
                    max_score = score
                    best_dir = d
            group_sorted = sorted(group, key=lambda d: d.name.lower())
            print(f"\nGroup: {key}")
            for d in group_sorted:
                if d != best_dir:
                    if delete:
                        if dry_run:
                            print(f"\033[93m[DRY RUN] Would delete directory: {d} with Score: {scores[d]}\033[0m")
                        else:
                            print(f"\033[91mDeleting directory: {d} with Score: {scores[d]}\033[0m")
                            try:
                                shutil.rmtree(d)
                            except Exception as e:
                                print(f"Error deleting {d}: {e}")
                    else:
                        print(f"\033[91mDuplicate directory: {d} with Score: {scores[d]}\033[0m")
            print(f"\033[92mKeeping directory: {best_dir} with Score: {max_score}\033[0m")
        else:
            if debug:
                d = group[0]
                score = calculate_score(d.name, compiled_patterns)
                print(f"{d.name}: Score = {score}")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="simulate deletion without executing")
    parser.add_argument("--delete", action="store_true", help="delete duplicate directories")
    parser.add_argument("--debug", action="store_true", help="enable debug output (shows all groups)")
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    config = load_config(Path("config.toml"))
    base_dirs = [Path(p) for p in config.get("paths", [])]
    raw_patterns = config.get("score_patterns", [])
    compiled_patterns = compile_score_patterns(raw_patterns)
    for base_dir in base_dirs:
        process_base_dir(base_dir, compiled_patterns, args.delete, args.dry_run, args.debug)

if __name__ == "__main__":
    main()
