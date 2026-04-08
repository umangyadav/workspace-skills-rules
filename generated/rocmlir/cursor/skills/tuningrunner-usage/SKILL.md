---
name: tuningrunner-usage
description: >-
  Tune rocMLIR kernels with tuningRunner.py. Finds best perfConfig per kernel
  config and writes tuning DB. Use when asked to tune kernels, create tuning
  databases, or optimize kernel configurations.
---

# tuningRunner.py Usage

Source: `mlir/utils/performance/tuningRunner.py`. After tuning, use the output DB with `perfRunner.py` for benchmarking (see `skills/perfrunner-usage/SKILL.md`).

**Important**: Ensure no other processes are using the GPUs during tuning or benchmarking. Shared GPU usage causes noisy and unreliable results. Check with `rocm-smi` or `fuser /dev/kfd` before starting. Use `--gpus` to target specific GPUs:

```bash
python3 tuningRunner.py --op gemm -c <configs> --gpus 0
```

## Config source (exactly one required)

- `-c` / `--configs-file` -- file of configs (use `-` for stdin)
- `--config` -- single config string or `.mlir` file path
- `--test-dir` -- fusion E2E test directory (requires `--op fusion`)

## Required flag

`--op`: `conv`, `gemm`, `fusion`, `attention`, `gemm_gemm`, `conv_gemm`

## Key flags

| Flag | Default | Purpose |
|------|---------|---------|
| `-o` / `--output` | `tuning_results_local.tsv` | Output TSV (or `-` for stdout) |
| `--tuning-space` | `full` | `quick`, `full`, `greedy`, `exhaustive` |
| `--verify-mode` | `gpu` | `none`, `cpu`, `gpu` |
| `--verify-perf-configs` | off | Verify each perf config, not just the winner |
| `--gpus` | all | Select GPU IDs for parallel tuning |
| `--num-cpus` | auto | Max CPU threads for compilation |
| `--data-type` | `f32 f16 i8` | Force data types (gemm only): `f32`, `f16`, `bf16`, `i8`, `fp8`, `f4E2M1FN`, etc. |
| `--scale-type` | none | Force scale types for scaled gemm: `f32`, `f8E8M0FNU` |
| `--rocmlir-gen-flags` | none | Extra flags to pass to rocmlir-gen |
| `--retune` | off | Ignore existing rows, retune all |
| `--retry` | none | Retry: `failed`, `timed_out`, `crashed` |
| `--timeout` | none | Per-config timeout (seconds) |
| `--abort-on-error` | off | Abort tuning on first error (used in CI) |
| `--wait-for-compiles` | off | Wait for all compilations before tuning (useful for APUs) |
| `-s` / `--status` | off | Print pending count, no tuning |
| `-d` / `-v` / `-q` | normal | Debug / verbose / quiet logging |

## Output TSV format

```
# arch	numCUs	numChiplets	testVector	perfConfig	TFlops	tuningSpace	commitId	timestamp	durationSec
```

State file: `{output}.state` JSON tracks failed/timed_out/crashed for recovery.

## Examples

```bash
python3 tuningRunner.py --op gemm -c configs/tier1-gemm-configs -o tuning_db.tsv
python3 tuningRunner.py --op gemm --config "-g 3 -m 1024 -k 769 -n 512 -t f32"
python3 tuningRunner.py --op conv -c configs/tier1-conv-configs --tuning-space quick
python3 tuningRunner.py --op gemm -c configs/tier1-gemm-configs --gpus 2 3
python3 tuningRunner.py --op fusion --test-dir ../mlir/test/fusion/resnet50-e2e
cat configs.txt | python3 tuningRunner.py --op gemm -c - -o db.tsv
```
