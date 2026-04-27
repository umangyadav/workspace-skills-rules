---
name: perfrunner-usage
description: >-
  Run performance benchmarks with perfRunner.py for rocmlirTriton. Covers all
  operations, modes, and external baselines. Use when asked to run benchmarks,
  compare MLIR vs MIOpen/hipBLASLt, or measure kernel performance.
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

- `-c` / `--configs_file` -- config file. The script's hard-coded default for conv (`mlir/utils/jenkins/performance/configs/tier1-conv-configs`) is **stale**; the actual configs live under `mlir/utils/performance/configs/`. Pass `-c` explicitly.
- `-o` -- output file name (default: `{chip}_perf.{date}`)
- `-t` / `--tuning_db` -- tuning DB TSV for "tuned" column
- `-qt` / `--quick_tuning_db` -- quick tuning DB
- `--test_dir` -- fusion-mode test directory. Default `../mlir/test/fusion/resnet50-e2e` only resolves when run from `build/`; from any other CWD pass an absolute or repo-rooted path (`mlir/test/fusion/resnet50-e2e`).
- `--mlir-build-dir` -- build dir (auto-detected)
- `--external-gemm-library` -- `hipBLASLt` (default) or `CK`
- `--data-type` -- force types: `f32`, `f16`, `i8`, `i8_i32`, `i8_i8`, `fp8`, `fp8_fp8`, `fp8_f32`
- `--scale-type` -- force scale types for scaled GEMM: `f32`, `f8E8M0FNU`
- `--rocmlir_gen_flags` -- pass extra flags to `rocmlir-gen` to toggle features
- `--use-rocprof` -- use rocprofv3 instead of tuning driver

## Typical workflow

Tune first with `tuningRunner.py` (see `skills/tuningrunner-usage/SKILL.md`), then benchmark with the tuning database:

```bash
# 1. Tune configs (note: --configs_file uses an underscore, not a dash)
python3 tuningRunner.py --operation gemm --configs_file <configs> --output mlir_tuning.tsv

# 2. Benchmark with tuning DB
python3 perfRunner.py --op gemm --batch_all -c <configs> -t mlir_tuning.tsv
```

## Examples

Run from the `build/` directory so default paths (`--test_dir`, `find_mlir_build_dir()`) resolve. Always pass `-c` explicitly because the script's default `-c` points at a stale `mlir/utils/jenkins/performance/configs/...` path and otherwise fails with `FileNotFoundError`:

```bash
# Conv vs MIOpen
python3 ../mlir/utils/performance/perfRunner.py --batch_all \
  -c ../mlir/utils/performance/configs/tier1-conv-configs -t mlir_tuning.tsv

# GEMM vs hipBLASLt
python3 ../mlir/utils/performance/perfRunner.py --op gemm --batch_all \
  -c ../mlir/utils/performance/configs/tier1-gemm-configs -t mlir_tuning.tsv

# GEMM vs CK (an explicit mode is required: --batch_all, --batch_external, ...)
python3 ../mlir/utils/performance/perfRunner.py --op gemm --batch_all \
  --external-gemm-library CK \
  -c ../mlir/utils/performance/configs/tier1-gemm-configs -t mlir_tuning.tsv

# Fusion (--test_dir replaces -c for fusion mode)
python3 ../mlir/utils/performance/perfRunner.py --op fusion \
  --test_dir ../mlir/test/fusion/resnet50-e2e -t tuning_fusion.tsv

# Single inline GEMM config: must include -t, -out_datatype, -transA, -transB, -g, -m, -k, -n
# (otherwise GemmConfiguration.from_command_line() raises 'Incomplete GEMM configuration').
python3 ../mlir/utils/performance/perfRunner.py --op gemm -- \
  -t f32 -out_datatype f32 -transA true -transB true -g 1 -m 1024 -k 769 -n 512
```

## External baselines

- Conv: MIOpen (`/opt/rocm/bin/MIOpenDriver`)
- GEMM: hipBLASLt (`hipblaslt-benchmark-driver`) or CK (`ck-gemm-benchmark-driver`)

Verify external baselines exist before running `--batch_all` or `--batch_external`:

```bash
which MIOpenDriver
ls build/bin/hipblaslt-benchmark-driver
ls build/bin/ck-gemm-benchmark-driver
```

## Build for benchmarking

```bash
cmake ... -DROCMLIR_ENABLE_BENCHMARKS=hipblaslt   # or 'ck' or 'all'
ninja ci-performance-scripts hipblaslt-benchmark-driver
# For CK baseline (target name uses '-gemm-', source dir is `ck-benchmark-driver/`):
# cmake ... -DROCMLIR_ENABLE_BENCHMARKS=ck
# ninja ci-performance-scripts ck-gemm-benchmark-driver
```

After modifying `perfRunner.py`, rebuild with `ninja ci-performance-scripts` to update the installed copy in the build directory.
