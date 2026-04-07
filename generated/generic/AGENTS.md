# rocMLIR AI Agent Rules and Skills


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
- `external/mlir-hal/` -- vendored MHAL dependency (rarely needs changes; use `[EXTERNAL]` commit prefix when modifying)

## Tools

- `rocmlir-gen` -- generate Rock dialect kernels and driver code to run/validate kernel output
- `rocmlir-driver` -- lower and run kernels through pipelines (`-c` for default full pipeline)
- `rocmlir-opt` -- MLIR optimizer with Rock passes
- `rocmlir-tuning-driver` -- JIT benchmark kernels

## Build

```
cmake -G Ninja .. -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++
ninja check-rocmlir
```

## Commit messages

- Jira: `[AIROCMLIR-NNN] Description (#PR)`
- Plain: `Fix/Add/Update description (#PR)`
- Non-functional: `[NFC] Description`
- External: `[EXTERNAL] Description`

## Confidentiality

This is a public repo. Never reference unreleased AMD hardware codenames, unannounced chip IDs, NDA-protected features, or internal project names. Use only publicly released `gfx*` identifiers.

## Downstream impact

Breaking changes to Rock dialect IR or C API require coordination with MIGraphX. Always keep `librockcompiler_deps.cmake` in sync.


---

# LLVM/MLIR C++ Standards

## Formatting and naming

- Style: `BasedOnStyle: LLVM`, `AlwaysBreakTemplateDeclarations: Yes`
- Classes/Enums: `CamelCase`; Functions/Members/Params/Vars: `camelBack`

## Casting -- never use `dynamic_cast`

```cpp
// GOOD
if (isa<MemRefType>(val.getType())) { auto t = cast<MemRefType>(val.getType()); }
auto t = dyn_cast<MemRefType>(val.getType()); // returns nullptr on failure

// BAD
auto t = dynamic_cast<MemRefType*>(ptr); // never use C++ RTTI
```

## ADT types -- prefer LLVM over STL

- `llvm::SmallVector<T, N>` over `std::vector`
- `llvm::StringRef` over `const std::string&`
- `llvm::ArrayRef<T>` over `const std::vector<T>&`
- Algorithms: `llvm::find`, `llvm::all_of`, `llvm::to_vector`, `llvm::zip_equal`

## Error handling -- never use exceptions

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

## Include order

1. Primary/dialect headers (`mlir/Dialect/Rock/...`)
2. Other MLIR headers (`mlir/IR/...`, `mlir/Support/...`)
3. LLVM headers (`llvm/ADT/...`, `llvm/Support/...`)
4. Standard library (`<algorithm>`, `<cstdint>`)

## Namespaces

- `using namespace mlir;` and `using namespace mlir::rock;` at file scope
- Anonymous namespace for local structs: `namespace { struct MyPass ... }`
- Pass defs: `namespace mlir { namespace rock { #define GEN_PASS_DEF_... } }`


---

# MLIR Pass and Pattern Writing

## Pass definition (TableGen-generated base)

```cpp
namespace mlir {
namespace rock {
#define GEN_PASS_DEF_ROCKCONVTOGEMMPASS
#include "mlir/Dialect/Rock/Passes.h.inc"
} // namespace rock
} // namespace mlir

namespace {
struct RockConvToGemmPass
    : public rock::impl::RockConvToGemmPassBase<RockConvToGemmPass> {
  void runOnOperation() override;
};
} // namespace
```

## Pattern rewriting -- two styles

**Greedy rewrite** (most common):
```cpp
struct MyPattern : public OpRewritePattern<MyOp> {
  LogicalResult matchAndRewrite(MyOp op, PatternRewriter &rw) const override;
};
// Drive with: applyPatternsGreedily(getOperation(), std::move(patterns))
```

**Dialect conversion** (type/legalization changes):
```cpp
struct MyConverter : public OpConversionPattern<MyOp> {
  LogicalResult matchAndRewrite(MyOp op, OpAdaptor adaptor,
                                ConversionPatternRewriter &rw) const override;
};
// Drive with: applyPartialConversion(getOperation(), target, std::move(patterns))
```

## Op creation

```cpp
auto newOp = GemmOp::create(builder, loc, resultType, operands...);
rewriter.replaceOpWithNewOp<NewOp>(oldOp, args...);
```

