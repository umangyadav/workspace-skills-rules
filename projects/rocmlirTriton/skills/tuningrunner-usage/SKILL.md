---
name: tuningrunner-usage
description: >-
  Tune rocmlirTriton kernels with tuningRunner.py. Finds the best perfConfig per
  kernel config and writes a tuning DB. Use when asked to tune kernels, create
  tuning databases, or optimize kernel configurations.
---

# tuningRunner.py Usage

Source: `mlir/utils/performance/tuningRunner.py`. After tuning, use the output TSV with `perfRunner.py` for benchmarking (see `skills/perfrunner-usage/SKILL.md`). Run `python3 tuningRunner.py --help` for the up-to-date flag reference.

**Important**: Ensure no other processes are using the GPU during tuning. Shared GPU usage causes noisy and unreliable results. Check with `rocm-smi` or `fuser /dev/kfd` before starting. To pin tuning to a specific GPU, use `ROCR_VISIBLE_DEVICES`/`HIP_VISIBLE_DEVICES` -- the script itself has no `--gpus` flag and is single-GPU per invocation:

```bash
ROCR_VISIBLE_DEVICES=0 python3 tuningRunner.py --op gemm -c <configs>
```

## Config source

- `-c` / `--configs_file` -- file of configurations. The script's hard-coded default points at `mlir/utils/jenkins/performance/configs/tier1-conv-configs`, which **does not exist** -- the actual configs live under `mlir/utils/performance/configs/`. Always pass `-c` explicitly, e.g. `-c mlir/utils/performance/configs/tier1-gemm-configs`.
- `--config <STR ...>` -- one or more inline config strings to test instead of a file (`nargs='*'`). For GEMM, the string **must** include all of `-t`, `-out_datatype`, `-transA`, `-transB`, `-g`, `-m`, `-k`, `-n` -- otherwise `perfRunner.GemmConfig.from_command_line()` raises `ValueError: Incomplete GEMM configuration`.
- `--test_dir` -- fusion E2E tests directory. Default `../mlir/test/fusion/resnet50-e2e` only resolves when run from the `build/` directory. From any other CWD, pass an absolute or repo-rooted path (the actual source is `mlir/test/fusion/resnet50-e2e`). Used only when `--op fusion`.

## Operation

`--op` / `--operation`: `conv` (default), `gemm`, `fusion`, `attention`, `gemm_gemm`, `conv_gemm`

## Key flags (from `tuningRunner.py --help`)

| Flag | Default | Purpose |
|------|---------|---------|
| `-o` / `--output` | `tuning_results_local.tsv` | Output TSV (appends to existing file) |
| `--mlir-build-dir` | auto (`find_mlir_build_dir`) | rocmlirTriton build dir |
| `--rocmlir_gen_flags` | unset | Extra flags forwarded to `rocmlir-gen` (note: underscore, not dash) |
| `--tuning-space` | `full` | `quick`, `full`, `greedy`, `exhaustive` |
| `--disable-verify-winning-config` / `--no-disable-verify-winning-config` | `False` | When set, skip CPU-reference verification of the winning config (`rocmlir-gen -pv`) |
| `--verify-all-perfconfigs` | off | Compile and verify *every* applicable perf-config, not just the winner. Incompatible with `--disable-verify-winning-config=True` |
| `--data-type` | `f32 f16 i8` | Force a set of dtypes. Choices: `f32`, `f16`, `bf16`, `i8`, `i8_i32`, `i8_i8`, `fp8`, `fp8_f32`, `fp8_fp8`, `f4E2M1FN` |
| `--scale-type` | unset | Force scale types for scaled GEMM (`-scaledGemm` configs only): `f32`, `f8E8M0FNU` |
| `--tflops` | off | Append a `TFlops` column to the output TSV |
| `--compact-print` | off | Print info only when the winning config changes |
| `--abort-on-error` | off | Abort tuning on first error (used in CI) |
| `--debug` / `-d` | off | Verbose debug output; also writes a `{output}.debug` TSV |
| `--quiet` / `-q` | off | Quiet mode (suppress per-test output) |

There is **no** `--gpus`, `--num-cpus`, `--retune`, `--retry`, `--timeout`, `--wait-for-compiles`, `--status`/`-s`, `-v`, or `--verify-mode` flag. The previous version of this skill listed several of those; they were never implemented in this fork.

## Output TSV format

Header columns (printed once at the top of `--output`):

```
# arch    numCUs    numChiplets    testVector    perfConfig (<tuning-space>)
```

`<tuning-space>` is the value passed to `--tuning-space` (e.g. `perfConfig (quick)`). When `--tflops` is set, an additional `TFlops` column is appended. When `--debug` is set, a parallel `{output}.debug` TSV records every tested perf-config (not just winners).

## Examples

Run from the rocmlirTriton `build/` directory so the script's default `--test_dir`/`find_mlir_build_dir()` resolve correctly:

```bash
python3 ../mlir/utils/performance/tuningRunner.py --op gemm \
  -c ../mlir/utils/performance/configs/tier1-gemm-configs -o tuning_db.tsv
python3 ../mlir/utils/performance/tuningRunner.py --op gemm \
  --config "-t f32 -out_datatype f32 -transA false -transB false -g 3 -m 1024 -k 769 -n 512"
python3 ../mlir/utils/performance/tuningRunner.py --op conv \
  -c ../mlir/utils/performance/configs/tier1-conv-configs --tuning-space quick
python3 ../mlir/utils/performance/tuningRunner.py --op fusion --test_dir ../mlir/test/fusion/resnet50-e2e
python3 ../mlir/utils/performance/tuningRunner.py --op gemm \
  -c ../mlir/utils/performance/configs/tier1-gemm-configs --tflops --abort-on-error
ROCR_VISIBLE_DEVICES=2 python3 ../mlir/utils/performance/tuningRunner.py --op gemm \
  -c ../mlir/utils/performance/configs/tier1-gemm-configs -o gpu2.tsv
```
