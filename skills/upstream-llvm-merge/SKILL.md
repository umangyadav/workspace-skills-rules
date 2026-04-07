---
name: upstream-llvm-merge
description: >-
  Merge upstream LLVM into rocMLIR via git subtree. Handles branch creation,
  squash pull, patching, and CI. Use when asked to merge LLVM upstream,
  update LLVM, or do an upstream merge.
---

# Upstream LLVM Merge

`external/llvm-project/` is a **git subtree** (not a submodule).

## Workflow

### 1. Create merge branch

```bash
git checkout develop
git pull origin develop
git checkout -b upstream-merge-<month>-<year>
```

### 2. Squash-pull LLVM

```bash
git remote add llvm https://github.com/llvm/llvm-project.git  # if not already added
git fetch llvm
git subtree pull --prefix=external/llvm-project --squash llvm main
```

Produces: `Squashed 'external/llvm-project/' changes from OLD..NEW`

### 3. Apply internal patches (if needed)

Commit message: `Apply internal patches.`

### 4. Fix rocMLIR breakage

Common fixes:
- MLIR API renames (methods, builder signatures)
- New pass registration requirements
- TableGen syntax changes
- LLVM IR / intrinsic changes in `RockToGPU` / `RockPrepareLLVM`
- CMake target name or link changes

### 5. Update deps

Update `librockcompiler_deps.cmake` if library dependencies changed.

### 6. Keep branch current

Periodically merge `develop` into the merge branch:
```bash
git merge develop
```

### 7. Open PR

Set Jenkins parameter `ignoreExternalLinting=true` to skip clang-format/tidy on `external/`.

## Cherry-picking individual LLVM fixes

For targeted fixes between full merges:
```bash
# Apply fix to external/llvm-project/ with [EXTERNAL] prefix
git commit -m "[EXTERNAL] Cherry pick https://github.com/llvm/llvm-project/pull/NNNNN"
```

## Branch naming

`upstream-merge-jan-26`, `upstream_merge_10_25`, `upstream_merge_dec18`
