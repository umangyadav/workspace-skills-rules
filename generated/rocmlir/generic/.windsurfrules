# rocmlir AI Agent Rules and Skills


---

## Rules


---

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

## Skills


---

# Build, Test, and Lint

## Usage

"Build and test the project" or "Verify the build"

## Step 1: Build

```bash
mkdir -p build && cd build
cmake -G Ninja .. -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DLLVM_CCACHE_BUILD=ON \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DMLIR_ENABLE_EXECUTION_ENGINE=ON \
  -DMLIR_ENABLE_ROCM_RUNNER=ON \
  -DROCMLIR_DRIVER_PR_E2E_TEST_ENABLED=ON \
  -DROCMLIR_DRIVER_TEST_GPU_VALIDATION=ON
ninja && ninja rocmlir-driver rocmlir-gen mlir-runner \
  ci-performance-scripts mlir_runner_utils mlir_rocm_runtime \
  mlir_c_runner_utils mlir_async_runtime
```

### Full local build (PR + nightly with random data)

```bash
cmake -G Ninja .. -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DLLVM_CCACHE_BUILD=ON \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DMLIR_ENABLE_EXECUTION_ENGINE=ON \
  -DMLIR_ENABLE_ROCM_RUNNER=ON \
  -DROCMLIR_DRIVER_PR_E2E_TEST_ENABLED=ON \
  -DROCMLIR_DRIVER_E2E_TEST_ENABLED=ON \
  -DROCK_E2E_TEST_ENABLED=ON \
  -DROCMLIR_DRIVER_RANDOM_DATA_SEED=1 \
  -DROCMLIR_DRIVER_TEST_GPU_VALIDATION=ON
```

### Nightly fixed E2E build

```bash
cmake -G Ninja .. -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DROCMLIR_DRIVER_PR_E2E_TEST_ENABLED=OFF \
  -DROCMLIR_DRIVER_E2E_TEST_ENABLED=ON \
  -DROCK_E2E_TEST_ENABLED=ON \
  -DROCMLIR_DRIVER_TEST_GPU_VALIDATION=ON
```

### Nightly random E2E build

```bash
cmake -G Ninja .. -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DROCMLIR_DRIVER_PR_E2E_TEST_ENABLED=OFF \
  -DROCMLIR_DRIVER_E2E_TEST_ENABLED=ON \
  -DROCK_E2E_TEST_ENABLED=ON \
  -DROCMLIR_DRIVER_RANDOM_DATA_SEED=1 \
  -DROCMLIR_DRIVER_TEST_GPU_VALIDATION=OFF
```

### MIGraphX development build

```bash
mkdir -p build_migx && cd build_migx
cmake -G Ninja .. -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_C_COMPILER_LAUNCHER=ccache \
  -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
  -DBUILD_FAT_LIBROCKCOMPILER=ON
ninja && cmake --install . --prefix <install-prefix>
```

This builds `librockcompiler` as a static library and installs it for MIGraphX integration.

Always verify exit code. If build fails, stop and report -- do not proceed to test/lint.



## Step 2: Test

```bash
ninja check-rocmlir          # Full Lit + unit tests
ninja RocMLIRUnitTests       # GoogleTest only
```


## Step 3: Lint

- **C++ format**: `git-clang-format origin/develop`
- **C++ tidy**: see `mlir/utils/jenkins/static-checks/premerge-checks.py`
- **Python lint/format**: see `.github/workflows/ci.yml` for flake8/yapf configuration

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

---

# Kernel Profiling

## Tools

- **rocprofv3** (`/opt/rocm/bin/rocprofv3`): low-level GPU profiler for timing and HW counters
- **rocprof-compute**: comprehensive analysis with structured bottleneck reports

Official docs: [Using rocprofv3](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-rocprofv3.html) -- refer here for installation, dependencies, full CLI options, and output formats.

## Step 0: Verify installation

Before profiling, confirm that the tools are available and the GPU is accessible:

```bash
rocprofv3 --version
rocprof-compute --version
rocminfo | grep gfx
```

- **rocprofv3**: included with ROCm. If missing, check ROCm installation and ensure `/opt/rocm/bin` is in `PATH`.
- **rocprof-compute**: included with ROCm >= 6.2. For older ROCm or custom installs, requires Python >= 3.8, CMake >= 3.19, and additional Python dependencies. See [installation docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/install/core-install.html) for source build and `pip install -r requirements.txt`.
- **rocminfo**: verifies GPU is visible. If no `gfx` output, check ROCm drivers and device permissions.

