---
name: perf-reports-utils
description: >-
  Generate performance reports, regression analysis, and manage tier-1 configs.
  Use when asked to generate reports, compare performance, analyze regressions,
  or add new benchmark configs.
---

# Performance Report Scripts

## createPerformanceReports.py

Generate HTML comparing MLIR vs external library.

```bash
python3 createPerformanceReports.py <chip> [lib]
# lib: hipBLASLt (default), CK, MIOpen
```

- Reads: `{chip}_mlir_vs_{lib}_perf.csv`
- Writes: plot CSV, stats CSV, `{chip}_MLIR_vs_{lib}.html`

## createFusionPerformanceReports.py

```bash
python3 createFusionPerformanceReports.py <chip>
```

- Reads: `{chip}_{conv|gemm}_mlir_fusion_perf.csv`
- Writes: `{chip}_{conv|gemm}_fusion.html`

## perfRegressionReport.py

Compare old vs new performance.

```bash
python3 perfRegressionReport.py <chip> [old_csv] [new_csv] [output_html]
```

- Defaults: `./oldData/{chip}_mlir_vs_miopen_perf.csv` vs `./{chip}_mlir_vs_miopen_perf.csv`
- Writes: `{chip}_MLIR_Performance_Changes.html`

## parameterSweeps.py

Correctness sweeps (not performance benchmarks).

```bash
python3 parameterSweeps.py <config>
# config: conv_structure, perf_config, mfma_perf_config, vanilla_perf_config, wmma_perf_config
```

Requires: `ninja rocmlir-gen rocmlir-driver mlir-runner ci-performance-scripts`

## handleNewConfigs.py

Add new configs to tier-1 files.

```bash
python3 handleNewConfigs.py --new new_configs.txt --configs-dir configs/
```

Classifies (conv/gemm/attn/etc.), deduplicates, appends to tier-1 files.

## reportUtils.py (library, not run directly)

Shared constants: `PERF_REPORT_FILE`, `CONV_TEST_PARAMETERS`, `GEMM_TEST_PARAMETERS`, `geo_mean`, `html_report`
