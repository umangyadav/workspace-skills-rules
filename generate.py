#!/usr/bin/env python3
"""Generate tool-specific rule/skill formats from plain markdown sources.

Reads rules/*.md + rules/metadata.yaml + skills/*/SKILL.md and produces
output in generated/{cursor,claude,copilot,generic}/.

Usage:
    python3 generate.py                  # all targets
    python3 generate.py --target cursor  # single target
"""

import argparse
import os
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
RULES_DIR = ROOT / "rules"
SKILLS_DIR = ROOT / "skills"
GEN_DIR = ROOT / "generated"
METADATA_PATH = RULES_DIR / "metadata.yaml"


def load_metadata():
    with open(METADATA_PATH) as f:
        return yaml.safe_load(f)


def load_rule_content(name):
    path = RULES_DIR / f"{name}.md"
    return path.read_text()


def collect_skills():
    skills = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            skills.append((skill_dir.name, skill_file.read_text()))
    return skills


def generate_cursor(metadata):
    out = GEN_DIR / "cursor"
    rules_out = out / "rules"
    skills_out = out / "skills"
    rules_out.mkdir(parents=True, exist_ok=True)
    skills_out.mkdir(parents=True, exist_ok=True)

    for rule in metadata["rules"]:
        name = rule["name"]
        content = load_rule_content(name)

        frontmatter_lines = ["---"]
        frontmatter_lines.append(f'description: {rule["description"]}')
        if rule.get("alwaysApply"):
            frontmatter_lines.append("alwaysApply: true")
        elif rule.get("globs"):
            frontmatter_lines.append(f'globs: {rule["globs"]}')
            frontmatter_lines.append("alwaysApply: false")
        frontmatter_lines.append("---")

        mdc_content = "\n".join(frontmatter_lines) + "\n\n" + content
        (rules_out / f"{name}.mdc").write_text(mdc_content)

    for skill_name, _ in collect_skills():
        src = SKILLS_DIR / skill_name
        dst = skills_out / skill_name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

    print(f"  cursor: {rules_out} ({len(metadata['rules'])} rules, "
          f"{len(list(skills_out.iterdir()))} skills)")


def generate_claude(metadata):
    out = GEN_DIR / "claude"
    out.mkdir(parents=True, exist_ok=True)
    claude_dir = out / ".claude"
    claude_dir.mkdir(exist_ok=True)

    sections = []
    for rule in metadata["rules"]:
        content = load_rule_content(rule["name"])
        sections.append(content)

    sections.append("\n# Skills\n")
    sections.append("The following skills are available for on-demand use:\n")
    for skill_name, skill_content in collect_skills():
        body = skill_content.split("---", 2)[-1].strip() if "---" in skill_content else skill_content
        first_line = body.split("\n")[0] if body else skill_name
        sections.append(f"- **{skill_name}**: {first_line}")

    (out / "CLAUDE.md").write_text("\n\n---\n\n".join(sections) + "\n")

    settings = {"permissions": {"allow": ["Read", "Write", "Shell"]}}
    (claude_dir / "settings.json").write_text(
        __import__("json").dumps(settings, indent=2) + "\n")

    skills_link = out / "skills"
    if skills_link.exists():
        skills_link.unlink()
    skills_link.symlink_to("../../skills")

    print(f"  claude: {out} (CLAUDE.md + .claude/ + skills symlink)")


def generate_copilot(metadata):
    out = GEN_DIR / "copilot"
    gh_dir = out / ".github"
    instr_dir = gh_dir / "instructions"
    gh_dir.mkdir(parents=True, exist_ok=True)
    instr_dir.mkdir(exist_ok=True)

    always_sections = []
    for rule in metadata["rules"]:
        if rule.get("alwaysApply"):
            always_sections.append(load_rule_content(rule["name"]))

    (gh_dir / "copilot-instructions.md").write_text(
        "\n\n---\n\n".join(always_sections) + "\n")

    for rule in metadata["rules"]:
        if rule.get("globs") and not rule.get("alwaysApply"):
            content = load_rule_content(rule["name"])
            fname = rule["name"].replace("-", "_") + ".instructions.md"
            header = f"<!-- applyTo: {rule['globs']} -->\n\n"
            (instr_dir / fname).write_text(header + content)

    print(f"  copilot: {gh_dir} (copilot-instructions.md + "
          f"{len(list(instr_dir.iterdir()))} instruction files)")


def generate_generic(metadata):
    out = GEN_DIR / "generic"
    out.mkdir(parents=True, exist_ok=True)

    sections = ["# rocMLIR AI Agent Rules and Skills\n"]

    sections.append("## Rules\n")
    for rule in metadata["rules"]:
        content = load_rule_content(rule["name"])
        sections.append(content)

    sections.append("## Skills\n")
    for skill_name, skill_content in collect_skills():
        body = skill_content.split("---", 2)[-1].strip() if "---" in skill_content else skill_content
        sections.append(body)

    full = "\n\n---\n\n".join(sections) + "\n"
    (out / "AGENTS.md").write_text(full)
    (out / ".windsurfrules").write_text(full)

    print(f"  generic: {out} (AGENTS.md + .windsurfrules)")


TARGETS = {
    "cursor": generate_cursor,
    "claude": generate_claude,
    "copilot": generate_copilot,
    "generic": generate_generic,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=list(TARGETS.keys()),
                        help="Generate only this target (default: all)")
    args = parser.parse_args()

    metadata = load_metadata()

    targets = [args.target] if args.target else list(TARGETS.keys())
    print(f"Generating {len(targets)} target(s)...")
    for target in targets:
        TARGETS[target](metadata)

    print("Done.")


if __name__ == "__main__":
    main()