## Step 1: Generate kernel

```bash
rocmlir-gen --operation gemm --arch gfx942 -t f16 -m 4096 -k 4096 -n 4096 -ph | \
  rocmlir-driver -c > kernel.mlir
```

## Step 2a: Profile with rocprofv3 (quick)

```bash
rocprofv3 --kernel-trace --stats -f csv -o results -- \
  mlir-runner kernel.mlir --shared-libs=... --entry-point-result=void
```

- PMC counters: use `rocmlir_metrics.txt` for LDS bank conflict (`pmc: LDSBankConflict`)
- Output: `results.csv` (timing), `results_kernel_stats.csv` (aggregates)

## Step 2b: Profile with ROCm Compute Profiler (comprehensive)

[ROCm Compute Profiler](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/what-is-rocprof-compute.html) provides kernel-level profiling with hardware counter analysis, Speed-of-Light evaluations, and roofline analysis. See [profiling docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/profile/mode.html) for full options.

```bash
rocprof-compute profile -n my_kernel -- \
  mlir-runner kernel.mlir --shared-libs=... --entry-point-result=void
```

Filtering: `-k <kernel>`, `-b <block>` (SQ, LDS, TCC, etc.), `--gpu-id`. See [filtering docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/profile/mode.html#filtering).

## Step 3: Analyze

See [CLI analysis docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/analyze/cli.html) and [standalone GUI docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/analyze/standalone-gui.html).

```bash
rocprof-compute analyze -p ./workloads/my_kernel/<arch>/

rocprof-compute analyze -p ... --gui   # Standalone GUI
```

Features: Speed-of-Light analysis, memory chart analysis, roofline analysis, [baseline comparisons](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/analyze/cli.html#analysis-baseline-comparison).

## Step 4: Identify bottlenecks

| Bottleneck | What to check |
|-----------|---------------|
| **Compute bound** | SQ occupancy, VALU/MFMA utilization, wavefront stalls |
| **Memory bound** | L2 (TCC) hit rate, HBM bandwidth, LDS bank conflicts |
| **Latency bound** | Instruction fetch stalls, barrier waits, dependency stalls |

For the full list of available counters and derived metrics, run `rocprofv3 --list-avail` or see [MI200 performance counters and metrics](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-rocprofv3.html#kernel-counter-collection). Extra counters can be defined via YAML files with `--extra-counters` (see [extra counters docs](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-rocprofv3.html#extra-counters)).

Map findings to rocMLIR tuning parameters defined in `mlir/include/mlir/Dialect/Rock/IR/RockAttrDefs.td` (see also `RockTuningParamAttrInterface.td` and `RockAccelTuningParamAttrInterface.td`).

## Thread tracing with rocprof-compute-viewer

Thread traces provide instruction-level visibility into GPU kernel execution. See [official thread trace docs](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html) for full details.

### Prerequisites

1. ROCm 7.2+ with aqlprofile and rocprof-trace-decoder installed (see [prerequisites](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#prerequisites))
2. Install [rocprof-compute-viewer](https://github.com/ROCm/rocprof-compute-viewer/releases) client for visualization

Verify before tracing:

```bash
ls /opt/rocm/lib/libaqlprofile*.so
ls /opt/rocm/lib/librocprof-trace-decoder*.so
rocprofv3 --version
```

If `libaqlprofile` or `librocprof-trace-decoder` is missing, follow the [prerequisite instructions](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#prerequisites) to install them. Without these, `rocprofv3 --att` will fail with "INVALID_SHADER_DATA" or "Agent not supported".

### Collect traces with rocprofv3

Default collection:

```bash
rocprofv3 --att -d att_dump -- <application>
```

With input file for fine-grained control (see [input file format](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#using-input-file)):

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
```

For AMD Instinct, enable perfmon streaming with `--att-activity`:

```bash
rocprofv3 --att --att-activity 8 -d att_dump -- <application>
```

Key parameters: `--att-target-cu`, `--att-shader-engine-mask`, `--att-simd-select`, `--att-buffer-size`, `--kernel-include-regex`, `--kernel-iteration-range`. See [full parameter table](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#rocprofv3-parameters-for-thread-tracing).

### Using with rocMLIR

Create a `run.sh` script with full absolute paths:

```bash
#!/bin/bash
<rocMLIR>/build/bin/rocmlir-gen --operation=gemm -m 16384 -n 16384 -k 384 -g 1 --arch <arch> | \
  <rocMLIR>/build/bin/rocmlir-gen -ph - | \
  <rocMLIR>/build/bin/rocmlir-driver -c --arch <arch> | \
  <rocMLIR>/mlir/utils/widgets/rocm-run
```

Make executable and trace:

```bash
chmod +x run.sh
rocprofv3 --att -i att.json -d att_dump -- $(pwd)/run.sh
```

### Output files

- `stats_*.csv` -- instruction latency summary per kernel (hitcount, latency, stalls, idle cycles)
- `ui_output_agent_*_dispatch_*/` -- open in rocprof-compute-viewer for visualization
- `.att` / `.out` -- raw trace data and code object binaries

Download to local machine with `scp -r` and open in rocprof-compute-viewer.

### Troubleshooting

- **Empty stats CSV**: kernel may not launch enough waves to fill `att-target-cu`; try increasing waves, changing `target_cu`, or widening `att-shader-engine-mask`
- **File not found**: use full absolute paths in `run.sh`; verify `run.sh` has executable permissions
- **Data lost warnings**: reduce `att-perfcounter-ctrl` value or increase `att-buffer-size`
- See [official troubleshooting](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#troubleshooting)

## Integration with perfRunner.py

- `--use-rocprof` flag uses rocprofv3 for benchmarking
- `rocmlir_metrics.txt` defines PMC counters collected
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
- `--rocmlir_gen_flags` -- pass extra flags to rocmlir-gen to toggle features
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
python3 perfRunner.py --batch_all -t mlir_tuning.tsv                    # conv vs MIOpen with tuning DB
python3 perfRunner.py --op gemm --batch_all -t mlir_tuning.tsv          # GEMM vs hipBLASLt with tuning DB
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
which MIOpenDriver               # conv baseline (from ROCm install)
ls build/bin/hipblaslt-benchmark-driver  # gemm baseline (built from source)
ls build/bin/ck-gemm-benchmark-driver    # CK baseline (if using --external-gemm-library CK)
```

## Build for benchmarking

```bash
cmake ... -DROCMLIR_ENABLE_BENCHMARKS=hipblaslt  # or 'ck' or 'all'
ninja ci-performance-scripts hipblaslt-benchmark-driver
# For CK baseline:
# cmake ... -DROCMLIR_ENABLE_BENCHMARKS=ck
# ninja ci-performance-scripts ck-benchmark-driver
```

After modifying `perfRunner.py` source, rebuild with `ninja ci-performance-scripts` to update the installed copy in the build directory.

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

---

# Release Management

## Branch naming

Release branches follow the `release/rocm-rel-X.Y` pattern (e.g., `release/rocm-rel-7.2`). PR branches targeting a release branch must **not** contain "release" in their name -- this is the only naming constraint.

## Release branch lifecycle

1. Cut from `develop` at release milestone
2. Only bug fixes and critical patches -- **no new features**
3. Cherry-pick from `develop` (reference PR number)
4. `[EXTERNAL]` LLVM cherry-picks for critical crash fixes
5. Performance fixes require benchmark evidence

## Patch review checklist

- [ ] Associated JIRA ticket linked in PR description?
- [ ] Bug fix or critical regression? (no new features)
- [ ] Fix exists on `develop` first? (always fix develop, then cherry-pick)
- [ ] Change is minimal and targeted? (no large refactors)
- [ ] `check-rocmlir` passes?
- [ ] Performance benchmarks unaffected? (evidence for perf fixes)
- [ ] `librockcompiler_deps.cmake` consistent?
- [ ] No unreleased hardware references?

## Release CI

Release patches must pass Jenkins PR CI and nightly CI, and require at least two approvals before merging. After merging, notify MIGraphX team to update their rocMLIR commit hash.

## CI triggers on release branches

- GitHub Actions: `release/**` (Python lint + tests)
- Azure Pipelines: `mainline` (release integration)
- Jenkins: fat library builds on release branches

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
| `--rocmlir-gen-flags` | none | Extra flags to pass to rocmlir-gen |
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

---

# Upstream LLVM Merge

`external/llvm-project/` is a **git subtree** (not a submodule). Source is `ROCm/llvm-project` `amd-staging` branch (lags upstream by a few months).

## Prerequisites

- Wait for bulk promotion to `amd-staging` to be announced
- Take separate clones of [ROCm/llvm-project](https://github.com/ROCm/llvm-project/tree/amd-staging) and rocMLIR for reference during conflict resolution

## Workflow

### 1. Create merge branch

```bash
git checkout develop
git pull origin develop
git checkout -b upstream_merge_<month>
```

### 2. Squash-pull LLVM

```bash
git subtree pull --squash --prefix=external/llvm-project git@github.com:ROCm/llvm-project.git amd-staging
```

If you get an error about the prefix never being added, use `--prefix=./external/llvm-project`.

Produces two commits:
1. `Squashed 'external/llvm-project/' changes from <old>..<new>`
2. `Merge commit '<sha>' into upstream_merge_<month>`

### 3. Resolve conflicts

Check out your llvm-project clone to the revision you just merged (find it in the squash commit). Use both rocMLIR and llvm-project checkouts to understand each conflict:

- **Local changes that need upstreaming**: document them, keep both versions as needed
- **Upstream changes modified during review**: take the upstream version
- **Conflicts outside `mlir/`**: take upstream's version (copy from your llvm-project checkout)
- **Overlapping patches**: line-based merging can duplicate or drop sections; compare carefully against both sources
- **"Impossible" errors** (missing methods, duplicate overrides): usually overlapping patches merged incorrectly

There is no clean way to capture conflict-resolution patches separately -- they get absorbed into the squash commit.

### 4. Fix rocMLIR breakage

Each fix in a separate commit with a descriptive message referencing the upstream PR that caused it. Keep internal and external patches in separate commits.

```
Fix <description>. Caused by https://github.com/llvm/llvm-project/pull/NNNNN
```

Before fixing breakage, check the previous upstream merge PR for its attached diff files (`mlir_diffs.txt`, `llvm_diffs.txt`). These show all custom rocMLIR patches applied on top of upstream. Verify that none of these patches were lost during the new merge -- re-apply any that were dropped by the subtree pull.

Use `git log --grep` on upstream to find relevant changes when debugging breakage.

### 5. Copy non-MLIR directories

Once you know the upstream commit, copy over non-MLIR directories in case subtree pull missed something.

### 6. Update deps

Regenerate `librockcompiler_deps.cmake` using:

```bash
perl mlir/utils/jenkins/static-checks/get_fat_library_deps_list.pl
```

### 7. Generate diff files for review

```bash
diff -rup <llvm-project-clone>/mlir rocMLIR/external/llvm-project/mlir > mlir_diffs.txt
diff -rup <llvm-project-clone>/llvm rocMLIR/external/llvm-project/llvm > llvm_diffs.txt
```

Use these to identify changes merged incorrectly, opportunities to upstream, or cases where we should use the upstream version. Note that upstreamed changes may still appear in the diff since `amd-staging` lags upstream -- check against `llvm/llvm-project` main to be sure.

### 8. Keep branch current

Periodically merge `develop` into the merge branch:
```bash
git merge develop
```

### 9. Verify external patches preserved

Ask team members to confirm their `[EXTERNAL]` commits are still present after the merge.

### 10. Build and test

Build rocMLIR and run tests on a machine with GPUs:

```bash
cmake --build . --target check-llvm
cmake --build . --target check-mlir
cmake --build . --target check-rocmlir
```

`check-rocmlir` exercises internal code and requires GPUs. Jenkins nightly provides more extensive coverage.

### 11. Open PR with checklist

Set Jenkins parameter `ignoreExternalLinting=true` to skip clang-format/tidy on `external/`.

PR description should include this checklist:

```markdown
### External LIT Tests
- [ ] `check-llvm`
- [ ] `check-mlir`

### Jenkins Internal CI
- [ ] Weekly (parameterSweeps + Tuning)
- [ ] Nightly CI
- [ ] PR CI

### MIGraphX CI
- [ ] Update MIGraphX SHA and run through their CI

### Performance
- [ ] Compare tuning runtime with a recent weekly run to check for regressions

### Navi2X (if applicable)
- [ ] parameterSweeps
- [ ] Nightly E2E tests (fixed + random data)
- [ ] PR E2E tests
```

## Common failure patterns

- **MLIR errors**: wrong dialect, wrong op, or incorrect conflict resolution (e.g., using old op name when both old and new exist)
- **Crashes**: usually assertion failures from changed invariants; use `git log --grep` on upstream to trace the cause
- **Result failures**: data structure changes (e.g., affine map representation) causing code to read data the old way
- **Test failures**: sometimes the right fix is updating the test (dialect/op changes, changed correct output)

## Cherry-picking individual LLVM fixes

For targeted fixes between full merges:
```bash
git commit -m "[EXTERNAL] Cherry pick https://github.com/llvm/llvm-project/pull/NNNNN"
```

## Branch naming

`upstream_merge_dec`, `upstream_merge_jan_26`, `upstream-merge-march-2026`
