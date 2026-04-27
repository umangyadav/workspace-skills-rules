---
name: triton-bump
description: >-
  Bump the Triton submodule in rocmlirTriton. Updates external/triton, rebuilds
  LLVM, audits replication points, refreshes triton-patches, and runs tests.
  Use when asked to bump Triton, update the Triton submodule, sync with
  upstream Triton, or refresh local Triton patches.
---

# Triton Bump

`external/triton/` is a **git submodule** of `triton-lang/triton`. Several Triton Python pipelines and helpers are replicated in C++ inside `mlir/`. Whenever the submodule advances, those replicas must be re-synced.

The full reference is `docs/bump_triton_version.md` -- read it once before starting and keep it open during the bump.

## Workflow

### 1. Create the bump branch

```bash
git checkout develop
git pull origin develop
git checkout -b triton-bump-<month>-<year>     # or triton-bump-<short-sha>
```

### 2. Record the old commit and update the submodule

```bash
cd external/triton
export OLD_COMMIT=$(git rev-parse HEAD)
git fetch
git checkout <new-target-sha>                  # or `git pull` to track upstream main
export NEW_COMMIT=$(git rev-parse HEAD)
cd ../..
git add external/triton
```

### 3. Rebuild LLVM via the wrapper

The Triton submodule pins LLVM through `external/triton/cmake/llvm-hash.txt`; bumping Triton may bump LLVM too.

```bash
bash scripts/build-llvm.sh
```

This wrapper:
1. Initializes submodules (recursive)
2. Applies every `triton-patches/*.patch` to `external/triton/` (idempotent)
3. Forces `MLIR_ENABLE_ROCM_RUNNER=ON` in Triton's build script
4. Runs Triton's `scripts/build-llvm-project.sh`

If a patch fails to apply, see step 4.

### 4. Re-evaluate `triton-patches/`

For each patch in `triton-patches/`:

```bash
cd external/triton
git diff ${OLD_COMMIT}..${NEW_COMMIT} -- <files-touched-by-patch>
```

- If the upstream change already covers what the patch did, **delete the patch file**
- If the patch still applies cleanly, leave it
- If the patch conflicts, rebase it manually and update the file (commit with `[TRITON-PATCH] ...`)

### 5. Diff the replication-source files

```bash
cd external/triton
git diff ${OLD_COMMIT}..${NEW_COMMIT} -- third_party/amd/backend/compiler.py > /tmp/compiler.py.diff
git diff ${OLD_COMMIT}..${NEW_COMMIT} -- python/src/llvm.cc > /tmp/llvm.cc.diff
git diff ${OLD_COMMIT}..${NEW_COMMIT} -- third_party/amd/python/triton_amd.cc > /tmp/triton_amd.cc.diff
git diff ${OLD_COMMIT}..${NEW_COMMIT} -- third_party/amd/lib/TritonAMDGPUTransforms/AccelerateAMDMatmul.cpp > /tmp/AccelerateAMDMatmul.cpp.diff
git diff ${OLD_COMMIT}..${NEW_COMMIT} -- third_party/amd/include/TritonAMDGPUToLLVM/TargetUtils.h > /tmp/TargetUtils.h.diff
cd ../..
```

### 6. Sync the C++ replicas

| Triton (Python / C++) | rocmlirTriton (C++) |
|-----------------------|---------------------|
| `make_ttir`, `make_ttgir`, `make_llir` part 1 | `mlir/lib/Dialect/Rock/Pipelines/Pipelines.cpp` |
| `make_llir` part 2, `make_amdgcn`, `make_hsaco` | `mlir/lib/Translation/TritonToHsaco/TritonToHsaco.cpp` |
| `init_targets`, `createTargetMachine`, `optimize_module` (`llvm.cc`) | `TritonToHsaco.cpp` (`initializeLLVMTargets`, `createTargetMachine`, `optimizeModule`) |
| `getMfmaVersion`, `getWmmaVersion`, `mlirTypeToScaledElemType` (`AccelerateAMDMatmul.cpp`) | `mlir/lib/Dialect/Rock/utility/tritonUtils.cpp` (`mlirTypeToScaleDotElemType` extends BF16/FP16) |
| `triton_amd.cc` Python pass bindings | corresponding `pm->addPass(...)` in `Pipelines.cpp` |
| `ISAFamily` / hardware capabilities | `mlir/lib/Dialect/Rock/IR/AmdArchDb.cpp` |

For each diff, mirror the change in the corresponding C++ file. Notes:

- New pass added in Python -> find C++ creation in `triton_amd.cc`, add the `pm->addPass(...)` call, include the relevant Triton header
- Pass signature changed -> update the call site to match (check `external/triton/third_party/amd/include/TritonAMDGPUTransforms/Passes.h`)
- New `ISAFamily` value -> update every switch in `AmdArchDb.cpp` (`getMatrixAccelKind`, `isFastAtomicAddSupported`, `isFastAtomicMaxSupported`, `getMaxNumChiplets`, `getMinNumCU`, `getMaxWavesPerEU`, etc.) and confirm `tritonUtils.cpp::getMfmaVersion`/`getWmmaVersion` handle the new chip
- Hardware feature gates in Python -> use `rock::*` helpers in C++ (`rock::supportsTDM(arch)`), adding new helpers in `AmdArchDb.cpp` if needed
- Skip features intentionally NOT replicated (see `rules/triton-integration.md`): `instrumentation.patch`, `knobs.*`, `add_di_scope`, `translate_to_mir`, `dump_sched_dag`, `swap_mir`, `dump_ir_*`, FPSan, `schedule_hint` loop processing

Commit each fix separately with a descriptive message:

```
Sync <change>. Caused by https://github.com/triton-lang/triton/pull/NNNNN
```

### 7. Build and fix breakage

```bash
bash cmake.sh
```

Resolve compilation errors; expect some from upstream LLVM API changes that came in with the LLVM bump.

### 8. Regenerate `librockcompiler_deps.cmake`

A bump can add or remove libraries baked into `librockCompiler.a`:

```bash
cd build
perl ../mlir/utils/jenkins/static-checks/get_fat_library_deps_list.pl \
  > ../mlir/tools/rocmlir-lib/librockcompiler_deps.cmake
cd ..
git add mlir/tools/rocmlir-lib/librockcompiler_deps.cmake
```

### 9. Run tests

```bash
bash tests.sh
```

If new top-level `fusion_*_with_host.mlir` files are added during the bump, also include them in `tests.sh`.

### 10. Open the PR with the bump checklist

PR description must include the bump checklist (lifted from `docs/bump_triton_version.md`):

```markdown
### Triton Bump Checklist

- [ ] Submodule updated from `OLD_COMMIT` to `NEW_COMMIT`
- [ ] LLVM rebuilt via `scripts/build-llvm.sh`
- [ ] `triton-patches/` re-evaluated; obsolete patches removed
- [ ] Diffed `compiler.py`, `llvm.cc`, `triton_amd.cc`, `AccelerateAMDMatmul.cpp`, `TargetUtils.h`
- [ ] `Pipelines.cpp` synced (`make_ttir`, `make_ttgir`, `make_llir` part 1)
- [ ] `TritonToHsaco.cpp` synced (`make_llir` part 2 + LLVM helpers)
- [ ] `tritonUtils.cpp` synced (`getMfmaVersion`, `getWmmaVersion`, `mlirTypeToScaleDotElemType`)
- [ ] `AmdArchDb.cpp` updated for any new `ISAFamily`
- [ ] `librockcompiler_deps.cmake` regenerated
- [ ] `cmake.sh` build succeeds
- [ ] `tests.sh` passes
- [ ] MIGraphX integration check (notify MIGraphX team if downstream impact)
```

## Common failure patterns

- **Missing pass**: new pass call in `compiler.py` -> find binding in `triton_amd.cc` and add C++ call
- **Pass signature change**: check the new signature in `external/triton/third_party/amd/include/TritonAMDGPUTransforms/Passes.h`
- **`ISAFamily` switch warnings**: `default:` case silently returned a fallback -- audit every `switch` in `AmdArchDb.cpp` and `tritonUtils.cpp`
- **Test failures**: behavioral change upstream -- update the test expectation only after confirming the new behavior is intended
- **Header errors**: mirror the includes from `triton_amd.cc` or other Triton files; CMake propagates Triton's include dirs through the helper functions in `cmake/triton.cmake`

## Local Triton patches (between bumps)

For targeted Triton fixes that cannot wait for upstream, add a new `triton-patches/<name>.patch` file:

```bash
cd external/triton
# ... edit files ...
git diff > ../../triton-patches/<name>.patch
git checkout .          # leave the submodule clean
cd ../..
git add triton-patches/<name>.patch
git commit -m "[TRITON-PATCH] <description>"
```

The wrapper applies patches in lexicographic order (`*.patch`), so prefix with a number if ordering matters.
