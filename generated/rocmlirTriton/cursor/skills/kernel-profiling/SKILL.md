---
name: kernel-profiling
description: >-
  Profile and analyze rocmlirTriton kernel performance using rocprofv3 and
  rocprof-compute. Identifies bottlenecks and maps to tuning parameters. Use
  when asked to profile a kernel, analyze bottlenecks, or optimize kernel
  performance.
---

# Kernel Profiling

## Tools

- **rocprofv3** (`/opt/rocm/bin/rocprofv3`): low-level GPU profiler for timing and HW counters
- **rocprof-compute**: comprehensive analysis with structured bottleneck reports

Official docs: [Using rocprofv3](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-rocprofv3.html) -- refer here for installation, dependencies, full CLI options, and output formats.

## Step 0: Verify installation

```bash
rocprofv3 --version
rocprof-compute --version
rocminfo | grep gfx
```

- **rocprofv3**: included with ROCm. If missing, check ROCm installation and ensure `/opt/rocm/bin` is in `PATH`.
- **rocprof-compute**: included with ROCm >= 6.2. For older ROCm or custom installs, see [installation docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/install/core-install.html).
- **rocminfo**: verifies GPU is visible.

## Step 1: Generate kernel

The runtime libs come from Triton's LLVM build under `external/triton/llvm-project/build/`:

```bash
SHARED_LIBS="external/triton/llvm-project/build/lib/libmlir_rocm_runtime.so,build/lib/libconv-validation-wrappers.so,external/triton/llvm-project/build/lib/libmlir_runner_utils.so,external/triton/llvm-project/build/lib/libmlir_c_runner_utils.so"

build/bin/rocmlir-gen --operation gemm --arch gfx942 -t f16 -m 4096 -k 4096 -n 4096 -ph | \
  build/bin/rocmlir-driver -c > kernel.mlir
```

## Step 2a: Profile with rocprofv3 (quick)

```bash
rocprofv3 --kernel-trace --stats -f csv -o results -- \
  external/triton/llvm-project/build/bin/mlir-runner kernel.mlir \
    --shared-libs=$SHARED_LIBS --entry-point-result=void
```

- PMC counters: use `mlir/utils/performance/rocmlir_metrics.txt` for LDS bank conflict (`pmc: LDSBankConflict`)
- Output: `results.csv` (timing), `results_kernel_stats.csv` (aggregates)

## Step 2b: Profile with ROCm Compute Profiler (comprehensive)

[ROCm Compute Profiler](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/what-is-rocprof-compute.html) provides kernel-level profiling with HW counters, Speed-of-Light evaluations, and roofline analysis. See [profiling docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/profile/mode.html).

```bash
rocprof-compute profile -n my_kernel -- \
  external/triton/llvm-project/build/bin/mlir-runner kernel.mlir \
    --shared-libs=$SHARED_LIBS --entry-point-result=void
```

Filtering: `-k <kernel>`, `-b <block>` (SQ, LDS, TCC, etc.), `--gpu-id`. See [filtering docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/profile/mode.html#filtering).

## Step 3: Analyze

```bash
rocprof-compute analyze -p ./workloads/my_kernel/<arch>/
rocprof-compute analyze -p ... --gui   # Standalone GUI
```

Features: Speed-of-Light analysis, memory chart, roofline, [baseline comparisons](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/analyze/cli.html#analysis-baseline-comparison).

## Step 4: Identify bottlenecks

| Bottleneck | What to check |
|-----------|---------------|
| **Compute bound** | SQ occupancy, VALU/MFMA utilization, wavefront stalls |
| **Memory bound** | L2 (TCC) hit rate, HBM bandwidth, LDS bank conflicts |
| **Latency bound** | Instruction fetch stalls, barrier waits, dependency stalls |

For the full list of available counters and derived metrics, run `rocprofv3 --list-avail` or see [MI200 performance counters and metrics](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-rocprofv3.html#kernel-counter-collection). Extra counters can be defined via YAML files with `--extra-counters`.

Map findings to rocmlirTriton tuning parameters defined in `mlir/include/mlir/Dialect/Rock/IR/RockAttrDefs.td` (see also `RockTuningParamAttrInterface.td` and `RockAccelTuningParamAttrInterface.td`). Triton-specific scheduling knobs live on the Triton side (TTGIR pass options); when needed, follow the Pipelines.cpp wiring back to the corresponding pass.

## Thread tracing with rocprof-compute-viewer

Thread traces provide instruction-level visibility. See [official thread trace docs](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html).

### Prerequisites

1. ROCm 7.2+ with aqlprofile and rocprof-trace-decoder ([prerequisites](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#prerequisites))
2. Install [rocprof-compute-viewer](https://github.com/ROCm/rocprof-compute-viewer/releases) for visualization

```bash
ls /opt/rocm/lib/libaqlprofile*.so
ls /opt/rocm/lib/librocprof-trace-decoder*.so
rocprofv3 --version
```

### Collect traces

Default collection:

```bash
rocprofv3 --att -d att_dump -- <application>
```

Input file for fine-grained control:

```json
{
    "jobs": [
        {
            "advanced_thread_trace": true,
            "att_target_cu": 1,
            "att_shader_engine_mask": "0x1",
            "att_simd_select": "0xF",
            "att_buffer_size": "0x6000000"
        }
    ]
}
```

```bash
rocprofv3 --att -i att.json -d att_dump -- <application>
rocprofv3 --att --att-activity 8 -d att_dump -- <application>   # AMD Instinct
```

Key parameters: `--att-target-cu`, `--att-shader-engine-mask`, `--att-simd-select`, `--att-buffer-size`, `--kernel-include-regex`, `--kernel-iteration-range`. See [full parameter table](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#rocprofv3-parameters-for-thread-tracing).

### Using with rocmlirTriton

Create a `run.sh` with full absolute paths:

```bash
#!/bin/bash
<rocmlirTriton>/build/bin/rocmlir-gen --operation=gemm -m 16384 -n 16384 -k 384 -g 1 --arch <arch> | \
  <rocmlirTriton>/build/bin/rocmlir-gen -ph - | \
  <rocmlirTriton>/build/bin/rocmlir-driver -c --arch <arch> | \
  <rocmlirTriton>/mlir/utils/widgets/rocm-run
```

```bash
chmod +x run.sh
rocprofv3 --att -i att.json -d att_dump -- $(pwd)/run.sh
```

### Output files

- `stats_*.csv` -- instruction latency summary (hitcount, latency, stalls, idle cycles)
- `ui_output_agent_*_dispatch_*/` -- open in rocprof-compute-viewer
- `.att` / `.out` -- raw trace data and code object binaries

### Troubleshooting

- **Empty stats CSV**: kernel may not launch enough waves for `att-target-cu`; widen `att-shader-engine-mask`
- **File not found**: use full absolute paths in `run.sh`
- **Data lost warnings**: reduce `att-perfcounter-ctrl` or increase `att-buffer-size`
- See [official troubleshooting](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#troubleshooting)

## Integration with perfRunner.py

- `--use-rocprof` flag uses rocprofv3 for benchmarking
- `mlir/utils/performance/rocmlir_metrics.txt` defines the PMC counters collected
- LDSBankConflict: 0% optimal, 100% bad
