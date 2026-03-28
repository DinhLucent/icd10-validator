# ICD-10 Validator

> Python library for validating ICD-10 codes with format checking, chapter classification, billable code detection, and encounter extension handling.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-61%20passed-brightgreen.svg)]()

## Why This Exists

ICD-10 codes power medical billing, clinical research, and EHR systems worldwide. Invalid codes cause **claim denials**, audit failures, and data quality issues. This library provides instant validation with detailed diagnostics.

## Features

| Feature | Description |
|---|---|
| **Format Validation** | 7 validation rules: empty, letter prefix, format, chapter, length, billability, extension |
| **Chapter Classification** | All 22 ICD-10 chapters with code ranges and categories |
| **Billability Detection** | Identifies if a code is at the billable level or needs more digits |
| **Auto-Formatting** | Handles missing dots (`E119` → `E11.9`) and case normalization |
| **Extension Support** | Validates 7th character extensions (A=Initial, D=Subsequent, S=Sequela) |
| **FHIR Output** | Generate FHIR Coding resources from any valid code |
| **Strict Mode** | Treat warnings as errors for production billing systems |
| **Batch Validation** | Validate hundreds of codes in one call |

## Quick Start

```python
from src import ICD10Validator, CodeCategory

validator = ICD10Validator()

# Validate a code
result = validator.validate("E11.9")
print(result.is_valid)     # True
print(result.code.chapter)  # Chapter IV: Endocrine

# Quick check
print(validator.is_valid("E11.9"))  # True
print(validator.is_valid("XXX"))    # False

# Classify a code
info = validator.classify("S52.001A")
print(info["chapter"]["category"])     # Injury
print(info["extension_description"])   # Initial encounter
print(info["is_billable"])             # True

# Batch validation
results = validator.validate_batch(["E11.9", "J45", "", "123"])
valid_count = sum(1 for r in results if r.is_valid)
```

## CLI Usage

```bash
# Validate one or more codes
python -m src.cli validate E11.9 J45.0 A00.1

# Validate with JSON output
python -m src.cli validate E11.9 --json

# Classify a code
python -m src.cli classify E11.9

# List all 22 chapters
python -m src.cli chapters

# Quick pass/fail check (exit code 0 or 1)
python -m src.cli check E11.9 J45.0

# Strict mode (warnings = errors)
python -m src.cli validate E11 --strict
```

## Validation Rules

| Rule | Severity | Description |
|---|---|---|
| `E001_EMPTY` | Error | Code is empty |
| `E002_NO_LETTER` | Error | Must start with A-Z |
| `E003_BAD_FORMAT` | Error | Invalid ICD-10 format |
| `E004_NO_CHAPTER` | Error | No matching chapter |
| `E005_TOO_SHORT` | Error | Less than 3 characters |
| `W001_NOT_BILLABLE` | Warning | Category-level code, not billable |
| `W002_UNUSUAL_EXTENSION` | Warning | Non-standard extension character |

## Architecture

```
src/
├── chapters.py    # 22 ICD-10 chapters with code range lookup
├── codes.py       # Code parser with auto-dot, extensions, billability
├── validator.py   # Validation engine with 7 rules
└── cli.py         # Command-line interface
```

## Testing

```bash
pytest tests/ -v
```

**61 tests** covering chapters, code parsing, validation, CLI, and extension data.

## License

MIT License — see [LICENSE](LICENSE) for details.
