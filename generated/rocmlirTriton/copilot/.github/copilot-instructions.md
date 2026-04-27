# rocmlirTriton Project Overview

rocmlirTriton is a fork/derivative of [rocMLIR](https://github.com/ROCm/rocMLIR) that lowers Rock dialect kernels (convolution, GEMM, attention, fused ops) through [OpenAI Triton](https://github.com/triton-lang/triton)'s TTIR/TTGIR/LLIR pipeline to AMD GPU code. It targets AMD hardware (ROCm).

## Compilation arc

```
TOSA / MIGraphX
    -> highlevel  (Linalg + Rock view-to-transform, fold-broadcast, ...)
    -> Rock dialect (rock.gemm/conv/attention -> rock.gridwise -> rock.blockwise -> ptr arith)
    -> RockToTTIRPass + RockFuncToTritonFuncPass   <-- bridge into the Triton (`tt`) dialect
    -> Triton IR (TTIR)         via makeTTIR
    -> TritonGPU IR (TTGIR)     via makeTTGIR
    -> LLVM IR                  via makeLLIR
    -> AMDGCN -> HSACO          via TritonToHsacoPass
    -> Host glue (gpu.launch_func + LLVM lowering) via RestoreHostCode + buildHostLoweringPipeline
```

The four rocmlir-driver pipelines that drive this are `rock-highlevel-pipeline`, `rock-kernel-pipeline`, `rock-triton-pipeline`, `rock-backend-pipeline` (see `mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp`). Most of the Triton-side stages (`makeTTIR`/`makeTTGIR`/`makeLLIR`, `TritonToHsacoPass`) are C++ replicas of upstream Triton's Python `compiler.py`.

## Key facts

- Repository: [ROCm/rocmlirTriton](https://github.com/ROCm/rocmlirTriton) -- **currently private** (incubating); may be opened up later
- Primary consumer: [MIGraphX](https://github.com/ROCm/AMDMIGraphX) via the `librockCompiler` fat library
- License: Apache 2.0 with LLVM Exceptions (`LICENSE.TXT`)
- CMake project name is still `rocMLIR` (`project(rocMLIR VERSION 2.0.0 ...)`), so binaries and helper functions retain `rocmlir-*` / `add_rocmlir_*` names

## Source layout

- `mlir/` -- all rocmlirTriton sources (edit here)
- `external/triton/` -- **git submodule** of upstream Triton; brings its own `external/triton/llvm-project/` LLVM/MLIR
- `triton-patches/*.patch` -- local patches applied on top of the Triton submodule by `scripts/build-llvm.sh`
- `cmake/triton.cmake` -- wires `find_package(MLIR)` and `add_subdirectory(external/triton)` and defines `add_rocmlir_*` helpers
- `scripts/build-llvm.sh` -- wrapper that initializes submodules, applies `triton-patches/`, forces `MLIR_ENABLE_ROCM_RUNNER=ON`, and runs Triton's `build-llvm-project.sh`
- `cmake.sh` -- build helper that calls `scripts/build-llvm.sh`, configures CMake with `BUILD_FAT_LIBROCKCOMPILER=ON`, and runs Ninja
- `tests.sh` -- E2E smoke tests run end-to-end via `mlir-runner` from `external/triton/llvm-project/build/`
- `docs/` -- in-tree design docs (`bump_triton_version.md`, `scaled_gemm.md`, `cpu_validation_optimization.md`)

## Tools

- `rocmlir-gen` -- generate Rock dialect kernels and host harness
- `rocmlir-driver` -- run kernel/host pipelines (`-c` is the default full pipeline)
- `rocmlir-opt` -- MLIR optimizer with Rock + Triton passes registered
- `rocmlir-tuning-driver` -- JIT tuning harness over perf configs
- `rocmlir-translate` -- translate IR (e.g. `--gpu-module-to-rocdir`, `--triton-to-hsaco`)
- `rocmlir-lsp-server` -- LSP server for editor integration

## Build

```sh
bash cmake.sh                # default: BUILD_FAT_LIBROCKCOMPILER=ON, RelWithDebInfo, lld
bash tests.sh                # E2E smoke + targeted lit suites
```

`mlir-runner` and the `libmlir_*_runtime.so` shared libraries come from `external/triton/llvm-project/build/`, **not** from a sibling `external/llvm-project/`.

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
- License headers, third-party notices, and Apache 2.0 + LLVM Exceptions language must already be in place on every new file -- "we'll fix headers before going public" is not an acceptable plan.

## Downstream impact

Breaking changes to Rock dialect IR or C API require coordination with MIGraphX. Always keep `mlir/tools/rocmlir-lib/librockcompiler_deps.cmake` in sync after any dependency change (especially Triton bumps).


---

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


---

# Skill Dispatch

Before starting any task, check whether an available skill matches the user's request. Skills are located in `.cursor/skills/*/SKILL.md`. Read the matching skill file and follow its process before doing anything else.

## Trigger keywords -> skill mapping

| If the request mentions...                               | Use skill            |
|----------------------------------------------------------|----------------------|
| review PR, PR feedback, analyze PR                       | `pr-review`          |
| build, compile, test, lint, check build, run tests.sh    | `build-test-workflow`|
| profile, benchmark perf, kernel bottleneck               | `kernel-profiling`   |
| run benchmarks, perfRunner, performance comparison       | `perfrunner-usage`   |
| tune, tuning, perfConfig, tuningRunner                   | `tuningrunner-usage` |
| release branch, cherry-pick, release patch               | `release-management` |
| bump Triton, update Triton submodule, sync with Triton   | `triton-bump`        |
| add Triton patch, refresh triton-patches                 | `triton-bump`        |

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

