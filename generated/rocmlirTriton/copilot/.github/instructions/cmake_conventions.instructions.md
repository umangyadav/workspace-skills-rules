<!-- applyTo: **/CMakeLists.txt,**/*.cmake -->

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
