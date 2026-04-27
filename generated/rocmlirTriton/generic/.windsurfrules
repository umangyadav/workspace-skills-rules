# rocmlirTriton AI Agent Rules and Skills


---

## Rules


---

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

# Triton Integration

rocmlirTriton depends on upstream [Triton](https://github.com/triton-lang/triton) as a git submodule. Triton brings its own LLVM/MLIR and AMD backend; we replicate parts of Triton's Python pipeline in C++.

## Submodule layout

- Submodule: `external/triton/` (declared in `.gitmodules`, branch tracked by SHA)
- LLVM/MLIR: built from `external/triton/llvm-project/` via Triton's `scripts/build-llvm-project.sh`
- LLVM hash pinned by `external/triton/cmake/llvm-hash.txt`

## Local patches

`triton-patches/*.patch` are applied to the Triton submodule by `scripts/build-llvm.sh` before LLVM/MLIR is built. Each patch must be:

- Idempotent (the wrapper detects already-applied patches via `git apply --check --reverse`)
- Justified in the commit message that adds the patch
- Re-evaluated on every Triton bump (drop the patch if it landed upstream)

Never modify `external/triton/` directly without a corresponding `.patch` file -- the submodule is checked out fresh on every build.

## Rock <-> Triton dialect bridge

The two passes that hand the IR off from the Rock dialect to Triton's `tt` dialect are owned entirely by us (no upstream counterpart):

| Pass | File | Role |
|------|------|------|
| `RockToTTIRPass` (`-rock-to-ttir`) | `mlir/lib/Dialect/Rock/Transforms/RockToTTIR.cpp` | Rewrite `rock.blockwise_*`, `rock.gemm`, `rock.reduce`, ... into `tt.load`/`tt.store`/`tt.dot`/`tt.reduce`. |
| `RockFuncToTritonFuncPass` (`-rock-func-to-triton-func`) | `mlir/lib/Dialect/Rock/Transforms/FuncToTritonFunc.cpp` | Convert `func.func` kernels to `tt.func`, lift tensor args to `!tt.ptr`, and fold `arith.addi`-on-pointers into `tt.addptr`. |
| `RockSerializeHostFuncsPass` / `RockRestoreHostCodePass` | `Transforms/SerializeHostFuncs.cpp`, `Transforms/RestoreHostCode.cpp` | Park host functions before the Triton-only stages and restore them afterwards as `gpu.launch_func`. |

Both bridge passes are scheduled by `rock::buildKernelPipeline`. After they run, the module body is `tt.func` only, and the Triton C++ pipeline (next section) takes over.

## Python-to-C++ replication points

These C++ functions/files mirror Triton Python logic. Whenever the submodule advances, audit them against upstream (see the `triton-bump` skill):

| Triton (Python / C++) | rocmlirTriton (C++) |
|-----------------------|---------------------|
| `make_ttir` (`amd/backend/compiler.py`) | `makeTTIR()` in `mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp` |
| `make_ttgir` (`amd/backend/compiler.py`) | `makeTTGIR()` in `Pipelines.cpp` |
| `make_llir` part 1 (MLIR-side passes) | `makeLLIR()` in `Pipelines.cpp` (registered as the `rock-triton-pipeline`) |
| `make_llir` part 2 (LLVM IR finalization), `make_amdgcn`, `make_hsaco` | `mlir/lib/Translation/TritonToHsaco/TritonToHsaco.cpp` (`TritonToHsacoPass`) |
| `init_targets`, `createTargetMachine`, `optimize_module` (`llvm.cc`) | `TritonToHsaco.cpp` |
| `getMfmaVersion`, `getWmmaVersion`, `mlirTypeToScaledElemType` (`AccelerateAMDMatmul.cpp`) | `mlir/lib/Dialect/Rock/utility/tritonUtils.cpp` |
| `ISAFamily`, hardware feature checks (`TargetUtils.h`) | `mlir/lib/Dialect/Rock/IR/AmdArchDb.cpp` |
| `triton_amd.cc` Python pass bindings | corresponding `pm->addPass(...)` calls in `Pipelines.cpp` |

The four pass-pipeline registrations exposed to `rocmlir-opt` (`rock-highlevel-pipeline`, `rock-kernel-pipeline`, `rock-triton-pipeline`, `rock-backend-pipeline`) live at the bottom of `Pipelines.cpp`. `rocmlir-driver`'s `-kernel-pipeline=` keywords (`migraphx`, `highlevel`, `gpu`, `triton`, `binary`, `full`) map onto these.

## Hardware feature detection

Always use `rock::*` helpers (e.g. `rock::supportsTDM(arch)`) instead of `triton::AMD::TargetInfo(...)` directly. If a needed `rock` helper is missing, add one in `AmdArchDb.cpp` rather than calling Triton's `TargetInfo` from Rock code.

## Intentionally NOT replicated

These Python features are intentionally absent from the C++ pipeline -- do **not** add them when syncing:

- `HIPBackend.instrumentation.patch()`
- `knobs.*` configuration (we use hardcoded defaults)
- `passes.llvmir.add_di_scope()` (TODO, non-critical)
- `llvm.translate_to_mir()`, `llvm.dump_sched_dag()` (debugging only)
- `knobs.amd.swap_mir`, `knobs.compilation.dump_ir_*` (debugging only)
- FPSan instrumentation mode
- Full `schedule_hint` loop processing (partially hardcoded)

## After a submodule bump

1. Rebuild LLVM with `bash scripts/build-llvm.sh`
2. Re-validate every `triton-patches/*.patch`
3. Diff the replication-point files against `${OLD_COMMIT}..${NEW_COMMIT}`
4. Rebuild rocmlirTriton with `bash cmake.sh`
5. Regenerate `mlir/tools/rocmlir-lib/librockcompiler_deps.cmake` via `perl mlir/utils/jenkins/static-checks/get_fat_library_deps_list.pl`
6. Run `bash tests.sh`

See the `triton-bump` skill (`skills/triton-bump/SKILL.md`) and `docs/bump_triton_version.md` for the full workflow.


---

# LLVM/MLIR C++ Quick Reference

rocmlirTriton-specific patterns and examples. For the full rules, see [LLVM Coding Standards](https://llvm.org/docs/CodingStandards.html) and the code-review checklist.

## Casting patterns

```cpp
if (isa<MemRefType>(val.getType())) { auto t = cast<MemRefType>(val.getType()); }
auto t = dyn_cast<MemRefType>(val.getType()); // returns nullptr on failure
```

## Error handling patterns

```cpp
// Return LogicalResult from helpers/verifiers/rewrites
LogicalResult verify() { return emitOpError("mismatch") << " expected " << n; }

// In pass runOnOperation()
if (failed(result)) { signalPassFailure(); return; }
```

## Debug support

```cpp
#define DEBUG_TYPE "rock-my-pass"
LLVM_DEBUG(llvm::dbgs() << "message\n");
```

## LLVM algorithms (prefer over STL equivalents)

- `llvm::find`, `llvm::all_of`, `llvm::any_of`, `llvm::none_of`
- `llvm::to_vector`, `llvm::zip_equal`, `llvm::enumerate`
- `llvm::sort` (over `std::sort` for determinism)

## Namespace conventions

- `using namespace mlir;` and `using namespace mlir::rock;` at `.cpp` file scope
- Anonymous namespace only for local class/struct declarations: `namespace { struct MyPass ... }`
- Pass defs: `namespace mlir { namespace rock { #define GEN_PASS_DEF_... } }`

## Triton-aware C++

When calling into Triton, prefer the project's wrapper helpers in `mlir/lib/Dialect/Rock/utility/tritonUtils.cpp` and `mlir/lib/Dialect/Rock/IR/AmdArchDb.cpp` over reaching directly into `triton::AMD::*`. This isolates the C++ surface that needs review on every Triton bump.

## Naming

The `.clang-tidy` enforces LLVM-style names with `readability-identifier-naming` (CamelCase for classes/types/members/parameters/variables, camelBack for functions). Keep new code consistent with surrounding files.


---

# CMake Conventions

## Project structure

- Root: `project(rocMLIR VERSION 2.0.0 LANGUAGES CXX C)` (name retained from the rocMLIR fork)
- Triton + MLIR: pulled in via `cmake/triton.cmake` (`find_package(MLIR)` + `add_subdirectory(external/triton)`)
- MLIR-HAL: currently disabled (`include(cmake/mlir-hal.cmake)` is commented out, see top-level `CMakeLists.txt`)
- Generator: always Ninja (`-G Ninja`)
- C++ standard: 17

## MLIR_DIR resolution (in `cmake/triton.cmake`)

`MLIR_DIR` is resolved in this order:

1. Already set on the CMake command line (`-DMLIR_DIR=...`)
2. `$ENV{MLIR_DIR}` if exported in the environment
3. `external/triton/llvm-project/build/lib/cmake/mlir/` if Triton's LLVM has been built
4. `${LLVM_LIBRARY_DIR}/cmake/mlir` if Triton already provided `LLVM_LIBRARY_DIR`
5. Fallback: invoke `scripts/build-llvm.sh` automatically and retry

Set `MLIR_DIR` explicitly when integrating against an external LLVM install.

## Custom CMake functions (defined in `cmake/triton.cmake`)

| Function | Use for |
|----------|---------|
| `add_rocmlir_dialect_library` | Dialect IR libraries |
| `add_rocmlir_conversion_library` | Conversion pass libraries |
| `add_rocmlir_test_library` | Test helper libraries |
| `add_rocmlir_public_c_api_library` | C API libraries |
| `add_rocmlir_tool` | CLI tools (auto-handles `BUILD_FAT_LIBROCKCOMPILER` exclude logic) |
| `add_rocmlir_triton_library` | Rock-to-Triton glue libraries |

## Notable CMake options

| Option | Default | Purpose |
|--------|---------|---------|
| `BUILD_FAT_LIBROCKCOMPILER` | OFF (ON via `cmake.sh`) | Static `librockCompiler.a` for MIGraphX |
| `MLIR_INCLUDE_TESTS` | ON | Enables `check-rocmlir-build-only` |
| `ROCK_E2E_TEST_ENABLED` | OFF | Full E2E test suite |
| `ROCMLIR_DRIVER_E2E_TEST_ENABLED` | OFF | Build E2E driver tests |
| `ROCMLIR_DRIVER_PR_E2E_TEST_ENABLED` | OFF | PR-scoped E2E tests |
| `ROCMLIR_DRIVER_RANDOM_DATA_SEED` | `none` | Random-data E2E mode |
| `ROCMLIR_GEN_FLAGS` | "" | Extra flags forwarded to `rocmlir-gen` (e.g. `-mfma=off -wmma=off`) |
| `ROCMLIR_ENABLE_BENCHMARKS` | "" | `hipblaslt`, `ck`, or `all` |
| `MLIR_ENABLE_ROCM_RUNNER` | ON | Required for `mlir-runner` GPU execution |
| `ROCMLIR_PARALLEL_LINK_JOBS` / `_COMPILE_JOBS` | "" | Limit Ninja link/compile concurrency |

## Triton-specific CMake settings (set in `cmake/triton.cmake`)

- `TRITON_BUILD_PYTHON_MODULE OFF` (we use the C++ API)
- `TRITON_BUILD_PROTON OFF`
- `TRITON_BUILD_UT OFF`
- `TRITON_CODEGEN_BACKENDS "amd" "nvidia"`

Do not change these defaults without coordinating with the Triton bump owner.


---

# Python Standards

## Source of truth

- **CI workflow**: `.github/workflows/ci.yml` -- defines flake8 ignore list and yapf checks on changed `mlir/**/*.py`
- **flake8 config**: `.flake8` (`max-line-length = 100`, ignore list mirrored in CI)
- **yapf config**: `.style.yapf`
- **Dependencies**: `pip_requirements.txt`

Consult these files directly for the latest configuration before writing or fixing Python code under `mlir/` or `scripts/`.

## CI scope

GitHub Actions only lints **changed** `mlir/**/*.py` files (computed against the merge base of the PR's base branch). Files under `external/` are excluded. Local pre-commit run:

```bash
yapf --diff <changed-files>
flake8 --ignore=E501,E251,E124,W605,W504,E131,E126,W503,E123 <changed-files>
```


---

# Code Review Checklist

## Pre-commit formatting

Before every commit, run `git clang-format --diff origin/develop` (or the appropriate base branch) and fix any issues. If the diff is non-empty, apply fixes and include them in the commit. This prevents CI failures from the premerge clang-format check.

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

## Branch naming

- Feature: `users/<username>/<description>` or `<jira-id>-<description>`
- Triton bump: `triton-bump-<month>-<year>` or `triton-bump-<commit-prefix>`
- Prefer rebase over merge for clean history


---

# Testing Conventions

See also: `code-review.md` (Major section) and `dev-workflow.md` (Testing a new operation or feature) for review-time testing requirements.

## When to use each test type

| Type | Location | Use for |
|------|----------|---------|
| **Lit** (`.mlir`) | `mlir/test/` | Passes, pipelines, driver integration |
| **GoogleTest** | `mlir/unittests/` | C++ helpers, attributes, transform maps |
| **E2E (lit)** | `mlir/test/e2e/`, `mlir/test/fusion/pr-e2e/`, `mlir/test/fusion/nightly-misc-e2e/`, `mlir/test/fusion/resnet50-e2e/` | Full GPU pipeline |
| **E2E (smoke)** | top-level `tests.sh`, `test_prefill_changes.sh` | Hand-curated GPU smoke tests covering gemm/conv/attention/fusion |

## Lit test patterns

```mlir
// Pass test (most common)
// RUN: rocmlir-opt --my-pass %s | FileCheck %s

// Split input + diagnostics (for verifier/negative tests)
// RUN: rocmlir-opt --my-pass -split-input-file -verify-diagnostics %s | FileCheck %s

// rocmlir-gen → rocmlir-opt (test generated IR)
// RUN: rocmlir-gen --arch gfx942 --operation gemm -t f16 -m 1024 -k 768 -n 512 | rocmlir-opt | FileCheck %s

// Arch substitution for arch-dependent IR
// RUN: sed s/##TOKEN_ARCH##/%arch/g %s | rocmlir-driver --arch %arch --kernel-pipeline=migraphx,highlevel - | FileCheck %s

// Pipeline dump verification
// RUN: rocmlir-driver -dump-pipelines -kernel-pipeline=gpu -arch=gfx90a /dev/null -o /dev/null 2>&1 | FileCheck %s

// E2E: rocmlir-gen → rocmlir-driver → mlir-runner (GPU required)
// RUN: rocmlir-gen --arch %arch --operation gemm -pv | rocmlir-driver -c | mlir-runner --shared-libs=... | FileCheck %s
```

## tests.sh smoke suite

`tests.sh` is the canonical end-to-end smoke entry point. It:

1. Detects `$ARCH` and `$NUM_CU` from `rocminfo`
2. Builds `check-rocmlir-build-only ci-performance-scripts`
3. Runs gemm/conv/attention/fusion pipelines through `mlir-runner` from `external/triton/llvm-project/build/`
4. Filters `LIT_FILTER` over targeted lit subdirectories (`fusion/fusability`, `fusion/pr-e2e/`, `Dialect/Rock`, `rocmlir-gen`, `Conversion`, `rocmlir-driver`, `capi`, `rocmlir-tuning-driver`)

Whenever a new dialect/conversion area is added, update `tests.sh` so the corresponding `LIT_FILTER` line covers it.

## Key substitutions

Defined in `lit.cfg.py` / `lit.site.cfg.py.in` files:
- `mlir/test/lit.cfg.py` -- main substitutions (`%arch`, `%shlibext`, `%linalg_test_lib_dir`, etc.)
- E2E and fusion lit configs add suite-specific substitutions

## FileCheck defaults

`FILECHECK_OPTS="-enable-var-scope --allow-unused-prefixes=false"` -- all CHECK prefixes must be used.

## Test targets

- `check-rocmlir` -- full suite
- `check-rocmlir-build-only` -- compile only (used in CI build stage)
- `MLIRRockUnitTests` -- GoogleTest only (run via `./mlir/unittests/Dialect/Rock/MLIRRockUnitTests`)
- E2E (PR subset): enable with `-DROCMLIR_DRIVER_PR_E2E_TEST_ENABLED=ON`
- E2E (full): enable with `-DROCK_E2E_TEST_ENABLED=ON` and `-DROCMLIR_DRIVER_E2E_TEST_ENABLED=ON`

## Architecture and dtype coverage

- New ops/passes must work on all supported GPU architectures present in CI (`gfx90a`, `gfx942`, `gfx950`, `gfx1100`, etc.)
- Guard arch-specific ops with target checks in both code and tests; `tests.sh` already gates several `gfx950`-only paths
- Enumerate all dtypes the op should support (`f16`, `bf16`, `f32`, `f8E4M3FN`, `f8E5M2`, `f4E2M1FN`, `i8`, etc.)
- Add E2E tests covering each supported dtype; reject unsupported dtypes with `emitOpError`
- For scaled GEMM features, ensure `f8E8M0FNU` scale handling works (see `docs/scaled_gemm.md`)

## Fusion test requirements

MIGraphX-related or fusion changes must include fusion lit tests in `mlir/test/fusion/` (compile-level) and/or `mlir/test/fusion/pr-e2e/` (GPU E2E). Top-level `fusion_*_with_host.mlir` files at the repo root are exercised by `tests.sh` for end-to-end coverage.


---

# rocmlirTriton CLI Tools

Binaries live in `build/bin/`. The MLIR runtime libraries used by `mlir-runner` come from `external/triton/llvm-project/build/lib/`.

## rocmlir-gen -- generate MLIR from problem specs

Key flags: `-operation` (`conv`/`gemm`/`attention`/`gemm_gemm`/`conv_gemm`), `-arch`, `-num_cu`, `-num_chiplets`, `-t` (input dtype), `-out_datatype`, `-m`/`-k`/`-n` (GEMM dims), `-g` (groups), `-ph` (host harness), `-pv` (validate), `-pr` (print results), `-perf_config`, `-emit-tuning-key`

Conv: `-fil_layout`, `-in_layout`, `-out_layout`, `-batchsize`, `-in_channels`, `-out_channels`, `-fil_h/w`, padding/strides/dilations

Attention: `-seq_len_q`, `-seq_len_k`, `-head_dim_qk`, `-head_dim_v`, `-num_heads_q`, `-num_heads_kv`, `--causal`

Scaled GEMM: `-scaledGemm`, `-quantBlockSize`, `-scale_a_dtype`, `-scale_b_dtype`, e.g. `-t f8E4M3FN -scale_a_dtype f8E8M0FNU` (gfx950 only -- see `docs/scaled_gemm.md`)

Features: `-mfma`, `-wmma`, `-dot`, `-atomic_add` (each: `infer`/`on`/`off`)

## rocmlir-driver -- run lowering pipelines

- `-kernel-pipeline`: comma list of `migraphx`, `highlevel`, `gpu`, `triton`, `binary`, or `full` (= `gpu,triton,binary`)
  - `gpu` runs `rock::buildKernelPipeline` (Rock -> RockToTTIR -> tt.func)
  - `triton` runs `rock::buildTritonPipeline` (TTIR -> TTGIR -> LLVM dialect, replicating Triton's `make_ttir`/`make_ttgir`/`make_llir`)
  - `binary` runs `rock::buildBackendPipeline` (`TritonToHsacoPass` + host glue via `RockRestoreHostCode` + `buildHostLoweringPipeline`)
- `-host-pipeline`: comma list of `migraphx`, `highlevel`, `backend`
- `-c`: hidden legacy shorthand for `-kernel-pipeline=full` (does **not** set the host pipeline; pair with `-host-pipeline=...` if you also need host lowering)
- `-arch`, `-dump-pipelines`, `-disable-verify-passes`, `-dump-cpu-schedules=<dir>`

## rocmlir-opt -- MLIR optimizer

Standard `mlir-opt` interface with all Rock + MIGraphX + Triton-related passes registered via `InitRocMLIRPasses.h`. Useful pipeline names registered through `rock::registerPipelines()`:

- `--rock-highlevel-pipeline`
- `--rock-kernel-pipeline` (ends in `tt.func`)
- `--rock-triton-pipeline` (TTIR -> TTGIR -> LLIR)
- `--rock-backend-pipeline` (LLVM IR -> HSACO + host lowering)

Useful individual passes for the Rock<->Triton bridge: `--rock-to-ttir`, `--rock-func-to-triton-func`, `--rock-serialize-host-funcs`, `--rock-restore-host-code`, `--triton-to-hsaco`.

## rocmlir-translate -- translation entry points

- `--gpu-module-to-rocdir`
- `--triton-to-hsaco` (the C++ replication of Triton's `make_hsaco`)

## rocmlir-tuning-driver -- JIT benchmark

`--tuning-space` (`quick`/`full`/`greedy`/`exhaustive`), `--num-iterations`, `--warmup-iterations`, `--sleep-us`, `--use-median`, `--show-all-measurements`

## rocmlir-lsp-server

LSP server that registers Rock/MIGraphX dialects for editor integration with `.mlir` files.

## Python performance/tuning scripts (`mlir/utils/performance/`)

- `perfRunner.py` -- main benchmark runner (gemm/conv/attention/fusion across configs)
- `tuningRunner.py` -- tuning orchestrator over perf-config space
- `parameterSweeps.py` -- parameter sweep driver for exhaustive tuning
- `attentionSweeps.py` -- attention-specific sweeps
- `perfRegressionReport.py`, `createPerformanceReports.py`, `createFusionPerformanceReports.py` -- report generators
- `reportUtils.py`, `perfCommonUtils.py` -- shared utilities
- `handleNewConfigs.py`, `convertRocBlasToPerfRunner.py` -- config helpers
- Configs: `configs/tier1-{gemm,conv,attention,gemmgemm}-configs`, `problem-config-tier-1-models`, `bert-configs-raw`

## Widgets (`mlir/utils/widgets/`)

- `rocm-run` / `xmir-run` -- shell wrappers around `mlir-runner` with the right `--shared-libs`

## Common pipelines

```bash
# Smoke
rocmlir-gen --arch gfx942 -p | rocmlir-opt

# Full lowering + validate (single op), Triton mlir-runner
rocmlir-gen --arch gfx942 -ph -pv | rocmlir-driver -c | \
  external/triton/llvm-project/build/bin/mlir-runner \
    --shared-libs=external/triton/llvm-project/build/lib/libmlir_rocm_runtime.so,build/lib/libconv-validation-wrappers.so,external/triton/llvm-project/build/lib/libmlir_runner_utils.so,external/triton/llvm-project/build/lib/libmlir_c_runner_utils.so \
    --entry-point-result=void

# Tuning a single config
rocmlir-gen --arch gfx942 --perf_config= | rocmlir-tuning-driver --tuning-space=quick

# Fusion E2E from .mlir input
sed -e "s/gfx1100/$ARCH/g" -e "s/rock.num_cu = 96/rock.num_cu = $NUM_CU/g" fusion_with_host.mlir | \
  rocmlir-driver -c | mlir-runner --shared-libs=... --entry-point-result=void
```

## Tuning + benchmarking

```bash
# Tune
python3 tuningRunner.py --abort-on-error --operation gemm \
  --configs-file=configs/tier1-gemm-configs --output=mlir_tuning_${CHIP}.tsv

# Benchmark with the tuning DB
python3 perfRunner.py --op=gemm --batch_all \
  --configs_file=configs/tier1-gemm-configs \
  --tuning_db=mlir_tuning_${CHIP}.tsv

# Multi-GPU tuning
python3 tuningRunner.py --operation gemm --configs-file=configs/tier1-gemm-configs --gpus 0 1 2 3
```

## Parameter sweeps

```bash
python3 parameterSweeps.py -j <num_workers> <CONFIG> --log-failures
```

All Python scripts are in `mlir/utils/performance/`. Run `python3 <script>.py --help` for full flag reference.


---

# Development Workflow

## Adding a new Rock dialect operation

1. Define op in `mlir/include/mlir/Dialect/Rock/IR/RockOps.td` (inherit `Rock_Op`, add traits, `hasVerifier = 1`)
2. Implement verifier: `LogicalResult NewOp::verify()` in `mlir/lib/Dialect/Rock/IR/RockDialect.cpp`
3. Add lowering in `mlir/lib/Dialect/Rock/Transforms/` using `OpRewritePattern` or `OpConversionPattern`
4. Register pass in `mlir/include/mlir/Dialect/Rock/Passes.td`
5. Wire into pipeline in `mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp`
6. Add Lit tests in `mlir/test/Dialect/Rock/` (round-trip + pass tests)
7. Update `CMakeLists.txt` if new files added

## Adding a conversion pass (e.g. FooToBar)

1. Declare in `mlir/include/mlir/Conversion/RocMLIRPasses.td`
2. Create `mlir/lib/Conversion/FooToBar/` with pattern + pass `.cpp` files
3. Add `add_rocmlir_conversion_library(...)` in CMakeLists
4. Add Lit tests in `mlir/test/Conversion/FooToBar/`

## Touching the Rock <-> Triton bridge

The two passes that translate Rock dialect IR into Triton's `tt` dialect:

- `mlir/lib/Dialect/Rock/Transforms/RockToTTIR.cpp` (`-rock-to-ttir`) -- rewrite Rock blockwise/gemm ops to `tt.load`/`tt.store`/`tt.dot`/`tt.reduce`. Add a new `OpRewritePattern` here when you introduce a Rock op that needs to reach the GPU through Triton.
- `mlir/lib/Dialect/Rock/Transforms/FuncToTritonFunc.cpp` (`-rock-func-to-triton-func`) -- module-level pass that turns `func.func` kernels into `tt.func`, lifts tensor args to `!tt.ptr`, and folds pointer arith into `tt.addptr`. Touch this when the kernel calling convention or pointer-attribute layout changes.

Both are scheduled by `rock::buildKernelPipeline` in `Pipelines.cpp`. After they run, the kernel module body is `tt.func` only.

## Touching the Triton-driven pipeline

If your change crosses into the part of the pipeline that runs on `tt`/`ttg` IR:

1. Find the Python equivalent in `external/triton/third_party/amd/backend/compiler.py` and the binding in `external/triton/third_party/amd/python/triton_amd.cc`.
2. Mirror the change in `mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp` (`makeTTIR`/`makeTTGIR`/`makeLLIR` -- TTIR/TTGIR/LLIR MLIR-side passes) or `mlir/lib/Translation/TritonToHsaco/TritonToHsaco.cpp` (LLVM IR finalization, AMDGCN, HSACO).
3. Use `rock::*` helpers (`rock::supportsTDM`, etc.) to gate hardware-conditional passes.
4. If you need a hardware capability not yet exposed by `rock`, add it to `mlir/lib/Dialect/Rock/IR/AmdArchDb.cpp` rather than reaching into `triton::AMD::TargetInfo`.
5. If a fix should also live in upstream Triton, prefer drafting an upstream PR; only add a `triton-patches/*.patch` when waiting for upstream is not viable.

## Adding a MIGraphX operation

1. Define op in `mlir/include/mlir/Dialect/MIGraphX/IR/MIGraphX.td`
2. Add lowering in `mlir/lib/Conversion/MIGraphXToTosa/`
3. Add tests in `mlir/test/Conversion/`

## Testing a new operation or feature

### Architecture coverage

- New ops/passes must work on all supported GPU architectures (`gfx90a`, `gfx942`, `gfx950`, `gfx1100`, ...)
- If an op is architecture-specific, guard it with proper target checks in both code and tests
- Use `lit.cfg.py` to configure arch-specific test guards

### Data type coverage

- Enumerate all dtypes the op should support (`f16`, `bf16`, `f32`, `f8E4M3FN`, `f8E5M2`, `f4E2M1FN`, `i8`, `i4`, etc.)
- Ensure the implementation handles each supported dtype explicitly -- do not silently fall through
- Return a clear error (`emitOpError`) for unsupported dtypes rather than producing wrong results
- Add E2E tests covering each supported dtype and Lit tests that verify unsupported dtypes are rejected
- Scaled GEMM features must respect the `f8E8M0FNU` scale convention (see `docs/scaled_gemm.md`)

### Edge cases and completeness

- Consider boundary conditions: zero-size tensors, non-aligned shapes, large dimensions, scalar inputs
- For optimization passes, verify the optimization fires (FileCheck for expected IR) and verify correctness (E2E with random data)
- Test both the optimized path and the fallback/unoptimized path
- If the feature interacts with fusion, test fused and unfused variants and update `tests.sh` if a new top-level `fusion_*_with_host.mlir` is added

## Debugging a pass failure

```bash
# Isolate
rocmlir-opt --my-pass input.mlir

# Enable debug output (requires -DLLVM_ENABLE_ASSERTIONS=ON)
rocmlir-opt --my-pass input.mlir --debug-only=my-pass

# Dump full pipeline (rocMLIR side)
rocmlir-driver -dump-pipelines -kernel-pipeline=full input.mlir 2>&1

# Dump GCN assembly emitted via Triton
rocmlir-driver --debug-only=serialize-to-blob -c input.mlir
```

## Debugging Triton-side failures

```bash
# Bridge only: Rock dialect -> tt.func (no TTGIR yet)
rocmlir-driver -kernel-pipeline=gpu --arch=gfx942 input.mlir

# Stop after TTIR/TTGIR/LLIR (no HSACO emission)
rocmlir-driver -kernel-pipeline=gpu,triton --arch=gfx942 input.mlir

# Inspect just the bridge passes individually
rocmlir-opt --rock-to-ttir input.mlir
rocmlir-opt --rock-func-to-triton-func input.mlir

# Run only the Triton-driven pass pipeline on a tt.func module
rocmlir-opt --rock-triton-pipeline='arch=gfx942 num-warps=4 ...' tt.mlir

# Compare against upstream Triton's Python pipeline by running a reference
# kernel through `python -m triton.runtime.compile` (only when Triton's
# Python module is available; not built by default in this repo)
```


---

# CI Pipelines

rocmlirTriton currently runs three CI systems. The configuration is largely inherited from rocMLIR; some pieces are intentionally pared down for the early-stage repo.

## Jenkins (primary, GPU-heavy) -- PR only today

Files in `mlir/utils/jenkins/`:

| File | Purpose |
|------|---------|
| `Jenkinsfile` | **Private CI**, runs on every PR. The only active Jenkins pipeline today. |
| `Jenkinsfile.downstream` | **Deprecated.** Used to drive a public-CI mirror. Public CI is no longer used; the file is kept in-tree for history but is not run. The "ALSO CHANGE Jenkinsfile.downstream" comment at the top of `Jenkinsfile` is stale -- ignore it. |
| `Jenkinsfile.release` | Release-build storage only (`Set System Property` + `Store a Release Build`); ~50 lines. |

PR pipeline (`Jenkinsfile`) is a **matrix** with axis `CODEPATH` over `vanilla, mfma, navi21, navi3x, navi4x, gfx950`. Per matrix row (each in a Docker container, ROCm clang from `/opt/rocm/llvm/bin`):

1. SCM checkout (with `robustScmCheckout` deep-clone fallback for "reference is not a tree")
2. Prepare Docker environment (image is ROCm-based; pulled via `dockerImage()`)
3. **Configure and build rocmlirTriton** -- `bash cmake.sh` (`RelWithDebInfo`, `BUILD_FAT_LIBROCKCOMPILER=ON`)
4. **Static checks** -- `python3 mlir/utils/jenkins/static-checks/premerge-checks.py --base-commit=origin/${TARGET}`. **Only runs on the `mfma` codepath** (`if (params.nightly == false) && (codepath == "mfma")`). Honors `params.ignoreExternalLinting` to skip the `external/` tree.
5. **Run tests** -- `bash tests.sh` (the in-tree smoke suite)

Nightly / weekly stages exist in the file but are commented out: shared-library random E2E, MIGraphX integration, `tuna-script.sh` tuning of selected GEMM/conv configs, static-lib package build, weekly parameter sweeps, weekly fusion tuning, perfDB archival, plot generation. Re-enabling any of those is a private-CI-only change today -- do **not** propagate it to `Jenkinsfile.downstream`.

## Azure Pipelines (ROCm ecosystem)

- Config: `.azuredevops/rocm-ci.yml`
- Triggers: push to `develop`/`mainline`, PRs to `develop`
- Excludes: `.github/`, `*.md`
- Loads shared templates from the `ROCm/ROCm` repo: `/.azuredevops/variables-global.yml@pipelines_repo` and `${{ variables.CI_COMPONENT_PATH }}/rocMLIR.yml@pipelines_repo`
- Note: the template name is still `rocMLIR.yml` (carryover from the fork). Keep it that way until ROCm/ROCm publishes a `rocmlirTriton.yml` template; do not switch unilaterally.

## GitHub Actions (lightweight Python lint, only)

- Workflow: `.github/workflows/ci.yml` -- name `"Python Lint and Format Check"`
- Triggers: `pull_request` and `push` to `develop` and `release/**`, paths `mlir/**`, excludes `external/**`
- Container: `python:3.8`, runs as root via `--user root`, fixes git ownership before checkout
- Steps:
  1. Install `pip_requirements.txt`
  2. Compute changed `mlir/**/*.py` against `git merge-base HEAD origin/<base>`
  3. `flake8 --ignore=E501,E251,E124,W605,W504,E131,E126,W503,E123 <files>`
  4. `yapf --diff <files>` (fails the job if any diff is produced)
  5. If no `*.py` under `mlir/` changed, prints "skipping" and passes

There is **no** pytest workflow, **no** codecov workflow, and no GPU/build job in GitHub Actions today (those live in Jenkins/Azure). The only file in `.github/workflows/` is `ci.yml` (plus the placeholder `README.md`).

## CODEOWNERS

All paths: `@causten` (`.github/CODEOWNERS`).

## Source of truth when CI fails

| Failing check | Look in |
|---------------|---------|
| `Python Lint and Format Check` | `.github/workflows/ci.yml`, `.flake8`, `.style.yapf` |
| Azure `rocMLIR` job | `.azuredevops/rocm-ci.yml` + ROCm/ROCm `rocMLIR.yml` template |
| Jenkins `Configure and build rocmlirTriton` | `cmake.sh`, `scripts/build-llvm.sh`, `cmake/triton.cmake` |
| Jenkins `Static checks (clang-format & clang-tidy)` | `mlir/utils/jenkins/static-checks/premerge-checks.py`, `clang-format.ignore`, `clang-tidy.ignore` |
| Jenkins `Run tests` | `tests.sh` |


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


---

## Skills


---

# Build, Test, and Lint

## Usage

"Build and test the project", "Run tests.sh", or "Verify the build".

## Step 0: Prerequisites

```bash
git submodule update --init --recursive   # required for external/triton
which clang-20 || which clang             # cmake.sh defaults to clang-20
which ninja
which lld
rocminfo | grep gfx                       # GPU access for tests.sh
```

If `external/triton/llvm-project/build/` is missing, the build will trigger `scripts/build-llvm.sh` automatically (this can take 15-40 minutes the first time).

## Step 1: Configure + build

The canonical entry point is `cmake.sh`, which:

1. Runs `scripts/build-llvm.sh` (submodule init, applies `triton-patches/*.patch`, forces `MLIR_ENABLE_ROCM_RUNNER=ON`, builds LLVM/MLIR)
2. Wipes and recreates `build/`
3. Configures with Ninja, `BUILD_FAT_LIBROCKCOMPILER=ON`, `RelWithDebInfo`, `lld`, all E2E flags ON
4. Builds `libconv-validation-wrappers.so`, then `check-rocmlir-build-only` and `ci-performance-scripts`

```bash
bash cmake.sh
```

### Manual configure (when you need to change options)

```bash
mkdir -p build && cd build
cmake -G Ninja .. \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_C_COMPILER=clang-20 \
  -DCMAKE_CXX_COMPILER=clang++-20 \
  -DCMAKE_EXE_LINKER_FLAGS="-fuse-ld=lld" \
  -DCMAKE_SHARED_LINKER_FLAGS="-fuse-ld=lld" \
  -DCMAKE_MODULE_LINKER_FLAGS="-fuse-ld=lld" \
  -DBUILD_FAT_LIBROCKCOMPILER=ON \
  -DLLD_BUILD_TOOLS=ON \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DROCK_E2E_TEST_ENABLED=ON \
  -DROCMLIR_DRIVER_PR_E2E_TEST_ENABLED=ON \
  -DROCMLIR_DRIVER_E2E_TEST_ENABLED=ON
ninja libconv-validation-wrappers.so
ninja check-rocmlir-build-only ci-performance-scripts
```

To configure against a pre-built MLIR (e.g. shared dev environment), pass `-DMLIR_DIR=/path/to/lib/cmake/mlir` and skip `scripts/build-llvm.sh`.

Always verify exit codes. If the build fails, stop and report -- do not proceed to test/lint.

## Step 2: Test

```bash
# Full smoke + targeted lit suites (requires GPU)
bash tests.sh

# Compile-only sanity
cd build && ninja check-rocmlir-build-only

# Unit tests
cd build && ninja MLIRRockUnitTests && ./mlir/unittests/Dialect/Rock/MLIRRockUnitTests

# Targeted lit suite (matches what tests.sh runs)
cd build && LIT_FILTER=Dialect/Rock ninja check-rocmlir
cd build && LIT_FILTER=fusion/pr-e2e/ ninja check-rocmlir
cd build && LIT_FILTER=rocmlir-tuning-driver ninja check-rocmlir
```

`tests.sh` auto-detects `$ARCH` and `$NUM_CU` from `rocminfo` and gates `gfx950`-only scaled GEMM cases.

## Step 3: Lint

- **C++ format**: `git clang-format --diff origin/develop`
- **C++ tidy**: rules in `.clang-tidy`; the Jenkins premerge invokes `mlir/utils/jenkins/static-checks/premerge-checks.py` (clang-format + clang-tidy, **only on the `mfma` matrix row**)
- **Python lint/format**: `flake8 --ignore=E501,E251,E124,W605,W504,E131,E126,W503,E123` + `yapf --diff` on changed `mlir/**/*.py` (see `.github/workflows/ci.yml`); no pytest gate exists yet

## Step 4: Report

```markdown
## Build-Test-Lint Report
### Build Status: [PASS/FAIL]
<errors if any>
### Test Status: [PASS/FAIL] (X passed, Y failed, Z skipped)
<failed test names if any>
### Lint Status: [PASS/FAIL]
<lint issues if any>
### Summary: <one-line>
```

## Rules

- Never pipe build output through `tail`/`head` -- errors get hidden
- Test and lint are independent -- run both even if one fails
- Do not attempt to fix issues -- reporting only
- If `scripts/build-llvm.sh` is triggered, expect a long first run; subsequent builds reuse `external/triton/llvm-project/build/`

---

# Kernel Profiling

## Tools

- **rocprofv3** (`/opt/rocm/bin/rocprofv3`): low-level GPU profiler for timing and HW counters
- **rocprof-compute**: comprehensive analysis with structured bottleneck reports

Official docs: [Using rocprofv3](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-rocprofv3.html) -- refer here for installation, dependencies, full CLI options, and output formats.

## Step 0: Verify installation

```bash
rocprofv3 --version
rocprof-compute --version
rocminfo | grep gfx
```

- **rocprofv3**: included with ROCm. If missing, check ROCm installation and ensure `/opt/rocm/bin` is in `PATH`.
- **rocprof-compute**: included with ROCm >= 6.2. For older ROCm or custom installs, see [installation docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/install/core-install.html).
- **rocminfo**: verifies GPU is visible.

## Step 1: Generate kernel

The runtime libs come from Triton's LLVM build under `external/triton/llvm-project/build/`:

```bash
SHARED_LIBS="external/triton/llvm-project/build/lib/libmlir_rocm_runtime.so,build/lib/libconv-validation-wrappers.so,external/triton/llvm-project/build/lib/libmlir_runner_utils.so,external/triton/llvm-project/build/lib/libmlir_c_runner_utils.so"

build/bin/rocmlir-gen --operation gemm --arch gfx942 -t f16 -m 4096 -k 4096 -n 4096 -ph | \
  build/bin/rocmlir-driver -c > kernel.mlir
```

## Step 2a: Profile with rocprofv3 (quick)

```bash
rocprofv3 --kernel-trace --stats -f csv -o results -- \
  external/triton/llvm-project/build/bin/mlir-runner kernel.mlir \
    --shared-libs=$SHARED_LIBS --entry-point-result=void
```

- PMC counters: use `mlir/utils/performance/rocmlir_metrics.txt` for LDS bank conflict (`pmc: LDSBankConflict`)
- Output: `results.csv` (timing), `results_kernel_stats.csv` (aggregates)

## Step 2b: Profile with ROCm Compute Profiler (comprehensive)

[ROCm Compute Profiler](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/what-is-rocprof-compute.html) provides kernel-level profiling with HW counters, Speed-of-Light evaluations, and roofline analysis. See [profiling docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/profile/mode.html).

```bash
rocprof-compute profile -n my_kernel -- \
  external/triton/llvm-project/build/bin/mlir-runner kernel.mlir \
    --shared-libs=$SHARED_LIBS --entry-point-result=void
```

Filtering: `-k <kernel>`, `-b <block>` (SQ, LDS, TCC, etc.), `--gpu-id`. See [filtering docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/profile/mode.html#filtering).

## Step 3: Analyze

```bash
rocprof-compute analyze -p ./workloads/my_kernel/<arch>/
rocprof-compute analyze -p ... --gui   # Standalone GUI
```

Features: Speed-of-Light analysis, memory chart, roofline, [baseline comparisons](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/analyze/cli.html#analysis-baseline-comparison).

## Step 4: Identify bottlenecks

| Bottleneck | What to check |
|-----------|---------------|
| **Compute bound** | SQ occupancy, VALU/MFMA utilization, wavefront stalls |
| **Memory bound** | L2 (TCC) hit rate, HBM bandwidth, LDS bank conflicts |
| **Latency bound** | Instruction fetch stalls, barrier waits, dependency stalls |

For the full list of available counters and derived metrics, run `rocprofv3 --list-avail` or see [MI200 performance counters and metrics](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-rocprofv3.html#kernel-counter-collection). Extra counters can be defined via YAML files with `--extra-counters`.

Map findings to rocmlirTriton tuning parameters defined in `mlir/include/mlir/Dialect/Rock/IR/RockAttrDefs.td` (see also `RockTuningParamAttrInterface.td` and `RockAccelTuningParamAttrInterface.td`). Triton-specific scheduling knobs live on the Triton side (TTGIR pass options); when needed, follow the Pipelines.cpp wiring back to the corresponding pass.

## Thread tracing with rocprof-compute-viewer

Thread traces provide instruction-level visibility. See [official thread trace docs](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html).

### Prerequisites

1. ROCm 7.2+ with aqlprofile and rocprof-trace-decoder ([prerequisites](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#prerequisites))
2. Install [rocprof-compute-viewer](https://github.com/ROCm/rocprof-compute-viewer/releases) for visualization

```bash
ls /opt/rocm/lib/libaqlprofile*.so
ls /opt/rocm/lib/librocprof-trace-decoder*.so
rocprofv3 --version
```

### Collect traces

Default collection:

```bash
rocprofv3 --att -d att_dump -- <application>
```

Input file for fine-grained control:

```json
{
    "jobs": [
        {
            "advanced_thread_trace": true,
            "att_target_cu": 1,
            "att_shader_engine_mask": "0x1",
            "att_simd_select": "0xF",
            "att_buffer_size": "0x6000000"
        }
    ]
}
```

```bash
rocprofv3 --att -i att.json -d att_dump -- <application>
rocprofv3 --att --att-activity 8 -d att_dump -- <application>   # AMD Instinct
```

Key parameters: `--att-target-cu`, `--att-shader-engine-mask`, `--att-simd-select`, `--att-buffer-size`, `--kernel-include-regex`, `--kernel-iteration-range`. See [full parameter table](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#rocprofv3-parameters-for-thread-tracing).

### Using with rocmlirTriton

Create a `run.sh` with full absolute paths:

```bash
#!/bin/bash
<rocmlirTriton>/build/bin/rocmlir-gen --operation=gemm -m 16384 -n 16384 -k 384 -g 1 --arch <arch> | \
  <rocmlirTriton>/build/bin/rocmlir-gen -ph - | \
  <rocmlirTriton>/build/bin/rocmlir-driver -c --arch <arch> | \
  <rocmlirTriton>/mlir/utils/widgets/rocm-run
```

```bash
chmod +x run.sh
rocprofv3 --att -i att.json -d att_dump -- $(pwd)/run.sh
```

### Output files

- `stats_*.csv` -- instruction latency summary (hitcount, latency, stalls, idle cycles)
- `ui_output_agent_*_dispatch_*/` -- open in rocprof-compute-viewer
- `.att` / `.out` -- raw trace data and code object binaries

### Troubleshooting

- **Empty stats CSV**: kernel may not launch enough waves for `att-target-cu`; widen `att-shader-engine-mask`
- **File not found**: use full absolute paths in `run.sh`
- **Data lost warnings**: reduce `att-perfcounter-ctrl` or increase `att-buffer-size`
- See [official troubleshooting](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#troubleshooting)

## Integration with perfRunner.py

- `--use-rocprof` flag uses rocprofv3 for benchmarking
- `mlir/utils/performance/rocmlir_metrics.txt` defines the PMC counters collected
- LDSBankConflict: 0% optimal, 100% bad

---

# perfRunner.py Usage

Source: `mlir/utils/performance/perfRunner.py`. Run `python3 perfRunner.py --help` for the full and up-to-date flag reference.

**Important**: Ensure no other processes are using the GPUs during benchmarking. Shared GPU usage causes noisy and unreliable results. Check with `rocm-smi` or `fuser /dev/kfd` before starting. Use `ROCR_VISIBLE_DEVICES` to target a specific GPU:

```bash
ROCR_VISIBLE_DEVICES=0 python3 perfRunner.py --op gemm --batch_all -c <configs> -t mlir_tuning.tsv
```

## Operations (`--op`)

`conv` (default), `gemm`, `fusion`, `attention`, `gemm_gemm`, `conv_gemm`

## Modes (mutually exclusive)

| Flag | Behavior |
|------|----------|
| (no args) / `--batch_all` | MLIR + external baseline, writes `{chip}_mlir_vs_{lib}_perf.csv` |
| `-b` / `--batch_mlir` | MLIR-only batch from config file |
| `--batch_external` | External library only |
| `--external` | Single config external |
| `--tuning` | Tune MIOpen kernels (conv only) |

## Key flags

- `-c` / `--configs_file` -- config file (default: `tier1-conv-configs`)
- `-o` -- output file name (default: `{chip}_perf.{date}`)
- `-t` / `--tuning_db` -- tuning DB TSV for "tuned" column
- `-qt` / `--quick_tuning_db` -- quick tuning DB
- `--test_dir` -- test directory for fusion mode (default: `../mlir/test/fusion/resnet50-e2e`)
- `--mlir-build-dir` -- build dir (auto-detected)
- `--external-gemm-library` -- `hipBLASLt` (default) or `CK`
- `--data-type` -- force types: `f32`, `f16`, `i8`, `i8_i32`, `i8_i8`, `fp8`, `fp8_fp8`, `fp8_f32`
- `--scale-type` -- force scale types for scaled GEMM: `f32`, `f8E8M0FNU`
- `--rocmlir_gen_flags` -- pass extra flags to `rocmlir-gen` to toggle features
- `--use-rocprof` -- use rocprofv3 instead of tuning driver

## Typical workflow

Tune first with `tuningRunner.py` (see `skills/tuningrunner-usage/SKILL.md`), then benchmark with the tuning database:

```bash
# 1. Tune configs
python3 tuningRunner.py --operation gemm --configs-file <configs> --output mlir_tuning.tsv

# 2. Benchmark with tuning DB
python3 perfRunner.py --op gemm --batch_all -c <configs> -t mlir_tuning.tsv
```

## Examples

```bash
python3 perfRunner.py --batch_all -t mlir_tuning.tsv                    # conv vs MIOpen
python3 perfRunner.py --op gemm --batch_all -t mlir_tuning.tsv          # GEMM vs hipBLASLt
python3 perfRunner.py --op gemm --external-gemm-library CK -t mlir_tuning.tsv
python3 perfRunner.py --op fusion --test_dir ../mlir/test/fusion/resnet50-e2e -t tuning_fusion.tsv

# Single config (no tuning DB needed)
python3 perfRunner.py --op gemm -- -t f32 -transA true -transB true -g 1 -m 1024 -k 769 -n 512
```

## External baselines

- Conv: MIOpen (`/opt/rocm/bin/MIOpenDriver`)
- GEMM: hipBLASLt (`hipblaslt-benchmark-driver`) or CK (`ck-gemm-benchmark-driver`)

Verify external baselines exist before running `--batch_all` or `--batch_external`:

```bash
which MIOpenDriver
ls build/bin/hipblaslt-benchmark-driver
ls build/bin/ck-gemm-benchmark-driver
```

## Build for benchmarking

```bash
cmake ... -DROCMLIR_ENABLE_BENCHMARKS=hipblaslt   # or 'ck' or 'all'
ninja ci-performance-scripts hipblaslt-benchmark-driver
# For CK baseline:
# cmake ... -DROCMLIR_ENABLE_BENCHMARKS=ck
# ninja ci-performance-scripts ck-benchmark-driver
```

After modifying `perfRunner.py`, rebuild with `ninja ci-performance-scripts` to update the installed copy in the build directory.

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

---

# Release Management

## Branch naming

Release branches follow the `release/rocm-rel-X.Y` pattern (e.g., `release/rocm-rel-7.2`). PR branches targeting a release branch must **not** contain "release" in their name -- this is the only naming constraint.

## Release branch lifecycle

1. Cut from `develop` at release milestone
2. Only bug fixes and critical patches -- **no new features**
3. Cherry-pick from `develop` (reference PR number)
4. Triton submodule moves on release branches require explicit approval and a `[TRITON-BUMP]` commit; do not silently bump
5. Performance fixes require benchmark evidence

## Patch review checklist

- [ ] Associated JIRA ticket linked in PR description?
- [ ] Bug fix or critical regression? (no new features)
- [ ] Fix exists on `develop` first? (always fix `develop`, then cherry-pick)
- [ ] Change is minimal and targeted? (no large refactors)
- [ ] `tests.sh` passes locally?
- [ ] `check-rocmlir-build-only` and unit tests pass?
- [ ] Performance benchmarks unaffected? (evidence for perf fixes)
- [ ] `librockcompiler_deps.cmake` consistent if dependencies changed?
- [ ] Triton submodule SHA unchanged (or explicitly approved)?
- [ ] No unreleased hardware references?

## Release CI

Release patches must pass Jenkins PR CI and (when re-enabled) nightly CI, and require at least two approvals before merging. After merging, notify the MIGraphX team to update their rocmlirTriton commit hash.

## CI triggers on release branches

- GitHub Actions: `Python Lint and Format Check` runs on push/PR to `release/**` (flake8 + yapf on changed `mlir/**/*.py`); no other GHA gates today
- Azure Pipelines: triggers on push to `mainline` (release integration) and PRs to `develop`
- Jenkins: `Jenkinsfile.release` only "Stores a Release Build" -- it does **not** run the full PR build/test matrix, so make sure your changes have already been validated by the regular `Jenkinsfile` PR pipeline

---

# Triton Bump

`external/triton/` is a **git submodule** of `triton-lang/triton`. Several Triton Python pipelines and helpers are replicated in C++ inside `mlir/`. Whenever the submodule advances, those replicas must be re-synced.

The full reference is `docs/bump_triton_version.md` -- read it once before starting and keep it open during the bump.

## Workflow

### 1. Create the bump branch

```bash
git checkout develop
git pull origin develop
git checkout -b triton-bump-<month>-<year>     # or triton-bump-<short-sha>
```

### 2. Record the old commit and update the submodule

```bash
cd external/triton
export OLD_COMMIT=$(git rev-parse HEAD)
git fetch
git checkout <new-target-sha>                  # or `git pull` to track upstream main
export NEW_COMMIT=$(git rev-parse HEAD)
cd ../..
git add external/triton
```

### 3. Rebuild LLVM via the wrapper

The Triton submodule pins LLVM through `external/triton/cmake/llvm-hash.txt`; bumping Triton may bump LLVM too.

```bash
bash scripts/build-llvm.sh
```

This wrapper:
1. Initializes submodules (recursive)
2. Applies every `triton-patches/*.patch` to `external/triton/` (idempotent)
3. Forces `MLIR_ENABLE_ROCM_RUNNER=ON` in Triton's build script
4. Runs Triton's `scripts/build-llvm-project.sh`

If a patch fails to apply, see step 4.

### 4. Re-evaluate `triton-patches/`

For each patch in `triton-patches/`:

```bash
cd external/triton
git diff ${OLD_COMMIT}..${NEW_COMMIT} -- <files-touched-by-patch>
```

- If the upstream change already covers what the patch did, **delete the patch file**
- If the patch still applies cleanly, leave it
- If the patch conflicts, rebase it manually and update the file (commit with `[TRITON-PATCH] ...`)

### 5. Diff the replication-source files

```bash
cd external/triton
git diff ${OLD_COMMIT}..${NEW_COMMIT} -- third_party/amd/backend/compiler.py > /tmp/compiler.py.diff
git diff ${OLD_COMMIT}..${NEW_COMMIT} -- python/src/llvm.cc > /tmp/llvm.cc.diff
git diff ${OLD_COMMIT}..${NEW_COMMIT} -- third_party/amd/python/triton_amd.cc > /tmp/triton_amd.cc.diff
git diff ${OLD_COMMIT}..${NEW_COMMIT} -- third_party/amd/lib/TritonAMDGPUTransforms/AccelerateAMDMatmul.cpp > /tmp/AccelerateAMDMatmul.cpp.diff
git diff ${OLD_COMMIT}..${NEW_COMMIT} -- third_party/amd/include/TritonAMDGPUToLLVM/TargetUtils.h > /tmp/TargetUtils.h.diff
cd ../..
```

### 6. Sync the C++ replicas

| Triton (Python / C++) | rocmlirTriton (C++) |
|-----------------------|---------------------|
| `make_ttir`, `make_ttgir`, `make_llir` part 1 | `mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp` |
| `make_llir` part 2, `make_amdgcn`, `make_hsaco` | `mlir/lib/Translation/TritonToHsaco/TritonToHsaco.cpp` |
| `init_targets`, `createTargetMachine`, `optimize_module` (`llvm.cc`) | `TritonToHsaco.cpp` (`initializeLLVMTargets`, `createTargetMachine`, `optimizeModule`) |
| `getMfmaVersion`, `getWmmaVersion`, `mlirTypeToScaledElemType` (`AccelerateAMDMatmul.cpp`) | `mlir/lib/Dialect/Rock/utility/tritonUtils.cpp` (`mlirTypeToScaleDotElemType` extends BF16/FP16) |
| `triton_amd.cc` Python pass bindings | corresponding `pm->addPass(...)` in `Pipelines.cpp` |
| `ISAFamily` / hardware capabilities | `mlir/lib/Dialect/Rock/IR/AmdArchDb.cpp` |

For each diff, mirror the change in the corresponding C++ file. Notes:

- New pass added in Python -> find C++ creation in `triton_amd.cc`, add the `pm->addPass(...)` call, include the relevant Triton header
- Pass signature changed -> update the call site to match (check `external/triton/third_party/amd/include/TritonAMDGPUTransforms/Passes.h`)
- New `ISAFamily` value -> update every switch in `AmdArchDb.cpp` (`getMatrixAccelKind`, `isFastAtomicAddSupported`, `isFastAtomicMaxSupported`, `getMaxNumChiplets`, `getMinNumCU`, `getMaxWavesPerEU`, etc.) and confirm `tritonUtils.cpp::getMfmaVersion`/`getWmmaVersion` handle the new chip
- Hardware feature gates in Python -> use `rock::*` helpers in C++ (`rock::supportsTDM(arch)`), adding new helpers in `AmdArchDb.cpp` if needed
- Skip features intentionally NOT replicated (see `rules/triton-integration.md`): `instrumentation.patch`, `knobs.*`, `add_di_scope`, `translate_to_mir`, `dump_sched_dag`, `swap_mir`, `dump_ir_*`, FPSan, `schedule_hint` loop processing

Commit each fix separately with a descriptive message:

```
Sync <change>. Caused by https://github.com/triton-lang/triton/pull/NNNNN
```

### 7. Build and fix breakage

```bash
bash cmake.sh
```

Resolve compilation errors; expect some from upstream LLVM API changes that came in with the LLVM bump.

### 8. Regenerate `librockcompiler_deps.cmake`

A bump can add or remove libraries baked into `librockCompiler.a`:

```bash
cd build
perl ../mlir/utils/jenkins/static-checks/get_fat_library_deps_list.pl \
  > ../mlir/tools/rocmlir-lib/librockcompiler_deps.cmake
cd ..
git add mlir/tools/rocmlir-lib/librockcompiler_deps.cmake
```

### 9. Run tests

```bash
bash tests.sh
```

If new top-level `fusion_*_with_host.mlir` files are added during the bump, also include them in `tests.sh`.

### 10. Open the PR with the bump checklist

PR description must include the bump checklist (lifted from `docs/bump_triton_version.md`):

```markdown
### Triton Bump Checklist

- [ ] Submodule updated from `OLD_COMMIT` to `NEW_COMMIT`
- [ ] LLVM rebuilt via `scripts/build-llvm.sh`
- [ ] `triton-patches/` re-evaluated; obsolete patches removed
- [ ] Diffed `compiler.py`, `llvm.cc`, `triton_amd.cc`, `AccelerateAMDMatmul.cpp`, `TargetUtils.h`
- [ ] `Pipelines.cpp` synced (`make_ttir`, `make_ttgir`, `make_llir` part 1)
- [ ] `TritonToHsaco.cpp` synced (`make_llir` part 2 + LLVM helpers)
- [ ] `tritonUtils.cpp` synced (`getMfmaVersion`, `getWmmaVersion`, `mlirTypeToScaleDotElemType`)
- [ ] `AmdArchDb.cpp` updated for any new `ISAFamily`
- [ ] `librockcompiler_deps.cmake` regenerated
- [ ] `cmake.sh` build succeeds
- [ ] `tests.sh` passes
- [ ] MIGraphX integration check (notify MIGraphX team if downstream impact)
```

## Common failure patterns

- **Missing pass**: new pass call in `compiler.py` -> find binding in `triton_amd.cc` and add C++ call
- **Pass signature change**: check the new signature in `external/triton/third_party/amd/include/TritonAMDGPUTransforms/Passes.h`
- **`ISAFamily` switch warnings**: `default:` case silently returned a fallback -- audit every `switch` in `AmdArchDb.cpp` and `tritonUtils.cpp`
- **Test failures**: behavioral change upstream -- update the test expectation only after confirming the new behavior is intended
- **Header errors**: mirror the includes from `triton_amd.cc` or other Triton files; CMake propagates Triton's include dirs through the helper functions in `cmake/triton.cmake`

## Local Triton patches (between bumps)

For targeted Triton fixes that cannot wait for upstream, add a new `triton-patches/<name>.patch` file:

```bash
cd external/triton
# ... edit files ...
git diff > ../../triton-patches/<name>.patch
git checkout .          # leave the submodule clean
cd ../..
git add triton-patches/<name>.patch
git commit -m "[TRITON-PATCH] <description>"
```

The wrapper applies patches in lexicographic order (`*.patch`), so prefix with a number if ordering matters.

---

# tuningRunner.py Usage

Source: `mlir/utils/performance/tuningRunner.py`. After tuning, use the output DB with `perfRunner.py` for benchmarking (see `skills/perfrunner-usage/SKILL.md`).

**Important**: Ensure no other processes are using the GPUs during tuning or benchmarking. Shared GPU usage causes noisy and unreliable results. Check with `rocm-smi` or `fuser /dev/kfd` before starting. Use `--gpus` to target specific GPUs:

```bash
python3 tuningRunner.py --op gemm -c <configs> --gpus 0
```

## Config source (exactly one required)

- `-c` / `--configs-file` -- file of configs (use `-` for stdin)
- `--config` -- single config string or `.mlir` file path
- `--test-dir` -- fusion E2E test directory (requires `--op fusion`)

## Required flag

`--op`: `conv`, `gemm`, `fusion`, `attention`, `gemm_gemm`, `conv_gemm`

## Key flags

| Flag | Default | Purpose |
|------|---------|---------|
| `-o` / `--output` | `tuning_results_local.tsv` | Output TSV (or `-` for stdout) |
| `--tuning-space` | `full` | `quick`, `full`, `greedy`, `exhaustive` |
| `--verify-mode` | `gpu` | `none`, `cpu`, `gpu` |
| `--verify-perf-configs` | off | Verify each perf config, not just the winner |
| `--gpus` | all | Select GPU IDs for parallel tuning |
| `--num-cpus` | auto | Max CPU threads for compilation |
| `--data-type` | `f32 f16 i8` | Force data types (gemm only): `f32`, `f16`, `bf16`, `i8`, `fp8`, `f4E2M1FN`, etc. |
| `--scale-type` | none | Force scale types for scaled gemm: `f32`, `f8E8M0FNU` |
| `--rocmlir-gen-flags` | none | Extra flags to pass to `rocmlir-gen` |
| `--retune` | off | Ignore existing rows, retune all |
| `--retry` | none | Retry: `failed`, `timed_out`, `crashed` |
| `--timeout` | none | Per-config timeout (seconds) |
| `--abort-on-error` | off | Abort tuning on first error (used in CI) |
| `--wait-for-compiles` | off | Wait for all compilations before tuning (useful for APUs) |
| `-s` / `--status` | off | Print pending count, no tuning |
| `-d` / `-v` / `-q` | normal | Debug / verbose / quiet logging |

## Output TSV format

```
# arch	numCUs	numChiplets	testVector	perfConfig	TFlops	tuningSpace	commitId	timestamp	durationSec
```

State file: `{output}.state` JSON tracks failed/timed_out/crashed for recovery.

## Examples

```bash
python3 tuningRunner.py --op gemm -c configs/tier1-gemm-configs -o tuning_db.tsv
python3 tuningRunner.py --op gemm --config "-g 3 -m 1024 -k 769 -n 512 -t f32"
python3 tuningRunner.py --op conv -c configs/tier1-conv-configs --tuning-space quick
python3 tuningRunner.py --op gemm -c configs/tier1-gemm-configs --gpus 2 3
python3 tuningRunner.py --op fusion --test-dir ../mlir/test/fusion/resnet50-e2e
cat configs.txt | python3 tuningRunner.py --op gemm -c - -o db.tsv
```
