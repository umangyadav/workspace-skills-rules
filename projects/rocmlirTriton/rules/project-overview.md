# rocmlirTriton Project Overview

rocmlirTriton is a fork/derivative of [rocMLIR](https://github.com/ROCm/rocMLIR) that lowers Rock dialect kernels (convolution, GEMM, attention, fused ops) through [OpenAI Triton](https://github.com/triton-lang/triton)'s TTIR/TTGIR/LLIR pipeline to AMD GPU code. It targets AMD hardware (ROCm).

## Key facts

- Public repository on [ROCm/rocmlirTriton](https://github.com/ROCm/rocmlirTriton)
- Primary consumer: [MIGraphX](https://github.com/ROCm/AMDMIGraphX) via the `librockCompiler` fat library
- License: Apache 2.0 with LLVM Exceptions (`LICENSE.TXT`)
- CMake project name is still `rocMLIR` (`project(rocMLIR VERSION 2.0.0 ...)`), so binaries and helper functions retain `rocmlir-*` / `add_rocmlir_*` names

## Source layout

- `mlir/` -- all rocmlirTriton sources (edit here)
- `external/triton/` -- **git submodule** of upstream Triton; brings its own `external/triton/llvm-project/` LLVM/MLIR
- `triton-patches/*.patch` -- local patches applied on top of the Triton submodule by `scripts/build-llvm.sh`
- `cmake/triton.cmake` -- wires `find_package(MLIR)` and `add_subdirectory(external/triton)` and defines `add_rocmlir_*` helpers
- `scripts/build-llvm.sh` -- wrapper that initializes submodules, applies `triton-patches/`, forces `MLIR_ENABLE_ROCM_RUNNER=ON`, and runs Triton's `build-llvm-project.sh`
- `cmake.sh` -- build helper that calls `scripts/build-llvm.sh`, configures CMake with `BUILD_FAT_LIBROCKCOMPILER=ON`, and runs Ninja
- `tests.sh` -- E2E smoke tests run end-to-end via `mlir-runner` from `external/triton/llvm-project/build/`
- `docs/` -- in-tree design docs (`bump_triton_version.md`, `scaled_gemm.md`, `cpu_validation_optimization.md`)

## Tools

- `rocmlir-gen` -- generate Rock dialect kernels and host harness
- `rocmlir-driver` -- run kernel/host pipelines (`-c` is the default full pipeline)
- `rocmlir-opt` -- MLIR optimizer with Rock + Triton passes registered
- `rocmlir-tuning-driver` -- JIT tuning harness over perf configs
- `rocmlir-translate` -- translate IR (e.g. `--gpu-module-to-rocdir`, `--triton-to-hsaco`)
- `rocmlir-lsp-server` -- LSP server for editor integration

## Build

```sh
bash cmake.sh                # default: BUILD_FAT_LIBROCKCOMPILER=ON, RelWithDebInfo, lld
bash tests.sh                # E2E smoke + targeted lit suites
```

`mlir-runner` and the `libmlir_*_runtime.so` shared libraries come from `external/triton/llvm-project/build/`, **not** from a sibling `external/llvm-project/`.

## Commit messages

- Jira: `[AIROCMLIR-NNN] Description (#PR)`
- Plain: `Fix/Add/Update description (#PR)`
- Non-functional: `[NFC] Description`
- Triton bump: `[TRITON-BUMP] Description`
- Local Triton patch update: `[TRITON-PATCH] Description`
- Release backport: `[BACKPORT] Description (#PR)`

## Confidentiality

This is a public repo. Never reference unreleased AMD hardware codenames, unannounced chip IDs, NDA-protected features, or internal project names. Use only publicly released `gfx*` identifiers.

## Downstream impact

Breaking changes to Rock dialect IR or C API require coordination with MIGraphX. Always keep `mlir/tools/rocmlir-lib/librockcompiler_deps.cmake` in sync after any dependency change (especially Triton bumps).
