"""ICD-10 code validation engine."""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Optional

from .codes import ICD10Code, CodeCategory, parse_code
from .chapters import ICD10Chapter, get_chapter


class ValidationSeverity(str, enum.Enum):
    """Severity level of a validation finding."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationFinding:
    """A single validation finding."""
    severity: ValidationSeverity
    code: str
    message: str
    rule: str


@dataclass
class ValidationResult:
    """Result of validating one or more ICD-10 codes.

    Attributes:
        code: The parsed ICD-10 code.
        is_valid: Whether the code passes all validation rules.
        findings: List of validation findings (errors, warnings, info).
    """
    code: ICD10Code
    is_valid: bool = True
    findings: list[ValidationFinding] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationFinding]:
        return [f for f in self.findings if f.severity == ValidationSeverity.WARNING]

    def to_dict(self) -> dict:
        return {
            "code": self.code.normalized,
            "is_valid": self.is_valid,
            "chapter": self.code.chapter.number if self.code.chapter else None,
            "category": self.code.code_category.value,
            "is_billable": self.code.is_billable,
            "findings": [
                {
                    "severity": f.severity.value,
                    "message": f.message,
                    "rule": f.rule,
                }
                for f in self.findings
            ],
        }


class ICD10Validator:
    """Validator engine for ICD-10 codes.

    Performs multiple validation checks:
    - Format validation (letter + digits + optional decimal)
    - Chapter existence check
    - Billability analysis
    - Code length validation
    - Extension character validation

    Example:
        >>> validator = ICD10Validator()
        >>> result = validator.validate("E11.9")
        >>> result.is_valid
        True
        >>> result.code.chapter.category
        'Endocrine'
    """

    def __init__(self, *, strict: bool = False) -> None:
        """Initialize the validator.

        Args:
            strict: If True, warnings are treated as errors.
        """
        self.strict = strict

    def validate(self, raw_code: str) -> ValidationResult:
        """Validate a single ICD-10 code.

        Args:
            raw_code: The code string to validate.

        Returns:
            ValidationResult with parsed code and findings.
        """
        code = parse_code(raw_code)
        result = ValidationResult(code=code)

        # Rule 1: Empty code
        if not raw_code.strip():
            result.findings.append(ValidationFinding(
                severity=ValidationSeverity.ERROR,
                code=raw_code,
                message="Code is empty",
                rule="E001_EMPTY",
            ))
            result.is_valid = False
            return result

        # Rule 2: Must start with a letter
        if not code.letter:
            result.findings.append(ValidationFinding(
                severity=ValidationSeverity.ERROR,
                code=raw_code,
                message="Code must start with a letter (A-Z)",
                rule="E002_NO_LETTER",
            ))
            result.is_valid = False
            return result

        # Rule 3: Format validation
        if not code.is_valid_format:
            result.findings.append(ValidationFinding(
                severity=ValidationSeverity.ERROR,
                code=raw_code,
                message=f"Invalid ICD-10 format: '{raw_code}'. Expected pattern: X00 or X00.0 to X00.0000",
                rule="E003_BAD_FORMAT",
            ))
            result.is_valid = False

        # Rule 4: Chapter must exist
        if code.chapter is None and len(code.normalized) >= 3:
            result.findings.append(ValidationFinding(
                severity=ValidationSeverity.ERROR,
                code=raw_code,
                message=f"Code '{code.normalized}' does not belong to any ICD-10 chapter",
                rule="E004_NO_CHAPTER",
            ))
            result.is_valid = False

        # Rule 5: Code length (minimum 3 characters for a valid code)
        if len(code.normalized.replace(".", "")) < 3:
            result.findings.append(ValidationFinding(
                severity=ValidationSeverity.ERROR,
                code=raw_code,
                message="ICD-10 codes must be at least 3 characters",
                rule="E005_TOO_SHORT",
            ))
            result.is_valid = False

        # Rule 6: Billability warning
        if code.is_valid_format and not code.is_billable:
            result.findings.append(ValidationFinding(
                severity=ValidationSeverity.WARNING,
                code=raw_code,
                message=f"Code '{code.normalized}' is a category code, not billable. Add subcategory digits for claims.",
                rule="W001_NOT_BILLABLE",
            ))
            if self.strict:
                result.is_valid = False

        # Rule 7: Extension character validation
        if code.extension:
            valid_extensions = {"A", "D", "S", "K", "P", "G"}
            if code.extension.upper() not in valid_extensions:
                result.findings.append(ValidationFinding(
                    severity=ValidationSeverity.WARNING,
                    code=raw_code,
                    message=f"Extension '{code.extension}' is not a standard encounter type (A/D/S/K/P/G)",
                    rule="W002_UNUSUAL_EXTENSION",
                ))

        # Info: Chapter classification
        if code.chapter:
            result.findings.append(ValidationFinding(
                severity=ValidationSeverity.INFO,
                code=raw_code,
                message=f"Chapter {code.chapter.number}: {code.chapter.title} ({code.chapter.category})",
                rule="I001_CHAPTER_INFO",
            ))

        return result

    def validate_batch(self, codes: list[str]) -> list[ValidationResult]:
        """Validate multiple codes at once.

        Args:
            codes: List of code strings to validate.

        Returns:
            List of ValidationResult objects.
        """
        return [self.validate(code) for code in codes]

    def is_valid(self, code: str) -> bool:
        """Quick validation check — returns True/False only.

        Args:
            code: The code to validate.

        Returns:
            True if the code is valid.
        """
        return self.validate(code).is_valid

    def classify(self, code: str) -> dict:
        """Get comprehensive classification info for a code.

        Args:
            code: The ICD-10 code.

        Returns:
            Dictionary with chapter, category, billability info.
        """
        parsed = parse_code(code)
        return {
            "code": parsed.normalized,
            "letter": parsed.letter,
            "category_code": parsed.category_code,
            "subcategory": parsed.subcategory,
            "extension": parsed.extension,
            "extension_description": parsed.extension_description,
            "code_level": parsed.code_category.value,
            "is_billable": parsed.is_billable,
            "is_valid_format": parsed.is_valid_format,
            "chapter": {
                "number": parsed.chapter.number,
                "title": parsed.chapter.title,
                "code_range": parsed.chapter.code_range,
                "category": parsed.chapter.category,
            } if parsed.chapter else None,
        }
