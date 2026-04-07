---
name: perfrunner-usage
description: >-
  Run performance benchmarks with perfRunner.py. Covers all operations,
  modes, and external baselines. Use when asked to run benchmarks, compare
  MLIR vs MIOpen/hipBLASLt, or measure kernel performance.
---

# perfRunner.py Usage

## Operations (`--op`)

`conv` (default), `gemm`, `fusion`, `attention`, `gemm_gemm`, `conv_gemm`

## Modes (mutually exclusive)

| Flag | Behavior |
|------|----------|
| (no args) / `--batch_all` | MLIR + external baseline, writes `{chip}_mlir_vs_{lib}_perf.csv` |
| `-b` / `--batch_mlir` | MLIR-only batch from config file |
| `--batch_external` | External library only |
| `--external` | Single config external |
| `--tuning` | Tune MIOpen kernels (conv only) |

## Key flags

- `-c` -- config file (default: `tier1-conv-configs`)
- `-t` / `--tuning_db` -- tuning DB TSV for "tuned" column
- `-qt` / `--quick_tuning_db` -- quick tuning DB
- `--mlir-build-dir` -- build dir (auto-detected)
- `--external-gemm-library` -- `hipBLASLt` (default) or `CK`
- `--data-type` -- force types: `f32`, `f16`, `i8`, `fp8`, etc.
- `--use-rocprof` -- use rocprofv3 instead of tuning driver

## Examples

```bash
python3 perfRunner.py                                    # conv vs MIOpen
python3 perfRunner.py --batch_all -t tuning_db.tsv       # with tuned column
python3 perfRunner.py --op gemm --batch_all              # GEMM vs hipBLASLt
python3 perfRunner.py --op gemm --external-gemm-library CK
python3 perfRunner.py --op fusion --test_dir ../mlir/test/fusion/resnet50-e2e -t db.tsv

# Single config
python3 perfRunner.py --op gemm -- -t f32 -transA true -transB true -g 1 -m 1024 -k 769 -n 512
```

## External baselines

- Conv: MIOpen (`/opt/rocm/bin/MIOpenDriver`)
- GEMM: hipBLASLt (`hipblaslt-benchmark-driver`) or CK (`ck-gemm-benchmark-driver`)

## Build for benchmarking

```bash
cmake ... -DROCMLIR_ENABLE_BENCHMARKS=hipblaslt
ninja ci-performance-scripts hipblaslt-benchmark-driver
```
