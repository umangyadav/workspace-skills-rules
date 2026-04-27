---
name: pr-review
description: >-
  Review a GitHub PR for rocmlirTriton with a structured checklist covering CI
  status, code quality, confidentiality, LLVM/MLIR standards, and Triton
  submodule awareness. Use when asked to review a pull request, analyze PR
  changes, or provide PR feedback.
---

# PR Review

## Usage

"Review PR #1234" or "Review https://github.com/ROCm/rocmlirTriton/pull/1234"

## Process

### 1. Fetch PR info

Fetch the PR branch so you can read files at their actual line numbers (needed for `file:line` references later):

```bash
git fetch origin pull/<number>/head:pr-<number>
```

Then gather PR metadata and diff. Prefer `gh` if available; fall back to the GitHub REST API with `curl` if not:

```bash
# Option A: gh CLI
gh pr view <number> --json title,body,author,baseRefName,headRefName,files,statusCheckRollup
gh pr diff <number>
gh pr checks <number>

# Option B: curl fallback (if gh is not installed)
curl -s "https://api.github.com/repos/ROCm/rocmlirTriton/pulls/<number>"
curl -s "https://api.github.com/repos/ROCm/rocmlirTriton/pulls/<number>/files"
curl -s "https://api.github.com/repos/ROCm/rocmlirTriton/commits/<HEAD_SHA>/check-runs"
curl -s "https://api.github.com/repos/ROCm/rocmlirTriton/commits/<HEAD_SHA>/status"
```

Use `git show pr-<number>:<filepath>` to read files at their PR-branch state with correct line numbers.

### 2. Check CI status

Flag any failing checks (see the `ci-pipelines` rule for the full picture):

- GitHub Actions: `Python Lint and Format Check` (flake8 + yapf on changed `mlir/**/*.py` only; nothing else runs in GHA)
- Azure Pipelines: ROCm CI via `rocMLIR.yml@pipelines_repo`
- Jenkins: PR pipeline only (matrix over `vanilla, mfma, navi21, navi3x, navi4x, gfx950`); per row runs `bash cmake.sh` -> `premerge-checks.py` (clang-format/tidy, **only on `mfma` codepath**) -> `bash tests.sh`. Nightly/weekly are currently commented out.

### 3. Review changed files

Read all changed files. Apply checklists from:
- `rules/code-review.mdc` -- coding standards, LLVM conventions, review severity levels
- `rules/llvm-cpp-standards.mdc` -- rocmlirTriton-specific C++ patterns and idioms
- `rules/cmake-conventions.mdc` -- CMake helper functions, MLIR_DIR resolution, options
- `rules/testing-conventions.mdc` -- Lit test patterns, `tests.sh` smoke suite, fusion test requirements
- `rules/dev-workflow.mdc` -- testing requirements for new ops/features (arch, dtype, edge cases)
- `rules/triton-integration.mdc` -- Triton submodule, LLVM build flow, replication points

**Critical**: unreleased HW references, exceptions, RTTI, `#include <iostream>`, `using namespace std`, static ctors, committed temp files, breaking IR changes, direct edits to `external/triton/` (must be `triton-patches/*.patch` instead)
**Major**: naming, verifiers, tests, error handling, memory safety, license headers, CMake updates, missing `rock::*` hardware-feature wrappers when calling Triton APIs
**Major (logic)**: redundant/dead code, unnecessarily complex algorithms, opportunities for simplification (e.g., replace loops with LLVM algorithms, merge redundant conditions, reduce nesting). Prefer upstream LLVM/MLIR/Triton functionality over custom implementations -- flag cases where an existing utility, pass, or API could replace custom code
**Minor**: include order, comments, early returns, braces, preincrement, trailing whitespace

### 4. Triton-specific concerns

- Any change to `external/triton` SHA must come with the bump checklist (see `skills/triton-bump/SKILL.md`):
  - Updated `Pipelines.cpp` / `TritonToHsaco.cpp` / `tritonUtils.cpp` / `AmdArchDb.cpp` if upstream changed those files
  - `triton-patches/*.patch` re-evaluated; obsolete patches removed
  - `librockcompiler_deps.cmake` regenerated
- Any new pass call that depends on hardware features must use a `rock::*` helper, not `triton::AMD::TargetInfo` directly
- New `triton-patches/*.patch` must include a justification in the PR description (link to upstream issue/PR if applicable)

### 5. Other project-specific concerns

- License headers on new files (SPDX `Apache-2.0 WITH LLVM-exception`)
- `librockcompiler_deps.cmake` updated if dependencies change
- Downstream MIGraphX impact for IR/API changes
- New top-level `fusion_*_with_host.mlir` covered by `tests.sh`
- Release branch PRs: also apply release patch checklist (see `skills/release-management/SKILL.md`)

### 6. Report

```markdown
## PR Review: <title>

**PR**: #<number> by <author>
**Branch**: <head> -> <base>

### CI Status
- GitHub Actions: PASS/FAIL/PENDING
- Azure Pipelines: PASS/FAIL/PENDING/N/A
- Jenkins: PASS/FAIL/PENDING/N/A

### Summary
<Brief summary>

### Critical Issues
<List or "None">

### Major Issues
<List or "None">

### Minor Issues
<List or "None">

### Triton Sync Notes
<List or "Not applicable">

### Recommendations
<Suggestions>

### Verdict
APPROVE / REQUEST_CHANGES / COMMENT
```

## Rules

- Reference issues by `file:line` (not diff-relative)
- Accompany each issue with a proposed fix
- Only flag actual issues, not observations about correct behavior
- For Triton-bump PRs, read `docs/bump_triton_version.md` and apply the full bump checklist before approving
