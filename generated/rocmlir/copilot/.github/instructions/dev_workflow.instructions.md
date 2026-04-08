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

## Adding a MIGraphX operation

1. Define op in `mlir/include/mlir/Dialect/MIGraphX/IR/MIGraphX.td`
2. Add lowering in `mlir/lib/Conversion/MIGraphXToTosa/` or `MIGraphXToLinalg/`
3. Add tests in `mlir/test/Conversion/`

## Testing a new operation or feature

### Architecture coverage

- New ops/passes must work on all supported GPU architectures (gfx90a, gfx942, etc.)
- If an op is architecture-specific, guard it with proper target checks in both code and tests
- Use `lit.cfg.py` to configure arch-specific test guards

### Data type coverage

- Enumerate all dtypes the op should support (f16, bf16, f32, f8, i8, i4, etc.)
- Ensure the implementation handles each supported dtype explicitly -- do not silently fall through
- Return a clear error (`emitOpError`) for unsupported dtypes rather than producing wrong results
- Add E2E tests covering each supported dtype and Lit tests that verify unsupported dtypes are rejected

### Edge cases and completeness

- Consider boundary conditions: zero-size tensors, non-aligned shapes, large dimensions, scalar inputs
- For optimization passes, verify the optimization fires (FileCheck for expected IR) and verify correctness (E2E with random data)
- Test both the optimized path and the fallback/unoptimized path
- If the feature interacts with fusion, test fused and unfused variants

## Debugging a pass failure

```bash
# Isolate
rocmlir-opt --my-pass input.mlir

# Enable debug output (requires -DLLVM_ENABLE_ASSERTIONS=ON)
rocmlir-opt --my-pass input.mlir --debug-only=my-pass

# Dump full pipeline
rocmlir-driver -dump-pipelines -kernel-pipeline=full input.mlir 2>&1
```
