# Code Review Checklist

## Pre-commit formatting

Before every commit, run `git clang-format --diff origin/develop` (or the appropriate base branch) and fix any issues. If the diff is non-empty, apply fixes and include them in the commit. This prevents CI failures from the premerge clang-format check.

For changes that touch `external/triton/` or `triton-patches/`, additionally run `pre-commit run --from-ref origin/develop --to-ref HEAD` (or `--from-ref upstream/main` when validating against upstream Triton). This mirrors the upstream Triton hook stack -- ruff, yapf, clang-format (LLVM v19.1.6), mypy, plus the standard `pre-commit-hooks` set (trailing-whitespace, end-of-file-fixer, check-merge-conflict, debug-statements, detect-private-key, etc.).

## Premerge CI gates

- **clang-format**: `git-clang-format` vs base (LLVM style, no diff allowed) -- on Jenkins this gate runs **only on the `mfma` matrix row** via `mlir/utils/jenkins/static-checks/premerge-checks.py`
- **clang-tidy**: errors fail, warnings tolerated; rules in `.clang-tidy` (`llvm-*`, `misc-*`, `readability-identifier-naming`); same `mfma`-only gating
- **Python lint/format**: flake8 + yapf on changed `mlir/**/*.py` (GitHub Actions, see `.github/workflows/ci.yml`); no pytest gate exists yet
- **Azure Pipelines**: ROCm CI (`.azuredevops/rocm-ci.yml`) on push/PR to `develop`/`mainline` (uses ROCm/ROCm's `rocMLIR.yml` template)
- **Jenkins**: PR pipeline only today (`Jenkinsfile`, private CI); nightly/weekly stages exist in source but are commented out. `Jenkinsfile.downstream` is deprecated (public CI is no longer used) and `Jenkinsfile.release` only stores release builds.

## Reference

- [LLVM Coding Standards](https://llvm.org/docs/CodingStandards.html) -- the authoritative style guide

## Critical (blocks merge)

- No unreleased hardware codenames, unannounced chip IDs, or NDA features in code/comments/commits/docs
- No C++ exceptions; use `LogicalResult` / `emitOpError` / `signalPassFailure`
- No RTTI (`dynamic_cast`, `typeid`); use LLVM's `isa`/`cast`/`dyn_cast`
- No special values (e.g. `-1`, `nullptr`) to signal failure; use `FailureOr<>` instead
- No `#include <iostream>`; use LLVM's `raw_ostream` for all output
- No `using namespace std`; always use explicit `std::` prefix
- No static constructors/destructors (global objects with ctors/dtors)
- No committed temp/generated files (build artifacts, `*.pyc`, editor files, secrets, profiler output) -- see shared rule `workspace-hygiene`
- No direct edits to `external/triton/`; capture local changes as `triton-patches/*.patch` instead
- Breaking IR or C API changes must be documented and coordinated with MIGraphX
- Triton submodule bumps in `external/triton` must come with the C++ replication audit (see `triton-integration.md` and the `triton-bump` skill)

## Major

- Follow DRY (don't repeat yourself), YAGNI (you aren't gonna need it), KISS (keep it simple)
- No raw `new`/`delete`; use MLIR's allocation utilities, `std::unique_ptr`, or arena-based ownership
- Prefer composition over inheritance; CRTP only where MLIR/LLVM requires it
- Prefer `StringRef`, `ArrayRef`, `MutableArrayRef` over `std::string`, `std::vector` for non-owning parameters
- Prefer `SmallVector` over `std::vector` for small/local collections
- Prefer `llvm::DenseMap` over `std::map`/`std::unordered_map`
- Use `assert` liberally with descriptive messages; use `llvm_unreachable` for impossible paths (not `assert(false)`)
- Prefer C++-style casts (`static_cast`, `const_cast`) over C-style casts
- Restrict visibility: `static` for file-local functions, anonymous namespaces only for class declarations
- No default labels in fully covered switches over enumerations (preserves `-Wswitch`); important when consuming Triton's `ISAFamily` enum
- Use `llvm::sort` instead of `std::sort` to avoid non-determinism with equal elements
- Naming: classes `CamelCase`, functions/vars `camelBack` (per LLVM style and `.clang-tidy`)
- New ops need `hasVerifier = 1` with `verify()` implementation
- New passes and ops need positive E2E tests and both positive and negative Lit tests with FileCheck
- New optimizations must verify presence of expected IR ops/instructions via FileCheck
- Lit tests must follow [MLIR FileCheck best practices](https://mlir.llvm.org/getting_started/TestingGuide/#filecheck-best-practices) -- in particular "tests should be minimal". Don't dump a full Python-generated module; reduce to the smallest IR fragment that exercises the change. Bug fixes specifically should ship a minimized regression test.
- Errors propagated via `LogicalResult`, never silently dropped
- `librockcompiler_deps.cmake` updated when fat-library dependencies change
- Hardware feature checks go through `rock::*` helpers (e.g. `rock::supportsTDM`), not `triton::AMD::TargetInfo` directly
- License header on new files (SPDX `Apache-2.0 WITH LLVM-exception`)
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

## PR description

Write the description per the upstream Triton template style: explain **why, not how** ([reference](https://cbea.ms/git-commit/#why-not-how)). Reviewers use the diff to see *what* changed; the description should justify *why* the change is correct and worth landing. Either include a test (lit / unittest / E2E) or call out explicitly why one isn't needed.

## Upstream Triton review conventions (for `external/triton/` and submodule bumps)

When the change touches `external/triton/`, `triton-patches/`, or bumps the Triton SHA, apply these upstream conventions on top of the rocMLIR review checklist above:

- **Code style**: Triton uses `BasedOnStyle: LLVM` clang-format -- identical to ours -- so the same `git clang-format` workflow works. Triton-side libraries also build with `-fno-exceptions -fno-rtti -Werror -Wno-covered-switch-default -fvisibility=hidden`; don't introduce code that violates these.
- **Decision tier**: Triton's `CONTRIBUTING.md` distinguishes "uncontroversial" changes (bug fixes, perf wins with reasonable trade-offs) from "controversial" ones (IR / API / pass infra changes). Patches in `triton-patches/` that change Triton IR or pass behaviour belong in the controversial tier and need an explicit upstream-direction note in the PR description -- either "this will be upstreamed as PR #N" or "this is a permanent fork because ...".
- **Test placement** (if you add Triton-side tests): `external/triton/test/` for lit, `external/triton/unittest/` for C++ gtest, `external/triton/python/test/` for end-to-end Python tests. Avoid creating new test files unless necessary -- extend an existing one.
- **MLIR reproducer**: when a Triton-stage crash happens during review, ask the author for the MLIR reproducer (Triton emits one with `external_resources / mlir_reproducer` metadata). Save it to `/tmp/repro.mlir` and reproduce locally with `triton-opt /tmp/repro.mlir --run-reproducer`. Don't accept "works on my machine" for compiler crashes.
- **CODEOWNERS awareness**: `external/triton/.github/CODEOWNERS` is per-file at `.h` / `.cpp` granularity (e.g. `lib/Analysis/Alias.cpp @Jokeren`, `lib/Dialect/TritonGPU/Transforms/Pipeline.cpp @ptillet`). When patching one of those files locally, name the upstream owner in the PR description so the reviewer knows whose code we're diverging from -- this also makes upstreaming the patch later much easier.
- **No new contributor checklist**: our Jenkins doesn't enforce upstream's PR template, but the spirit (run pre-commit, add tests, justify trivial-only changes) is the same.

## Branch naming

- Feature: `users/<username>/<description>` or `<jira-id>-<description>`
- Triton bump: `triton-bump-<month>-<year>` or `triton-bump-<commit-prefix>`
- Prefer rebase over merge for clean history
