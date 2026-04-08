---
name: kernel-profiling
description: >-
  Profile and analyze rocMLIR kernel performance using rocprofv3 and
  rocprof-compute. Identifies bottlenecks and maps to tuning parameters.
  Use when asked to profile a kernel, analyze bottlenecks, or optimize
  kernel performance.
---

# Kernel Profiling

## Tools

- **rocprofv3** (`/opt/rocm/bin/rocprofv3`): low-level GPU profiler for timing and HW counters
- **rocprof-compute**: comprehensive analysis with structured bottleneck reports

Official docs: [Using rocprofv3](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-rocprofv3.html) -- refer here for installation, dependencies, full CLI options, and output formats.

## Step 0: Verify installation

Before profiling, confirm that the tools are available and the GPU is accessible:

```bash
rocprofv3 --version
rocprof-compute --version
rocminfo | grep gfx
```

- **rocprofv3**: included with ROCm. If missing, check ROCm installation and ensure `/opt/rocm/bin` is in `PATH`.
- **rocprof-compute**: included with ROCm >= 6.2. For older ROCm or custom installs, requires Python >= 3.8, CMake >= 3.19, and additional Python dependencies. See [installation docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/install/core-install.html) for source build and `pip install -r requirements.txt`.
- **rocminfo**: verifies GPU is visible. If no `gfx` output, check ROCm drivers and device permissions.

## Step 1: Generate kernel

```bash
rocmlir-gen --operation gemm --arch gfx942 -t f16 -m 4096 -k 4096 -n 4096 -ph | \
  rocmlir-driver -c > kernel.mlir
```

## Step 2a: Profile with rocprofv3 (quick)

```bash
rocprofv3 --kernel-trace --stats -f csv -o results -- \
  mlir-runner kernel.mlir --shared-libs=... --entry-point-result=void
```

- PMC counters: use `rocmlir_metrics.txt` for LDS bank conflict (`pmc: LDSBankConflict`)
- Output: `results.csv` (timing), `results_kernel_stats.csv` (aggregates)

## Step 2b: Profile with ROCm Compute Profiler (comprehensive)

[ROCm Compute Profiler](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/what-is-rocprof-compute.html) provides kernel-level profiling with hardware counter analysis, Speed-of-Light evaluations, and roofline analysis. See [profiling docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/profile/mode.html) for full options.

```bash
rocprof-compute profile -n my_kernel -- \
  mlir-runner kernel.mlir --shared-libs=... --entry-point-result=void
```

Filtering: `-k <kernel>`, `-b <block>` (SQ, LDS, TCC, etc.), `--gpu-id`. See [filtering docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/profile/mode.html#filtering).

## Step 3: Analyze

See [CLI analysis docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/analyze/cli.html) and [standalone GUI docs](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/analyze/standalone-gui.html).

```bash
rocprof-compute analyze -p ./workloads/my_kernel/<arch>/

rocprof-compute analyze -p ... --gui   # Standalone GUI
```

Features: Speed-of-Light analysis, memory chart analysis, roofline analysis, [baseline comparisons](https://rocm.docs.amd.com/projects/rocprofiler-compute/en/latest/how-to/analyze/cli.html#analysis-baseline-comparison).

## Step 4: Identify bottlenecks

| Bottleneck | What to check |
|-----------|---------------|
| **Compute bound** | SQ occupancy, VALU/MFMA utilization, wavefront stalls |
| **Memory bound** | L2 (TCC) hit rate, HBM bandwidth, LDS bank conflicts |
| **Latency bound** | Instruction fetch stalls, barrier waits, dependency stalls |

For the full list of available counters and derived metrics, run `rocprofv3 --list-avail` or see [MI200 performance counters and metrics](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-rocprofv3.html#kernel-counter-collection). Extra counters can be defined via YAML files with `--extra-counters` (see [extra counters docs](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-rocprofv3.html#extra-counters)).

Map findings to rocMLIR tuning parameters defined in `mlir/include/mlir/Dialect/Rock/IR/RockAttrDefs.td` (see also `RockTuningParamAttrInterface.td` and `RockAccelTuningParamAttrInterface.td`).

## Thread tracing with rocprof-compute-viewer

Thread traces provide instruction-level visibility into GPU kernel execution. See [official thread trace docs](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html) for full details.

### Prerequisites

1. ROCm 7.2+ with aqlprofile and rocprof-trace-decoder installed (see [prerequisites](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#prerequisites))
2. Install [rocprof-compute-viewer](https://github.com/ROCm/rocprof-compute-viewer/releases) client for visualization

Verify before tracing:

```bash
ls /opt/rocm/lib/libaqlprofile*.so
ls /opt/rocm/lib/librocprof-trace-decoder*.so
rocprofv3 --version
```

If `libaqlprofile` or `librocprof-trace-decoder` is missing, follow the [prerequisite instructions](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#prerequisites) to install them. Without these, `rocprofv3 --att` will fail with "INVALID_SHADER_DATA" or "Agent not supported".

### Collect traces with rocprofv3

Default collection:

```bash
rocprofv3 --att -d att_dump -- <application>
```

With input file for fine-grained control (see [input file format](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#using-input-file)):

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
```

For AMD Instinct, enable perfmon streaming with `--att-activity`:

```bash
rocprofv3 --att --att-activity 8 -d att_dump -- <application>
```

Key parameters: `--att-target-cu`, `--att-shader-engine-mask`, `--att-simd-select`, `--att-buffer-size`, `--kernel-include-regex`, `--kernel-iteration-range`. See [full parameter table](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#rocprofv3-parameters-for-thread-tracing).

### Using with rocMLIR

Create a `run.sh` script with full absolute paths:

```bash
#!/bin/bash
<rocMLIR>/build/bin/rocmlir-gen --operation=gemm -m 16384 -n 16384 -k 384 -g 1 --arch <arch> | \
  <rocMLIR>/build/bin/rocmlir-gen -ph - | \
  <rocMLIR>/build/bin/rocmlir-driver -c --arch <arch> | \
  <rocMLIR>/mlir/utils/widgets/rocm-run
```

Make executable and trace:

```bash
chmod +x run.sh
rocprofv3 --att -i att.json -d att_dump -- $(pwd)/run.sh
```

### Output files

- `stats_*.csv` -- instruction latency summary per kernel (hitcount, latency, stalls, idle cycles)
- `ui_output_agent_*_dispatch_*/` -- open in rocprof-compute-viewer for visualization
- `.att` / `.out` -- raw trace data and code object binaries

Download to local machine with `scp -r` and open in rocprof-compute-viewer.

### Troubleshooting

- **Empty stats CSV**: kernel may not launch enough waves to fill `att-target-cu`; try increasing waves, changing `target_cu`, or widening `att-shader-engine-mask`
- **File not found**: use full absolute paths in `run.sh`; verify `run.sh` has executable permissions
- **Data lost warnings**: reduce `att-perfcounter-ctrl` value or increase `att-buffer-size`
- See [official troubleshooting](https://rocm.docs.amd.com/projects/rocprofiler-sdk/en/latest/how-to/using-thread-trace.html#troubleshooting)

## Integration with perfRunner.py

- `--use-rocprof` flag uses rocprofv3 for benchmarking
- `rocmlir_metrics.txt` defines PMC counters collected
- LDSBankConflict: 0% optimal, 100% bad