## Type handling

```cpp
if (!isa<MemRefType>(val.getType()))
  return op.emitOpError("expected memref");
auto memType = cast<MemRefType>(val.getType());
auto newType = MemRefType::get(shape, elementType);
```


---

# MLIR TableGen Conventions

## Dialect definition

```tablegen
def Rock_Dialect : Dialect {
  let name = "rock";
  let cppNamespace = "::mlir::rock";
  let useDefaultAttributePrinterParser = 1;
  let usePropertiesForAttributes = 1;
}
```

## Op definition

```tablegen
def Rock_GemmOp : Rock_Op<"gemm", [
    DeclareOpInterfaceMethods<RockGemmWrapperInterface>,
    DeclareOpInterfaceMethods<MemoryEffectsOpInterface>,
    RockFusionRoot, AttrSizedOperandSegments]> {
  let arguments = (ins ...);
  let results = (outs Optional<AnyRankedTensor>:$result);
  let hasVerifier = 1;
  let assemblyFormat = [{ ... }];
}
```

Common traits: `Pure`, `DeclareOpInterfaceMethods<I>`, `AttrSizedOperandSegments`, `RockFusionRoot`, `ViewLikeOpInterface`, `SingleBlockImplicitTerminator`

## Attribute/Enum definitions

```tablegen
class Rock_Attr<string name, list<Trait> traits = []> : AttrDef<Rock_Dialect, name, traits>;
def ConvOpType : I32EnumAttrCase<"Fwd", 0, "conv">;
def ConvOpTypes : Rock_I32Enum<"ConvOpType", "...", [ConvOpType, ...]>;
```

## Pass declarations

```tablegen
def RockConvToGemmPass : Pass<"rock-conv-to-gemm", "func::FuncOp"> {
  let summary = "Convert conv to gemm";
  let dependentDialects = ["rock::RockDialect"];
  let options = [Option<"flag", "flag", "bool", "false", "description">];
}
```

## Source layout

- Definitions: `mlir/include/mlir/Dialect/<Name>/IR/` (.td, .h)
- Implementation: `mlir/lib/Dialect/<Name>/IR/` (.cpp)
- Transforms: `mlir/lib/Dialect/<Name>/Transforms/`
- Conversions: `mlir/lib/Conversion/<ConvName>/`
- Conversion passes: `mlir/include/mlir/Conversion/RocMLIRPasses.td`


---

# CMake Conventions

## Project structure

- Root: `project(rocMLIR VERSION 2.0.0 LANGUAGES CXX C)`
- LLVM: `add_subdirectory` via `cmake/llvm-project.cmake`
- MHAL: `cmake/mlir-hal.cmake`
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
| `ROCMLIR_DRIVER_PR_E2E_TEST_ENABLED` | OFF | PR-scoped E2E tests |
| `ROCMLIR_BUILD_TUNING_DRIVER` | OFF | Tuning driver tool |
| `ROCMLIR_ENABLE_BENCHMARKS` | "" | `hipblaslt`, `ck`, or `all` |


---

# Python Standards

## Formatting (CI-enforced)

- **Formatter**: yapf (default style)
  - Fix: `yapf -i <file>`
- **Linter**: flake8 with ignored rules: `E501,E251,E124,W605,W504,E131,E126,W503,E123`
  - Run: `flake8 --ignore=E501,E251,E124,W605,W504,E131,E126,W503,E123 <files>`
- **CI**: GitHub Actions runs both on changed `mlir/**/*.py` files vs merge base

## Testing

- Framework: **pytest**
- Test location: `mlir/utils/performance/tests/`
- Run: `cd mlir/utils/performance && python -m pytest tests/ -v`
- No GPU required (tests mock HIP)

## Environment

- Python 3.10+ (CI container)
- Dependencies: `pip install -r pip_requirements.txt`
- Key packages: numpy, scipy, pandas, jinja2, pybind11, yapf, flake8, pytest


---

# Code Review Checklist

## Premerge CI gates

- **clang-format**: `git-clang-format` vs base (LLVM style, no diff allowed)
- **clang-tidy**: errors fail, warnings tolerated
- **Python**: flake8 + yapf on changed `mlir/**/*.py` (GitHub Actions)

