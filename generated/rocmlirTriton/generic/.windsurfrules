# rocmlirTriton AI Agent Rules and Skills


---

## Rules


---

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

To configure against a pre-built MLIR (e.g. a shared dev environment), pass `-DMLIR_DIR=/path/to/lib/cmake/mlir` and skip `scripts/build-llvm.sh`. For one-off configure changes, edit `cmake.sh` rather than reproducing the long `cmake -G Ninja ...` line by hand -- the cmake options it sets (compiler/linker, E2E flags, build type) are the canonical set. The full option list is documented in `cmake-conventions.md`.

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

`tests.sh` auto-detects `$ARCH` and `$NUM_CU` from `rocminfo` and gates `gfx950`-only scaled GEMM cases. See `testing-conventions.md` for the lit suite layout and `tests.sh` smoke contents.

## Step 3: Lint

- **C++ format**: `git clang-format --diff origin/develop`
- **C++ tidy**: rules in `.clang-tidy`; the Jenkins premerge invokes `mlir/utils/jenkins/static-checks/premerge-checks.py` (clang-format + clang-tidy, **only on the `mfma` matrix row** -- see `ci-pipelines.md`)
- **Python lint/format**: see `python-standards.md` for the canonical commands and ignore list

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

The runtime libs come from Triton's LLVM build under `external/triton/llvm-project/build/`. Set `$SHARED_LIBS` once and reuse below; the canonical four-library string is the same one `tests.sh` uses (also documented in `rules/rocmlir-tools.md`):

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

Create a `run.sh` with full absolute paths. `mlir/utils/widgets/rocm-run` is the canonical wrapper for `mlir-runner` -- prefer it over typing the long `--shared-libs=...` line.

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

- `-c` / `--configs_file` -- config file. The script's hard-coded default for conv (`mlir/utils/jenkins/performance/configs/tier1-conv-configs`) is **stale**; the actual configs live under `mlir/utils/performance/configs/`. Pass `-c` explicitly.
- `-o` -- output file name (default: `{chip}_perf.{date}`)
- `-t` / `--tuning_db` -- tuning DB TSV for "tuned" column
- `-qt` / `--quick_tuning_db` -- quick tuning DB
- `--test_dir` -- fusion-mode test directory. Default `../mlir/test/fusion/resnet50-e2e` only resolves when run from `build/`; from any other CWD pass an absolute or repo-rooted path (`mlir/test/fusion/resnet50-e2e`).
- `--mlir-build-dir` -- build dir (auto-detected)
- `--external-gemm-library` -- `hipBLASLt` (default) or `CK`
- `--data-type` -- force types: `f32`, `f16`, `i8`, `i8_i32`, `i8_i8`, `fp8`, `fp8_fp8`, `fp8_f32`
- `--scale-type` -- force scale types for scaled GEMM: `f32`, `f8E8M0FNU`
- `--rocmlir_gen_flags` -- pass extra flags to `rocmlir-gen` to toggle features
- `--use-rocprof` -- use rocprofv3 instead of tuning driver

## Typical workflow

Tune first with `tuningRunner.py` (see `skills/tuningrunner-usage/SKILL.md`), then benchmark with the tuning database:

```bash
# 1. Tune configs (note: --configs_file uses an underscore, not a dash)
python3 tuningRunner.py --operation gemm --configs_file <configs> --output mlir_tuning.tsv

# 2. Benchmark with tuning DB
python3 perfRunner.py --op gemm --batch_all -c <configs> -t mlir_tuning.tsv
```

## Examples

Run from the `build/` directory so default paths (`--test_dir`, `find_mlir_build_dir()`) resolve:

