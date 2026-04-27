---
name: pr-review
description: >-
  Review a GitHub PR for rocmlirTriton with a structured checklist covering CI
  status, code quality, confidentiality, LLVM/MLIR standards, Triton submodule
  awareness, and whether the change needs to be back-ported to rocMLIR. Use
  when asked to review a pull request, analyze PR changes, or provide PR
  feedback.
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

Flag any failing checks. Per-check details, file paths, and what each gate looks at live in `ci-pipelines.md`. Quick summary: GitHub Actions (Python lint only), Azure (`rocMLIR.yml`), Jenkins PR matrix (clang-format/tidy on `mfma` row only).

### 3. Review changed files

Read all changed files. Apply the existing checklists -- don't re-derive them:

- `code-review.md` -- coding standards, severity tiers (Critical / Major / Minor), license headers, decision tiers for `external/triton/` patches
- `llvm-cpp-standards.md` -- C++ patterns (debug macros, namespaces, naming, `.editorconfig`)
- `cmake-conventions.md` -- CMake helpers, `external/triton/` style, dialect/tablegen idiom
- `testing-conventions.md` -- lit patterns, `tests.sh` requirements, fusion-test rules, arch/dtype coverage
- `dev-workflow.md` -- adding ops/passes, bridge-pass touch points
- `triton-integration.md` -- bridge passes, replication points, hardware-feature-detection rule, `librockcompiler_deps.cmake` policy
- `project-overview.md` -- confidentiality / unreleased-HW policy

In the report, cite which severity (Critical/Major/Minor from `code-review.md`) applies. Add a **Major (logic)** flag for: redundant/dead code, unnecessarily complex algorithms, opportunities to replace custom code with an existing LLVM/MLIR/Triton utility, opportunities for simplification (e.g. replace loops with LLVM algorithms, merge redundant conditions, reduce nesting).

### 4. Triton-specific concerns

- Any change to `external/triton` SHA must come with the bump checklist (see `skills/triton-bump/SKILL.md`):
  - Updated `Pipelines.cpp` / `TritonToHsaco.cpp` / `tritonUtils.cpp` / `AmdArchDb.cpp` if upstream changed those files
  - `triton-patches/*.patch` re-evaluated; obsolete patches removed
  - `librockcompiler_deps.cmake` regenerated
- Any new pass call that depends on hardware features must use a `rock::*` helper (see `triton-integration.md`)
- New `triton-patches/*.patch` must include a justification in the PR description (link to upstream issue/PR if applicable)

### 5. Other project-specific concerns

- License headers on new files (template in `code-review.md`)
- `librockcompiler_deps.cmake` updated if dependencies change
- Downstream MIGraphX impact for IR/API changes
- New top-level `fusion_*_with_host.mlir` covered by `tests.sh`
- Release branch PRs: also apply release patch checklist (see `skills/release-management/SKILL.md`)

### 6. rocMLIR back-port check

`rocmlirTriton` was forked from `rocMLIR` and most of `mlir/` is still shared between the two trees. For every change that isn't Triton-submodule-only, ask: **"does this fix/feature also need to land in `ROCm/rocMLIR`?"**

Likely needs a back-port (shared with rocMLIR):
- `mlir/lib/Dialect/Rock/` (except `RockToTTIR` / `RockFuncToTritonFunc` / `RockSerializeHostFuncs` / `RockRestoreHostCode`), `mlir/lib/Dialect/MIGraphX/`, `mlir/lib/Conversion/MIGraphXTo*/`, `mlir/lib/Analysis/`
- `mlir/tools/{rocmlir-gen,rocmlir-driver,rocmlir-opt,rocmlir-tuning-driver,rocmlir-lsp-server}/` (excluding any Triton-pipeline registrations)
- `mlir/utils/performance/`, `mlir/utils/jenkins/static-checks/`
- Generic `cmake/` helpers and root CMake options that aren't Triton-specific

rocmlirTriton-only (no back-port needed):
- `external/triton/`, `triton-patches/`, `cmake/triton.cmake`, `scripts/build-llvm.sh`, `cmake.sh`
- `RockToTTIRPass`, `RockFuncToTritonFuncPass`, `TritonToHsacoPass`, the Triton portion of `rock::buildTritonPipeline` / `buildBackendPipeline` in `Pipelines.cpp`, `tritonUtils.cpp`
- `librockcompiler_deps.cmake`, `docs/bump_triton_version.md`, `skills/triton-bump/`, `Jenkinsfile.downstream` (deprecated)

If the change touches shared territory, the PR description should either (a) link to a parallel `ROCm/rocMLIR` PR, (b) include a one-line note explaining why the divergence is intentional, or (c) confirm the file no longer exists / has been refactored on the rocMLIR side. Flag any missing back-port in the report so it's not silently lost.

### 7. Report

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

### rocMLIR Back-port
<List shared paths that need a parallel rocMLIR PR, or "Not applicable">

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
