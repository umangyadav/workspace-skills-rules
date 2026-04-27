# rocmlirTriton Project Overview

rocmlirTriton is a fork/derivative of [rocMLIR](https://github.com/ROCm/rocMLIR) that lowers Rock dialect kernels (convolution, GEMM, attention, fused ops) through [OpenAI Triton](https://github.com/triton-lang/triton)'s TTIR/TTGIR/LLIR pipeline to AMD GPU code. It targets AMD hardware (ROCm).

The compilation arc, the four `rocmlir-driver` pipelines, the Rock<->Triton bridge passes, and the Python-to-C++ replication points all live in `triton-integration.md`. The CLI tools (`rocmlir-gen`, `rocmlir-driver`, `rocmlir-opt`, `rocmlir-tuning-driver`, `rocmlir-translate`, `rocmlir-lsp-server`) and their flags are documented in `rocmlir-tools.md`. Build/test commands live in the `build-test-workflow` skill.

## Key facts

- Repository: [ROCm/rocmlirTriton](https://github.com/ROCm/rocmlirTriton) -- **currently private** (incubating); may be opened up later
- Primary consumer: [MIGraphX](https://github.com/ROCm/AMDMIGraphX) via the `librockCompiler` fat library
- License: Apache 2.0 with LLVM Exceptions (`LICENSE.TXT`)
- CMake project name is still `rocMLIR` (`project(rocMLIR VERSION 2.0.0 ...)`), so binaries and helper functions retain `rocmlir-*` / `add_rocmlir_*` names

## Source layout

- `mlir/` -- all rocmlirTriton sources (edit here)
- `external/triton/` -- **git submodule** of upstream Triton; brings its own `external/triton/llvm-project/` LLVM/MLIR. `mlir-runner` and the `libmlir_*_runtime.so` shared libraries used by `tests.sh` come from `external/triton/llvm-project/build/`
- `triton-patches/*.patch` -- local patches applied on top of the Triton submodule by `scripts/build-llvm.sh`
- `cmake/triton.cmake` -- wires `find_package(MLIR)` and `add_subdirectory(external/triton)` and defines `add_rocmlir_*` helpers
- `scripts/build-llvm.sh`, `cmake.sh`, `tests.sh` -- canonical build/test entry points (see `build-test-workflow` skill)
- `docs/` -- in-tree design docs (`bump_triton_version.md`, `scaled_gemm.md`, `cpu_validation_optimization.md`)

## Commit messages

- Jira: `[AIROCMLIR-NNN] Description (#PR)`
- Plain: `Fix/Add/Update description (#PR)`
- Non-functional: `[NFC] Description`
- Triton bump: `[TRITON-BUMP] Description`
- Local Triton patch update: `[TRITON-PATCH] Description`
- Release backport: `[BACKPORT] Description (#PR)`

## Confidentiality

This repo is **private** today, but treat it as if it could be open-sourced at any time:

- Write code, comments, commit messages, and PR descriptions as if the world will read them tomorrow -- avoid information that would have to be redacted before going public.
- Internal-only references (NDA hardware codenames, unannounced chip IDs, customer names, internal Jira/Confluence URLs, internal Slack/email content) belong in internal trackers, **not** in this repo.
- It is fine to reference unreleased `gfx*` IDs only when they are already mentioned upstream (in the pinned Triton submodule, the LLVM AMDGPU backend, or upstream rocMLIR). Otherwise prefer publicly released `gfx*` identifiers.
- Do not paste customer kernels, model weights, or proprietary IR dumps into the repo (tests, comments, or commit bodies).
- License headers, third-party notices, and Apache 2.0 + LLVM Exceptions language must already be in place on every new file -- "we'll fix headers before going public" is not an acceptable plan (template in `code-review.md`).

## Downstream impact

Breaking changes to Rock dialect IR or C API require coordination with MIGraphX. Always keep `mlir/tools/rocmlir-lib/librockcompiler_deps.cmake` in sync after any dependency change (especially Triton bumps -- regenerated as part of the `triton-bump` skill).


---

# Code Review Checklist

## Pre-commit formatting

Before every commit, run `git clang-format --diff origin/develop` (or the appropriate base branch) and fix any issues. If the diff is non-empty, apply fixes and include them in the commit. This prevents CI failures from the premerge clang-format check.

For changes that touch `external/triton/` or `triton-patches/`, additionally run `pre-commit run --from-ref origin/develop --to-ref HEAD` (or `--from-ref upstream/main` when validating against upstream Triton). This mirrors the upstream Triton hook stack -- ruff, yapf, clang-format (LLVM v19.1.6), mypy, plus the standard `pre-commit-hooks` set (trailing-whitespace, end-of-file-fixer, check-merge-conflict, debug-statements, detect-private-key, etc.).

CI gates and where they run (Jenkins, Azure, GitHub Actions) are summarised in `ci-pipelines.md`; the Python lint config is in `python-standards.md`.

## Reference

- [LLVM Coding Standards](https://llvm.org/docs/CodingStandards.html) -- the authoritative style guide
- `llvm-cpp-standards.md` -- rocmlirTriton-specific C++ patterns (debug macros, casting, namespaces, naming)
- `cmake-conventions.md` -- CMake helpers and `external/triton/` style rules

## Critical (blocks merge)

- No unreleased hardware codenames, unannounced chip IDs, or NDA features (full confidentiality policy in `project-overview.md`)
- No C++ exceptions; use `LogicalResult` / `emitOpError` / `signalPassFailure`
- No RTTI (`dynamic_cast`, `typeid`); use LLVM's `isa`/`cast`/`dyn_cast`
- No special values (e.g. `-1`, `nullptr`) to signal failure; use `FailureOr<>` instead
- No `#include <iostream>`; use LLVM's `raw_ostream` for all output
- No `using namespace std`; always use explicit `std::` prefix
- No static constructors/destructors (global objects with ctors/dtors)
- No committed temp/generated files -- see shared rule `workspace-hygiene`
- No direct edits to `external/triton/`; capture local changes as `triton-patches/*.patch` instead
- Breaking IR or C API changes must be documented and coordinated with MIGraphX
- Triton submodule bumps must come with the C++ replication audit (see `triton-integration.md` and the `triton-bump` skill)

## Major

- Follow DRY, YAGNI, KISS
- No raw `new`/`delete`; use MLIR's allocation utilities, `std::unique_ptr`, or arena-based ownership
- Prefer composition over inheritance; CRTP only where MLIR/LLVM requires it
- Prefer `StringRef`, `ArrayRef`, `MutableArrayRef` over `std::string`, `std::vector` for non-owning parameters
- Prefer `SmallVector` over `std::vector` for small/local collections
- Prefer `llvm::DenseMap` over `std::map`/`std::unordered_map`
- Use `assert` liberally with descriptive messages; use `llvm_unreachable` for impossible paths (not `assert(false)`)
- Restrict visibility: `static` for file-local functions, anonymous namespaces only for class declarations
- No default labels in fully covered switches over enumerations (preserves `-Wswitch`); important when consuming Triton's `ISAFamily` enum
- Use `llvm::sort` instead of `std::sort` to avoid non-determinism
- Naming: classes `CamelCase`, functions/vars `camelBack` (per LLVM style and `.clang-tidy`)
- New ops need `hasVerifier = 1` with `verify()` implementation
- New passes and ops need positive E2E tests and both positive and negative Lit tests with FileCheck (patterns in `testing-conventions.md`)
- Lit tests must follow [MLIR FileCheck best practices](https://mlir.llvm.org/getting_started/TestingGuide/#filecheck-best-practices) -- "tests should be minimal". Bug fixes ship a minimized regression test.
- Errors propagated via `LogicalResult`, never silently dropped
- `librockcompiler_deps.cmake` updated when fat-library deps change (see `triton-integration.md`)
- Hardware feature checks go through `rock::*` helpers (see `triton-integration.md`), not `triton::AMD::TargetInfo`
- License header on new files (template below)
- TODOs must reference a tracking issue: `TODO(#issue-number)`

## Minor

- Include order: main module header, local/private, MLIR/LLVM, stdlib (each sorted lexicographically)
- Headers must be self-contained with proper include guards
- Comments as English prose with proper capitalization; `///` for Doxygen on public APIs
- Prefer early returns; no `else` after `return`
- Prefer preincrement; range-based for loops; don't re-evaluate `end()` in iterator loops
- Omit braces for single simple statements; brace multi-statement / nested blocks
- `auto` only when type is obvious; `auto &` for values, `auto *` for pointers to avoid copies
- Files end with newline; no trailing whitespace

## License headers

All new `.cpp`, `.h`, and `.py` files must include a license header with the correct current year. Verify on every review.

**C++/Header files:**

```
//===- FileName.cpp - Brief description ----------------------------------===//
//
// Part of the MLIR Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
```

**Python files:**

```
# Part of the MLIR Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
```

Checklist: header present on all new source/header/Python files; copyright year matches the current year (not copied from older files); SPDX is exactly `Apache-2.0 WITH LLVM-exception`.

## PR description

Write per the upstream Triton template style: explain **why, not how** ([reference](https://cbea.ms/git-commit/#why-not-how)). Reviewers use the diff to see *what* changed; the description should justify *why* the change is correct and worth landing. Either include a test (lit / unittest / E2E) or call out explicitly why one isn't needed.

## Upstream Triton review conventions (for `external/triton/` and submodule bumps)

When the change touches `external/triton/`, `triton-patches/`, or bumps the Triton SHA, apply these on top of the checklist above:

- **Code style**: Triton uses `BasedOnStyle: LLVM` clang-format -- identical to ours -- so the same `git clang-format` workflow works. Triton-side compile flags (`-fno-exceptions -fno-rtti -Werror -Wno-covered-switch-default -fvisibility=hidden`) are documented in `cmake-conventions.md`; don't introduce code that violates them.
- **Decision tier**: Triton's `CONTRIBUTING.md` distinguishes "uncontroversial" changes (bug fixes, perf wins) from "controversial" ones (IR / API / pass infra). `triton-patches/` that change Triton IR or pass behaviour belong in the controversial tier and need an upstream-direction note in the PR description -- either "this will be upstreamed as PR #N" or "this is a permanent fork because ...".
- **Test placement**: `external/triton/test/` for lit, `external/triton/unittest/` for C++ gtest, `external/triton/python/test/` for E2E Python tests. Avoid creating new test files unless necessary -- extend an existing one.
- **MLIR reproducer**: when a Triton-stage crash happens during review, ask the author for the MLIR reproducer (Triton emits one with `external_resources / mlir_reproducer` metadata). Save it to `/tmp/repro.mlir` and reproduce with `triton-opt /tmp/repro.mlir --run-reproducer`. Don't accept "works on my machine" for compiler crashes.
- **CODEOWNERS awareness**: `external/triton/.github/CODEOWNERS` is per-file at `.h` / `.cpp` granularity (e.g. `lib/Analysis/Alias.cpp @Jokeren`, `lib/Dialect/TritonGPU/Transforms/Pipeline.cpp @ptillet`). When patching one of those files locally, name the upstream owner in the PR description so the reviewer knows whose code we're diverging from -- this also makes upstreaming the patch later much easier.
- **No new contributor checklist**: our Jenkins doesn't enforce upstream's PR template, but the spirit (run pre-commit, add tests, justify trivial-only changes) is the same.

## Branch naming

- Feature: `users/<username>/<description>` or `<jira-id>-<description>`
- Triton bump: `triton-bump-<month>-<year>` or `triton-bump-<commit-prefix>`
- Prefer rebase over merge for clean history


---

# Skill Dispatch

Before starting any task, check whether an available skill matches the user's request. If a skill matches, read its `SKILL.md` and follow the documented process step by step. Do not improvise a workflow when a skill already defines one.

## Trigger keywords -> skill mapping

| If the request mentions...                                              | Use skill            |
|-------------------------------------------------------------------------|----------------------|
| review PR, PR feedback, analyze PR, back-port to rocMLIR                | `pr-review`          |
| build, compile, test, lint, check build, run tests.sh                   | `build-test-workflow`|
| profile, benchmark perf, kernel bottleneck                              | `kernel-profiling`   |
| run benchmarks, perfRunner, performance comparison                      | `perfrunner-usage`   |
| tune, tuning, perfConfig, tuningRunner                                  | `tuningrunner-usage` |
| release branch, cherry-pick, release patch                              | `release-management` |
| bump Triton, update Triton submodule, sync with Triton, add/refresh triton-patch | `triton-bump` |


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
