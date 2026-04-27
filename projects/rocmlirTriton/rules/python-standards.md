# Python Standards

## Source of truth

- **CI workflow**: `.github/workflows/ci.yml` -- defines flake8 ignore list and yapf checks on changed `mlir/**/*.py`
- **flake8 config**: `.flake8` (`max-line-length = 100`, ignore list mirrored in CI)
- **yapf config**: `.style.yapf`
- **Dependencies**: `pip_requirements.txt`

Consult these files directly for the latest configuration before writing or fixing Python code under `mlir/` or `scripts/`.

## CI scope

GitHub Actions only lints **changed** `mlir/**/*.py` files (computed against the merge base of the PR's base branch). Files under `external/` are excluded. Local pre-commit run:

```bash
yapf --diff <changed-files>
flake8 --ignore=E501,E251,E124,W605,W504,E131,E126,W503,E123 <changed-files>
```
