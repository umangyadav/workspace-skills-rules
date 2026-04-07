#!/usr/bin/env python3
"""Validate all rules and skills against best practices.

Checks:
  - SKILL.md frontmatter: name (max 64 chars, lowercase/hyphens/numbers), description (max 1024 chars)
  - SKILL.md body: under 500 lines
  - Rules: under 50 lines (soft), under 500 lines (hard)
  - Generated .mdc: valid YAML frontmatter with required fields
  - All files end with newline
  - No trailing whitespace
"""

import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
ERRORS = []
WARNINGS = []


def error(msg):
    ERRORS.append(msg)
    print(f"  ERROR: {msg}")


def warn(msg):
    WARNINGS.append(msg)
    print(f"  WARN:  {msg}")


def ok(msg):
    print(f"  OK:    {msg}")


def validate_skill(skill_dir):
    skill_file = skill_dir / "SKILL.md"
    print(f"\n--- Skill: {skill_dir.name} ---")

    if not skill_file.exists():
        error(f"{skill_dir.name}: missing SKILL.md")
        return

    content = skill_file.read_text()
    lines = content.split("\n")

    if not content.endswith("\n"):
        error(f"{skill_dir.name}: file does not end with newline")

    for i, line in enumerate(lines, 1):
        if line != line.rstrip():
            warn(f"{skill_dir.name}:{i}: trailing whitespace")
            break

    line_count = len(lines)
    if line_count > 500:
        error(f"{skill_dir.name}: {line_count} lines (max 500)")
    else:
        ok(f"{line_count} lines (under 500)")

    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        error(f"{skill_dir.name}: missing YAML frontmatter")
        return

    try:
        fm = yaml.safe_load(fm_match.group(1))
    except yaml.YAMLError as e:
        error(f"{skill_dir.name}: invalid YAML frontmatter: {e}")
        return

    name = fm.get("name", "")
    if not name:
        error(f"{skill_dir.name}: missing 'name' in frontmatter")
    elif len(name) > 64:
        error(f"{skill_dir.name}: name '{name}' exceeds 64 chars ({len(name)})")
    elif not re.match(r"^[a-z0-9-]+$", name):
        error(f"{skill_dir.name}: name '{name}' must be lowercase letters/numbers/hyphens")
    else:
        ok(f"name: '{name}'")

    if name and name != skill_dir.name:
        warn(f"{skill_dir.name}: name '{name}' doesn't match directory name")

    desc = fm.get("description", "")
    if not desc:
        error(f"{skill_dir.name}: missing 'description' in frontmatter")
    elif len(desc) > 1024:
        error(f"{skill_dir.name}: description exceeds 1024 chars ({len(desc)})")
    else:
        ok(f"description: {len(desc)} chars")

    if desc:
        has_what = any(w in desc.lower() for w in ["profile", "review", "build", "merge",
                                                     "manage", "run", "tune", "generate"])
        has_when = any(w in desc.lower() for w in ["use when", "use after", "triggered"])
        if not has_what:
            warn(f"{skill_dir.name}: description may be missing WHAT the skill does")
        if not has_when:
            warn(f"{skill_dir.name}: description may be missing WHEN to use it")


def validate_rule_source(rule_file):
    print(f"\n--- Rule: {rule_file.name} ---")
    content = rule_file.read_text()
    lines = content.split("\n")

    if not content.endswith("\n"):
        error(f"{rule_file.name}: file does not end with newline")

    for i, line in enumerate(lines, 1):
        if line != line.rstrip():
            warn(f"{rule_file.name}:{i}: trailing whitespace")
            break

    line_count = len(lines)
    if line_count > 500:
        error(f"{rule_file.name}: {line_count} lines (hard max 500)")
    elif line_count > 50:
        warn(f"{rule_file.name}: {line_count} lines (best practice: under 50)")
    else:
        ok(f"{line_count} lines")

    if not lines[0].startswith("#"):
        warn(f"{rule_file.name}: should start with a markdown heading")
    else:
        ok(f"heading: {lines[0]}")


