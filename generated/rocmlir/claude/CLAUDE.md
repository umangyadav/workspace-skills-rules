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

# LLVM/MLIR C++ Quick Reference

rocMLIR-specific patterns and examples. For the full rules, see [LLVM Coding Standards](https://llvm.org/docs/CodingStandards.html) and the code-review checklist.

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


---

# CMake Conventions

## Project structure

- Root: `project(rocMLIR VERSION 2.0.0 LANGUAGES CXX C)`
- LLVM: `add_subdirectory` via `cmake/llvm-project.cmake`
- MHAL: `cmake/mlir-hal.cmake` (being decoupled; see PR #2333, #2325)
- Generator: always Ninja (`-G Ninja`)

## Custom CMake functions (defined in `cmake/llvm-project.cmake`)

| Function | Use for |
|----------|---------|
| `add_rocmlir_dialect_library` | Dialect IR libraries |
| `add_rocmlir_conversion_library` | Conversion pass libraries |
| `add_rocmlir_test_library` | Test helper libraries |
| `add_rocmlir_public_c_api_library` | C API libraries |
| `add_rocmlir_tool` | CLI tools |
| `add_rocmlir_unittest` | GoogleTest binaries |

## Notable CMake options

| Option | Default | Purpose |
|--------|---------|---------|
| `BUILD_FAT_LIBROCKCOMPILER` | OFF | Static library for MIGraphX |
| `ROCK_E2E_TEST_ENABLED` | OFF | Full E2E test suite |
| `ROCMLIR_DRIVER_PR_E2E_TEST_ENABLED` | OFF (recommend ON) | PR-scoped E2E tests |
| `ROCMLIR_BUILD_TUNING_DRIVER` | OFF (recommend ON) | Tuning driver tool |
| `ROCMLIR_ENABLE_BENCHMARKS` | "" | `hipblaslt`, `ck`, or `all` |


---

# Python Standards

## Source of truth

- **CI workflow**: `.github/workflows/ci.yml` -- defines flake8 ignore list, yapf checks, and pytest job
- **Dependencies**: `pip_requirements.txt`
- **Test location**: `mlir/utils/performance/tests/`

Consult these files directly for the latest configuration before writing or fixing Python code under `mlir/`.


---

# Code Review Checklist

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

# Testing Conventions

See also: `code-review.md` (Major section) and `dev-workflow.md` (Testing a new operation or feature) for review-time testing requirements.

## When to use each test type

| Type | Location | Use for |
|------|----------|---------|
| **Lit** (`.mlir`) | `mlir/test/` | Passes, pipelines, driver integration |
| **GoogleTest** | `mlir/unittests/` | C++ helpers, attributes, transform maps |
| **pytest** | `mlir/utils/performance/tests/` | Performance script logic (no GPU) |
| **E2E** | `mlir/test/e2e/`, `mlir/test/fusion/pr-e2e/` | Full GPU pipeline |

## Lit test patterns

```mlir
// Pass test (most common)
// RUN: rocmlir-opt --my-pass %s | FileCheck %s

// Split input + diagnostics (for verifier/negative tests)
// RUN: rocmlir-opt --my-pass -split-input-file -verify-diagnostics %s | FileCheck %s

// rocmlir-gen → rocmlir-opt (test generated IR)
// RUN: rocmlir-gen --arch gfx942 --operation gemm -t f16 -m 1024 -k 768 -n 512 | rocmlir-opt | FileCheck %s

// Arch substitution for arch-dependent IR in test file
// RUN: sed s/##TOKEN_ARCH##/%arch/g %s | rocmlir-driver --arch %arch --kernel-pipeline=migraphx,highlevel - | FileCheck %s

// Pipeline dump verification
// RUN: rocmlir-driver -dump-pipelines -kernel-pipeline=gpu -arch=gfx90a /dev/null -o /dev/null 2>&1 | FileCheck %s

// E2E: rocmlir-gen → rocmlir-driver → mlir-runner (GPU required)
// RUN: rocmlir-gen --arch %arch --operation gemm -pv | rocmlir-driver -c | mlir-runner --shared-libs=... | FileCheck %s

// Fusion E2E: clone-harness → lowering → verification → xmir-runner
// RUN: rocmlir-gen -fut <func> --arch %arch --clone-harness %s | \
//   rocmlir-driver -kernel-pipeline=migraphx,highlevel -host-pipeline=migraphx,highlevel | \
//   rocmlir-gen -ph -rand 1 -rand_type float -fut <func>_wrapper --verifier clone - | \
//   rocmlir-driver -host-pipeline mhal -kernel-pipeline full | \
//   xmir-runner --shared-libs=... --entry-point-result=void | FileCheck %s

```

## Key substitutions

Defined in `lit.cfg.py` / `lit.site.cfg.py.in` files:
- `mlir/test/lit.cfg.py` -- main substitutions (`%arch`, `%shlibext`, `%linalg_test_lib_dir`, etc.)
- `mlir/test/e2e/lit.cfg.py` -- E2E-specific substitutions
- `mlir/test/fusion/e2e/lit.cfg.py` -- fusion E2E substitutions

## FileCheck defaults

`FILECHECK_OPTS="-enable-var-scope --allow-unused-prefixes=false"` -- all CHECK prefixes must be used.

## Test targets

- `check-rocmlir` -- full suite
- `check-rocmlir-build-only` -- compile only
- `RocMLIRUnitTests` -- GoogleTest only
- E2E (PR subset): enable with `-DROCMLIR_DRIVER_PR_E2E_TEST_ENABLED=ON`
- E2E (full): enable with `-DROCK_E2E_TEST_ENABLED=ON`

## Fusion test requirements

MIGraphX-related or fusion changes must include fusion tests in `mlir/test/fusion/` (compile-level) and/or `mlir/test/fusion/pr-e2e/` (GPU E2E).

## Adding E2E tests with `.toml` files

1. Create or edit a `.toml` config in `mlir/test/e2e/` (e.g. `PrMyFeature.toml`)
2. Register the config name in `mlir/test/e2e/CMakeLists.txt` under the appropriate `list(APPEND CONFIGS ...)` block:
   - PR tests (`ROCMLIR_DRIVER_PR_E2E_TEST_ENABLED`) -- keep a small representative subset with short runtime to catch regressions quickly
   - Full/nightly tests (`ROCK_E2E_TEST_ENABLED`) -- add extensive coverage here (large configs, more dtypes, edge cases)
3. Optionally add a `.cfg` file (e.g. `PrMyFeature.cfg`) to apply arch or feature guards
4. Tests are auto-generated from `.toml` by `generateE2ETest.py` at build time


---

# rocMLIR CLI Tools

## rocmlir-gen -- generate MLIR from problem specs

Key flags: `-operation` (conv/gemm/attention/gemm_gemm/conv_gemm), `-arch`, `-t` (dtype), `-m/-k/-n` (GEMM dims), `-g` (groups), `-ph` (host harness), `-pv` (validate), `-pr` (print results), `-perf_config`, `-emit-tuning-key`

Conv: `-fil_layout`, `-in_layout`, `-out_layout`, `-batchsize`, `-in_channels`, `-out_channels`, `-fil_h/w`, padding/strides/dilations

Features: `-mfma`, `-wmma`, `-dot`, `-atomic_add` (each: `infer`/`on`/`off`)

## rocmlir-driver -- run lowering pipelines

- `-kernel-pipeline`: `applicability`, `migraphx`, `highlevel`, `gpu`, `rocdl`, `binary`, `full` (=`gpu,binary`)
- `-host-pipeline`: `migraphx`, `highlevel`, `mhal` (being decoupled; see PR #2333), `runner`
- `-c`: shorthand for `-kernel-pipeline=full -host-pipeline=runner`
- `-targets`: GPU targets; `-verify-passes`; `-dump-pipelines`

## rocmlir-opt -- MLIR optimizer

Standard `mlir-opt` interface with all Rock/MIGraphX passes registered.

## rocmlir-tuning-driver -- JIT benchmark

`-tuning-space` (quick/full/greedy/exhaustive), `-num-iterations`, `-warmup-iterations`, `-benchmark-config`, `-show-all-measurements`

## Python performance/tuning scripts (`mlir/utils/performance/`)

- `perfRunner.py` -- main benchmark runner; drives rocmlir-gen + rocmlir-driver to benchmark gemm/conv/attention across configs
- `tuningRunner.py` -- tuning orchestrator; explores perf_config space, selects best configs, updates perfDB
- `parameterSweeps.py` -- parameter sweep driver for exhaustive/weekly CI tuning
- `attentionSweeps.py` -- attention-specific parameter sweeps
- `perfRegressionReport.py` -- generates perf regression reports comparing runs
- `createPerformanceReports.py` / `createFusionPerformanceReports.py` -- CI report generators
- `reportUtils.py` / `perfCommonUtils.py` -- shared utilities for reporting and perf scripts
- `handleNewConfigs.py` -- processes new tuning configs into the config database
- `convertRocBlasToPerfRunner.py` -- converts rocBLAS configs to perfRunner format
- Config files: `configs/tier1-gemm-configs`, `configs/tier1-conv-configs`, `configs/tier1-attention-configs`, `configs/tier1-gemmgemm-configs`, `problem-config-tier-1-models`, `bert-configs-raw`

## Widgets (`mlir/utils/widgets/`)

- `rocm-run` / `xmir-run` -- shell wrappers for running rocMLIR / MIGraphX IR on GPU

## Common C++ tool pipelines

```bash
# Smoke test
rocmlir-gen --arch gfx942 -p | rocmlir-opt

# Full lowering + validate (single op)
rocmlir-gen --arch gfx942 -ph -pv | rocmlir-driver -c | mlir-runner --shared-libs=...

# Tuning a single config
rocmlir-gen --arch gfx942 --perf_config= | rocmlir-tuning-driver -tuning-space full

# Kernel to assembly
rocmlir-gen ... | rocmlir-driver -kernel-pipeline=gpu,rocdl --arch=gfx942 | \
  rocmlir-translate -gpu-module-to-rocdlir | opt -O3 | llc -mcpu=gfx942
```

## Lit test pipelines (from `mlir/test/`)

```bash
# E2E test: rocmlir-gen generates + validates a kernel
rocmlir-gen --arch %arch --operation gemm -t f16 -m 1024 -k 768 -n 512 -pv | \
  rocmlir-driver -c | mlir-runner --shared-libs=... | FileCheck %s

# Fusion E2E: clone-harness → lowering → host pipeline → xmir-runner
rocmlir-gen -fut mlir_attention --arch %arch --clone-harness %s | \
  rocmlir-driver -kernel-pipeline=migraphx,highlevel -host-pipeline=migraphx,highlevel | \
  rocmlir-gen -ph -rand 1 -rand_type float -fut mlir_attention_wrapper --verifier clone - | \
  rocmlir-driver -host-pipeline mhal -kernel-pipeline full | \
  xmir-runner --shared-libs=... --entry-point-result=void | FileCheck %s

# IR verification: check pass output with FileCheck
rocmlir-gen --arch %arch ... | rocmlir-driver -arch %arch -c \
  -mlir-print-ir-after=<pass-name> 2>&1 | FileCheck %s --check-prefix=...
```

## Tuning and benchmarking pipeline

```bash
# 1. Tune gemm/conv configs → produces tuning DB (.tsv)
python3 tuningRunner.py --abort-on-error --operation gemm \
  --configs-file=<configs> --output=mlir_tuning_${CHIP}.tsv

python3 tuningRunner.py --abort-on-error --operation conv \
  --configs-file=<configs> --output=mlir_tuning_${CHIP}.tsv

# 2. Tune fusion models (resnet50, bert) → produces fusion tuning DB
python3 tuningRunner.py --abort-on-error --op fusion \
  --test-dir ../mlir/test/fusion/resnet50-e2e/ -o tuning_fusion_${CHIP}.tsv

python3 tuningRunner.py --abort-on-error --op fusion \
  --test-dir ../mlir/test/xmir/bert-torch-tosa-e2e/ -o tuning_fusion_${CHIP}.tsv

# 3. Benchmark with tuning DB
python3 perfRunner.py --op=conv --batch_all \
  --configs_file=<conv-configs> \
  --tuning_db=mlir_tuning_${CHIP}.tsv \
  --quick_tuning_db=mlir_quick_tuning_${CHIP}.tsv

python3 perfRunner.py --op=gemm --batch_all \
  --configs_file=<gemm-configs> \
  --tuning_db=mlir_tuning_${CHIP}.tsv \
  --quick_tuning_db=mlir_quick_tuning_${CHIP}.tsv

python3 perfRunner.py --op=attention -b \
  --configs_file=<attn-configs> \
  --tuning_db=mlir_tuning_${CHIP}.tsv

python3 perfRunner.py --op=fusion \
  --test_dir=mlir/test/fusion/resnet50-e2e/ \
  --tuning_db=tuning_fusion_${CHIP}.tsv

# 4. Multi-GPU tuning
python3 tuningRunner.py --operation gemm --configs-file=<configs> --gpus 0 1 2 3
```

## Parameter sweeps

```bash
# Exhaustive parameter sweeps across all tier-1 configs
python3 parameterSweeps.py -j <num_workers> <CONFIG> --log-failures
```

All Python scripts are in `mlir/utils/performance/`. Run `python <script>.py --help` for full flag reference.


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

## Adding a MIGraphX operation

1. Define op in `mlir/include/mlir/Dialect/MIGraphX/IR/MIGraphX.td`
2. Add lowering in `mlir/lib/Conversion/MIGraphXToTosa/` or `MIGraphXToLinalg/`
3. Add tests in `mlir/test/Conversion/`

## Testing a new operation or feature

### Architecture coverage

- New ops/passes must work on all supported GPU architectures (gfx90a, gfx942, etc.)
- If an op is architecture-specific, guard it with proper target checks in both code and tests
- Use `lit.cfg.py` to configure arch-specific test guards

### Data type coverage

- Enumerate all dtypes the op should support (f16, bf16, f32, f8, i8, i4, etc.)
- Ensure the implementation handles each supported dtype explicitly -- do not silently fall through
- Return a clear error (`emitOpError`) for unsupported dtypes rather than producing wrong results
- Add E2E tests covering each supported dtype and Lit tests that verify unsupported dtypes are rejected

### Edge cases and completeness

- Consider boundary conditions: zero-size tensors, non-aligned shapes, large dimensions, scalar inputs
- For optimization passes, verify the optimization fires (FileCheck for expected IR) and verify correctness (E2E with random data)
- Test both the optimized path and the fallback/unoptimized path
- If the feature interacts with fusion, test fused and unfused variants

## Debugging a pass failure

```bash
# Isolate
rocmlir-opt --my-pass input.mlir

# Enable debug output (requires -DLLVM_ENABLE_ASSERTIONS=ON)
rocmlir-opt --my-pass input.mlir --debug-only=my-pass

# Dump full pipeline
rocmlir-driver -dump-pipelines -kernel-pipeline=full input.mlir 2>&1
```


---

# CI Pipelines

rocMLIR uses three CI systems.

## Jenkins (primary, GPU-heavy)

- Config: `mlir/utils/jenkins/Jenkinsfile` (Groovy)
- Variants for downstream and release builds (keep in sync with main Jenkinsfile)
- Docker: `rocm/mlir:rocm<version>-latest` (check Jenkinsfile for current version), Ninja, ROCm clang, `RelWithDebInfo`
- PR: premerge clang-format/tidy, selected tuning, limited E2E subset
- Nightly: all E2E tests with random data, perf comparison reports, MIGraphX check stages
- Weekly: exhaustively tunes all tier1 configs + parameter sweeps + perfDB archival
- Upstream merges: set `ignoreExternalLinting=true` to skip linting `external/`

## Azure Pipelines (ROCm ecosystem)

- Config: `.azuredevops/rocm-ci.yml`
- Triggers: push to `develop`/`mainline`, PRs to `develop`
- Excludes: `.github/`, `*.md`
- Uses shared templates from `ROCm/ROCm` repo

## GitHub Actions (lightweight)

- Config: `.github/workflows/ci.yml`
- Triggers: PRs and push to `develop` and `release/**`
- Jobs: flake8 + yapf on changed `mlir/**/*.py`, pytest for perf scripts
- Codecov: `.github/workflows/codecov-report.yml` (biweekly, not blocking)

## CODEOWNERS

All paths: `@causten` (`.github/CODEOWNERS`)


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


# Skills


---

The following skills are available for on-demand use:


---

- **build-test-workflow**: # Build, Test, and Lint

---

- **kernel-profiling**: # Kernel Profiling

---

- **perfrunner-usage**: # perfRunner.py Usage

---

- **pr-review**: # PR Review

---

- **release-management**: # Release Management

---

- **tuningrunner-usage**: # tuningRunner.py Usage

---

- **upstream-llvm-merge**: # Upstream LLVM Merge
