<!-- applyTo: mlir/**/*.cpp,mlir/**/*.h,mlir/**/*.td -->

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

## Touching the Rock <-> Triton bridge

The two passes that translate Rock dialect IR into Triton's `tt` dialect:

- `mlir/lib/Dialect/Rock/Transforms/RockToTTIR.cpp` (`-rock-to-ttir`) -- rewrite Rock blockwise/gemm ops to `tt.load`/`tt.store`/`tt.dot`/`tt.reduce`. Add a new `OpRewritePattern` here when you introduce a Rock op that needs to reach the GPU through Triton.
- `mlir/lib/Dialect/Rock/Transforms/FuncToTritonFunc.cpp` (`-rock-func-to-triton-func`) -- module-level pass that turns `func.func` kernels into `tt.func`, lifts tensor args to `!tt.ptr`, and folds pointer arith into `tt.addptr`. Touch this when the kernel calling convention or pointer-attribute layout changes.

Both are scheduled by `rock::buildKernelPipeline` in `Pipelines.cpp`. After they run, the kernel module body is `tt.func` only.

## Touching the Triton-driven pipeline

If your change crosses into the part of the pipeline that runs on `tt`/`ttg` IR:

1. Find the Python equivalent in `external/triton/third_party/amd/backend/compiler.py` and the binding in `external/triton/third_party/amd/python/triton_amd.cc`.
2. Mirror the change in `mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp` (`makeTTIR`/`makeTTGIR`/`makeLLIR` -- TTIR/TTGIR/LLIR MLIR-side passes) or `mlir/lib/Translation/TritonToHsaco/TritonToHsaco.cpp` (LLVM IR finalization, AMDGCN, HSACO).
3. Use `rock::*` helpers (`rock::supportsTDM`, etc.) to gate hardware-conditional passes.
4. If you need a hardware capability not yet exposed by `rock`, add it to `mlir/lib/Dialect/Rock/IR/AmdArchDb.cpp` rather than reaching into `triton::AMD::TargetInfo`.
5. If a fix should also live in upstream Triton, prefer drafting an upstream PR; only add a `triton-patches/*.patch` when waiting for upstream is not viable.

## Adding a MIGraphX operation

1. Define op in `mlir/include/mlir/Dialect/MIGraphX/IR/MIGraphX.td`
2. Add lowering in `mlir/lib/Conversion/MIGraphXToTosa/`
3. Add tests in `mlir/test/Conversion/`

## Testing a new operation or feature

### Architecture coverage

- New ops/passes must work on all supported GPU architectures (`gfx90a`, `gfx942`, `gfx950`, `gfx1100`, ...)
- If an op is architecture-specific, guard it with proper target checks in both code and tests
- Use `lit.cfg.py` to configure arch-specific test guards

### Data type coverage

- Enumerate all dtypes the op should support (`f16`, `bf16`, `f32`, `f8E4M3FN`, `f8E5M2`, `f4E2M1FN`, `i8`, `i4`, etc.)
- Ensure the implementation handles each supported dtype explicitly -- do not silently fall through
- Return a clear error (`emitOpError`) for unsupported dtypes rather than producing wrong results
- Add E2E tests covering each supported dtype and Lit tests that verify unsupported dtypes are rejected
- Scaled GEMM features must respect the `f8E8M0FNU` scale convention (see `docs/scaled_gemm.md`)

### Edge cases and completeness

- Consider boundary conditions: zero-size tensors, non-aligned shapes, large dimensions, scalar inputs
- For optimization passes, verify the optimization fires (FileCheck for expected IR) and verify correctness (E2E with random data)
- Test both the optimized path and the fallback/unoptimized path
- If the feature interacts with fusion, test fused and unfused variants and update `tests.sh` if a new top-level `fusion_*_with_host.mlir` is added

## Debugging a pass failure

```bash
# Isolate
rocmlir-opt --my-pass input.mlir

# Enable debug output (requires -DLLVM_ENABLE_ASSERTIONS=ON)
rocmlir-opt --my-pass input.mlir --debug-only=my-pass

# Dump full pipeline (rocMLIR side)
rocmlir-driver -dump-pipelines -kernel-pipeline=full input.mlir 2>&1

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

# Compare against upstream Triton's Python pipeline by running a reference
# kernel through `python -m triton.runtime.compile` (only when Triton's
# Python module is available; not built by default in this repo)
```
