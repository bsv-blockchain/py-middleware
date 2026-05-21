# CLAUDE.md

## Linting & Formatting

- Formatter: `black` (line-length 100, target Python 3.10)
- Linter: `ruff`
- Run before committing:
  ```
  black bsv_middleware/ tests/
  ruff check --fix bsv_middleware/ tests/
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
