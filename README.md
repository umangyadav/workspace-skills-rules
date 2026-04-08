# AI Coding Rules and Skills

Portable rules and skills for AI-assisted development, organized by project.

## Structure

```
projects/
  <project>/
    rules/          # project-specific rules (.md) + metadata.yaml
    skills/         # project-specific skills (SKILL.md per directory)
shared/
  rules/            # rules shared across projects
  skills/           # skills shared across projects
generated/
  <project>/
    cursor/         # .mdc rules + skills
    claude/         # CLAUDE.md + .claude/
    copilot/        # .github/ instructions
    generic/        # AGENTS.md + .windsurfrules
generate.py         # generates tool-specific output
validate.py         # validates rules and skills
```

## Quick start

```bash
# Generate all projects, all targets
python3 generate.py

# Generate for a specific project
python3 generate.py --project rocmlir

# Generate a specific project + target
python3 generate.py --project rocmlir --target cursor

# Validate
python3 validate.py --project rocmlir
```

## Import into your tool

**Cursor**:

Option 1 -- Symlink (recommended for local dev):
```bash
cd <your-project>
mkdir -p .cursor
ln -s <path-to-this-repo>/generated/<project>/cursor/rules .cursor/rules
ln -s <path-to-this-repo>/generated/<project>/cursor/skills .cursor/skills
```

Option 2 -- Copy files:
```bash
cp -r <path-to-this-repo>/generated/<project>/cursor/rules/ .cursor/rules/
cp -r <path-to-this-repo>/generated/<project>/cursor/skills/ .cursor/skills/
```

Option 3 -- Git submodule in your project:
```bash
git submodule add <this-repo-url> .cursor/ai-rules
ln -s ai-rules/generated/<project>/cursor/rules .cursor/rules
ln -s ai-rules/generated/<project>/cursor/skills .cursor/skills
```

Option 4 -- Remote rules via GitHub (experimental):
In Cursor Settings > Rules, add the GitHub repo URL under "Remote Rules". Cursor clones the rules into `~/.cursor/projects/{project}/rules/`. See [Cursor docs](https://cursor.com/docs/context/rules#remote-rules-via-github). Note: this feature currently has a [known issue](https://forum.cursor.com/t/remote-rules-via-github/148949) where imported rules may not activate. Use Options 1-3 until this is resolved.

**Claude Code**: copy `generated/<project>/claude/CLAUDE.md` and `generated/<project>/claude/.claude/` to your project root.

**GitHub Copilot**: copy `generated/<project>/copilot/.github/` to your project root.

**Windsurf / Generic**: copy `generated/<project>/generic/AGENTS.md` to your project root.

## Adding a new project

1. Create `projects/<project-name>/rules/` and `projects/<project-name>/skills/`
2. Add a `metadata.yaml` in the rules directory defining rules and their scopes
3. Add rule `.md` files and skill directories
4. Run `python3 generate.py --project <project-name>`
5. Run `python3 validate.py --project <project-name>`

## Current projects

### rocmlir

[rocMLIR](https://github.com/ROCm/rocMLIR) -- an MLIR-based kernel generator for AMD GPUs.

- 9 rules, 7 skills
- See `projects/rocmlir/` for details

## License

MIT
