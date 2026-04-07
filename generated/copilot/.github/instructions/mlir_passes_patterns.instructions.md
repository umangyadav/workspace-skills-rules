<!-- applyTo: mlir/lib/**/*.cpp -->

# MLIR Pass and Pattern Writing

## Pass definition (TableGen-generated base)

```cpp
namespace mlir {
namespace rock {
#define GEN_PASS_DEF_ROCKCONVTOGEMMPASS
#include "mlir/Dialect/Rock/Passes.h.inc"
} // namespace rock
} // namespace mlir

namespace {
struct RockConvToGemmPass
    : public rock::impl::RockConvToGemmPassBase<RockConvToGemmPass> {
  void runOnOperation() override;
};
} // namespace
```

## Pattern rewriting -- two styles

**Greedy rewrite** (most common):
```cpp
struct MyPattern : public OpRewritePattern<MyOp> {
  LogicalResult matchAndRewrite(MyOp op, PatternRewriter &rw) const override;
};
// Drive with: applyPatternsGreedily(getOperation(), std::move(patterns))
```

**Dialect conversion** (type/legalization changes):
```cpp
struct MyConverter : public OpConversionPattern<MyOp> {
  LogicalResult matchAndRewrite(MyOp op, OpAdaptor adaptor,
                                ConversionPatternRewriter &rw) const override;
};
// Drive with: applyPartialConversion(getOperation(), target, std::move(patterns))
```

## Op creation

```cpp
auto newOp = GemmOp::create(builder, loc, resultType, operands...);
rewriter.replaceOpWithNewOp<NewOp>(oldOp, args...);
```

## Type handling

```cpp
if (!isa<MemRefType>(val.getType()))
  return op.emitOpError("expected memref");
auto memType = cast<MemRefType>(val.getType());
auto newType = MemRefType::get(shape, elementType);
```
