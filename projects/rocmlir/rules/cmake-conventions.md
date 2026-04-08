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
