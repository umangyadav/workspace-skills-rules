---
name: tuningrunner-usage
description: >-
  Tune rocMLIR kernels with tuningRunner.py. Finds best perfConfig per kernel
  config and writes tuning DB. Use when asked to tune kernels, create tuning
  databases, or optimize kernel configurations.
---

# tuningRunner.py Usage

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
| `--gpus` | all | Select GPU IDs for parallel tuning |
| `--retune` | off | Ignore existing rows, retune all |
| `--retry` | none | Retry: `failed`, `timed_out`, `crashed` |
| `--timeout` | none | Per-config timeout (seconds) |
| `-s` / `--status` | off | Print pending count, no tuning |

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
