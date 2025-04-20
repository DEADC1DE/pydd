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
import logging
import sys
from guessit import guessit

colorama.init()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dd.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_path: Path) -> dict:
    try:
        with config_path.open("rb") as f:
            return tomllib.load(f)
    except Exception as e:
        logger.error(f"Error loading configuration file {config_path}: {e}")
        raise

def validate_config(config: dict):
    required_keys = ["paths", "score_patterns"]
    for key in required_keys:
        if key not in config or not config[key]:
            raise ValueError(f"Invalid configuration: '{key}' missing or empty")
    for pattern in config["score_patterns"]:
        if "pattern" not in pattern or "score" not in pattern:
            raise ValueError("Each 'score_pattern' requires 'pattern' and 'score'")
    logger.info("Configuration successfully validated")

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
                    logger.debug(f"Extracted IMDB ID from {nfo}: {match.group(1)}")
                return match.group(1)
        except Exception as e:
            logger.warning(f"Error reading {nfo}: {e}")
    return None

def canonicalize_name(name: str, debug: bool = False) -> str:
    info = guessit(name)
    title = info.get("title", name).lower()
    year = info.get("year", "")
    canonical = f"{title} {year}" if year else title
    if debug:
        logger.debug(f"Canonical name for {name}: {canonical}")
    return canonical

def get_canonical_key(dir_path: Path, debug: bool = False) -> str:
    imdb_id = get_imdb_id_from_directory(dir_path, debug)
    if imdb_id:
        if debug:
            logger.debug(f"Using IMDB ID for {dir_path}: {imdb_id}")
        return f"imdb:{imdb_id}"
    return canonicalize_name(dir_path.name, debug)

def process_base_dir(base_dir: Path, compiled_patterns: dict, delete: bool, dry_run: bool, debug: bool) -> dict:
    if not base_dir.exists():
        logger.warning(f"Directory {base_dir} does not exist")
        return {"processed": 0, "duplicates": 0}
    subdirs = [d for d in base_dir.iterdir() if d.is_dir()]
    dir_info = {}
    for d in subdirs:
        key = get_canonical_key(d, debug)
        dir_info[d] = key
    grouped_dirs = defaultdict(list)
    for d, key in dir_info.items():
        grouped_dirs[key].append(d)
    total_dirs = len(subdirs)
    total_duplicates = 0
    is_interactive = sys.stdout.isatty()
    for key in sorted(grouped_dirs.keys()):
        group = grouped_dirs[key]
        if len(group) > 1:
            logger.info(f"Group: {key}")
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
            for d in group_sorted:
                if d != best_dir:
                    if delete:
                        if dry_run:
                            msg = f"[DRY RUN] Would delete directory: {d} with score: {scores[d]}"
                            if is_interactive:
                                msg = f"\033[93m{msg}\033[0m"
                            logger.info(msg)
                        else:
                            try:
                                shutil.rmtree(d)
                                msg = f"Deleted directory {d} with score: {scores[d]}"
                                if is_interactive:
                                    msg = f"\033[91m{msg}\033[0m"
                                logger.info(msg)
                            except PermissionError:
                                logger.error(f"No permission to delete {d}")
                            except Exception as e:
                                logger.error(f"Error deleting {d}: {e}")
                    else:
                        msg = f"Duplicate directory: {d} with score: {scores[d]}"
                        if is_interactive:
                            msg = f"\033[91m{msg}\033[0m"
                        logger.info(msg)
                    total_duplicates += 1
            msg = f"Retaining directory: {best_dir} with score: {max_score}"
            if is_interactive:
                msg = f"\033[92m{msg}\033[0m"
            logger.info(msg)
    return {"processed": total_dirs, "duplicates": total_duplicates}

def parse_args():
    parser = argparse.ArgumentParser(description="Manage directory duplicates")
    parser.add_argument("--config", default="config.toml", help="Path to configuration file")
    parser.add_argument("--delete", action="store_true", help="Automatically delete duplicates")
    parser.add_argument("--dry-run", action="store_true", help="Dry run without making changes")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    return parser.parse_args()

def main():
    args = parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    config_path = Path(args.config)
    config = load_config(config_path)
    validate_config(config)
    base_dirs = [Path(p) for p in config.get("paths", [])]
    raw_patterns = config.get("score_patterns", [])
    compiled_patterns = compile_score_patterns(raw_patterns)
    total_dirs = 0
    total_duplicates = 0
    for base_dir in base_dirs:
        result = process_base_dir(base_dir, compiled_patterns, args.delete, args.dry_run, args.debug)
        total_dirs += result["processed"]
        total_duplicates += result["duplicates"]
    logger.info(f"\nSummary: {total_dirs} directories processed, {total_duplicates} duplicates found")

if __name__ == "__main__":
    main()