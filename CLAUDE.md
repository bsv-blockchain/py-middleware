# CLAUDE.md

## Linting & Formatting

- Formatter: `black` (line-length 100, target Python 3.10)
- Linter: `ruff`
- Run before committing:
  ```
  black bsv_middleware/ tests/ update_coverage.py
  ruff check --fix bsv_middleware/ tests/ update_coverage.py
  pytest tests/ --tb=short -q
  ```

## Python

- Minimum version: Python 3.10
- Use modern type annotations (`dict`, `list`, `str | None`) instead of `typing.Dict`, `typing.List`, `typing.Optional`

## Dependencies

- `bsv-sdk>=2.1.3`
- `django>=3.2.0,<5.0.0`

## Testing

```
pytest tests/ -v --tb=short
```

## CI/CD

- Branch: `main` (not `master`)
- GitHub org: `bsv-blockchain` (not `bitcoin-sv`)
- build.yml: runs tests on Python 3.10, 3.11, 3.12, 3.13
- workflow.yml: publishes to PyPI on tag push (`v*.*.*`)
- Version must be updated in both `pyproject.toml` and `bsv_middleware/__init__.py`

## Pre-push Checklist

1. `black` formatting
2. `ruff` lint
3. `pytest` passes
4. Version bumped in `pyproject.toml` and `bsv_middleware/__init__.py`
