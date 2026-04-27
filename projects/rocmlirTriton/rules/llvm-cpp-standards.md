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

For rocMLIR-side passes:

```cpp
#define DEBUG_TYPE "rock-my-pass"
LLVM_DEBUG(llvm::dbgs() << "message\n");
```

For passes that live in `external/triton/` (or `triton-patches/`), follow upstream Triton's `LDBG` idiom -- it auto-prefixes each line with `[DEBUG_TYPE]:` so logs stay grep-friendly under `--debug-only=...`. The base macros live in `include/triton/Conversion/TritonGPUToLLVM/Utility.h`; if your file doesn't include it, redefine them locally:

```cpp
#define DEBUG_TYPE "tritonamd-my-pass"
#define DBGS() (llvm::dbgs() << "[" DEBUG_TYPE "]: ")
#define LDBG(X) LLVM_DEBUG(DBGS() << X << "\n")
// usage
LDBG("rewrote " << op->getName() << " to " << newOp->getName());
```

## LLVM algorithms (prefer over STL equivalents)

- `llvm::find`, `llvm::all_of`, `llvm::any_of`, `llvm::none_of`
- `llvm::to_vector`, `llvm::zip_equal`, `llvm::enumerate`
- `llvm::sort` (over `std::sort` for determinism)

## Namespace conventions

- `using namespace mlir;` and `using namespace mlir::rock;` at `.cpp` file scope (rocMLIR side).
- Anonymous namespace only for local class/struct declarations: `namespace { struct MyPass ... }`.
- Pass defs (rocMLIR side): `namespace mlir { namespace rock { #define GEN_PASS_DEF_... } }`.
- Pass defs (Triton-patch side): use the C++17 nested form `namespace mlir::triton { #define GEN_PASS_DEF_... #include "...Passes.h.inc" }`. This matches upstream Triton; do **not** introduce the older `namespace mlir { namespace triton { ... } }` style in `external/triton/` patches.
- Triton convention is to follow the named-namespace block with an anonymous `namespace { using namespace mlir; using namespace mlir::triton; ... }` for the pass implementation. Mirror that layout when patching Triton.

## Triton-aware C++

When calling into Triton, prefer the project's wrapper helpers in `mlir/lib/Dialect/Rock/utility/tritonUtils.cpp` and `mlir/lib/Dialect/Rock/IR/AmdArchDb.cpp` over reaching directly into `triton::AMD::*`. This isolates the C++ surface that needs review on every Triton bump.

When you genuinely need TritonGPU IR helpers (layouts, swizzling, linear-layout math), reach for the upstream utility headers rather than reimplementing -- in particular `triton/Tools/LayoutUtils.h`, `triton/Tools/LinearLayout.h`, `triton/Dialect/TritonGPU/Transforms/Utility.h`, and `triton/Dialect/Triton/IR/Utility.h`.

## Naming

The `.clang-tidy` enforces LLVM-style names with `readability-identifier-naming` (CamelCase for classes/types/members/parameters/variables, camelBack for functions). Keep new code consistent with surrounding files.

Upstream Triton has **no `.clang-tidy`** of its own -- it relies on `clang-format` (LLVM style, v19.1.6) plus reviewer judgement. So when patching `external/triton/`, our `.clang-tidy` rules don't run there; mirror the surrounding Triton file's style (still LLVM-flavoured: `CamelCase` types, `camelBack` functions/members) and don't introduce names that would fail our `readability-identifier-naming` check on our side either.

## Indentation (`.editorconfig`)

Upstream Triton ships an `.editorconfig` that overrides the global 4-space default per file type. Honour it when patching `external/triton/`:

| File type | Indent |
|-----------|--------|
| `.cpp`, `.h`, `.cu`, `.cuh`, `.mlir` | **2 spaces** |
| `.td` (TableGen) | **4 spaces** |
| `.py` | 4 spaces |
| `CMakeLists.txt`, `*.cmake`, `*.yaml`, `*.yml` | 2 spaces |
| `Makefile` | hard tab |

`clang-format` will fix C++ indents but won't catch a wrong-indent `.td` or `CMakeLists.txt` patch. Make sure your editor honours `.editorconfig` (or run a manual pass) before sending the diff.