def validate_mdc(mdc_file):
    print(f"\n--- Generated .mdc: {mdc_file.name} ---")
    content = mdc_file.read_text()

    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        error(f"{mdc_file.name}: missing YAML frontmatter")
        return

    try:
        fm = yaml.safe_load(fm_match.group(1))
    except yaml.YAMLError as e:
        error(f"{mdc_file.name}: invalid YAML frontmatter: {e}")
        return

    if "description" not in fm:
        error(f"{mdc_file.name}: missing 'description' in frontmatter")
    else:
        ok(f"description present")

    if fm.get("alwaysApply"):
        ok("alwaysApply: true")
    elif "globs" in fm:
        ok(f"globs: {fm['globs']}")
    else:
        warn(f"{mdc_file.name}: no globs or alwaysApply set")


def validate_metadata():
    print(f"\n--- Metadata: rules/metadata.yaml ---")
    with open(ROOT / "rules" / "metadata.yaml") as f:
        meta = yaml.safe_load(f)

    rule_names = {r["name"] for r in meta["rules"]}
    rule_files = {f.stem for f in (ROOT / "rules").glob("*.md")}

    missing_files = rule_names - rule_files
    extra_files = rule_files - rule_names

    if missing_files:
        error(f"metadata references rules without .md files: {missing_files}")
    if extra_files:
        warn(f".md files without metadata entries: {extra_files}")

    for rule in meta["rules"]:
        if not rule.get("description"):
            error(f"metadata: rule '{rule['name']}' missing description")
        if not rule.get("alwaysApply") and not rule.get("globs"):
            error(f"metadata: rule '{rule['name']}' has neither alwaysApply nor globs")

    ok(f"{len(meta['rules'])} rules defined in metadata")


def validate_generated():
    print(f"\n--- Generated output completeness ---")
    cursor_rules = list((ROOT / "generated/cursor/rules").glob("*.mdc"))
    cursor_skills = list((ROOT / "generated/cursor/skills").iterdir())
    ok(f"cursor: {len(cursor_rules)} rules, {len(cursor_skills)} skills")

    claude_md = ROOT / "generated/claude/CLAUDE.md"
    if claude_md.exists():
        ok(f"claude: CLAUDE.md ({claude_md.stat().st_size} bytes)")
    else:
        error("claude: missing CLAUDE.md")

    copilot_main = ROOT / "generated/copilot/.github/copilot-instructions.md"
    copilot_instr = list((ROOT / "generated/copilot/.github/instructions").glob("*.md"))
    if copilot_main.exists():
        ok(f"copilot: copilot-instructions.md + {len(copilot_instr)} instruction files")
    else:
        error("copilot: missing copilot-instructions.md")

    agents = ROOT / "generated/generic/AGENTS.md"
    windsurf = ROOT / "generated/generic/.windsurfrules"
    if agents.exists() and windsurf.exists():
        ok(f"generic: AGENTS.md + .windsurfrules")
    else:
        error("generic: missing output files")


def main():
    print("=" * 60)
    print("Validating rocMLIR rules and skills")
    print("=" * 60)

    validate_metadata()

    print("\n" + "=" * 60)
    print("RULE SOURCE FILES")
    print("=" * 60)
    for rule_file in sorted((ROOT / "rules").glob("*.md")):
        validate_rule_source(rule_file)

    print("\n" + "=" * 60)
    print("SKILLS")
    print("=" * 60)
    for skill_dir in sorted((ROOT / "skills").iterdir()):
        if skill_dir.is_dir():
            validate_skill(skill_dir)

    print("\n" + "=" * 60)
    print("GENERATED CURSOR .mdc FILES")
    print("=" * 60)
    for mdc_file in sorted((ROOT / "generated/cursor/rules").glob("*.mdc")):
        validate_mdc(mdc_file)

    print("\n" + "=" * 60)
    print("GENERATED OUTPUT COMPLETENESS")
    print("=" * 60)
    validate_generated()

    print("\n" + "=" * 60)
    print(f"SUMMARY: {len(ERRORS)} errors, {len(WARNINGS)} warnings")
    print("=" * 60)

    if ERRORS:
        print("\nErrors:")
        for e in ERRORS:
            print(f"  - {e}")

    if WARNINGS:
        print("\nWarnings:")
        for w in WARNINGS:
            print(f"  - {w}")

    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
