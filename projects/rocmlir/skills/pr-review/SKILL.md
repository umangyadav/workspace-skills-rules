---
name: pr-review
description: >-
  Review a GitHub PR for rocMLIR with structured checklist covering CI status,
  code quality, confidentiality, and LLVM/MLIR standards. Use when asked to
  review a pull request, analyze PR changes, or provide PR feedback.
---

# PR Review

## Usage

"Review PR #1234" or "Review https://github.com/ROCm/rocMLIR/pull/1234"

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
curl -s "https://api.github.com/repos/ROCm/rocMLIR/pulls/<number>"
curl -s "https://api.github.com/repos/ROCm/rocMLIR/pulls/<number>/files"
curl -s "https://api.github.com/repos/ROCm/rocMLIR/commits/<HEAD_SHA>/check-runs"
curl -s "https://api.github.com/repos/ROCm/rocMLIR/commits/<HEAD_SHA>/status"
```

Use `git show pr-<number>:<filepath>` to read files at their PR-branch state with correct line numbers.

### 2. Check CI status

Flag any failing checks:
- GitHub Actions (Python flake8 + yapf, pytest)
- Azure Pipelines (ROCm build/test)
- Jenkins (premerge clang-format/tidy, build, tests)

### 3. Review changed files

Read all changed files. Apply checklists from:
- `rules/code-review.mdc` -- coding standards, LLVM conventions, review severity levels
- `rules/llvm-cpp-standards.mdc` -- rocMLIR-specific C++ patterns and idioms
- `rules/cmake-conventions.mdc` -- CMake functions, options, and build conventions
- `rules/testing-conventions.mdc` -- Lit test patterns, E2E `.toml` workflow, fusion test requirements
- `rules/dev-workflow.mdc` -- testing requirements for new ops/features (arch, dtype, edge cases)

**Critical**: unreleased HW references, exceptions, RTTI, `#include <iostream>`, `using namespace std`, static ctors, committed temp files, breaking IR changes
**Major**: naming, verifiers, tests, error handling, memory safety, license headers, external commits separated, CMake updates
**Major (logic)**: redundant/dead code, unnecessarily complex algorithms, opportunities for simplification (e.g., replace loops with LLVM algorithms, merge redundant conditions, reduce nesting). Prefer upstream LLVM/MLIR functionality over custom implementations -- flag cases where an existing upstream utility, pass, or API could replace custom code
**Minor**: include order, comments, early returns, braces, preincrement, trailing whitespace

### 4. Check project-specific concerns

- License headers on new files (SPDX `Apache-2.0 WITH LLVM-exception`)
- `librockcompiler_deps.cmake` updated if deps change
- Downstream MIGraphX impact for IR/API changes
- Release branch PRs: also apply release patch checklist (see `skills/release-management/SKILL.md`)

### 5. Report

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

### Recommendations
<Suggestions>

### Verdict
APPROVE / REQUEST_CHANGES / COMMENT
```

## Rules

- Reference issues by `file:line` (not diff-relative)
- Accompany each issue with a proposed fix
- Only flag actual issues, not observations about correct behavior
