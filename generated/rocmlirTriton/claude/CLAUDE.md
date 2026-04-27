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

# Triton Integration

rocmlirTriton depends on upstream [Triton](https://github.com/triton-lang/triton) as a git submodule. Triton brings its own LLVM/MLIR and AMD backend; we replicate parts of Triton's Python pipeline in C++.

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

The four `rocmlir-driver` pipelines that drive this -- `rock-highlevel-pipeline`, `rock-kernel-pipeline`, `rock-triton-pipeline`, `rock-backend-pipeline` -- are registered at the bottom of `mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp`. `rocmlir-driver`'s `-kernel-pipeline=` keywords (`migraphx`, `highlevel`, `gpu`, `triton`, `binary`, `full`) map onto these (see `rocmlir-tools.md`). Most Triton-side stages (`makeTTIR`/`makeTTGIR`/`makeLLIR`, `TritonToHsacoPass`) are C++ replicas of upstream Triton's Python `compiler.py`.

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

These C++ functions/files mirror Triton Python logic. Whenever the submodule advances, audit them against upstream (full procedure: `triton-bump` skill):

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

## Hardware feature detection

Always use `rock::*` helpers (e.g. `rock::supportsTDM(arch)`) instead of `triton::AMD::TargetInfo(...)` directly. If a needed `rock` helper is missing, add one in `AmdArchDb.cpp` rather than calling Triton's `TargetInfo` from Rock code. This is the canonical rule referenced from `code-review.md`, `dev-workflow.md`, and the bump skill.

## librockcompiler_deps.cmake

The fat library `librockCompiler.a` (consumed by MIGraphX) has its dependency list pinned in `mlir/tools/rocmlir-lib/librockcompiler_deps.cmake`. Regenerate it whenever Triton libraries are added/removed (almost always on Triton bumps); the regeneration command lives in the `triton-bump` skill.

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

The canonical step-by-step bump procedure is `docs/bump_triton_version.md` in the rocmlirTriton repo (10 steps: submodule update, LLVM rebuild, patch re-evaluation, upstream diffs, C++ replica sync, fat-library deps regen, tests). The `triton-bump` skill (`skills/triton-bump/SKILL.md`) wraps the doc with project conventions (bump branch naming, PR-description checklist, between-bumps `[TRITON-PATCH]` workflow). Always start from the doc -- don't open-code a bump.


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

For rocMLIR-side passes:

```cpp
#define DEBUG_TYPE "rock-my-pass"
LLVM_DEBUG(llvm::dbgs() << "message\n");
```

For passes that live in `external/triton/` (or `triton-patches/`), follow upstream Triton's `LDBG` idiom -- it auto-prefixes each line with `[DEBUG_TYPE]:` so logs stay grep-friendly under `--debug-only=...`. The base macros live in `include/triton/Conversion/TritonGPUToLLVM/Utility.h`; if your file doesn't include it, redefine them locally:

```cpp
#define DEBUG_TYPE "tritonamd-my-pass"
#define DBGS() (llvm::dbgs() << "[" DEBUG_TYPE "]: ")
#define LDBG(X) LLVM_DEBUG(DBGS() << X << "\n")
// usage
LDBG("rewrote " << op->getName() << " to " << newOp->getName());
```

## LLVM algorithms (prefer over STL equivalents)

- `llvm::find`, `llvm::all_of`, `llvm::any_of`, `llvm::none_of`
- `llvm::to_vector`, `llvm::zip_equal`, `llvm::enumerate`
- `llvm::sort` (over `std::sort` for determinism)

## Namespace conventions

- `using namespace mlir;` and `using namespace mlir::rock;` at `.cpp` file scope (rocMLIR side).
- Anonymous namespace only for local class/struct declarations: `namespace { struct MyPass ... }`.
- Pass defs (rocMLIR side): `namespace mlir { namespace rock { #define GEN_PASS_DEF_... } }`.
- Pass defs (Triton-patch side): use the C++17 nested form `namespace mlir::triton { #define GEN_PASS_DEF_... #include "...Passes.h.inc" }`. This matches upstream Triton; do **not** introduce the older `namespace mlir { namespace triton { ... } }` style in `external/triton/` patches.
- Triton convention is to follow the named-namespace block with an anonymous `namespace { using namespace mlir; using namespace mlir::triton; ... }` for the pass implementation. Mirror that layout when patching Triton.

## Triton-aware C++

The hardware-feature-detection rule (`rock::*` helpers vs. `triton::AMD::TargetInfo`) lives in `triton-integration.md` -- follow it whenever you call into Triton from rocMLIR-side code.

When you genuinely need TritonGPU IR helpers (layouts, swizzling, linear-layout math), reach for the upstream utility headers rather than reimplementing -- in particular `triton/Tools/LayoutUtils.h`, `triton/Tools/LinearLayout.h`, `triton/Dialect/TritonGPU/Transforms/Utility.h`, and `triton/Dialect/Triton/IR/Utility.h`.

## Naming

The `.clang-tidy` enforces LLVM-style names with `readability-identifier-naming` (CamelCase for classes/types/members/parameters/variables, camelBack for functions). Keep new code consistent with surrounding files.

Upstream Triton has **no `.clang-tidy`** of its own -- it relies on `clang-format` (LLVM style, v19.1.6) plus reviewer judgement. So when patching `external/triton/`, our `.clang-tidy` rules don't run there; mirror the surrounding Triton file's style (still LLVM-flavoured: `CamelCase` types, `camelBack` functions/members) and don't introduce names that would fail our `readability-identifier-naming` check on our side either.

## Indentation (`.editorconfig`)

Upstream Triton ships an `.editorconfig` that overrides the global 4-space default per file type. Honour it when patching `external/triton/`:

| File type | Indent |
|-----------|--------|
| `.cpp`, `.h`, `.cu`, `.cuh`, `.mlir` | **2 spaces** |
| `.td` (TableGen) | **4 spaces** |
| `.py` | 4 spaces |
| `CMakeLists.txt`, `*.cmake`, `*.yaml`, `*.yml` | 2 spaces |
| `Makefile` | hard tab |

`clang-format` will fix C++ indents but won't catch a wrong-indent `.td` or `CMakeLists.txt` patch. Make sure your editor honours `.editorconfig` (or run a manual pass) before sending the diff.


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
| `add_rocmlir_dialect_library` | Dialect IR libraries (rocMLIR side) |
| `add_rocmlir_conversion_library` | Conversion pass libraries (rocMLIR side) |
| `add_rocmlir_test_library` | Test helper libraries |
| `add_rocmlir_public_c_api_library` | C API libraries |
| `add_rocmlir_tool` | CLI tools (auto-handles `BUILD_FAT_LIBROCKCOMPILER` exclude logic) |
| `add_rocmlir_triton_library` | Rock-to-Triton glue libraries |

All `add_rocmlir_*` helpers wrap upstream `add_mlir_library` and pass `DEPENDS mlir-headers`. They also push the new target onto a per-category `GLOBAL` property (`ROCMLIR_DIALECT_LIBS`, `ROCMLIR_CONVERSION_LIBS`, `ROCMLIR_TEST_LIBS`, `ROCMLIR_PUBLIC_C_API_LIBS`, `ROCMLIR_TRITON_LIBS`) used by the fat-library aggregator.

## Upstream Triton CMake conventions (from `external/triton/`)

When you patch `external/triton/` (or write a `triton-patches/*.patch`), match Triton's own style. Do **not** introduce `add_rocmlir_*` helpers there.

### Triton's helper functions (top-level `external/triton/CMakeLists.txt`)

| Function | Purpose | Notes |
|----------|---------|-------|
| `add_triton_library(name SRCS... [DEPENDS] [LINK_LIBS PUBLIC])` | In-tree Triton library (dialect, transform, analysis) | Wraps an OBJECT library, registers the target in `GLOBAL TRITON_LIBS`, injects `${TRITON_DISABLE_EH_RTTI_FLAGS}` (`-fno-exceptions -fno-rtti`) on non-MSVC. |
| `add_triton_plugin(name ...)` | Backend plugins (e.g. `TritonAMD` in `third_party/amd`) | Registers in `GLOBAL TRITON_PLUGINS`. |
| `add_triton_object(name ...)` | The underlying object-library primitive used by the two above. Rarely called directly. |
| `add_triton_ut(NAME SRCS LIBS DEFS)` | C++ GoogleTest unit tests (`cmake/AddTritonUnitTest.cmake`) | Calls `gtest_discover_tests` (`DISCOVERY_TIMEOUT 60`), compiles with `-fno-rtti`, adds the test to the `TritonUnitTests` aggregate. |

### Naming / option conventions

- Every Triton build flag is **`TRITON_*`** (`TRITON_BUILD_PYTHON_MODULE`, `TRITON_BUILD_PROTON`, `TRITON_BUILD_UT`, `TRITON_BUILD_WITH_CCACHE`, `TRITON_PARALLEL_LINK_JOBS`, `TRITON_CODEGEN_BACKENDS`, `TRITON_PLUGIN_DIRS`). Mirror this if you add new options to `external/triton/`. Our own flags should stay `ROCMLIR_*` / `BUILD_*` and not clash.
- `cmake_minimum_required(VERSION 3.20)` and `cmake_policy(SET CMP0116 OLD)` -- inherited via `add_subdirectory(external/triton)`.
- C++17, `CMAKE_INCLUDE_CURRENT_DIR ON`, default `CMAKE_BUILD_TYPE Release`. Triton also defines two custom build types -- `TritonRelBuildWithAsserts` (`-O2 -g`) and `TritonBuildWithO1` (`-O1`) -- usable from rocmlirTriton's `cmake.sh` if needed.
- Triton-side compilation flags include `-Werror -Wno-covered-switch-default -fvisibility=hidden -fPIC`. Don't disable these wholesale; if a single source file needs to relax them, scope it with `target_compile_options(<target> PRIVATE ...)`.

### Dialect / tablegen idiom (per Triton sub-`CMakeLists.txt`)

```cmake
set(LLVM_TARGET_DEFINITIONS TritonOps.td)
mlir_tablegen(Ops.h.inc -gen-op-decls)
mlir_tablegen(Ops.cpp.inc -gen-op-defs)
add_mlir_doc(TritonOps TritonOps dialects/ -gen-op-doc)
add_public_tablegen_target(TritonTableGen)

add_triton_library(TritonIR
  Dialect.cpp Ops.cpp Types.cpp Utility.cpp
  DEPENDS TritonTableGen TritonCanonicalizeIncGen
  LINK_LIBS PUBLIC MLIRIR MLIRArithDialect MLIRMathDialect MLIRSCFDialect)
```

Match this layout in any `external/triton/` change: `mlir_tablegen` calls first, `add_public_tablegen_target` last in the `include/` `CMakeLists.txt`, and the library `DEPENDS` on that tablegen target. Add `add_mlir_doc(...)` calls for new ops/dialects.

## rocMLIR-side libraries that link against Triton

When a rocMLIR library (`add_rocmlir_*`) needs Triton symbols (e.g. `mlir/lib/Dialect/Rock/Pipelines/CMakeLists.txt`, `mlir/lib/Dialect/Rock/Transforms/CMakeLists.txt`):

1. Add Triton library names to `LINK_LIBS PUBLIC` (e.g. `TritonIR`, `TritonGPUIR`, `TritonGPUTransforms`, `TritonAnalysis`).
2. Append the four Triton include roots to `target_include_directories(<target> PRIVATE ...)`:
   ```cmake
   ${TRITON_PROJECT_DIR}/include
   ${TRITON_BINARY_DIR}/include
   ${TRITON_PROJECT_DIR}/third_party
   ${TRITON_BINARY_DIR}/third_party
   ```
3. Force the right tablegen ordering via `add_dependencies` -- Triton's tablegen targets (`TritonGPUTableGen`, `TritonGPUAttrDefsIncGen`, `TritonGPUCGAAttrIncGen`, `TritonGPUTypeInterfacesIncGen`, `TritonGPUOpInterfacesIncGen`, `TritonNvidiaGPU*`, `NVWS*`) must run before our library compiles or the generated `.inc` files won't exist yet. The existing `if(TARGET ...)` blocks in `Transforms/CMakeLists.txt` are the canonical pattern -- copy them, don't reinvent.

## Notable CMake options

| Option | Default | Purpose |
|--------|---------|---------|
| `BUILD_FAT_LIBROCKCOMPILER` | OFF (ON via `cmake.sh`) | Static `librockCompiler.a` for MIGraphX |
| `MLIR_INCLUDE_TESTS` | ON | Enables `check-rocmlir-build-only` |
| `ROCK_E2E_TEST_ENABLED` | OFF | Full E2E test suite |
| `ROCMLIR_DRIVER_E2E_TEST_ENABLED` | OFF | Build E2E driver tests |
| `ROCMLIR_DRIVER_PR_E2E_TEST_ENABLED` | OFF | PR-scoped E2E tests |
| `ROCMLIR_DRIVER_RANDOM_DATA_SEED` | `none` | Random-data E2E mode |
| `ROCMLIR_GEN_FLAGS` | "" | Extra flags forwarded to `rocmlir-gen` in lit substitutions (use only flags this fork's `rocmlir-gen` accepts; `-mfma=off -wmma=off` from upstream rocMLIR no longer applies here) |
| `ROCMLIR_ENABLE_BENCHMARKS` | "" | `hipblaslt`, `ck`, or `all` |
| `MLIR_ENABLE_ROCM_RUNNER` | ON | Required for `mlir-runner` GPU execution |
| `ROCMLIR_PARALLEL_LINK_JOBS` / `_COMPILE_JOBS` | "" | Limit Ninja link/compile concurrency |

## Triton-specific CMake settings (set in `cmake/triton.cmake` for our build)

- `TRITON_BUILD_PYTHON_MODULE OFF` (we use the C++ API)
- `TRITON_BUILD_PROTON OFF`
- `TRITON_BUILD_UT OFF`
- `TRITON_CODEGEN_BACKENDS "amd" "nvidia"`

Do not change these defaults without coordinating with the Triton bump owner. If you need to enable `TRITON_BUILD_UT` locally for upstream-style C++ unit tests, do it in `cmake.sh` rather than flipping the cache value in `cmake/triton.cmake`.


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

# Testing Conventions

This rule is the canonical home for *what* tests must exist and *how* they're written. For *when* tests are required at review time, see `code-review.md`. The high-level workflow for adding a new op/pass is in `dev-workflow.md`.

## When to use each test type

| Type | Location | Use for |
|------|----------|---------|
| **Lit** (`.mlir`) | `mlir/test/` | Passes, pipelines, driver integration |
| **GoogleTest** | `mlir/unittests/` | C++ helpers, attributes, transform maps |
| **E2E (lit)** | `mlir/test/e2e/`, `mlir/test/fusion/{pr-e2e,nightly-misc-e2e,resnet50-e2e}/` | Full GPU pipeline |
| **E2E (smoke)** | top-level `tests.sh`, `test_prefill_changes.sh` | Hand-curated GPU smoke covering gemm/conv/attention/fusion |

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

`tests.sh` is the canonical end-to-end smoke entry point. It auto-detects `$ARCH` and `$NUM_CU` from `rocminfo`, builds `check-rocmlir-build-only ci-performance-scripts`, runs gemm/conv/attention/fusion pipelines through `mlir-runner` (from `external/triton/llvm-project/build/`), and filters `LIT_FILTER` over targeted lit subdirectories (`fusion/fusability`, `fusion/pr-e2e/`, `Dialect/Rock`, `rocmlir-gen`, `Conversion`, `rocmlir-driver`, `capi`, `rocmlir-tuning-driver`).

Whenever a new dialect/conversion area is added, update `tests.sh` so the corresponding `LIT_FILTER` line covers it.

## Substitutions and FileCheck options

- `lit.cfg.py` / `lit.site.cfg.py.in` define `%arch`, `%shlibext`, `%linalg_test_lib_dir`, etc.; E2E and fusion lit configs add suite-specific extras.
- `FILECHECK_OPTS="-enable-var-scope --allow-unused-prefixes=false"` -- all CHECK prefixes must be used.

## Test targets

- `check-rocmlir` -- full suite
- `check-rocmlir-build-only` -- compile only (used in CI build stage)
- `MLIRRockUnitTests` -- GoogleTest (run via `./mlir/unittests/Dialect/Rock/MLIRRockUnitTests`)
- E2E (PR subset): `-DROCMLIR_DRIVER_PR_E2E_TEST_ENABLED=ON`
- E2E (full): `-DROCK_E2E_TEST_ENABLED=ON` and `-DROCMLIR_DRIVER_E2E_TEST_ENABLED=ON`

## Architecture and dtype coverage

- New ops/passes must work on every supported GPU arch present in CI (`gfx90a`, `gfx942`, `gfx950`, `gfx1100`, ...). Guard arch-specific ops with target checks in both code and tests; `tests.sh` already gates several `gfx950`-only paths.
- Enumerate all dtypes the op should support (`f16`, `bf16`, `f32`, `f8E4M3FN`, `f8E5M2`, `f4E2M1FN`, `i8`, ...). Add E2E tests covering each supported dtype; reject unsupported ones with `emitOpError`.
- Scaled GEMM features must respect the `f8E8M0FNU` scale convention -- see `docs/scaled_gemm.md`.

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

Hidden / aliased flags worth knowing (`--help` doesn't list them but they're real): `-pv` (`cl::Hidden`, sets `verifier=mlir` + host harness), `-ph` (alias for `--host-harness`), `-pr` (alias for `--print-results`), `-pi` (alias for `--print-inputs`), `-pvr` (alias for `--print-validation-results`), `-out_datatype` / `-to` / `-tc` / `-c_dtype` (aliases for `--out_dtype`).

Note: this fork of `rocmlir-gen` does **not** accept `-mfma`/`-wmma`/`-dot`/`-atomic_add` as `infer/on/off` flags (they exist in upstream rocMLIR but were removed here). Hardware-feature gating is now driven by `-arch=...` plus optional `--force-f8-types=<arch|nanoo|ocp>`. The `ROCMLIR_GEN_FLAGS` cmake variable still exists as a lit substitution, but only takes flags `rocmlir-gen` actually accepts.

## rocmlir-driver -- run lowering pipelines

- `-kernel-pipeline`: comma list of `migraphx`, `highlevel`, `gpu`, `triton`, `binary`, or `full` (= `gpu,triton,binary`)
  - `gpu` runs `rock::buildKernelPipeline` (Rock -> RockToTTIR -> tt.func)
  - `triton` runs `rock::buildTritonPipeline` (TTIR -> TTGIR -> LLVM dialect, replicating Triton's `make_ttir`/`make_ttgir`/`make_llir`)
  - `binary` runs `rock::buildBackendPipeline` (`TritonToHsacoPass` + host glue via `RockRestoreHostCode` + `buildHostLoweringPipeline`)
- `-host-pipeline`: comma list of `migraphx`, `highlevel`, `backend`
- `-c`: hidden legacy shorthand for `-kernel-pipeline=full` (does **not** set the host pipeline; pair with `-host-pipeline=...` if you also need host lowering)
- `-arch`, `-dump-pipelines`, `-disable-verify-passes`, `-dump-cpu-schedules=<dir>`

The full compilation arc and how each pipeline maps onto the C++ replicas are documented in `triton-integration.md`.

## rocmlir-opt -- MLIR optimizer

Standard `mlir-opt` interface with all Rock + MIGraphX + Triton-related passes registered via `InitRocMLIRPasses.h`. Useful pipeline names registered through `rock::registerPipelines()`:

- `--rock-highlevel-pipeline`
- `--rock-kernel-pipeline` (ends in `tt.func`)
- `--rock-triton-pipeline` (TTIR -> TTGIR -> LLIR)
- `--rock-backend-pipeline` (LLVM IR -> HSACO + host lowering)

Useful individual passes for the Rock<->Triton bridge: `--rock-to-ttir`, `--rock-func-to-triton-func`, `--rock-serialize-host-funcs`, `--rock-restore-host-code`, `--triton-to-hsaco`.

## rocmlir-translate -- translation entry points

The fork-specific entry point is `--triton-to-hsaco` (the C++ replication of Triton's `make_hsaco`). The remaining options are the standard upstream MLIR translations (`--mlir-to-llvmir`, `--import-llvm`, `--mlir-to-cpp`, `--serialize-spirv`/`--deserialize-spirv`, `--export-smtlib`, `--irdl-to-cpp`, `--import-wasm`). Run `rocmlir-translate --help` for the full list.

## rocmlir-tuning-driver -- JIT benchmark

`--tuning-space` (`quick`/`full`/`exhaustive`), `--num-iterations`, `--warmup-iterations`, `--sleep-us`, `--use-median`, `--show-all-measurements`. For Python orchestration on top of this, see the `tuningrunner-usage` skill.

## rocmlir-lsp-server

LSP server that registers Rock/MIGraphX dialects for editor integration with `.mlir` files.

## Python performance/tuning scripts

All under `mlir/utils/performance/`. The two main entry points (`tuningRunner.py`, `perfRunner.py`) have dedicated skills: `tuningrunner-usage`, `perfrunner-usage`. Other helpers (`parameterSweeps.py`, `attentionSweeps.py`, the various report generators) -- run `python3 <script>.py --help`. Configs under `mlir/utils/performance/configs/`.

## Widgets (`mlir/utils/widgets/`)

- `rocm-run` / `xmir-run` -- shell wrappers around `mlir-runner` with the right `--shared-libs`. Use these instead of typing the long `mlir-runner --shared-libs=...` invocation by hand.

## Common pipelines

```bash
# Smoke (default op is conv -- supply problem dims; here a small GEMM)
rocmlir-gen --arch gfx942 --operation gemm -t f16 -g 1 -m 64 -k 64 -n 64 -p | rocmlir-opt

# Full lowering + validate (single op), Triton mlir-runner.
# rocmlir-gen defaults to conv and needs explicit problem dims; substitute -operation conv -fil_layout/... for conv.
rocmlir-gen --arch gfx942 --operation gemm -t f16 -g 1 -m 64 -k 64 -n 64 -ph -pv | rocmlir-driver -c | \
  external/triton/llvm-project/build/bin/mlir-runner \
    --shared-libs=external/triton/llvm-project/build/lib/libmlir_rocm_runtime.so,build/lib/libconv-validation-wrappers.so,external/triton/llvm-project/build/lib/libmlir_runner_utils.so,external/triton/llvm-project/build/lib/libmlir_c_runner_utils.so \
    --entry-point-result=void

# Tuning a single config
rocmlir-gen --arch gfx942 --operation gemm -t f16 -g 1 -m 64 -k 64 -n 64 --perf_config= | rocmlir-tuning-driver --tuning-space=quick

# Fusion E2E from .mlir input
sed -e "s/gfx1100/$ARCH/g" -e "s/rock.num_cu = 96/rock.num_cu = $NUM_CU/g" fusion_with_host.mlir | \
  rocmlir-driver -c | mlir-runner --shared-libs=... --entry-point-result=void
```

The exact `--shared-libs=` string above is what `tests.sh` uses; the easier alternative for ad-hoc runs is `mlir/utils/widgets/rocm-run`.


---

# Development Workflow

## Adding a new Rock dialect operation

1. Define op in `mlir/include/mlir/Dialect/Rock/IR/RockOps.td` (inherit `Rock_Op`, add traits, `hasVerifier = 1`)
2. Implement verifier: `LogicalResult NewOp::verify()` in `mlir/lib/Dialect/Rock/IR/RockDialect.cpp`
3. Add lowering in `mlir/lib/Dialect/Rock/Transforms/` using `OpRewritePattern` or `OpConversionPattern`
4. Register pass in `mlir/include/mlir/Dialect/Rock/Passes.td`
5. Wire into pipeline in `mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp`
6. Add Lit tests in `mlir/test/Dialect/Rock/` (round-trip + pass tests; patterns in `testing-conventions.md`)
7. Update `CMakeLists.txt` if new files added (helpers in `cmake-conventions.md`)

## Adding a conversion pass (e.g. FooToBar)

1. Declare in `mlir/include/mlir/Conversion/RocMLIRPasses.td`
2. Create `mlir/lib/Conversion/FooToBar/` with pattern + pass `.cpp` files
3. Add `add_rocmlir_conversion_library(...)` in `CMakeLists.txt`
4. Add Lit tests in `mlir/test/Conversion/FooToBar/`

## Touching the Rock <-> Triton bridge

The two bridge passes (`-rock-to-ttir`, `-rock-func-to-triton-func`) and their files are documented in `triton-integration.md`. When extending them:

- Add a new `OpRewritePattern` in `RockToTTIR.cpp` when you introduce a Rock op that needs to reach the GPU through Triton.
- Touch `FuncToTritonFunc.cpp` when the kernel calling convention or pointer-attribute layout changes.

## Touching the Triton-driven pipeline

If your change crosses into the part of the pipeline that runs on `tt`/`ttg` IR:

1. Find the Python equivalent in `external/triton/third_party/amd/backend/compiler.py` and the binding in `external/triton/third_party/amd/python/triton_amd.cc`.
2. Mirror the change in the corresponding C++ replication point (table in `triton-integration.md`).
3. Use `rock::*` helpers (`rock::supportsTDM`, etc.) to gate hardware-conditional passes; add new helpers in `AmdArchDb.cpp` if needed.
4. If a fix should also live in upstream Triton, prefer drafting an upstream PR; only add a `triton-patches/*.patch` when waiting for upstream is not viable.

## Adding a MIGraphX operation

1. Define op in `mlir/include/mlir/Dialect/MIGraphX/IR/MIGraphX.td`
2. Add lowering in `mlir/lib/Conversion/MIGraphXToTosa/`
3. Add tests in `mlir/test/Conversion/`

## Testing a new operation or feature

Architecture coverage, dtype coverage, edge cases, and fusion-test requirements are documented in `testing-conventions.md`. The two key rules:

- New ops/passes must work on every supported GPU arch present in CI; arch-specific paths must be guarded in both code and tests.
- Enumerate all supported dtypes (`f16`, `bf16`, `f32`, `f8E4M3FN`, `f8E5M2`, `f4E2M1FN`, `i8`, `i4`, ...); reject unsupported ones with `emitOpError`.

## Debugging a pass failure

```bash
# Isolate
rocmlir-opt --my-pass input.mlir

# Enable debug output (requires -DLLVM_ENABLE_ASSERTIONS=ON)
rocmlir-opt --my-pass input.mlir --debug-only=my-pass

# Dump full pipeline (rocMLIR side); --arch is required even for a dump
rocmlir-driver --arch=gfx942 -dump-pipelines -kernel-pipeline=full input.mlir 2>&1

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
```

For full lowering + GPU validation (incl. the canonical `mlir-runner --shared-libs=...` invocation), use the `mlir/utils/widgets/rocm-run` wrapper or copy the line out of `tests.sh` -- see `rocmlir-tools.md` for the explicit form.


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

The PR pipeline is a `CODEPATH` matrix (`vanilla, mfma, navi21, navi3x, navi4x, gfx950`) running each row in a ROCm Docker container. The exact stage list lives in `mlir/utils/jenkins/Jenkinsfile` -- read it there rather than mirroring it here. Two things worth knowing without opening the file:

- Static checks (clang-format / clang-tidy via `mlir/utils/jenkins/static-checks/premerge-checks.py`) are gated on the `mfma` codepath only.
- Nightly / weekly stages exist but are commented out, and re-enabling them is a private-CI-only change -- do **not** propagate it to `Jenkinsfile.downstream`.

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

- **triton-bump**: # Triton Bump

---

- **tuningrunner-usage**: # tuningRunner.py Usage
