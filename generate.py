#!/usr/bin/env python3
"""Generate tool-specific rule/skill formats from plain markdown sources.

Reads projects/<project>/rules/*.md + metadata.yaml + skills/*/SKILL.md,
merges with shared/rules/ and shared/skills/, and produces output in
generated/<project>/{cursor,claude,copilot,generic}/.

Usage:
    python3 generate.py --project rocmlir              # all targets for rocmlir
    python3 generate.py --project rocmlir --target cursor
    python3 generate.py                                # all projects, all targets
"""

import argparse
import os
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
PROJECTS_DIR = ROOT / "projects"
SHARED_DIR = ROOT / "shared"
GEN_DIR = ROOT / "generated"


def get_project_dirs(project):
    project_dir = PROJECTS_DIR / project
    return {
        "rules": project_dir / "rules",
        "skills": project_dir / "skills",
        "metadata": project_dir / "rules" / "metadata.yaml",
    }


def load_metadata(dirs):
    with open(dirs["metadata"]) as f:
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

    return meta


def load_rule_content(name, dirs):
    path = dirs["rules"] / f"{name}.md"
    if path.exists():
        return path.read_text()
    shared_path = SHARED_DIR / "rules" / f"{name}.md"
    if shared_path.exists():
        return shared_path.read_text()
    raise FileNotFoundError(f"Rule '{name}' not found in project or shared rules")


def collect_skills(dirs):
    skills = []
    seen = set()

    for skill_dir in sorted(dirs["skills"].iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            skills.append((skill_dir.name, skill_file.read_text(), skill_dir))
            seen.add(skill_dir.name)

    shared_skills = SHARED_DIR / "skills"
    if shared_skills.exists():
        for skill_dir in sorted(shared_skills.iterdir()):
            if skill_dir.name not in seen:
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    skills.append((skill_dir.name, skill_file.read_text(), skill_dir))

    return skills


def generate_cursor(metadata, dirs, gen_out):
    out = gen_out / "cursor"
    rules_out = out / "rules"
    skills_out = out / "skills"
    rules_out.mkdir(parents=True, exist_ok=True)
    skills_out.mkdir(parents=True, exist_ok=True)

    for rule in metadata["rules"]:
        name = rule["name"]
        content = load_rule_content(name, dirs)

        frontmatter_lines = ["---"]
        desc = rule["description"]
        frontmatter_lines.append(f'description: "{desc}"')
        if rule.get("alwaysApply"):
            frontmatter_lines.append("alwaysApply: true")
        elif rule.get("globs"):
            globs = rule["globs"]
            frontmatter_lines.append(f'globs: "{globs}"')
            frontmatter_lines.append("alwaysApply: false")
        frontmatter_lines.append("---")

        mdc_content = "\n".join(frontmatter_lines) + "\n\n" + content
        (rules_out / f"{name}.mdc").write_text(mdc_content)

    for skill_name, _, skill_dir in collect_skills(dirs):
        dst = skills_out / skill_name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(skill_dir, dst)

    print(f"  cursor: {rules_out} ({len(metadata['rules'])} rules, "
          f"{len(list(skills_out.iterdir()))} skills)")


def generate_claude(metadata, dirs, gen_out):
    out = gen_out / "claude"
    out.mkdir(parents=True, exist_ok=True)
    claude_dir = out / ".claude"
    claude_dir.mkdir(exist_ok=True)

    sections = []
    for rule in metadata["rules"]:
        content = load_rule_content(rule["name"], dirs)
        sections.append(content)

    sections.append("\n# Skills\n")
    sections.append("The following skills are available for on-demand use:\n")
    for skill_name, skill_content, _ in collect_skills(dirs):
        body = skill_content.split("---", 2)[-1].strip() if "---" in skill_content else skill_content
        first_line = body.split("\n")[0] if body else skill_name
        sections.append(f"- **{skill_name}**: {first_line}")

    (out / "CLAUDE.md").write_text("\n\n---\n\n".join(sections) + "\n")

    settings = {"permissions": {"allow": ["Read", "Write", "Shell"]}}
    (claude_dir / "settings.json").write_text(
        __import__("json").dumps(settings, indent=2) + "\n")

    skills_src = dirs["skills"]
    skills_link = out / "skills"
    if skills_link.exists() or skills_link.is_symlink():
        skills_link.unlink()
    skills_link.symlink_to(os.path.relpath(skills_src, out))

    print(f"  claude: {out} (CLAUDE.md + .claude/ + skills symlink)")


def generate_copilot(metadata, dirs, gen_out):
    out = gen_out / "copilot"
    gh_dir = out / ".github"
    instr_dir = gh_dir / "instructions"
    gh_dir.mkdir(parents=True, exist_ok=True)
    instr_dir.mkdir(exist_ok=True)

    always_sections = []
    for rule in metadata["rules"]:
        if rule.get("alwaysApply"):
            always_sections.append(load_rule_content(rule["name"], dirs))

    (gh_dir / "copilot-instructions.md").write_text(
        "\n\n---\n\n".join(always_sections) + "\n")

    for rule in metadata["rules"]:
        if rule.get("globs") and not rule.get("alwaysApply"):
            content = load_rule_content(rule["name"], dirs)
            fname = rule["name"].replace("-", "_") + ".instructions.md"
            header = f"<!-- applyTo: {rule['globs']} -->\n\n"
            (instr_dir / fname).write_text(header + content)

    print(f"  copilot: {gh_dir} (copilot-instructions.md + "
          f"{len(list(instr_dir.iterdir()))} instruction files)")


def generate_generic(metadata, dirs, gen_out):
    out = gen_out / "generic"
    out.mkdir(parents=True, exist_ok=True)

    project_name = dirs["rules"].parent.name
    sections = [f"# {project_name} AI Agent Rules and Skills\n"]

    sections.append("## Rules\n")
    for rule in metadata["rules"]:
        content = load_rule_content(rule["name"], dirs)
        sections.append(content)

    sections.append("## Skills\n")
    for skill_name, skill_content, _ in collect_skills(dirs):
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


def list_projects():
    if not PROJECTS_DIR.exists():
        return []
    return sorted(d.name for d in PROJECTS_DIR.iterdir()
                  if d.is_dir() and (d / "rules" / "metadata.yaml").exists())


def run_project(project, target_names):
    dirs = get_project_dirs(project)
    if not dirs["metadata"].exists():
        print(f"  SKIP: {project} (no metadata.yaml)")
        return

    metadata = load_metadata(dirs)
    gen_out = GEN_DIR / project

    for target in target_names:
        TARGETS[target](metadata, dirs, gen_out)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", type=str,
                        help="Generate for a specific project (default: all projects)")
    parser.add_argument("--target", choices=list(TARGETS.keys()),
                        help="Generate only this target (default: all)")
    args = parser.parse_args()

    target_names = [args.target] if args.target else list(TARGETS.keys())
    projects = [args.project] if args.project else list_projects()

    if not projects:
        print("No projects found in projects/")
        return

    for project in projects:
        print(f"Generating {project} ({len(target_names)} target(s))...")
        run_project(project, target_names)

    print("Done.")


if __name__ == "__main__":
    main()
