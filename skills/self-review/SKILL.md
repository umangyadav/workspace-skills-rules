---
name: self-review
description: >-
  Review local branch changes before creating a PR. Checks code quality,
  confidentiality, commit messages, and LLVM/MLIR standards. Use when asked
  to self-review, review my changes, or check my branch before PR.
---

# Self Review

## Usage

"Self-review my changes" or "Review my branch before PR"

## Process

### 1. Gather changes

```bash
git branch --show-current
git status
git diff origin/develop...HEAD
git diff origin/develop...HEAD --name-only
git log origin/develop..HEAD --oneline
```

### 2. Review all changed files

Apply the same checklist as PR review (see `rules/code-review.md`):
- Critical/Major/Minor severity levels
- License headers, naming, tests, error handling
- No unreleased hardware references

### 3. Additional self-review checks

- [ ] No uncommitted changes that should be included
- [ ] No debug/temporary code left (stray `LLVM_DEBUG`, commented-out code, `printf`)
- [ ] Commit messages follow convention (`[AIROCMLIR-NNN]`, `[NFC]`, `[EXTERNAL]`)
- [ ] External changes in separate commits with `[EXTERNAL]` prefix
- [ ] Branch rebased on latest `develop`
- [ ] All new files have license headers
- [ ] Files end with newline, no trailing whitespace

### 4. Report

Use same format as PR review with:
- **Review-Type**: "Self Review"
- **Branch**: `<current-branch> -> develop`
- Include CI status as N/A (not yet pushed)
