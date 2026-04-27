# Testing Conventions

See also: `code-review.md` (Major section) and `dev-workflow.md` (Testing a new operation or feature) for review-time testing requirements.

## When to use each test type

| Type | Location | Use for |
|------|----------|---------|
| **Lit** (`.mlir`) | `mlir/test/` | Passes, pipelines, driver integration |
| **GoogleTest** | `mlir/unittests/` | C++ helpers, attributes, transform maps |
| **E2E (lit)** | `mlir/test/e2e/`, `mlir/test/fusion/pr-e2e/`, `mlir/test/fusion/nightly-misc-e2e/`, `mlir/test/fusion/resnet50-e2e/` | Full GPU pipeline |
| **E2E (smoke)** | top-level `tests.sh`, `test_prefill_changes.sh` | Hand-curated GPU smoke tests covering gemm/conv/attention/fusion |

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

`tests.sh` is the canonical end-to-end smoke entry point. It:

1. Detects `$ARCH` and `$NUM_CU` from `rocminfo`
2. Builds `check-rocmlir-build-only ci-performance-scripts`
3. Runs gemm/conv/attention/fusion pipelines through `mlir-runner` from `external/triton/llvm-project/build/`
4. Filters `LIT_FILTER` over targeted lit subdirectories (`fusion/fusability`, `fusion/pr-e2e/`, `Dialect/Rock`, `rocmlir-gen`, `Conversion`, `rocmlir-driver`, `capi`, `rocmlir-tuning-driver`)

Whenever a new dialect/conversion area is added, update `tests.sh` so the corresponding `LIT_FILTER` line covers it.

## Key substitutions

Defined in `lit.cfg.py` / `lit.site.cfg.py.in` files:
- `mlir/test/lit.cfg.py` -- main substitutions (`%arch`, `%shlibext`, `%linalg_test_lib_dir`, etc.)
- E2E and fusion lit configs add suite-specific substitutions

## FileCheck defaults

`FILECHECK_OPTS="-enable-var-scope --allow-unused-prefixes=false"` -- all CHECK prefixes must be used.

## Test targets

- `check-rocmlir` -- full suite
- `check-rocmlir-build-only` -- compile only (used in CI build stage)
- `MLIRRockUnitTests` -- GoogleTest only (run via `./mlir/unittests/Dialect/Rock/MLIRRockUnitTests`)
- E2E (PR subset): enable with `-DROCMLIR_DRIVER_PR_E2E_TEST_ENABLED=ON`
- E2E (full): enable with `-DROCK_E2E_TEST_ENABLED=ON` and `-DROCMLIR_DRIVER_E2E_TEST_ENABLED=ON`

## Architecture and dtype coverage

- New ops/passes must work on all supported GPU architectures present in CI (`gfx90a`, `gfx942`, `gfx950`, `gfx1100`, etc.)
- Guard arch-specific ops with target checks in both code and tests; `tests.sh` already gates several `gfx950`-only paths
- Enumerate all dtypes the op should support (`f16`, `bf16`, `f32`, `f8E4M3FN`, `f8E5M2`, `f4E2M1FN`, `i8`, etc.)
- Add E2E tests covering each supported dtype; reject unsupported dtypes with `emitOpError`
- For scaled GEMM features, ensure `f8E8M0FNU` scale handling works (see `docs/scaled_gemm.md`)

## Fusion test requirements

MIGraphX-related or fusion changes must include fusion lit tests in `mlir/test/fusion/` (compile-level) and/or `mlir/test/fusion/pr-e2e/` (GPU E2E). Top-level `fusion_*_with_host.mlir` files at the repo root are exercised by `tests.sh` for end-to-end coverage.
