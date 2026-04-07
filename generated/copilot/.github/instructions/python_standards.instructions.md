<!-- applyTo: mlir/**/*.py -->

# Python Standards

## Formatting (CI-enforced)

- **Formatter**: yapf (default style)
  - Fix: `yapf -i <file>`
- **Linter**: flake8 with ignored rules: `E501,E251,E124,W605,W504,E131,E126,W503,E123`
  - Run: `flake8 --ignore=E501,E251,E124,W605,W504,E131,E126,W503,E123 <files>`
- **CI**: GitHub Actions runs both on changed `mlir/**/*.py` files vs merge base

## Testing

- Framework: **pytest**
- Test location: `mlir/utils/performance/tests/`
- Run: `cd mlir/utils/performance && python -m pytest tests/ -v`
- No GPU required (tests mock HIP)

## Environment

- Python 3.10+ (CI container)
- Dependencies: `pip install -r pip_requirements.txt`
- Key packages: numpy, scipy, pandas, jinja2, pybind11, yapf, flake8, pytest
