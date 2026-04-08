# rocMLIR Project Overview

rocMLIR is an MLIR-based convolution, GEMM, attention, and fused kernel generator targeting AMD GPUs (ROCm).

## Key facts

- Primary consumer: [MIGraphX](https://github.com/ROCm/AMDMIGraphX) via `libRockCompiler` fat library
- Part of the [ROCm](https://github.com/ROCm) ecosystem (separate repo, not part of [rocm-libraries](https://github.com/ROCm/rocm-libraries))
- License: Apache 2.0 with LLVM Exceptions

## Source layout

- `mlir/` -- all rocMLIR sources (edit here)
- `external/llvm-project/` -- vendored LLVM/MLIR (rarely needs changes; use `[EXTERNAL]` commit prefix when modifying)
- `external/mlir-hal/` -- vendored MHAL dependency (being decoupled; see PR #2333, #2325; use `[EXTERNAL]` commit prefix when modifying)

## Tools

- `rocmlir-gen` -- generate Rock dialect kernels and driver code to run/validate kernel output
- `rocmlir-driver` -- lower and run kernels through pipelines (`-c` for default full pipeline)
- `rocmlir-opt` -- MLIR optimizer with Rock passes
- `rocmlir-tuning-driver` -- tune kernels by sweeping perf configs and selecting the best

## Build

```
cmake -G Ninja .. -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++
ninja check-rocmlir  # builds everything and runs all tests
```

## Commit messages

- Jira: `[AIROCMLIR-NNN] Description (#PR)`
- Plain: `Fix/Add/Update description (#PR)`
- Non-functional: `[NFC] Description`
- External: `[EXTERNAL] Description`
- Release backport: `[BACKPORT] Description (#PR)` (cherry-picks to release branches)

## Confidentiality

This is a public repo. Never reference unreleased AMD hardware codenames, unannounced chip IDs, NDA-protected features, or internal project names. Use only publicly released `gfx*` identifiers.

## Downstream impact

Breaking changes to Rock dialect IR or C API require coordination with MIGraphX. Always keep `librockcompiler_deps.cmake` in sync.


---

# Code Review Checklist

## Pre-commit formatting

Before every commit, run `git clang-format --diff origin/develop` (or the appropriate base branch) and fix any issues. If the diff is non-empty, apply fixes and include them in the commit. This prevents CI failures from the premerge clang-format check.

## Premerge CI gates

- **clang-format**: `git-clang-format` vs base (LLVM style, no diff allowed)
- **clang-tidy**: errors fail, warnings tolerated
- **Python lint/format**: flake8 + yapf on changed `mlir/**/*.py` (GitHub Actions)
- **Python tests**: pytest on `mlir/utils/performance/tests/` -- no GPU required (GitHub Actions)
- **Copilot code review**: automated AI review on PRs (GitHub Actions)

## Reference

- [LLVM Coding Standards](https://llvm.org/docs/CodingStandards.html) -- the authoritative style guide; all rules below derive from or extend it

## Critical (blocks merge)

- No unreleased hardware codenames, unannounced chip IDs, or NDA features in code/comments/commits/docs
- No C++ exceptions; use `LogicalResult` / `emitOpError` / `signalPassFailure`
- No RTTI (`dynamic_cast`, `typeid`); use LLVM's `isa`/`cast`/`dyn_cast`
- No special values (e.g. `-1`, `nullptr`) to signal failure; use `FailureOr<>` instead
- No `#include <iostream>`; use LLVM's `raw_ostream` for all output
- No `using namespace std`; always use explicit `std::` prefix
- No static constructors/destructors (global objects with ctors/dtors)
- No committed temp/generated files (build artifacts, `*.pyc`, editor files, secrets, profiler output) -- see shared rule `workspace-hygiene`
- Breaking IR or C API changes must be documented and coordinated with MIGraphX

## Major

- Follow DRY (don't repeat yourself), YAGNI (you aren't gonna need it), KISS (keep it simple)
- No raw `new`/`delete`; use MLIR's allocation utilities, `std::unique_ptr`, or arena-based ownership to avoid leaks and use-after-free
- Prefer composition over inheritance; use CRTP only where MLIR/LLVM requires it
- Prefer `StringRef`, `ArrayRef`, `MutableArrayRef` over `std::string`, `std::vector` for non-owning parameters
- Prefer `SmallVector` over `std::vector` for small/local collections
- Prefer `llvm::DenseMap` over `std::map`/`std::unordered_map`
- Use `assert` liberally with descriptive messages; use `llvm_unreachable` for impossible paths (not `assert(false)`)
- Prefer C++-style casts (`static_cast`, `const_cast`) over C-style casts
- Restrict visibility: use `static` for file-local functions, anonymous namespaces only for class declarations
- No default labels in fully covered switches over enumerations (preserves `-Wswitch`)
- Use `llvm::sort` instead of `std::sort` to avoid non-determinism with equal elements
- Naming: classes `CamelCase`, functions/vars `camelBack` (per LLVM style)
- New ops need `hasVerifier = 1` with `verify()` implementation
- New passes and ops need positive E2E tests and both positive and negative Lit tests with FileCheck
- New optimizations must verify presence of expected IR ops/instructions via FileCheck
- Errors propagated via `LogicalResult`, never silently dropped
- `librockcompiler_deps.cmake` updated when dependencies change
- License header on new files (SPDX `Apache-2.0 WITH LLVM-exception`)
- External changes (`external/`) in separate commits with `[EXTERNAL]` prefix
- TODOs must reference a tracking issue: `TODO(#issue-number)`

## Minor

- Include order: main module header, local/private, MLIR/LLVM, stdlib (each sorted lexicographically)
- Headers must be self-contained with proper include guards
- Comments as English prose with proper capitalization; use `///` for Doxygen on public APIs
- Prefer early returns; no `else` after `return`
- Prefer preincrement (`++i`) over postincrement (`i++`)
- Prefer range-based for loops; don't re-evaluate `end()` in explicit iterator loops
- Omit braces for single simple statements; use braces for multi-statement or nested blocks
- `auto` only when type is obvious; `auto &` for values, `auto *` for pointers to avoid copies
- Don't use `inline` for functions defined in class bodies (already implicitly inline)
- Spaces before parentheses only in control flow (`if (x)`), not function calls (`foo(x)`)
- Files end with newline; no trailing whitespace

## License headers

All new `.cpp`, `.h`, and `.py` files must include a license header with the correct current year. Verify on every review.

**C++/Header files (`.cpp`, `.h`):**

```
//===- FileName.cpp - Brief description ----------------------------------===//
//
// Part of the MLIR Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
```

**Python files (`.py`):**

```
# Part of the MLIR Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
```

**Review checklist:**
- Header present on all new source, header, and Python files
- Copyright year matches the current year (not copied from older files)
- SPDX identifier is exactly `Apache-2.0 WITH LLVM-exception`

## Branch naming

- Feature: `users/<username>/<description>` or `<jira-id>-<description>`
- Upstream merge: `upstream-merge-<month>-<year>`
- Prefer rebase over merge for clean history


---

# Skill Dispatch

Before starting any task, check whether an available skill matches the user's request. Skills are located in `.cursor/skills/*/SKILL.md`. Read the matching skill file and follow its process before doing anything else.

## Trigger keywords → skill mapping

| If the request mentions...                              | Use skill            |
|---------------------------------------------------------|----------------------|
| review PR, PR feedback, analyze PR                      | `pr-review`          |
| build, compile, test, lint, check build                 | `build-test-workflow` |
| profile, benchmark perf, kernel bottleneck              | `kernel-profiling`   |
| run benchmarks, perfRunner, performance comparison      | `perfrunner-usage`   |
| tune, tuning, perfConfig, tuningRunner                  | `tuningrunner-usage` |
| release branch, cherry-pick, release patch              | `release-management` |
| merge LLVM, upstream merge, subtree pull                | `upstream-llvm-merge`|

If a skill matches, read its `SKILL.md` and follow the documented process step by step. Do not improvise a workflow when a skill already defines one.


---

# Workspace Hygiene

## Never commit temp or generated files

Build artifacts, `*.pyc`, editor configs, secrets, and profiler output must not be committed. Ensure `.gitignore` covers these.

## Plan files and scratch notes

Keep plan files, scratch notes, and working documents in a git-excluded directory (e.g., `plans/` added to `.gitignore`). Do not commit them.

## Profiling and log output

Profiling output (`.rocprofv3/`, `att_dump/`, `*.csv`, `*.pftrace`, `*.json` traces), logs, and other temp files should go in a dedicated directory outside the source tree (e.g., `/tmp/<project>-profiling/`). Never commit profiling results to the repo.

## .gitignore checklist

Verify these are excluded:
- `build*/`, `*.pyc`, `*.orig`, `.cache/`, `.clangd/`
- `plans/`, `scratch/`, `notes/`
- `*.profraw`, `*.profdata`, `att_dump/`, `*.pftrace`
- Editor files: `.vscode/`, `.idea/`, `*.sw?`, `*~`

