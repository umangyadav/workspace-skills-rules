---
name: release-management
description: >-
  Manage rocmlirTriton release branches: create releases, cherry-pick patches,
  review release PRs. Use when asked about release branches, release patches,
  or release management.
---

# Release Management

## Branch naming

Release branches follow the `release/rocm-rel-X.Y` pattern (e.g., `release/rocm-rel-7.2`). PR branches targeting a release branch must **not** contain "release" in their name -- this is the only naming constraint.

## Release branch lifecycle

1. Cut from `develop` at release milestone
2. Only bug fixes and critical patches -- **no new features**
3. Cherry-pick from `develop` (reference PR number)
4. Triton submodule moves on release branches require explicit approval and a `[TRITON-BUMP]` commit; do not silently bump
5. Performance fixes require benchmark evidence

## Patch review checklist

- [ ] Associated JIRA ticket linked in PR description?
- [ ] Bug fix or critical regression? (no new features)
- [ ] Fix exists on `develop` first? (always fix `develop`, then cherry-pick)
- [ ] Change is minimal and targeted? (no large refactors)
- [ ] `tests.sh` passes locally?
- [ ] `check-rocmlir-build-only` and unit tests pass?
- [ ] Performance benchmarks unaffected? (evidence for perf fixes)
- [ ] `librockcompiler_deps.cmake` consistent if dependencies changed?
- [ ] Triton submodule SHA unchanged (or explicitly approved)?
- [ ] No unreleased hardware references?

## Release CI

Release patches must pass Jenkins PR CI and (when re-enabled) nightly CI, and require at least two approvals before merging. After merging, notify the MIGraphX team to update their rocmlirTriton commit hash.

## CI triggers on release branches

- GitHub Actions: `Python Lint and Format Check` runs on push/PR to `release/**` (flake8 + yapf on changed `mlir/**/*.py`); no other GHA gates today
- Azure Pipelines: triggers on push to `mainline` (release integration) and PRs to `develop`
- Jenkins: `Jenkinsfile.release` only "Stores a Release Build" -- it does **not** run the full PR build/test matrix, so make sure your changes have already been validated by the regular `Jenkinsfile` PR pipeline
