<!-- applyTo: mlir/utils/jenkins/Jenkinsfile*,.azuredevops/*,.github/workflows/* -->

# CI Pipelines

rocmlirTriton uses three CI systems.

## Jenkins (primary, GPU-heavy)

- Configs: `mlir/utils/jenkins/Jenkinsfile`, `Jenkinsfile.downstream`, `Jenkinsfile.release` (Groovy)
- Currently the PR pipeline is enabled; nightly/weekly stages exist but are commented out (see top-of-file comment)
- Docker: `mlir/utils/jenkins/Dockerfile` and `Dockerfile.migraphx-ci`; uses `rocm/mlir:rocm<version>-latest`-style images, Ninja, ROCm clang, `RelWithDebInfo`
- PR: premerge clang-format/tidy, build, targeted lit + E2E subset
- Nightly (when re-enabled): all E2E with random data, perf comparison, MIGraphX integration
- Weekly (when re-enabled): exhaustive tier1 tuning + parameter sweeps + perfDB archival

Whenever you re-enable a Jenkins stage, mirror the change in `Jenkinsfile.downstream`.

## Azure Pipelines (ROCm ecosystem)

- Config: `.azuredevops/rocm-ci.yml`
- Triggers: push to `develop`/`mainline`, PRs to `develop`
- Excludes: `.github/`, `*.md`
- Uses shared templates from the `ROCm/ROCm` repo (`/.azuredevops/variables-global.yml@pipelines_repo` and `${{ variables.CI_COMPONENT_PATH }}/rocMLIR.yml@pipelines_repo`)

## GitHub Actions (lightweight Python lint)

- Config: `.github/workflows/ci.yml`
- Container: `python:3.8`
- Triggers: PRs and pushes touching `mlir/**` on `develop` and `release/**`; `external/**` is excluded
- Steps: install `pip_requirements.txt`, compute changed `mlir/**/*.py` against the merge base, run `flake8` (with the project's ignore list) and `yapf --diff`

## CODEOWNERS

All paths: `@causten` (`.github/CODEOWNERS`).
