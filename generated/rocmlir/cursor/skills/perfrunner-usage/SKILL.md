---
name: perfrunner-usage
description: >-
  Run performance benchmarks with perfRunner.py. Covers all operations,
  modes, and external baselines. Use when asked to run benchmarks, compare
  MLIR vs MIOpen/hipBLASLt, or measure kernel performance.
---

# perfRunner.py Usage

Source: `mlir/utils/performance/perfRunner.py`. Run `python3 perfRunner.py --help` for the full and up-to-date flag reference.

**Important**: Ensure no other processes are using the GPUs during benchmarking. Shared GPU usage causes noisy and unreliable results. Check with `rocm-smi` or `fuser /dev/kfd` before starting. Use `ROCR_VISIBLE_DEVICES` to target a specific GPU:

```bash
ROCR_VISIBLE_DEVICES=0 python3 perfRunner.py --op gemm --batch_all -c <configs> -t mlir_tuning.tsv
```

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

- `-c` / `--configs_file` -- config file (default: `tier1-conv-configs`)
- `-o` -- output file name (default: `{chip}_perf.{date}`)
- `-t` / `--tuning_db` -- tuning DB TSV for "tuned" column
- `-qt` / `--quick_tuning_db` -- quick tuning DB
- `--test_dir` -- test directory for fusion mode (default: `../mlir/test/fusion/resnet50-e2e`)
- `--mlir-build-dir` -- build dir (auto-detected)
- `--external-gemm-library` -- `hipBLASLt` (default) or `CK`
- `--data-type` -- force types: `f32`, `f16`, `i8`, `i8_i32`, `i8_i8`, `fp8`, `fp8_fp8`, `fp8_f32`
- `--scale-type` -- force scale types for scaled GEMM: `f32`, `f8E8M0FNU`
- `--rocmlir_gen_flags` -- pass extra flags to rocmlir-gen to toggle features
- `--use-rocprof` -- use rocprofv3 instead of tuning driver

## Typical workflow

Tune first with `tuningRunner.py` (see `skills/tuningrunner-usage/SKILL.md`), then benchmark with the tuning database:

```bash
# 1. Tune configs
python3 tuningRunner.py --operation gemm --configs-file <configs> --output mlir_tuning.tsv

# 2. Benchmark with tuning DB
python3 perfRunner.py --op gemm --batch_all -c <configs> -t mlir_tuning.tsv
```

## Examples

```bash
python3 perfRunner.py --batch_all -t mlir_tuning.tsv                    # conv vs MIOpen with tuning DB
python3 perfRunner.py --op gemm --batch_all -t mlir_tuning.tsv          # GEMM vs hipBLASLt with tuning DB
python3 perfRunner.py --op gemm --external-gemm-library CK -t mlir_tuning.tsv
python3 perfRunner.py --op fusion --test_dir ../mlir/test/fusion/resnet50-e2e -t tuning_fusion.tsv

# Single config (no tuning DB needed)
python3 perfRunner.py --op gemm -- -t f32 -transA true -transB true -g 1 -m 1024 -k 769 -n 512
```

## External baselines

- Conv: MIOpen (`/opt/rocm/bin/MIOpenDriver`)
- GEMM: hipBLASLt (`hipblaslt-benchmark-driver`) or CK (`ck-gemm-benchmark-driver`)

Verify external baselines exist before running `--batch_all` or `--batch_external`:

```bash
which MIOpenDriver               # conv baseline (from ROCm install)
ls build/bin/hipblaslt-benchmark-driver  # gemm baseline (built from source)
ls build/bin/ck-gemm-benchmark-driver    # CK baseline (if using --external-gemm-library CK)
```

## Build for benchmarking

```bash
cmake ... -DROCMLIR_ENABLE_BENCHMARKS=hipblaslt  # or 'ck' or 'all'
ninja ci-performance-scripts hipblaslt-benchmark-driver
# For CK baseline:
# cmake ... -DROCMLIR_ENABLE_BENCHMARKS=ck
# ninja ci-performance-scripts ck-benchmark-driver
```

After modifying `perfRunner.py` source, rebuild with `ninja ci-performance-scripts` to update the installed copy in the build directory.
