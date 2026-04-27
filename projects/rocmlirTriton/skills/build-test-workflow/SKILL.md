---
name: build-test-workflow
description: >-
  Build, test, and lint rocmlirTriton with structured reporting. Use when asked
  to build the project, run tests.sh, run check-rocmlir, check lint, or verify
  a build.
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
