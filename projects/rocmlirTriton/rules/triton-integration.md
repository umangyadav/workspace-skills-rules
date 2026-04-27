# Triton Integration

rocmlirTriton depends on upstream [Triton](https://github.com/triton-lang/triton) as a git submodule. Triton brings its own LLVM/MLIR and AMD backend; we replicate parts of Triton's Python pipeline in C++.

## Compilation arc

```
TOSA / MIGraphX
    -> highlevel  (Linalg + Rock view-to-transform, fold-broadcast, ...)
    -> Rock dialect (rock.gemm/conv/attention -> rock.gridwise -> rock.blockwise -> ptr arith)
    -> RockToTTIRPass + RockFuncToTritonFuncPass   <-- bridge into the Triton (`tt`) dialect
    -> Triton IR (TTIR)         via makeTTIR
    -> TritonGPU IR (TTGIR)     via makeTTGIR
    -> LLVM IR                  via makeLLIR
    -> AMDGCN -> HSACO          via TritonToHsacoPass
    -> Host glue (gpu.launch_func + LLVM lowering) via RestoreHostCode + buildHostLoweringPipeline
```

The four `rocmlir-driver` pipelines that drive this -- `rock-highlevel-pipeline`, `rock-kernel-pipeline`, `rock-triton-pipeline`, `rock-backend-pipeline` -- are registered at the bottom of `mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp`. `rocmlir-driver`'s `-kernel-pipeline=` keywords (`migraphx`, `highlevel`, `gpu`, `triton`, `binary`, `full`) map onto these (see `rocmlir-tools.md`). Most Triton-side stages (`makeTTIR`/`makeTTGIR`/`makeLLIR`, `TritonToHsacoPass`) are C++ replicas of upstream Triton's Python `compiler.py`.

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

## Rock <-> Triton dialect bridge

The two passes that hand the IR off from the Rock dialect to Triton's `tt` dialect are owned entirely by us (no upstream counterpart):

| Pass | File | Role |
|------|------|------|
| `RockToTTIRPass` (`-rock-to-ttir`) | `mlir/lib/Dialect/Rock/Transforms/RockToTTIR.cpp` | Rewrite `rock.blockwise_*`, `rock.gemm`, `rock.reduce`, ... into `tt.load`/`tt.store`/`tt.dot`/`tt.reduce`. |
| `RockFuncToTritonFuncPass` (`-rock-func-to-triton-func`) | `mlir/lib/Dialect/Rock/Transforms/FuncToTritonFunc.cpp` | Convert `func.func` kernels to `tt.func`, lift tensor args to `!tt.ptr`, and fold `arith.addi`-on-pointers into `tt.addptr`. |
| `RockSerializeHostFuncsPass` / `RockRestoreHostCodePass` | `Transforms/SerializeHostFuncs.cpp`, `Transforms/RestoreHostCode.cpp` | Park host functions before the Triton-only stages and restore them afterwards as `gpu.launch_func`. |

Both bridge passes are scheduled by `rock::buildKernelPipeline`. After they run, the module body is `tt.func` only, and the Triton C++ pipeline (next section) takes over.

## Python-to-C++ replication points

These C++ functions/files mirror Triton Python logic. Whenever the submodule advances, audit them against upstream (full procedure: `triton-bump` skill):

| Triton (Python / C++) | rocmlirTriton (C++) |
|-----------------------|---------------------|
| `make_ttir` (`amd/backend/compiler.py`) | `makeTTIR()` in `mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp` |
| `make_ttgir` (`amd/backend/compiler.py`) | `makeTTGIR()` in `Pipelines.cpp` |
| `make_llir` part 1 (MLIR-side passes) | `makeLLIR()` in `Pipelines.cpp` (registered as the `rock-triton-pipeline`) |
| `make_llir` part 2 (LLVM IR finalization), `make_amdgcn`, `make_hsaco` | `mlir/lib/Translation/TritonToHsaco/TritonToHsaco.cpp` (`TritonToHsacoPass`) |
| `init_targets`, `createTargetMachine`, `optimize_module` (`llvm.cc`) | `TritonToHsaco.cpp` |
| `getMfmaVersion`, `getWmmaVersion`, `mlirTypeToScaledElemType` (`AccelerateAMDMatmul.cpp`) | `mlir/lib/Dialect/Rock/utility/tritonUtils.cpp` |
| `ISAFamily`, hardware feature checks (`TargetUtils.h`) | `mlir/lib/Dialect/Rock/IR/AmdArchDb.cpp` |
| `triton_amd.cc` Python pass bindings | corresponding `pm->addPass(...)` calls in `Pipelines.cpp` |

## Hardware feature detection

Always use `rock::*` helpers (e.g. `rock::supportsTDM(arch)`) instead of `triton::AMD::TargetInfo(...)` directly. If a needed `rock` helper is missing, add one in `AmdArchDb.cpp` rather than calling Triton's `TargetInfo` from Rock code. This is the canonical rule referenced from `code-review.md`, `dev-workflow.md`, and the bump skill.

## librockcompiler_deps.cmake

The fat library `librockCompiler.a` (consumed by MIGraphX) has its dependency list pinned in `mlir/tools/rocmlir-lib/librockcompiler_deps.cmake`. Regenerate it whenever Triton libraries are added/removed (almost always on Triton bumps); the regeneration command lives in the `triton-bump` skill.

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

The canonical step-by-step bump procedure is `docs/bump_triton_version.md` in the rocmlirTriton repo (10 steps: submodule update, LLVM rebuild, patch re-evaluation, upstream diffs, C++ replica sync, fat-library deps regen, tests). The `triton-bump` skill (`skills/triton-bump/SKILL.md`) wraps the doc with project conventions (bump branch naming, PR-description checklist, between-bumps `[TRITON-PATCH]` workflow). Always start from the doc -- don't open-code a bump.
