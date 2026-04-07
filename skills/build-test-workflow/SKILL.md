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
