# rocMLIR AI Coding Rules and Skills

Portable rules and skills for AI-assisted development on [rocMLIR](https://github.com/ROCm/rocMLIR) -- an MLIR-based kernel generator for AMD GPUs.

## Structure

- `rules/` -- 11 rules (plain `.md`, source of truth) with `metadata.yaml` for tool-specific config
- `skills/` -- 9 skills (`SKILL.md` per directory) for on-demand procedural workflows
- `generate.py` -- generates tool-specific output into `generated/`

## Quick start

```bash
# Generate all tool formats
python3 generate.py

# Generate for a specific tool
python3 generate.py --target cursor
python3 generate.py --target claude
python3 generate.py --target copilot
python3 generate.py --target generic
```

## Import into your tool

**Cursor**: copy `generated/cursor/rules/` and `generated/cursor/skills/` to `.cursor/` in your project.

**Claude Code**: copy `generated/claude/CLAUDE.md` and `generated/claude/.claude/` to your project root.

**GitHub Copilot**: copy `generated/copilot/.github/` to your project root.

**Windsurf / Generic**: copy `generated/generic/AGENTS.md` to your project root.

## Rules (auto-applied)

| Rule | Scope | Purpose |
|------|-------|---------|
| project-overview | always | Project context, confidentiality, downstream awareness |
| llvm-cpp-standards | C++ files | LLVM casting, ADT, error handling, naming, includes |
| mlir-passes-patterns | C++ impl | Pass definition, pattern rewriting, conversion targets |
| mlir-tablegen | .td files | Dialect, op, attribute, pass TableGen conventions |
| cmake-conventions | CMake files | Build system helpers and custom functions |
| python-standards | Python files | yapf, flake8, pytest standards |
| code-review | always | Review checklist, license, confidentiality, temp files |
| testing-conventions | test files | Lit, GoogleTest, E2E patterns and substitutions |
| rocmlir-tools | tool sources | rocmlir-gen/driver/opt/tuning-driver CLI reference |
| dev-workflow | C++/TD files | Step-by-step guides for adding ops, passes, conversions |
| ci-pipelines | CI configs | Jenkins, Azure Pipelines, GitHub Actions conventions |

## Skills (on-demand)

| Skill | Trigger | Purpose |
|-------|---------|---------|
| pr-review | "Review PR #1234" | Structured PR review with CI checks |
| self-review | "Review my changes" | Pre-PR self-review with checklist |
| build-test-workflow | "Build and test" | Build, test, lint with structured report |
| upstream-llvm-merge | "Merge upstream LLVM" | Git subtree merge workflow |
| release-management | "Manage release branch" | Release branch and patch workflow |
| perfrunner-usage | "Run benchmarks" | perfRunner.py usage guide |
| tuningrunner-usage | "Tune kernels" | tuningRunner.py usage guide |
| perf-reports-utils | "Generate reports" | Report script usage guide |
| kernel-profiling | "Profile kernel" | rocprofv3 and rocprof-compute workflow |

## License

Apache 2.0 with LLVM Exceptions (same as rocMLIR).
