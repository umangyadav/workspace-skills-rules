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

## Step 1: Generate kernel

```bash
rocmlir-gen --operation gemm --arch gfx942 -t f16 -m 4096 -k 4096 -n 4096 -ph -pv | \
  rocmlir-driver -c > kernel.mlir
```

## Step 2a: Profile with rocprofv3 (quick)

```bash
rocprofv3 --kernel-trace --stats -f csv -o results -- \
  mlir-runner kernel.mlir --shared-libs=... --entry-point-result=void
```

- PMC counters: use `rocmlir_metrics.txt` for LDS bank conflict (`pmc: LDSBankConflict`)
- Output: `results.csv` (timing), `results_kernel_stats.csv` (aggregates)

## Step 2b: Profile with rocprof-compute (comprehensive)

```bash
rocprof-compute profile -n my_kernel -- \
  mlir-runner kernel.mlir --shared-libs=... --entry-point-result=void
```

- Filter: `-k <kernel>`, `-b <block>` (SQ, LDS, TCC, etc.)
- List metrics: `rocprof-compute --list-metrics gfx942`

## Step 3: Analyze

```bash
# rocprof-compute CLI analysis
rocprof-compute analyze -p ./workloads/my_kernel/<arch>/

# Interactive modes
rocprof-compute analyze -p ... --gui   # GUI
rocprof-compute analyze -p ... --tui   # Terminal UI
```

## Step 4: Identify bottlenecks

| Bottleneck | What to check |
|-----------|---------------|
| **Compute bound** | SQ occupancy, VALU/MFMA utilization, wavefront stalls |
| **Memory bound** | L2 (TCC) hit rate, HBM bandwidth, LDS bank conflicts |
| **Latency bound** | Instruction fetch stalls, barrier waits, dependency stalls |

Map findings to rocMLIR tuning: block size, grid size, pipeline depth, direct-to-LDS.

## Integration with perfRunner.py

- `--use-rocprof` flag uses rocprofv3 for benchmarking
- `rocmlir_metrics.txt` defines PMC counters collected
- LDSBankConflict: 0% optimal, 100% bad
