#!/usr/bin/env python3
"""ManageSim health check — validates config, env vars, and pipeline configs."""

import os
import sys
import yaml
from pathlib import Path


def check_config():
    """Validate managesim.yaml configuration."""
    config_path = os.environ.get("MANAGESIM_CONFIG", "config/managesim.yaml")

    if not os.path.exists(config_path):
        # Check for example config
        example = "config/managesim.example.yaml"
        if os.path.exists(example):
            print(f"  [WARN] No personal config. Run: ./scripts/init-personal.sh")
            config_path = example
        else:
            print(f"  [FAIL] Config not found: {config_path}")
            return False

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"  [FAIL] Invalid YAML: {e}")
        return False

    # Required fields
    errors = []
    if not config.get("version"):
        errors.append("Missing 'version'")
    if not config.get("discord", {}).get("guild_id"):
        errors.append("Missing 'discord.guild_id'")
    if not config.get("server", {}).get("name"):
        errors.append("Missing 'server.name'")
    if not config.get("personal_assistant", {}).get("bot_token_env"):
        errors.append("Missing 'personal_assistant.bot_token_env'")

    for project in config.get("projects", []):
        if not project.get("id"):
            errors.append(f"Project missing 'id'")
        if not project.get("bot_token_env"):
            errors.append(f"Project '{project.get('id', '?')}' missing 'bot_token_env'")

    if errors:
        for e in errors:
            print(f"  [FAIL] {e}")
        return False

    print(f"  [OK] Config valid ({len(config.get('projects', []))} projects)")
    return True


def check_env():
    """Check .env file and required environment variables."""
    env_path = ".env"
    if not os.path.exists(env_path):
        print(f"  [WARN] No .env file. Copy .env.example to .env")
        return True  # Warning, not failure

    # Check for key variables
    required = ["ANTHROPIC_API_KEY"]
    missing = [v for v in required if not os.environ.get(v)]

    if missing:
        print(f"  [WARN] Missing env vars: {', '.join(missing)}")
        return True  # Warning, not failure

    print(f"  [OK] Environment variables present")
    return True


def check_pipelines():
    """Validate pipeline configuration files."""
    pipelines_dir = "config/pipelines"
    if not os.path.exists(pipelines_dir):
        print(f"  [FAIL] Pipelines directory not found: {pipelines_dir}")
        return False

    valid = 0
    for fname in os.listdir(pipelines_dir):
        if not fname.endswith(".yaml"):
            continue

        path = os.path.join(pipelines_dir, fname)
        try:
            with open(path) as f:
                config = yaml.safe_load(f)

            # Validate pipeline structure
            if not config.get("states"):
                print(f"  [FAIL] {fname}: missing 'states'")
                continue
            if not config.get("transitions"):
                print(f"  [FAIL] {fname}: missing 'transitions'")
                continue

            # Check all transition targets are valid states
            states = set(config["states"])
            for source, targets in config["transitions"].items():
                if source not in states:
                    print(f"  [FAIL] {fname}: unknown source state '{source}'")
                    continue
                for target in targets:
                    if target not in states:
                        print(f"  [FAIL] {fname}: unknown target state '{target}' in {source}")

            valid += 1
        except yaml.YAMLError as e:
            print(f"  [FAIL] {fname}: invalid YAML: {e}")

    print(f"  [OK] {valid} valid pipeline(s)")
    return valid > 0


def check_directories():
    """Check required directories exist."""
    required_dirs = [
        "config", "config/pipelines", "config/templates",
        "pipeline", "knowledge", "asset_base",
        "gateway/src", "evolution", "orchestrator/src",
        "creators", "skills", "tools", "scripts",
    ]

    missing = [d for d in required_dirs if not os.path.isdir(d)]
    if missing:
        for d in missing:
            print(f"  [FAIL] Missing directory: {d}")
        return False

    print(f"  [OK] All {len(required_dirs)} directories present")
    return True


def main():
    print("ManageSim Health Check")
    print("=" * 40)

    results = {}

    print("\n1. Directories:")
    results["directories"] = check_directories()

    print("\n2. Configuration:")
    results["config"] = check_config()

    print("\n3. Environment:")
    results["env"] = check_env()

    print("\n4. Pipelines:")
    results["pipelines"] = check_pipelines()

    # Summary
    print("\n" + "=" * 40)
    failures = [k for k, v in results.items() if not v]
    if failures:
        print(f"FAILED: {', '.join(failures)}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
