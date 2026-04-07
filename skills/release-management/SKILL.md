---
name: release-management
description: >-
  Manage rocMLIR release branches: create releases, cherry-pick patches,
  review release PRs. Use when asked about release branches, release patches,
  or release management.
---

# Release Management

## Branch naming

| Pattern | Example | Use |
|---------|---------|-----|
| `release/rocm-rel-X.Y` | `release/rocm-rel-7.2` | Standard release |
| `release/rocm-rel-X.Y-perf-fix` | `release/rocm-rel-7.2-perf-fix` | Performance patch |
| `mass-release-backport-X.Y` | `mass-release-backport-6.3` | Bulk cherry-picks |
| `gpuep-releases/gpuep-rel-YYMM` | `gpuep-releases/gpuep-rel-2605` | GPU Enterprise |

## Release branch lifecycle

1. Cut from `develop` at release milestone
2. Only bug fixes and critical patches -- **no new features**
3. Cherry-pick from `develop` (reference PR number)
4. `[EXTERNAL]` LLVM cherry-picks for critical crash fixes
5. Performance fixes require benchmark evidence

## Patch review checklist

- [ ] Bug fix or critical regression? (no new features)
- [ ] Fix exists on `develop` first? (always fix develop, then cherry-pick)
- [ ] Change is minimal and targeted? (no large refactors)
- [ ] `check-rocmlir` passes?
- [ ] Performance benchmarks unaffected? (evidence for perf fixes)
- [ ] `librockcompiler_deps.cmake` consistent?
- [ ] No unreleased hardware references?

## Release CI

`Jenkinsfile.release` builds the fat library:

```bash
cmake -G Ninja .. -DBUILD_FAT_LIBROCKCOMPILER=ON -DCMAKE_BUILD_TYPE=Release
```

Archives:
- `mlir-source-{branch}.tar.gz` -- source tarball
- `mlir-binary-{branch}.tar.gz` -- binaries (build/bin, build/lib, LLVM bins)

## CI triggers on release branches

- GitHub Actions: `release/**` (Python lint + tests)
- Azure Pipelines: `mainline` (release integration)
- Jenkins: `Jenkinsfile.release` for fat library builds
