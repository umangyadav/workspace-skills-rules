# CI Pipelines

rocmlirTriton currently runs three CI systems. The configuration is largely inherited from rocMLIR; some pieces are intentionally pared down for the early-stage repo.

## Jenkins (primary, GPU-heavy) -- PR only today

Files in `mlir/utils/jenkins/`:

| File | Purpose |
|------|---------|
| `Jenkinsfile` | **Private CI**, runs on every PR. The only active Jenkins pipeline today. |
| `Jenkinsfile.downstream` | **Deprecated.** Used to drive a public-CI mirror. Public CI is no longer used; the file is kept in-tree for history but is not run. The "ALSO CHANGE Jenkinsfile.downstream" comment at the top of `Jenkinsfile` is stale -- ignore it. |
| `Jenkinsfile.release` | Release-build storage only (`Set System Property` + `Store a Release Build`); ~50 lines. |

The PR pipeline is a `CODEPATH` matrix (`vanilla, mfma, navi21, navi3x, navi4x, gfx950`) running each row in a ROCm Docker container. The exact stage list lives in `mlir/utils/jenkins/Jenkinsfile` -- read it there rather than mirroring it here. Two things worth knowing without opening the file:

- Static checks (clang-format / clang-tidy via `mlir/utils/jenkins/static-checks/premerge-checks.py`) are gated on the `mfma` codepath only.
- Nightly / weekly stages exist but are commented out, and re-enabling them is a private-CI-only change -- do **not** propagate it to `Jenkinsfile.downstream`.

## Azure Pipelines (ROCm ecosystem)

- Config: `.azuredevops/rocm-ci.yml`
- Triggers: push to `develop`/`mainline`, PRs to `develop`
- Excludes: `.github/`, `*.md`
- Loads shared templates from the `ROCm/ROCm` repo: `/.azuredevops/variables-global.yml@pipelines_repo` and `${{ variables.CI_COMPONENT_PATH }}/rocMLIR.yml@pipelines_repo`
- Note: the template name is still `rocMLIR.yml` (carryover from the fork). Keep it that way until ROCm/ROCm publishes a `rocmlirTriton.yml` template; do not switch unilaterally.

## GitHub Actions (lightweight Python lint, only)

- Workflow: `.github/workflows/ci.yml` -- name `"Python Lint and Format Check"`
- Triggers: `pull_request` and `push` to `develop` and `release/**`, paths `mlir/**`, excludes `external/**`
- Container: `python:3.8`, runs as root via `--user root`, fixes git ownership before checkout
- Steps:
  1. Install `pip_requirements.txt`
  2. Compute changed `mlir/**/*.py` against `git merge-base HEAD origin/<base>`
  3. `flake8 --ignore=E501,E251,E124,W605,W504,E131,E126,W503,E123 <files>`
  4. `yapf --diff <files>` (fails the job if any diff is produced)
  5. If no `*.py` under `mlir/` changed, prints "skipping" and passes

There is **no** pytest workflow, **no** codecov workflow, and no GPU/build job in GitHub Actions today (those live in Jenkins/Azure). The only file in `.github/workflows/` is `ci.yml` (plus the placeholder `README.md`).

## CODEOWNERS

All paths: `@causten` (`.github/CODEOWNERS`).

## Source of truth when CI fails

| Failing check | Look in |
|---------------|---------|
| `Python Lint and Format Check` | `.github/workflows/ci.yml`, `.flake8`, `.style.yapf` |
| Azure `rocMLIR` job | `.azuredevops/rocm-ci.yml` + ROCm/ROCm `rocMLIR.yml` template |
| Jenkins `Configure and build rocmlirTriton` | `cmake.sh`, `scripts/build-llvm.sh`, `cmake/triton.cmake` |
| Jenkins `Static checks (clang-format & clang-tidy)` | `mlir/utils/jenkins/static-checks/premerge-checks.py`, `clang-format.ignore`, `clang-tidy.ignore` |
| Jenkins `Run tests` | `tests.sh` |