```bash
python3 ../mlir/utils/performance/perfRunner.py --batch_all -t mlir_tuning.tsv               # conv vs MIOpen
python3 ../mlir/utils/performance/perfRunner.py --op gemm --batch_all -t mlir_tuning.tsv     # GEMM vs hipBLASLt
python3 ../mlir/utils/performance/perfRunner.py --op gemm --external-gemm-library CK -t mlir_tuning.tsv
python3 ../mlir/utils/performance/perfRunner.py --op fusion \
  --test_dir ../mlir/test/fusion/resnet50-e2e -t tuning_fusion.tsv

# Single inline GEMM config: must include -t, -out_datatype, -transA, -transB, -g, -m, -k, -n
# (otherwise GemmConfig.from_command_line() raises 'Incomplete GEMM configuration').
python3 ../mlir/utils/performance/perfRunner.py --op gemm -- \
  -t f32 -out_datatype f32 -transA true -transB true -g 1 -m 1024 -k 769 -n 512
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
# For CK baseline (target name uses '-gemm-', source dir is `ck-benchmark-driver/`):
# cmake ... -DROCMLIR_ENABLE_BENCHMARKS=ck
# ninja ci-performance-scripts ck-gemm-benchmark-driver
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

Flag any failing checks. Per-check details, file paths, and what each gate looks at live in `ci-pipelines.md`. Quick summary: GitHub Actions (Python lint only), Azure (`rocMLIR.yml`), Jenkins PR matrix (clang-format/tidy on `mfma` row only).

### 3. Review changed files

Read all changed files. Apply the existing checklists -- don't re-derive them:

- `code-review.md` -- coding standards, severity tiers (Critical / Major / Minor), license headers, decision tiers for `external/triton/` patches
- `llvm-cpp-standards.md` -- C++ patterns (debug macros, namespaces, naming, `.editorconfig`)
- `cmake-conventions.md` -- CMake helpers, `external/triton/` style, dialect/tablegen idiom
- `testing-conventions.md` -- lit patterns, `tests.sh` requirements, fusion-test rules, arch/dtype coverage
- `dev-workflow.md` -- adding ops/passes, bridge-pass touch points
- `triton-integration.md` -- bridge passes, replication points, hardware-feature-detection rule, `librockcompiler_deps.cmake` policy
- `project-overview.md` -- confidentiality / unreleased-HW policy

In the report, cite which severity (Critical/Major/Minor from `code-review.md`) applies. Add a **Major (logic)** flag for: redundant/dead code, unnecessarily complex algorithms, opportunities to replace custom code with an existing LLVM/MLIR/Triton utility, opportunities for simplification (e.g. replace loops with LLVM algorithms, merge redundant conditions, reduce nesting).

### 4. Triton-specific concerns

- Any change to `external/triton` SHA must come with the bump checklist (see `skills/triton-bump/SKILL.md`):
  - Updated `Pipelines.cpp` / `TritonToHsaco.cpp` / `tritonUtils.cpp` / `AmdArchDb.cpp` if upstream changed those files
  - `triton-patches/*.patch` re-evaluated; obsolete patches removed
  - `librockcompiler_deps.cmake` regenerated
- Any new pass call that depends on hardware features must use a `rock::*` helper (see `triton-integration.md`)
- New `triton-patches/*.patch` must include a justification in the PR description (link to upstream issue/PR if applicable)

### 5. Other project-specific concerns

- License headers on new files (template in `code-review.md`)
- `librockcompiler_deps.cmake` updated if dependencies change
- Downstream MIGraphX impact for IR/API changes
- New top-level `fusion_*_with_host.mlir` covered by `tests.sh`
- Release branch PRs: also apply release patch checklist (see `skills/release-management/SKILL.md`)

### 6. rocMLIR back-port check

`rocmlirTriton` was forked from `rocMLIR` and most of `mlir/` is still shared between the two trees. For every change that isn't Triton-submodule-only, ask: **"does this fix/feature also need to land in `ROCm/rocMLIR`?"**

Likely needs a back-port (shared with rocMLIR):
- `mlir/lib/Dialect/Rock/` (except `RockToTTIR` / `RockFuncToTritonFunc` / `RockSerializeHostFuncs` / `RockRestoreHostCode`), `mlir/lib/Dialect/MIGraphX/`, `mlir/lib/Conversion/MIGraphXTo*/`, `mlir/lib/Analysis/`
- `mlir/tools/{rocmlir-gen,rocmlir-driver,rocmlir-opt,rocmlir-tuning-driver,rocmlir-lsp-server}/` (excluding any Triton-pipeline registrations)
- `mlir/utils/performance/`, `mlir/utils/jenkins/static-checks/`
- Generic `cmake/` helpers and root CMake options that aren't Triton-specific

rocmlirTriton-only (no back-port needed):
- `external/triton/`, `triton-patches/`, `cmake/triton.cmake`, `scripts/build-llvm.sh`, `cmake.sh`
- `RockToTTIRPass`, `RockFuncToTritonFuncPass`, `TritonToHsacoPass`, the Triton portion of `rock::buildTritonPipeline` / `buildBackendPipeline` in `Pipelines.cpp`, `tritonUtils.cpp`
- `librockcompiler_deps.cmake`, `docs/bump_triton_version.md`, `skills/triton-bump/`, `Jenkinsfile.downstream` (deprecated)

If the change touches shared territory, the PR description should either (a) link to a parallel `ROCm/rocMLIR` PR, (b) include a one-line note explaining why the divergence is intentional, or (c) confirm the file no longer exists / has been refactored on the rocMLIR side. Flag any missing back-port in the report so it's not silently lost.

### 7. Report

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

### rocMLIR Back-port
<List shared paths that need a parallel rocMLIR PR, or "Not applicable">

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

## Canonical reference

**`docs/bump_triton_version.md`** in the rocmlirTriton repo is the source of truth. It is a 10-step guide with mapping tables, "Features intentionally NOT implemented" list, pass-interface-change recipes, troubleshooting, and a per-step progress checklist. **Read it end-to-end and follow it step by step**; this skill only adds the project conventions the doc doesn't cover (branch naming, PR-description checklist, between-bumps patch workflow).

The replication-point table (Python source → C++ destination) is also summarised in `rules/triton-integration.md`; the canonical fully-detailed table is in section 5 of the doc.

## Project conventions on top of the doc

### 1. Bump branch

Create a dedicated bump branch off `develop` before doing any of the doc's steps:

```bash
git checkout develop && git pull origin develop
git checkout -b triton-bump-<month>-<year>     # or triton-bump-<short-sha>
```

Every commit on this branch should use the `[TRITON-BUMP]` prefix (or `[TRITON-PATCH]` for a single patch update -- see below).

### 2. Sync each C++ replica as a separate commit

Each fix in the doc's Step 5 should be a separate commit so reviewers can audit them individually:

```
Sync <change>. Caused by https://github.com/triton-lang/triton/pull/NNNNN
```

### 3. Local Triton patches between bumps

`docs/bump_triton_version.md` covers re-evaluating existing patches during a bump (its Step 3). When you need to **add** a new local patch *between* bumps, follow:

```bash
cd external/triton
# ... edit files ...
git diff > ../../triton-patches/<NN-name>.patch
git checkout .                  # leave the submodule clean
cd ../..
git add triton-patches/<NN-name>.patch
git commit -m "[TRITON-PATCH] <description>"
```

The wrapper `scripts/build-llvm.sh` applies patches in lexicographic order, so prefix with a number if ordering matters. The patch must be:

- Idempotent (`scripts/build-llvm.sh` checks via `git apply --check --reverse`)
- Justified in the commit message
- Either upstreamed or carry a comment explaining why it's a permanent fork (see "Decision tier" in `rules/code-review.md`)

### 4. PR description checklist

When opening the bump PR, paste this checklist into the PR body so reviewers can sign off line-by-line. (This is the **PR-facing** checklist; the doc's Section "Checklist Summary" is the agent's progress checklist while doing the work.)

```markdown
### Triton Bump Checklist