## Critical (blocks merge)

- No unreleased hardware codenames, unannounced chip IDs, or NDA features in code/comments/commits/docs
- No C++ exceptions; use `LogicalResult` / `emitOpError` / `signalPassFailure`
- No `dynamic_cast`; use `isa`/`cast`/`dyn_cast`
- No committed temp/generated files (build artifacts, `*.pyc`, editor files, secrets)
- Breaking IR or C API changes must be documented and coordinated with MIGraphX

## Major

- Naming: classes `CamelCase`, functions/vars `camelBack`
- New ops need `hasVerifier = 1` with `verify()` implementation
- New passes need Lit tests with FileCheck and round-trip verification
- Errors propagated via `LogicalResult`, never silently dropped
- `librockcompiler_deps.cmake` updated when dependencies change
- License header on new files (SPDX `Apache-2.0 WITH LLVM-exception`)
- External changes (`external/`) in separate commits with `[EXTERNAL]` prefix

## Minor

- Include order: dialect, MLIR, LLVM ADT, stdlib
- Comments as English prose with proper capitalization
- Prefer early returns; no `else` after `return`
- `auto` only when type is obvious; `auto &` for values, `auto *` for pointers
- Files end with newline; no trailing whitespace

## License header (new files)

```
//===- FileName.cpp - Brief description ----------------------------------===//
//
// Part of the MLIR Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
```

## Branch naming

- Feature: `users/<username>/<description>` or `<jira-id>-<description>`
- Upstream merge: `upstream-merge-<month>-<year>`
- Prefer rebase over merge for clean history


---

# Testing Conventions

## When to use each test type

| Type | Location | Use for |
|------|----------|---------|
| **Lit** (`.mlir`) | `mlir/test/` | Passes, pipelines, driver integration |
| **GoogleTest** | `mlir/unittests/` | C++ helpers, attributes, transform maps |
| **pytest** | `mlir/utils/performance/tests/` | Performance script logic (no GPU) |
| **E2E** | `mlir/test/e2e/`, `mlir/test/fusion/pr-e2e/` | Full GPU pipeline |

## Lit test patterns

```mlir
// Round-trip
// RUN: rocmlir-opt %s | FileCheck %s
// RUN: rocmlir-opt %s | rocmlir-opt | FileCheck %s

// Pass pipeline
// RUN: rocmlir-opt --my-pass %s | FileCheck %s

// Arch substitution
// RUN: sed s/##TOKEN_ARCH##/%arch/g %s | rocmlir-opt --my-pass | FileCheck %s

// Split input + diagnostics
// RUN: rocmlir-opt --my-pass -split-input-file --verify-diagnostics %s | FileCheck %s

// GPU-required
// REQUIRES: rocm-runner
```

## Key substitutions

`%arch`, `%features`, `%pv`, `%random_data`, `%rocmlir_gen_flags`, `%shlibext`, `%linalg_test_lib_dir`, `%conv_validation_wrapper_library_dir`

## FileCheck defaults

`FILECHECK_OPTS="-enable-var-scope --allow-unused-prefixes=false"` -- all CHECK prefixes must be used.

## Test targets

- `check-rocmlir` -- full suite
- `check-rocmlir-build-only` -- compile only
- `RocMLIRUnitTests` -- GoogleTest only
- E2E: enable with `-DROCK_E2E_TEST_ENABLED=ON`


---

# rocMLIR CLI Tools

## rocmlir-gen -- generate MLIR from problem specs

Key flags: `-operation` (conv/gemm/attention/gemm_gemm/conv_gemm), `-arch`, `-t` (dtype), `-m/-k/-n` (GEMM dims), `-g` (groups), `-ph` (host harness), `-pv` (validate), `-pr` (print results), `-perf_config`, `-emit-tuning-key`

Conv: `-fil_layout`, `-in_layout`, `-out_layout`, `-batchsize`, `-in_channels`, `-out_channels`, `-fil_h/w`, padding/strides/dilations

Features: `-mfma`, `-wmma`, `-dot`, `-atomic_add` (each: `infer`/`on`/`off`)

## rocmlir-driver -- run lowering pipelines

