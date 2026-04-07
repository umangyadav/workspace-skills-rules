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
- `rocmlir-tuning-driver` -- tune kernels by sweeping perf configs and selecting the best

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


# Skills


---

The following skills are available for on-demand use:


---

- **build-test-workflow**: # Build, Test, and Lint

---

- **kernel-profiling**: # Kernel Profiling

---

- **perf-reports-utils**: # Performance Report Scripts

---

- **perfrunner-usage**: # perfRunner.py Usage

---

- **pr-review**: # PR Review

---

- **release-management**: # Release Management

---

- **self-review**: # Self Review

---

- **tuningrunner-usage**: # tuningRunner.py Usage

---

- **upstream-llvm-merge**: # Upstream LLVM Merge
