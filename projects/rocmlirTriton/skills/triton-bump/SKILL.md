---
name: triton-bump
description: >-
  Bump the Triton submodule in rocmlirTriton. Updates external/triton, rebuilds
  LLVM, audits replication points, refreshes triton-patches, and runs tests.
  Use when asked to bump Triton, update the Triton submodule, sync with
  upstream Triton, or refresh local Triton patches.
---

# Triton Bump

## Canonical reference

**`docs/bump_triton_version.md`** in the rocmlirTriton repo is the source of truth. It is a 10-step guide with mapping tables, "Features intentionally NOT implemented" list, pass-interface-change recipes, troubleshooting, and a per-step progress checklist. **Read it end-to-end and follow it step by step**; this skill only adds the project conventions the doc doesn't cover (branch naming, PR-description checklist, between-bumps patch workflow).

The replication-point table (Python source → C++ destination) is also summarised in `rules/triton-integration.md`; the canonical fully-detailed table is in section 5 of the doc.

## Project conventions on top of the doc

### 1. Bump branch

Create a dedicated bump branch off `develop` before doing any of the doc's steps:

```bash
git checkout develop && git pull origin develop
git checkout -b triton-bump-<month>-<year>     # or triton-bump-<short-sha>
```

Every commit on this branch should use the `[TRITON-BUMP]` prefix (or `[TRITON-PATCH]` for a single patch update -- see below).

### 2. Sync each C++ replica as a separate commit

Each fix in the doc's Step 5 should be a separate commit so reviewers can audit them individually:

```
Sync <change>. Caused by https://github.com/triton-lang/triton/pull/NNNNN
```

### 3. Local Triton patches between bumps

`docs/bump_triton_version.md` covers re-evaluating existing patches during a bump (its Step 3). When you need to **add** a new local patch *between* bumps, follow:

```bash
cd external/triton
# ... edit files ...
git diff > ../../triton-patches/<NN-name>.patch
git checkout .                  # leave the submodule clean
cd ../..
git add triton-patches/<NN-name>.patch
git commit -m "[TRITON-PATCH] <description>"
```

The wrapper `scripts/build-llvm.sh` applies patches in lexicographic order, so prefix with a number if ordering matters. The patch must be:

- Idempotent (`scripts/build-llvm.sh` checks via `git apply --check --reverse`)
- Justified in the commit message
- Either upstreamed or carry a comment explaining why it's a permanent fork (see "Decision tier" in `rules/code-review.md`)

### 4. PR description checklist

When opening the bump PR, paste this checklist into the PR body so reviewers can sign off line-by-line. (This is the **PR-facing** checklist; the doc's Section "Checklist Summary" is the agent's progress checklist while doing the work.)

```markdown
### Triton Bump Checklist

- [ ] Submodule updated from `OLD_COMMIT` to `NEW_COMMIT`
- [ ] LLVM rebuilt via `scripts/build-llvm.sh`
- [ ] `triton-patches/` re-evaluated; obsolete patches removed (doc Step 3)
- [ ] Diffed `compiler.py`, `llvm.cc`, `triton_amd.cc`, `AccelerateAMDMatmul.cpp`, `TargetUtils.h` (doc Step 4)
- [ ] `Pipelines.cpp` synced (`make_ttir`, `make_ttgir`, `make_llir` part 1) (doc 5.1)
- [ ] `TritonToHsaco.cpp` synced (`make_llir` part 2 + LLVM helpers) (doc 5.3)
- [ ] `tritonUtils.cpp` synced (`getMfmaVersion`, `getWmmaVersion`, `mlirTypeToScaleDotElemType`) (doc 5.4)
- [ ] `AmdArchDb.cpp` updated for any new `ISAFamily` (doc 5.5)
- [ ] `librockcompiler_deps.cmake` regenerated (doc Step 9)
- [ ] `cmake.sh` build succeeds (doc Step 8)
- [ ] `tests.sh` passes (doc Step 10)
- [ ] MIGraphX integration check (notify MIGraphX team if downstream impact)
```

## When to deviate from the doc

If you find a step in `docs/bump_triton_version.md` that is wrong or out of date during a bump, fix the doc in the same PR (or a follow-up `[NFC]` PR) -- don't fork the procedure into this skill.
