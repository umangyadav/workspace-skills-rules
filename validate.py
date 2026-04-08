#!/usr/bin/env python3
"""Validate all rules and skills against best practices.

Checks:
  - SKILL.md frontmatter: name (max 64 chars, lowercase/hyphens/numbers), description (max 1024 chars)
  - SKILL.md body: under 500 lines
  - Rules: under 50 lines (soft), under 500 lines (hard)
  - Generated .mdc: valid YAML frontmatter with required fields
  - All files end with newline
  - No trailing whitespace

Usage:
    python3 validate.py --project rocmlir    # validate one project
    python3 validate.py                      # validate all projects
"""

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
PROJECTS_DIR = ROOT / "projects"
SHARED_DIR = ROOT / "shared"
GEN_DIR = ROOT / "generated"
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


def validate_metadata(rules_dir):
    meta_path = rules_dir / "metadata.yaml"
    print(f"\n--- Metadata: {meta_path.relative_to(ROOT)} ---")
    with open(meta_path) as f:
        meta = yaml.safe_load(f)

    shared_meta_path = SHARED_DIR / "rules" / "metadata.yaml"
    if shared_meta_path.exists():
        with open(shared_meta_path) as f:
            shared_meta = yaml.safe_load(f)
        if shared_meta and "rules" in shared_meta:
            project_names = {r["name"] for r in meta["rules"]}
            for rule in shared_meta["rules"]:
                if rule["name"] not in project_names:
                    meta["rules"].append(rule)

    rule_names = {r["name"] for r in meta["rules"]}
    rule_files = {f.stem for f in rules_dir.glob("*.md")}
    shared_rule_files = {f.stem for f in (SHARED_DIR / "rules").glob("*.md")} if (SHARED_DIR / "rules").exists() else set()
    all_rule_files = rule_files | shared_rule_files

    missing_files = rule_names - all_rule_files
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


def validate_generated(project, gen_out):
    print(f"\n--- Generated output completeness ---")

    cursor_rules_dir = gen_out / "cursor" / "rules"
    cursor_skills_dir = gen_out / "cursor" / "skills"
    if cursor_rules_dir.exists():
        cursor_rules = list(cursor_rules_dir.glob("*.mdc"))
        cursor_skills = list(cursor_skills_dir.iterdir()) if cursor_skills_dir.exists() else []
        ok(f"cursor: {len(cursor_rules)} rules, {len(cursor_skills)} skills")
    else:
        error("cursor: missing generated rules")

    claude_md = gen_out / "claude" / "CLAUDE.md"
    if claude_md.exists():
        ok(f"claude: CLAUDE.md ({claude_md.stat().st_size} bytes)")
    else:
        error("claude: missing CLAUDE.md")

    copilot_main = gen_out / "copilot" / ".github" / "copilot-instructions.md"
    copilot_instr_dir = gen_out / "copilot" / ".github" / "instructions"
    if copilot_main.exists():
        copilot_instr = list(copilot_instr_dir.glob("*.md")) if copilot_instr_dir.exists() else []
        ok(f"copilot: copilot-instructions.md + {len(copilot_instr)} instruction files")
    else:
        error("copilot: missing copilot-instructions.md")

    agents = gen_out / "generic" / "AGENTS.md"
    windsurf = gen_out / "generic" / ".windsurfrules"
    if agents.exists() and windsurf.exists():
        ok(f"generic: AGENTS.md + .windsurfrules")
    else:
        error("generic: missing output files")


def validate_project(project):
    project_dir = PROJECTS_DIR / project
    rules_dir = project_dir / "rules"
    skills_dir = project_dir / "skills"
    gen_out = GEN_DIR / project

    print("=" * 60)
    print(f"Validating project: {project}")
    print("=" * 60)

    validate_metadata(rules_dir)

    print("\n" + "=" * 60)
    print("RULE SOURCE FILES")
    print("=" * 60)
    for rule_file in sorted(rules_dir.glob("*.md")):
        validate_rule_source(rule_file)

    shared_rules_dir = SHARED_DIR / "rules"
    if shared_rules_dir.exists():
        for rule_file in sorted(shared_rules_dir.glob("*.md")):
            validate_rule_source(rule_file)

    print("\n" + "=" * 60)
    print("SKILLS")
    print("=" * 60)
    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.is_dir():
            validate_skill(skill_dir)

    shared_skills = SHARED_DIR / "skills"
    if shared_skills.exists():
        for skill_dir in sorted(shared_skills.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                validate_skill(skill_dir)

    if gen_out.exists():
        print("\n" + "=" * 60)
        print("GENERATED CURSOR .mdc FILES")
        print("=" * 60)
        mdc_dir = gen_out / "cursor" / "rules"
        if mdc_dir.exists():
            for mdc_file in sorted(mdc_dir.glob("*.mdc")):
                validate_mdc(mdc_file)

        print("\n" + "=" * 60)
        print("GENERATED OUTPUT COMPLETENESS")
        print("=" * 60)
        validate_generated(project, gen_out)


def list_projects():
    if not PROJECTS_DIR.exists():
        return []
    return sorted(d.name for d in PROJECTS_DIR.iterdir()
                  if d.is_dir() and (d / "rules" / "metadata.yaml").exists())


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", type=str,
                        help="Validate a specific project (default: all projects)")
    args = parser.parse_args()

    projects = [args.project] if args.project else list_projects()

    if not projects:
        print("No projects found in projects/")
        return 1

    for project in projects:
        validate_project(project)

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
