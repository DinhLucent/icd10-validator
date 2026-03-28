"""ICD-10 Validator - Validate, classify, and describe ICD-10 codes."""

__version__ = "1.0.0"
__author__ = "DinhLucent"

from .validator import ICD10Validator, ValidationResult, ValidationSeverity
from .chapters import ICD10Chapter, get_chapter, get_all_chapters
from .codes import ICD10Code, CodeCategory

__all__ = [
    "ICD10Validator",
    "ValidationResult",
    "ValidationSeverity",
    "ICD10Chapter",
    "ICD10Code",
    "CodeCategory",
    "get_chapter",
    "get_all_chapters",
]