- [ ] Submodule updated from `OLD_COMMIT` to `NEW_COMMIT`
- [ ] LLVM rebuilt via `scripts/build-llvm.sh`
- [ ] `triton-patches/` re-evaluated; obsolete patches removed (doc Step 3)
- [ ] Diffed `compiler.py`, `llvm.cc`, `triton_amd.cc`, `AccelerateAMDMatmul.cpp`, `TargetUtils.h` (doc Step 4)
- [ ] `Pipelines.cpp` synced (`make_ttir`, `make_ttgir`, `make_llir` part 1) (doc 5.1)
- [ ] `TritonToHsaco.cpp` synced (`make_llir` part 2 + LLVM helpers) (doc 5.3)
- [ ] `tritonUtils.cpp` synced (`getMfmaVersion`, `getWmmaVersion`, `mlirTypeToScaleDotElemType`) (doc 5.4)
- [ ] `AmdArchDb.cpp` updated for any new `ISAFamily` (doc 5.5)
- [ ] `librockcompiler_deps.cmake` regenerated (doc Step 9)
- [ ] `cmake.sh` build succeeds (doc Step 8)
- [ ] `tests.sh` passes (doc Step 10)
- [ ] MIGraphX integration check (notify MIGraphX team if downstream impact)
```

## When to deviate from the doc

If you find a step in `docs/bump_triton_version.md` that is wrong or out of date during a bump, fix the doc in the same PR (or a follow-up `[NFC]` PR) -- don't fork the procedure into this skill.

---

# tuningRunner.py Usage

Source: `mlir/utils/performance/tuningRunner.py`. After tuning, use the output TSV with `perfRunner.py` for benchmarking (see `skills/perfrunner-usage/SKILL.md`). Run `python3 tuningRunner.py --help` for the up-to-date flag reference.

**Important**: Ensure no other processes are using the GPU during tuning. Shared GPU usage causes noisy and unreliable results. Check with `rocm-smi` or `fuser /dev/kfd` before starting. To pin tuning to a specific GPU, use `ROCR_VISIBLE_DEVICES`/`HIP_VISIBLE_DEVICES` -- the script itself has no `--gpus` flag and is single-GPU per invocation:

```bash
ROCR_VISIBLE_DEVICES=0 python3 tuningRunner.py --op gemm -c <configs>
```

## Config source

- `-c` / `--configs_file` -- file of configurations. The script's hard-coded default points at `mlir/utils/jenkins/performance/configs/tier1-conv-configs`, which **does not exist** -- the actual configs live under `mlir/utils/performance/configs/`. Always pass `-c` explicitly, e.g. `-c mlir/utils/performance/configs/tier1-gemm-configs`.
- `--config <STR ...>` -- one or more inline config strings to test instead of a file (`nargs='*'`). For GEMM, the string **must** include all of `-t`, `-out_datatype`, `-transA`, `-transB`, `-g`, `-m`, `-k`, `-n` -- otherwise `perfRunner.GemmConfig.from_command_line()` raises `ValueError: Incomplete GEMM configuration`.
- `--test_dir` -- fusion E2E tests directory. Default `../mlir/test/fusion/resnet50-e2e` only resolves when run from the `build/` directory. From any other CWD, pass an absolute or repo-rooted path (the actual source is `mlir/test/fusion/resnet50-e2e`). Used only when `--op fusion`.

## Operation

`--op` / `--operation`: `conv` (default), `gemm`, `fusion`, `attention`, `gemm_gemm`, `conv_gemm`

## Key flags (from `tuningRunner.py --help`)

| Flag | Default | Purpose |
|------|---------|---------|
| `-o` / `--output` | `tuning_results_local.tsv` | Output TSV (appends to existing file) |
| `--mlir-build-dir` | auto (`find_mlir_build_dir`) | rocmlirTriton build dir |
| `--rocmlir_gen_flags` | unset | Extra flags forwarded to `rocmlir-gen` (note: underscore, not dash) |
| `--tuning-space` | `full` | `quick`, `full`, `greedy`, `exhaustive` |
| `--disable-verify-winning-config` / `--no-disable-verify-winning-config` | `False` | When set, skip CPU-reference verification of the winning config (`rocmlir-gen -pv`) |
| `--verify-all-perfconfigs` | off | Compile and verify *every* applicable perf-config, not just the winner. Incompatible with `--disable-verify-winning-config=True` |
| `--data-type` | `f32 f16 i8` | Force a set of dtypes. Choices: `f32`, `f16`, `bf16`, `i8`, `i8_i32`, `i8_i8`, `fp8`, `fp8_f32`, `fp8_fp8`, `f4E2M1FN` |
| `--scale-type` | unset | Force scale types for scaled GEMM (`-scaledGemm` configs only): `f32`, `f8E8M0FNU` |
| `--tflops` | off | Append a `TFlops` column to the output TSV |
| `--compact-print` | off | Print info only when the winning config changes |
| `--abort-on-error` | off | Abort tuning on first error (used in CI) |
| `--debug` / `-d` | off | Verbose debug output; also writes a `{output}.debug` TSV |
| `--quiet` / `-q` | off | Quiet mode (suppress per-test output) |

There is **no** `--gpus`, `--num-cpus`, `--retune`, `--retry`, `--timeout`, `--wait-for-compiles`, `--status`/`-s`, `-v`, or `--verify-mode` flag. The previous version of this skill listed several of those; they were never implemented in this fork.

## Output TSV format

Header columns (printed once at the top of `--output`):

```
# arch    numCUs    numChiplets    testVector    perfConfig (<tuning-space>)
```

`<tuning-space>` is the value passed to `--tuning-space` (e.g. `perfConfig (quick)`). When `--tflops` is set, an additional `TFlops` column is appended. When `--debug` is set, a parallel `{output}.debug` TSV records every tested perf-config (not just winners).

## Examples

Run from the rocmlirTriton `build/` directory so the script's default `--test_dir`/`find_mlir_build_dir()` resolve correctly:

```bash
python3 ../mlir/utils/performance/tuningRunner.py --op gemm \
  -c ../mlir/utils/performance/configs/tier1-gemm-configs -o tuning_db.tsv
python3 ../mlir/utils/performance/tuningRunner.py --op gemm \
  --config "-t f32 -out_datatype f32 -transA false -transB false -g 3 -m 1024 -k 769 -n 512"
python3 ../mlir/utils/performance/tuningRunner.py --op conv \
  -c ../mlir/utils/performance/configs/tier1-conv-configs --tuning-space quick
python3 ../mlir/utils/performance/tuningRunner.py --op fusion --test_dir ../mlir/test/fusion/resnet50-e2e
python3 ../mlir/utils/performance/tuningRunner.py --op gemm \
  -c ../mlir/utils/performance/configs/tier1-gemm-configs --tflops --abort-on-error
ROCR_VISIBLE_DEVICES=2 python3 ../mlir/utils/performance/tuningRunner.py --op gemm \
  -c ../mlir/utils/performance/configs/tier1-gemm-configs -o gpu2.tsv
```