- `-kernel-pipeline`: `applicability`, `migraphx`, `highlevel`, `gpu`, `rocdl`, `binary`, `full` (=`gpu,binary`)
- `-host-pipeline`: `migraphx`, `highlevel`, `mhal`, `runner`
- `-c`: shorthand for `-kernel-pipeline=full -host-pipeline=runner`
- `-targets`: GPU targets; `-verify-passes`; `-dump-pipelines`

## rocmlir-opt -- MLIR optimizer

Standard `mlir-opt` interface with all Rock/MIGraphX passes registered.

## rocmlir-tuning-driver -- JIT benchmark

`-tuning-space` (quick/full/greedy/exhaustive), `-num-iterations`, `-warmup-iterations`, `-benchmark-config`, `-show-all-measurements`

## Common pipelines

```bash
# Smoke test
rocmlir-gen --arch gfx942 -p | rocmlir-opt

# Full lowering + run
rocmlir-gen --arch gfx942 -ph -pv | rocmlir-driver -c | mlir-runner --shared-libs=...

# Tuning
rocmlir-gen --arch gfx942 --perf_config= | rocmlir-tuning-driver -tuning-space full

# Kernel to assembly
rocmlir-gen ... | rocmlir-driver -kernel-pipeline=gpu,rocdl --arch=gfx942 | \
  rocmlir-translate -gpu-module-to-rocdlir | opt -O3 | llc -mcpu=gfx942
```


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
- Variants: `Jenkinsfile.downstream`, `Jenkinsfile.release` (keep in sync)
- Docker: `rocm/mlir:rocm7.2-latest`, Ninja, ROCm clang, `RelWithDebInfo`
- PR: premerge clang-format/tidy, selected tuning, optional E2E
- Nightly: full benchmark + regression reports + hipBLASLt comparison
- Weekly: exhaustive MITuna tuning + parameter sweeps + perfDB archival
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
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++
ninja check-rocmlir-build-only
```

Always verify exit code. If build fails, stop and report -- do not proceed to test/lint.

Common options: `-DBUILD_FAT_LIBROCKCOMPILER=On`, `-DROCMLIR_ENABLE_BENCHMARKS=hipblaslt`

## Step 2: Test

```bash
ninja check-rocmlir          # Full Lit + unit tests
ninja RocMLIRUnitTests       # GoogleTest only
```

For E2E (requires GPU): add `-DROCK_E2E_TEST_ENABLED=ON` to cmake.

## Step 3: Lint

```bash
# C++ format check
git-clang-format origin/develop

# C++ tidy (premerge script)
python3 mlir/utils/jenkins/static-checks/premerge-checks.py --base-commit origin/develop

# Python
flake8 --ignore=E501,E251,E124,W605,W504,E131,E126,W503,E123 <files>
yapf --diff <files>
```

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

## Step 1: Generate kernel

```bash
rocmlir-gen --operation gemm --arch gfx942 -t f16 -m 4096 -k 4096 -n 4096 -ph -pv | \
  rocmlir-driver -c > kernel.mlir
```

## Step 2a: Profile with rocprofv3 (quick)

```bash
rocprofv3 --kernel-trace --stats -f csv -o results -- \
  mlir-runner kernel.mlir --shared-libs=... --entry-point-result=void
```

- PMC counters: use `rocmlir_metrics.txt` for LDS bank conflict (`pmc: LDSBankConflict`)
- Output: `results.csv` (timing), `results_kernel_stats.csv` (aggregates)

## Step 2b: Profile with rocprof-compute (comprehensive)

```bash
rocprof-compute profile -n my_kernel -- \
  mlir-runner kernel.mlir --shared-libs=... --entry-point-result=void
```

- Filter: `-k <kernel>`, `-b <block>` (SQ, LDS, TCC, etc.)
- List metrics: `rocprof-compute --list-metrics gfx942`

## Step 3: Analyze

```bash
# rocprof-compute CLI analysis
rocprof-compute analyze -p ./workloads/my_kernel/<arch>/

