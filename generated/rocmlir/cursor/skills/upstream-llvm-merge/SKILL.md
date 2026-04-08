---
name: upstream-llvm-merge
description: >-
  Merge upstream LLVM into rocMLIR via git subtree. Handles branch creation,
  squash pull, patching, and CI. Use when asked to merge LLVM upstream,
  update LLVM, or do an upstream merge.
---

# Upstream LLVM Merge

`external/llvm-project/` is a **git subtree** (not a submodule). Source is `ROCm/llvm-project` `amd-staging` branch (lags upstream by a few months).

## Prerequisites

- Wait for bulk promotion to `amd-staging` to be announced
- Take separate clones of [ROCm/llvm-project](https://github.com/ROCm/llvm-project/tree/amd-staging) and rocMLIR for reference during conflict resolution

## Workflow

### 1. Create merge branch

```bash
git checkout develop
git pull origin develop
git checkout -b upstream_merge_<month>
```

### 2. Squash-pull LLVM

```bash
git subtree pull --squash --prefix=external/llvm-project git@github.com:ROCm/llvm-project.git amd-staging
```

If you get an error about the prefix never being added, use `--prefix=./external/llvm-project`.

Produces two commits:
1. `Squashed 'external/llvm-project/' changes from <old>..<new>`
2. `Merge commit '<sha>' into upstream_merge_<month>`

### 3. Resolve conflicts

Check out your llvm-project clone to the revision you just merged (find it in the squash commit). Use both rocMLIR and llvm-project checkouts to understand each conflict:

- **Local changes that need upstreaming**: document them, keep both versions as needed
- **Upstream changes modified during review**: take the upstream version
- **Conflicts outside `mlir/`**: take upstream's version (copy from your llvm-project checkout)
- **Overlapping patches**: line-based merging can duplicate or drop sections; compare carefully against both sources
- **"Impossible" errors** (missing methods, duplicate overrides): usually overlapping patches merged incorrectly

There is no clean way to capture conflict-resolution patches separately -- they get absorbed into the squash commit.

### 4. Fix rocMLIR breakage

Each fix in a separate commit with a descriptive message referencing the upstream PR that caused it. Keep internal and external patches in separate commits.

```
Fix <description>. Caused by https://github.com/llvm/llvm-project/pull/NNNNN
```

Before fixing breakage, check the previous upstream merge PR for its attached diff files (`mlir_diffs.txt`, `llvm_diffs.txt`). These show all custom rocMLIR patches applied on top of upstream. Verify that none of these patches were lost during the new merge -- re-apply any that were dropped by the subtree pull.

Use `git log --grep` on upstream to find relevant changes when debugging breakage.

### 5. Copy non-MLIR directories

Once you know the upstream commit, copy over non-MLIR directories in case subtree pull missed something.

### 6. Update deps

Regenerate `librockcompiler_deps.cmake` using:

```bash
perl mlir/utils/jenkins/static-checks/get_fat_library_deps_list.pl
```

### 7. Generate diff files for review

```bash
diff -rup <llvm-project-clone>/mlir rocMLIR/external/llvm-project/mlir > mlir_diffs.txt
diff -rup <llvm-project-clone>/llvm rocMLIR/external/llvm-project/llvm > llvm_diffs.txt
```

Use these to identify changes merged incorrectly, opportunities to upstream, or cases where we should use the upstream version. Note that upstreamed changes may still appear in the diff since `amd-staging` lags upstream -- check against `llvm/llvm-project` main to be sure.

### 8. Keep branch current

Periodically merge `develop` into the merge branch:
```bash
git merge develop
```

### 9. Verify external patches preserved

Ask team members to confirm their `[EXTERNAL]` commits are still present after the merge.

### 10. Build and test

Build rocMLIR and run tests on a machine with GPUs:

```bash
cmake --build . --target check-llvm
cmake --build . --target check-mlir
cmake --build . --target check-rocmlir
```

`check-rocmlir` exercises internal code and requires GPUs. Jenkins nightly provides more extensive coverage.

### 11. Open PR with checklist

Set Jenkins parameter `ignoreExternalLinting=true` to skip clang-format/tidy on `external/`.

PR description should include this checklist:

```markdown
### External LIT Tests
- [ ] `check-llvm`
- [ ] `check-mlir`

### Jenkins Internal CI
- [ ] Weekly (parameterSweeps + Tuning)
- [ ] Nightly CI
- [ ] PR CI

### MIGraphX CI
- [ ] Update MIGraphX SHA and run through their CI

### Performance
- [ ] Compare tuning runtime with a recent weekly run to check for regressions

### Navi2X (if applicable)
- [ ] parameterSweeps
- [ ] Nightly E2E tests (fixed + random data)
- [ ] PR E2E tests
```

## Common failure patterns

- **MLIR errors**: wrong dialect, wrong op, or incorrect conflict resolution (e.g., using old op name when both old and new exist)
- **Crashes**: usually assertion failures from changed invariants; use `git log --grep` on upstream to trace the cause
- **Result failures**: data structure changes (e.g., affine map representation) causing code to read data the old way
- **Test failures**: sometimes the right fix is updating the test (dialect/op changes, changed correct output)

## Cherry-picking individual LLVM fixes

For targeted fixes between full merges:
```bash
git commit -m "[EXTERNAL] Cherry pick https://github.com/llvm/llvm-project/pull/NNNNN"
```

## Branch naming

`upstream_merge_dec`, `upstream_merge_jan_26`, `upstream-merge-march-2026`
