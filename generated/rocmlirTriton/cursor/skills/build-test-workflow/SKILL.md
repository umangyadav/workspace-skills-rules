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