# Interactive modes
rocprof-compute analyze -p ... --gui   # GUI
rocprof-compute analyze -p ... --tui   # Terminal UI
```

## Step 4: Identify bottlenecks

| Bottleneck | What to check |
|-----------|---------------|
| **Compute bound** | SQ occupancy, VALU/MFMA utilization, wavefront stalls |
| **Memory bound** | L2 (TCC) hit rate, HBM bandwidth, LDS bank conflicts |
| **Latency bound** | Instruction fetch stalls, barrier waits, dependency stalls |

Map findings to rocMLIR tuning: block size, grid size, pipeline depth, direct-to-LDS.

## Integration with perfRunner.py

- `--use-rocprof` flag uses rocprofv3 for benchmarking
- `rocmlir_metrics.txt` defines PMC counters collected
- LDSBankConflict: 0% optimal, 100% bad

---

# Performance Report Scripts

## createPerformanceReports.py

Generate HTML comparing MLIR vs external library.

```bash
python3 createPerformanceReports.py <chip> [lib]
# lib: hipBLASLt (default), CK, MIOpen
```

- Reads: `{chip}_mlir_vs_{lib}_perf.csv`
- Writes: plot CSV, stats CSV, `{chip}_MLIR_vs_{lib}.html`

## createFusionPerformanceReports.py

```bash
python3 createFusionPerformanceReports.py <chip>
```

- Reads: `{chip}_{conv|gemm}_mlir_fusion_perf.csv`
- Writes: `{chip}_{conv|gemm}_fusion.html`

## perfRegressionReport.py

Compare old vs new performance.

```bash
python3 perfRegressionReport.py <chip> [old_csv] [new_csv] [output_html]
```

- Defaults: `./oldData/{chip}_mlir_vs_miopen_perf.csv` vs `./{chip}_mlir_vs_miopen_perf.csv`
- Writes: `{chip}_MLIR_Performance_Changes.html`

## parameterSweeps.py

Correctness sweeps (not performance benchmarks).

```bash
python3 parameterSweeps.py <config>
# config: conv_structure, perf_config, mfma_perf_config, vanilla_perf_config, wmma_perf_config
```

Requires: `ninja rocmlir-gen rocmlir-driver mlir-runner ci-performance-scripts`

## handleNewConfigs.py

Add new configs to tier-1 files.

```bash
python3 handleNewConfigs.py --new new_configs.txt --configs-dir configs/
```

Classifies (conv/gemm/attn/etc.), deduplicates, appends to tier-1 files.

## reportUtils.py (library, not run directly)

Shared constants: `PERF_REPORT_FILE`, `CONV_TEST_PARAMETERS`, `GEMM_TEST_PARAMETERS`, `geo_mean`, `html_report`

---

# perfRunner.py Usage

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

- `-c` -- config file (default: `tier1-conv-configs`)
- `-t` / `--tuning_db` -- tuning DB TSV for "tuned" column
- `-qt` / `--quick_tuning_db` -- quick tuning DB
- `--mlir-build-dir` -- build dir (auto-detected)
- `--external-gemm-library` -- `hipBLASLt` (default) or `CK`
- `--data-type` -- force types: `f32`, `f16`, `i8`, `fp8`, etc.
- `--use-rocprof` -- use rocprofv3 instead of tuning driver

## Examples

```bash
python3 perfRunner.py                                    # conv vs MIOpen
python3 perfRunner.py --batch_all -t tuning_db.tsv       # with tuned column
python3 perfRunner.py --op gemm --batch_all              # GEMM vs hipBLASLt
python3 perfRunner.py --op gemm --external-gemm-library CK
python3 perfRunner.py --op fusion --test_dir ../mlir/test/fusion/resnet50-e2e -t db.tsv

