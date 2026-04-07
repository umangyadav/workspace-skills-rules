# rocMLIR CLI Tools

## rocmlir-gen -- generate MLIR from problem specs

Key flags: `-operation` (conv/gemm/attention/gemm_gemm/conv_gemm), `-arch`, `-t` (dtype), `-m/-k/-n` (GEMM dims), `-g` (groups), `-ph` (host harness), `-pv` (validate), `-pr` (print results), `-perf_config`, `-emit-tuning-key`

Conv: `-fil_layout`, `-in_layout`, `-out_layout`, `-batchsize`, `-in_channels`, `-out_channels`, `-fil_h/w`, padding/strides/dilations

Features: `-mfma`, `-wmma`, `-dot`, `-atomic_add` (each: `infer`/`on`/`off`)

## rocmlir-driver -- run lowering pipelines

- `-kernel-pipeline`: `applicability`, `migraphx`, `highlevel`, `gpu`, `rocdl`, `binary`, `full` (=`gpu,binary`)
- `-host-pipeline`: `migraphx`, `highlevel`, `mhal`, `runner`
- `-c`: shorthand for `-kernel-pipeline=full -host-pipeline=runner`
- `-targets`: GPU targets; `-verify-passes`; `-dump-pipelines`

## rocmlir-opt -- MLIR optimizer

Standard `mlir-opt` interface with all Rock/MIGraphX passes registered.

## rocmlir-tuning-driver -- JIT benchmark

`-tuning-space` (quick/full/greedy/exhaustive), `-num-iterations`, `-warmup-iterations`, `-benchmark-config`, `-show-all-measurements`

## Common pipelines

```bash
# Smoke test
rocmlir-gen --arch gfx942 -p | rocmlir-opt

# Full lowering + run
rocmlir-gen --arch gfx942 -ph -pv | rocmlir-driver -c | mlir-runner --shared-libs=...

# Tuning
rocmlir-gen --arch gfx942 --perf_config= | rocmlir-tuning-driver -tuning-space full

# Kernel to assembly
rocmlir-gen ... | rocmlir-driver -kernel-pipeline=gpu,rocdl --arch=gfx942 | \
  rocmlir-translate -gpu-module-to-rocdlir | opt -O3 | llc -mcpu=gfx942
```
