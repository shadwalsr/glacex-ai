"""
promote_classify_prompt.py

Updates config/prompt_versions.yaml to activate a new classify prompt version.

Usage:
    python scripts/promote_classify_prompt.py --classify classify_v2 [--dry-run]
"""

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# .env.local
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(".env.local")
except ImportError:
    print("[WARN] python-dotenv not installed; skipping .env.local load.")

try:
    import yaml
except ImportError:
    print(
        "\n[ERROR] 'pyyaml' package not installed.\n"
        "  Install it with:  pip install pyyaml\n"
        "  or:               uv add pyyaml\n"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONFIG_PATH  = Path("config/prompt_versions.yaml")
PROMPTS_DIR  = Path("prompts")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config(path: Path) -> dict:
    """Load and return the YAML config. Exits on error."""
    if not path.exists():
        print(f"[ERROR] Config file not found: {path}")
        print(
            "  Expected structure:\n"
            "    classify_prompt: classify_v1\n"
            "    extract_prompt:  extract_v2\n"
            "    digest_prompt:   digest_v1\n"
        )
        sys.exit(1)
    try:
        with path.open("r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh) or {}
        return config
    except yaml.YAMLError as exc:
        print(f"[ERROR] Failed to parse {path}: {exc}")
        sys.exit(1)


def save_config(path: Path, config: dict) -> None:
    """Write config dict back to YAML, preserving top-level key order."""
    with path.open("w", encoding="utf-8") as fh:
        fh.write("# Active prompt versions for the GlaceX pipeline.\n")
        fh.write("# Change a version here and commit → active on next run.\n")
        fh.write("# Never delete old prompt files from prompts/.\n")
        yaml.dump(config, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)


def validate_prompt_file(version: str) -> Path:
    """
    Check that prompts/<version>.txt exists.
    Returns the resolved path on success, exits on failure.
    """
    prompt_file = PROMPTS_DIR / f"{version}.txt"
    if not prompt_file.exists():
        print(f"\n[ERROR] Prompt file not found: {prompt_file}")
        available = sorted(PROMPTS_DIR.glob("*.txt")) if PROMPTS_DIR.exists() else []
        if available:
            print("  Available prompt files:")
            for p in available:
                print(f"    • {p}")
        else:
            print(f"  The '{PROMPTS_DIR}' directory is empty or does not exist.")
        sys.exit(1)
    return prompt_file


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote a classify prompt version in config/prompt_versions.yaml."
    )
    parser.add_argument(
        "--classify",
        required=True,
        metavar="VERSION",
        help="Prompt version to activate (e.g. classify_v2). "
             "The file prompts/<VERSION>.txt must exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the change without writing to disk.",
    )
    args = parser.parse_args()

    new_version = args.classify.strip()

    # 1. Validate target prompt file exists
    prompt_file = validate_prompt_file(new_version)

    # 2. Load current config
    config = load_config(CONFIG_PATH)
    current_version = config.get("classify_prompt", "<not set>")

    # 3. Print summary
    print("\n" + "=" * 60)
    print("  GlaceX Prompt Promotion Summary")
    print("=" * 60)
    print(f"  Config file     : {CONFIG_PATH}")
    print(f"  Prompt file     : {prompt_file}")
    print(f"  Current version : {current_version}")
    print(f"  New version     : {new_version}")

    if current_version == new_version:
        print(f"\n  ℹ️  '{new_version}' is already the active classify prompt.")
        print("  No changes needed.\n")
        sys.exit(0)

    if args.dry_run:
        print("\n  🔍 DRY RUN — no files were modified.")
        print(f"     Would change: classify_prompt: {current_version} → {new_version}")
        print()
        sys.exit(0)

    # 4. Apply the change
    config["classify_prompt"] = new_version
    save_config(CONFIG_PATH, config)

    print(f"\n  ✅ Updated classify_prompt: {current_version} → {new_version}")
    print(f"     File written: {CONFIG_PATH}")
    print()
    print("  Next steps:")
    print("    git add config/prompt_versions.yaml")
    print(f'    git commit -m "chore: promote classify prompt to {new_version}"')
    print("    git push")
    print()
    print("  The pipeline will use the new prompt on its next run.")
    print("  Old prompt files are preserved in prompts/ — never deleted.\n")


if __name__ == "__main__":
    main()
