<!-- applyTo: mlir/tools/**/*.cpp -->

# rocMLIR CLI Tools

## rocmlir-gen -- generate MLIR from problem specs

Key flags: `-operation` (conv/gemm/attention/gemm_gemm/conv_gemm), `-arch`, `-t` (dtype), `-m/-k/-n` (GEMM dims), `-g` (groups), `-ph` (host harness), `-pv` (validate), `-pr` (print results), `-perf_config`, `-emit-tuning-key`

Conv: `-fil_layout`, `-in_layout`, `-out_layout`, `-batchsize`, `-in_channels`, `-out_channels`, `-fil_h/w`, padding/strides/dilations

Features: `-mfma`, `-wmma`, `-dot`, `-atomic_add` (each: `infer`/`on`/`off`)

## rocmlir-driver -- run lowering pipelines

- `-kernel-pipeline`: `applicability`, `migraphx`, `highlevel`, `gpu`, `rocdl`, `binary`, `full` (=`gpu,binary`)
- `-host-pipeline`: `migraphx`, `highlevel`, `mhal` (being decoupled; see PR #2333), `runner`
- `-c`: shorthand for `-kernel-pipeline=full -host-pipeline=runner`
- `-targets`: GPU targets; `-verify-passes`; `-dump-pipelines`

## rocmlir-opt -- MLIR optimizer

Standard `mlir-opt` interface with all Rock/MIGraphX passes registered.

## rocmlir-tuning-driver -- JIT benchmark

`-tuning-space` (quick/full/greedy/exhaustive), `-num-iterations`, `-warmup-iterations`, `-benchmark-config`, `-show-all-measurements`

## Python performance/tuning scripts (`mlir/utils/performance/`)

- `perfRunner.py` -- main benchmark runner; drives rocmlir-gen + rocmlir-driver to benchmark gemm/conv/attention across configs
- `tuningRunner.py` -- tuning orchestrator; explores perf_config space, selects best configs, updates perfDB
- `parameterSweeps.py` -- parameter sweep driver for exhaustive/weekly CI tuning
- `attentionSweeps.py` -- attention-specific parameter sweeps
- `perfRegressionReport.py` -- generates perf regression reports comparing runs
- `createPerformanceReports.py` / `createFusionPerformanceReports.py` -- CI report generators
- `reportUtils.py` / `perfCommonUtils.py` -- shared utilities for reporting and perf scripts
- `handleNewConfigs.py` -- processes new tuning configs into the config database
- `convertRocBlasToPerfRunner.py` -- converts rocBLAS configs to perfRunner format
- Config files: `configs/tier1-gemm-configs`, `configs/tier1-conv-configs`, `configs/tier1-attention-configs`, `configs/tier1-gemmgemm-configs`, `problem-config-tier-1-models`, `bert-configs-raw`

## Widgets (`mlir/utils/widgets/`)

- `rocm-run` / `xmir-run` -- shell wrappers for running rocMLIR / MIGraphX IR on GPU

## Common C++ tool pipelines

```bash
# Smoke test
rocmlir-gen --arch gfx942 -p | rocmlir-opt

# Full lowering + validate (single op)
rocmlir-gen --arch gfx942 -ph -pv | rocmlir-driver -c | mlir-runner --shared-libs=...

# Tuning a single config
rocmlir-gen --arch gfx942 --perf_config= | rocmlir-tuning-driver -tuning-space full

# Kernel to assembly
rocmlir-gen ... | rocmlir-driver -kernel-pipeline=gpu,rocdl --arch=gfx942 | \
  rocmlir-translate -gpu-module-to-rocdlir | opt -O3 | llc -mcpu=gfx942
```

## Lit test pipelines (from `mlir/test/`)

```bash
# E2E test: rocmlir-gen generates + validates a kernel
rocmlir-gen --arch %arch --operation gemm -t f16 -m 1024 -k 768 -n 512 -pv | \
  rocmlir-driver -c | mlir-runner --shared-libs=... | FileCheck %s

# Fusion E2E: clone-harness → lowering → host pipeline → xmir-runner
rocmlir-gen -fut mlir_attention --arch %arch --clone-harness %s | \
  rocmlir-driver -kernel-pipeline=migraphx,highlevel -host-pipeline=migraphx,highlevel | \
  rocmlir-gen -ph -rand 1 -rand_type float -fut mlir_attention_wrapper --verifier clone - | \
  rocmlir-driver -host-pipeline mhal -kernel-pipeline full | \
  xmir-runner --shared-libs=... --entry-point-result=void | FileCheck %s

# IR verification: check pass output with FileCheck
rocmlir-gen --arch %arch ... | rocmlir-driver -arch %arch -c \
  -mlir-print-ir-after=<pass-name> 2>&1 | FileCheck %s --check-prefix=...
```

## Tuning and benchmarking pipeline

```bash
# 1. Tune gemm/conv configs → produces tuning DB (.tsv)
python3 tuningRunner.py --abort-on-error --operation gemm \
  --configs-file=<configs> --output=mlir_tuning_${CHIP}.tsv

python3 tuningRunner.py --abort-on-error --operation conv \
  --configs-file=<configs> --output=mlir_tuning_${CHIP}.tsv

# 2. Tune fusion models (resnet50, bert) → produces fusion tuning DB
python3 tuningRunner.py --abort-on-error --op fusion \
  --test-dir ../mlir/test/fusion/resnet50-e2e/ -o tuning_fusion_${CHIP}.tsv

python3 tuningRunner.py --abort-on-error --op fusion \
  --test-dir ../mlir/test/xmir/bert-torch-tosa-e2e/ -o tuning_fusion_${CHIP}.tsv

# 3. Benchmark with tuning DB
python3 perfRunner.py --op=conv --batch_all \
  --configs_file=<conv-configs> \
  --tuning_db=mlir_tuning_${CHIP}.tsv \
  --quick_tuning_db=mlir_quick_tuning_${CHIP}.tsv

python3 perfRunner.py --op=gemm --batch_all \
  --configs_file=<gemm-configs> \
  --tuning_db=mlir_tuning_${CHIP}.tsv \
  --quick_tuning_db=mlir_quick_tuning_${CHIP}.tsv

python3 perfRunner.py --op=attention -b \
  --configs_file=<attn-configs> \
  --tuning_db=mlir_tuning_${CHIP}.tsv

python3 perfRunner.py --op=fusion \
  --test_dir=mlir/test/fusion/resnet50-e2e/ \
  --tuning_db=tuning_fusion_${CHIP}.tsv

# 4. Multi-GPU tuning
python3 tuningRunner.py --operation gemm --configs-file=<configs> --gpus 0 1 2 3
```

## Parameter sweeps

```bash
# Exhaustive parameter sweeps across all tier-1 configs
python3 parameterSweeps.py -j <num_workers> <CONFIG> --log-failures
```

All Python scripts are in `mlir/utils/performance/`. Run `python <script>.py --help` for full flag reference.
