<!-- applyTo: mlir/tools/**/*.cpp -->

# rocmlirTriton CLI Tools

Binaries live in `build/bin/`. The MLIR runtime libraries used by `mlir-runner` come from `external/triton/llvm-project/build/lib/`.

## rocmlir-gen -- generate MLIR from problem specs

Key flags: `-operation` (`conv`/`gemm`/`attention`/`gemm_gemm`/`conv_gemm`), `-arch`, `-num_cu`, `-num_chiplets`, `-t` (input dtype), `-out_datatype`, `-m`/`-k`/`-n` (GEMM dims), `-g` (groups), `-ph` (host harness), `-pv` (validate), `-pr` (print results), `-perf_config`, `-emit-tuning-key`

Conv: `-fil_layout`, `-in_layout`, `-out_layout`, `-batchsize`, `-in_channels`, `-out_channels`, `-fil_h/w`, padding/strides/dilations

Attention: `-seq_len_q`, `-seq_len_k`, `-head_dim_qk`, `-head_dim_v`, `-num_heads_q`, `-num_heads_kv`, `--causal`

Scaled GEMM: `-scaledGemm`, `-quantBlockSize`, `-scale_a_dtype`, `-scale_b_dtype`, e.g. `-t f8E4M3FN -scale_a_dtype f8E8M0FNU` (gfx950 only -- see `docs/scaled_gemm.md`)

Features: `-mfma`, `-wmma`, `-dot`, `-atomic_add` (each: `infer`/`on`/`off`)

## rocmlir-driver -- run lowering pipelines

- `-kernel-pipeline`: `applicability`, `migraphx`, `highlevel`, `gpu`, `rocdl`, `binary`, `full` (`gpu,binary`)
- `-host-pipeline`: `migraphx`, `highlevel`, `runner` (mhal is currently disabled)
- `-c`: shorthand for `-kernel-pipeline=full -host-pipeline=runner`
- `-targets`, `-verify-passes`, `-dump-pipelines`

## rocmlir-opt -- MLIR optimizer

Standard `mlir-opt` interface with all Rock + MIGraphX + Triton-related passes registered via `InitRocMLIRPasses.h`.

## rocmlir-translate -- translation entry points

- `--gpu-module-to-rocdir`
- `--triton-to-hsaco` (the C++ replication of Triton's `make_hsaco`)

## rocmlir-tuning-driver -- JIT benchmark

`--tuning-space` (`quick`/`full`/`greedy`/`exhaustive`), `--num-iterations`, `--warmup-iterations`, `--sleep-us`, `--use-median`, `--show-all-measurements`

## rocmlir-lsp-server

LSP server that registers Rock/MIGraphX dialects for editor integration with `.mlir` files.

## Python performance/tuning scripts (`mlir/utils/performance/`)

- `perfRunner.py` -- main benchmark runner (gemm/conv/attention/fusion across configs)
- `tuningRunner.py` -- tuning orchestrator over perf-config space
- `parameterSweeps.py` -- parameter sweep driver for exhaustive tuning
- `attentionSweeps.py` -- attention-specific sweeps
- `perfRegressionReport.py`, `createPerformanceReports.py`, `createFusionPerformanceReports.py` -- report generators
- `reportUtils.py`, `perfCommonUtils.py` -- shared utilities
- `handleNewConfigs.py`, `convertRocBlasToPerfRunner.py` -- config helpers
- Configs: `configs/tier1-{gemm,conv,attention,gemmgemm}-configs`, `problem-config-tier-1-models`, `bert-configs-raw`

## Widgets (`mlir/utils/widgets/`)

- `rocm-run` / `xmir-run` -- shell wrappers around `mlir-runner` with the right `--shared-libs`

## Common pipelines

```bash
# Smoke
rocmlir-gen --arch gfx942 -p | rocmlir-opt

# Full lowering + validate (single op), Triton mlir-runner
rocmlir-gen --arch gfx942 -ph -pv | rocmlir-driver -c | \
  external/triton/llvm-project/build/bin/mlir-runner \
    --shared-libs=external/triton/llvm-project/build/lib/libmlir_rocm_runtime.so,build/lib/libconv-validation-wrappers.so,external/triton/llvm-project/build/lib/libmlir_runner_utils.so,external/triton/llvm-project/build/lib/libmlir_c_runner_utils.so \
    --entry-point-result=void

# Tuning a single config
rocmlir-gen --arch gfx942 --perf_config= | rocmlir-tuning-driver --tuning-space=quick

# Fusion E2E from .mlir input
sed -e "s/gfx1100/$ARCH/g" -e "s/rock.num_cu = 96/rock.num_cu = $NUM_CU/g" fusion_with_host.mlir | \
  rocmlir-driver -c | mlir-runner --shared-libs=... --entry-point-result=void
```

## Tuning + benchmarking

```bash
# Tune
python3 tuningRunner.py --abort-on-error --operation gemm \
  --configs-file=configs/tier1-gemm-configs --output=mlir_tuning_${CHIP}.tsv

# Benchmark with the tuning DB
python3 perfRunner.py --op=gemm --batch_all \
  --configs_file=configs/tier1-gemm-configs \
  --tuning_db=mlir_tuning_${CHIP}.tsv

# Multi-GPU tuning
python3 tuningRunner.py --operation gemm --configs-file=configs/tier1-gemm-configs --gpus 0 1 2 3
```

## Parameter sweeps

```bash
python3 parameterSweeps.py -j <num_workers> <CONFIG> --log-failures
```

All Python scripts are in `mlir/utils/performance/`. Run `python3 <script>.py --help` for full flag reference.
