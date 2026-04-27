<!-- applyTo: mlir/**/*.cpp,mlir/**/*.h -->

# LLVM/MLIR C++ Quick Reference

rocmlirTriton-specific patterns and examples. For the full rules, see [LLVM Coding Standards](https://llvm.org/docs/CodingStandards.html) and the code-review checklist.

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

## Triton-aware C++

When calling into Triton, prefer the project's wrapper helpers in `mlir/lib/Dialect/Rock/utility/tritonUtils.cpp` and `mlir/lib/Dialect/Rock/IR/AmdArchDb.cpp` over reaching directly into `triton::AMD::*`. This isolates the C++ surface that needs review on every Triton bump.

## Naming

The `.clang-tidy` enforces LLVM-style names with `readability-identifier-naming` (CamelCase for classes/types/members/parameters/variables, camelBack for functions). Keep new code consistent with surrounding files.
