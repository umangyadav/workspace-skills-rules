---
name: build-test-workflow
description: >-
  Build, test, and lint rocMLIR with structured reporting. Use when asked to
  build the project, run tests, check lint, or verify a build.
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