# Single config
python3 perfRunner.py --op gemm -- -t f32 -transA true -transB true -g 1 -m 1024 -k 769 -n 512
```

## External baselines

- Conv: MIOpen (`/opt/rocm/bin/MIOpenDriver`)
- GEMM: hipBLASLt (`hipblaslt-benchmark-driver`) or CK (`ck-gemm-benchmark-driver`)

## Build for benchmarking

```bash
cmake ... -DROCMLIR_ENABLE_BENCHMARKS=hipblaslt
ninja ci-performance-scripts hipblaslt-benchmark-driver
```

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

Read all changed files. Apply checklist from `rules/code-review.md`:

**Critical**: unreleased HW references, exceptions, `dynamic_cast`, committed temp files, breaking IR changes
**Major**: naming, verifiers, tests, error handling, license headers, external commits separated
**Minor**: include order, comments, early returns, trailing whitespace, missing newline

### 4. Check project-specific concerns

- License headers on new files (SPDX `Apache-2.0 WITH LLVM-exception`)
- `librockcompiler_deps.cmake` updated if deps change
- Downstream MIGraphX impact for IR/API changes
- Release branch PRs: also apply release patch checklist

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

| Pattern | Example | Use |
|---------|---------|-----|
| `release/rocm-rel-X.Y` | `release/rocm-rel-7.2` | Standard release |
| `release/rocm-rel-X.Y-perf-fix` | `release/rocm-rel-7.2-perf-fix` | Performance patch |
| `mass-release-backport-X.Y` | `mass-release-backport-6.3` | Bulk cherry-picks |
| `gpuep-releases/gpuep-rel-YYMM` | `gpuep-releases/gpuep-rel-2605` | GPU Enterprise |

## Release branch lifecycle

1. Cut from `develop` at release milestone
2. Only bug fixes and critical patches -- **no new features**
3. Cherry-pick from `develop` (reference PR number)
4. `[EXTERNAL]` LLVM cherry-picks for critical crash fixes
5. Performance fixes require benchmark evidence

## Patch review checklist

- [ ] Bug fix or critical regression? (no new features)
- [ ] Fix exists on `develop` first? (always fix develop, then cherry-pick)
- [ ] Change is minimal and targeted? (no large refactors)
- [ ] `check-rocmlir` passes?
- [ ] Performance benchmarks unaffected? (evidence for perf fixes)
- [ ] `librockcompiler_deps.cmake` consistent?
- [ ] No unreleased hardware references?

## Release CI

`Jenkinsfile.release` builds the fat library:

```bash
cmake -G Ninja .. -DBUILD_FAT_LIBROCKCOMPILER=ON -DCMAKE_BUILD_TYPE=Release
```

Archives:
- `mlir-source-{branch}.tar.gz` -- source tarball
- `mlir-binary-{branch}.tar.gz` -- binaries (build/bin, build/lib, LLVM bins)

## CI triggers on release branches

- GitHub Actions: `release/**` (Python lint + tests)
- Azure Pipelines: `mainline` (release integration)
- Jenkins: `Jenkinsfile.release` for fat library builds

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

---

# tuningRunner.py Usage

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
| `--gpus` | all | Select GPU IDs for parallel tuning |
| `--retune` | off | Ignore existing rows, retune all |
| `--retry` | none | Retry: `failed`, `timed_out`, `crashed` |
| `--timeout` | none | Per-config timeout (seconds) |
| `-s` / `--status` | off | Print pending count, no tuning |

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

`external/llvm-project/` is a **git subtree** (not a submodule).

## Workflow

### 1. Create merge branch

```bash
git checkout develop
git pull origin develop
git checkout -b upstream-merge-<month>-<year>
```

### 2. Squash-pull LLVM

```bash
git remote add llvm https://github.com/llvm/llvm-project.git  # if not already added
git fetch llvm
git subtree pull --prefix=external/llvm-project --squash llvm main
```

Produces: `Squashed 'external/llvm-project/' changes from OLD..NEW`

### 3. Apply internal patches (if needed)

Commit message: `Apply internal patches.`

### 4. Fix rocMLIR breakage

Common fixes:
- MLIR API renames (methods, builder signatures)
- New pass registration requirements
- TableGen syntax changes
- LLVM IR / intrinsic changes in `RockToGPU` / `RockPrepareLLVM`
- CMake target name or link changes

### 5. Update deps

Update `librockcompiler_deps.cmake` if library dependencies changed.

### 6. Keep branch current

Periodically merge `develop` into the merge branch:
```bash
git merge develop
```

### 7. Open PR

Set Jenkins parameter `ignoreExternalLinting=true` to skip clang-format/tidy on `external/`.

## Cherry-picking individual LLVM fixes

For targeted fixes between full merges:
```bash
# Apply fix to external/llvm-project/ with [EXTERNAL] prefix
git commit -m "[EXTERNAL] Cherry pick https://github.com/llvm/llvm-project/pull/NNNNN"
```

## Branch naming

`upstream-merge-jan-26`, `upstream_merge_10_25`, `upstream_merge_dec18`
