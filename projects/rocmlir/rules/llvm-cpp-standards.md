# LLVM/MLIR C++ Quick Reference

rocMLIR-specific patterns and examples. For the full rules, see [LLVM Coding Standards](https://llvm.org/docs/CodingStandards.html) and the code-review checklist.

## Casting patterns

```cpp
if (isa<MemRefType>(val.getType())) { auto t = cast<MemRefType>(val.getType()); }
auto t = dyn_cast<MemRefType>(val.getType()); // returns nullptr on failure
```

## Error handling patterns

```cpp
// Return LogicalResult from helpers/verifiers/rewrites
LogicalResult verify() { return emitOpError("mismatch") << " expected " << n; }

// In pass runOnOperation()
if (failed(result)) { signalPassFailure(); return; }
```

## Debug support

```cpp
#define DEBUG_TYPE "rock-my-pass"
LLVM_DEBUG(llvm::dbgs() << "message\n");
```

## LLVM algorithms (prefer over STL equivalents)

- `llvm::find`, `llvm::all_of`, `llvm::any_of`, `llvm::none_of`
- `llvm::to_vector`, `llvm::zip_equal`, `llvm::enumerate`
- `llvm::sort` (over `std::sort` for determinism)

## Namespace conventions

- `using namespace mlir;` and `using namespace mlir::rock;` at `.cpp` file scope
- Anonymous namespace only for local class/struct declarations: `namespace { struct MyPass ... }`
- Pass defs: `namespace mlir { namespace rock { #define GEN_PASS_DEF_... } }`
