# rocMLIR Project Overview

rocMLIR is an MLIR-based convolution, GEMM, attention, and fused kernel generator targeting AMD GPUs (ROCm).

## Key facts

- Primary consumer: [MIGraphX](https://github.com/ROCm/AMDMIGraphX) via `libRockCompiler` fat library
- Part of the [ROCm](https://github.com/ROCm) ecosystem (separate repo, not part of [rocm-libraries](https://github.com/ROCm/rocm-libraries))
- License: Apache 2.0 with LLVM Exceptions

## Source layout

- `mlir/` -- all rocMLIR sources (edit here)
- `external/llvm-project/` -- vendored LLVM/MLIR (rarely needs changes; use `[EXTERNAL]` commit prefix when modifying)
- `external/mlir-hal/` -- vendored MHAL dependency (being decoupled; see PR #2333, #2325; use `[EXTERNAL]` commit prefix when modifying)

## Tools

- `rocmlir-gen` -- generate Rock dialect kernels and driver code to run/validate kernel output
- `rocmlir-driver` -- lower and run kernels through pipelines (`-c` for default full pipeline)
- `rocmlir-opt` -- MLIR optimizer with Rock passes
- `rocmlir-tuning-driver` -- tune kernels by sweeping perf configs and selecting the best

## Build

```
cmake -G Ninja .. -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++
ninja check-rocmlir  # builds everything and runs all tests
```

## Commit messages

- Jira: `[AIROCMLIR-NNN] Description (#PR)`
- Plain: `Fix/Add/Update description (#PR)`
- Non-functional: `[NFC] Description`
- External: `[EXTERNAL] Description`
- Release backport: `[BACKPORT] Description (#PR)` (cherry-picks to release branches)

## Confidentiality

This is a public repo. Never reference unreleased AMD hardware codenames, unannounced chip IDs, NDA-protected features, or internal project names. Use only publicly released `gfx*` identifiers.

## Downstream impact

Breaking changes to Rock dialect IR or C API require coordination with MIGraphX. Always keep `librockcompiler_deps.cmake` in sync.
