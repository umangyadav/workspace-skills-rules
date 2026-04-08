---
name: release-management
description: >-
  Manage rocMLIR release branches: create releases, cherry-pick patches,
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
4. `[EXTERNAL]` LLVM cherry-picks for critical crash fixes
5. Performance fixes require benchmark evidence

## Patch review checklist

- [ ] Associated JIRA ticket linked in PR description?
- [ ] Bug fix or critical regression? (no new features)
- [ ] Fix exists on `develop` first? (always fix develop, then cherry-pick)
- [ ] Change is minimal and targeted? (no large refactors)
- [ ] `check-rocmlir` passes?
- [ ] Performance benchmarks unaffected? (evidence for perf fixes)
- [ ] `librockcompiler_deps.cmake` consistent?
- [ ] No unreleased hardware references?

## Release CI

Release patches must pass Jenkins PR CI and nightly CI, and require at least two approvals before merging. After merging, notify MIGraphX team to update their rocMLIR commit hash.

## CI triggers on release branches

- GitHub Actions: `release/**` (Python lint + tests)
- Azure Pipelines: `mainline` (release integration)
- Jenkins: fat library builds on release branches
