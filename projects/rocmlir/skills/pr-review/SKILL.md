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

```bash
gh pr view <number> --json title,body,author,baseRefName,headRefName,files,statusCheckRollup
gh pr diff <number>
gh pr checks <number>
```

### 2. Check CI status

Flag any failing checks:
- GitHub Actions (Python flake8 + yapf, pytest)
- Azure Pipelines (ROCm build/test)
- Jenkins (premerge clang-format/tidy, build, tests)

### 3. Review changed files

Read all changed files. Apply checklists from:
- `rules/code-review.md` -- coding standards, LLVM conventions, review severity levels
- `rules/llvm-cpp-standards.md` -- rocMLIR-specific C++ patterns and idioms
- `rules/cmake-conventions.md` -- CMake functions, options, and build conventions
- `rules/testing-conventions.md` -- Lit test patterns, E2E `.toml` workflow, fusion test requirements
- `rules/dev-workflow.md` -- testing requirements for new ops/features (arch, dtype, edge cases)

**Critical**: unreleased HW references, exceptions, RTTI, `#include <iostream>`, `using namespace std`, static ctors, committed temp files, breaking IR changes
**Major**: naming, verifiers, tests, error handling, memory safety, license headers, external commits separated, CMake updates
**Major (logic)**: redundant/dead code, unnecessarily complex algorithms, opportunities for simplification (e.g., replace loops with LLVM algorithms, merge redundant conditions, reduce nesting). Prefer upstream LLVM/MLIR functionality over custom implementations -- flag cases where an existing upstream utility, pass, or API could replace custom code
**Minor**: include order, comments, early returns, braces, preincrement, trailing whitespace

### 4. Check project-specific concerns

- License headers on new files (SPDX `Apache-2.0 WITH LLVM-exception`)
- `librockcompiler_deps.cmake` updated if deps change
- Downstream MIGraphX impact for IR/API changes
- Release branch PRs: also apply release patch checklist (see `skills/release-management/SKILL.md`) (see `skills/release-management/SKILL.md`)

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
