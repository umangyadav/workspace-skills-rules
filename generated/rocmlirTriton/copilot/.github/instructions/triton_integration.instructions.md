<!-- applyTo: mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp,mlir/lib/Translation/**/*.cpp,mlir/lib/Dialect/Rock/utility/tritonUtils.*,mlir/lib/Dialect/Rock/IR/AmdArchDb.cpp,triton-patches/**/*,scripts/build-llvm.sh,cmake/triton.cmake,.gitmodules -->

# Triton Integration

rocmlirTriton depends on upstream [Triton](https://github.com/triton-lang/triton) as a git submodule. Triton brings its own LLVM/MLIR and AMD backend; we replicate parts of Triton's Python pipeline in C++.

## Submodule layout

- Submodule: `external/triton/` (declared in `.gitmodules`, branch tracked by SHA)
- LLVM/MLIR: built from `external/triton/llvm-project/` via Triton's `scripts/build-llvm-project.sh`
- LLVM hash pinned by `external/triton/cmake/llvm-hash.txt`

## Local patches

`triton-patches/*.patch` are applied to the Triton submodule by `scripts/build-llvm.sh` before LLVM/MLIR is built. Each patch must be:

- Idempotent (the wrapper detects already-applied patches via `git apply --check --reverse`)
- Justified in the commit message that adds the patch
- Re-evaluated on every Triton bump (drop the patch if it landed upstream)

Never modify `external/triton/` directly without a corresponding `.patch` file -- the submodule is checked out fresh on every build.

## Python-to-C++ replication points

These C++ files mirror Triton Python logic. Whenever the submodule advances, audit them against upstream (see the `triton-bump` skill):

| Triton (Python / C++) | rocmlirTriton (C++) |
|-----------------------|---------------------|
| `make_ttir`, `make_ttgir`, `make_llir` part 1 (`compiler.py`) | `mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp` |
| `make_llir` part 2, `make_amdgcn`, `make_hsaco` (`compiler.py`) | `mlir/lib/Translation/TritonToHsaco/TritonToHsaco.cpp` |
| `init_targets`, `createTargetMachine`, `optimize_module` (`llvm.cc`) | `TritonToHsaco.cpp` |
| `getMfmaVersion`, `getWmmaVersion`, `mlirTypeToScaledElemType` (`AccelerateAMDMatmul.cpp`) | `mlir/lib/Dialect/Rock/utility/tritonUtils.cpp` |
| `ISAFamily`, hardware feature checks (`TargetUtils.h`) | `mlir/lib/Dialect/Rock/IR/AmdArchDb.cpp` |
| `triton_amd.cc` Python pass bindings | corresponding `pm->addPass(...)` in `Pipelines.cpp` |

## Hardware feature detection

Always use `rock::*` helpers (e.g. `rock::supportsTDM(arch)`) instead of `triton::AMD::TargetInfo(...)` directly. If a needed `rock` helper is missing, add one in `AmdArchDb.cpp` rather than calling Triton's `TargetInfo` from Rock code.

## Intentionally NOT replicated

These Python features are intentionally absent from the C++ pipeline -- do **not** add them when syncing:

- `HIPBackend.instrumentation.patch()`
- `knobs.*` configuration (we use hardcoded defaults)
- `passes.llvmir.add_di_scope()` (TODO, non-critical)
- `llvm.translate_to_mir()`, `llvm.dump_sched_dag()` (debugging only)
- `knobs.amd.swap_mir`, `knobs.compilation.dump_ir_*` (debugging only)
- FPSan instrumentation mode
- Full `schedule_hint` loop processing (partially hardcoded)

## After a submodule bump

1. Rebuild LLVM with `bash scripts/build-llvm.sh`
2. Re-validate every `triton-patches/*.patch`
3. Diff the replication-point files against `${OLD_COMMIT}..${NEW_COMMIT}`
4. Rebuild rocmlirTriton with `bash cmake.sh`
5. Regenerate `mlir/tools/rocmlir-lib/librockcompiler_deps.cmake` via `perl mlir/utils/jenkins/static-checks/get_fat_library_deps_list.pl`
6. Run `bash tests.sh`

See the `triton-bump` skill (`skills/triton-bump/SKILL.md`) and `docs/bump_triton_version.md` for the full workflow.
