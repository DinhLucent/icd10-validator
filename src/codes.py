"""ICD-10 code models and categorization."""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Optional

from .chapters import ICD10Chapter, get_chapter


class CodeCategory(str, enum.Enum):
    """ICD-10 code specificity categories."""

    CHAPTER = "chapter"       # Letter only (e.g., 'A')
    BLOCK = "block"           # 3 characters (e.g., 'A00')
    CATEGORY = "category"     # 3 characters, main category
    SUBCATEGORY = "subcategory"  # 4+ chars with decimal (e.g., 'A00.1')
    EXTENSION = "extension"   # Full code with extension (e.g., 'S52.001A')


# ICD-10 code patterns
_BLOCK_PATTERN = re.compile(r"^[A-Z]\d{2}$", re.IGNORECASE)
_CATEGORY_PATTERN = re.compile(r"^[A-Z]\d{2}$", re.IGNORECASE)
_SUBCATEGORY_PATTERN = re.compile(r"^[A-Z]\d{2}\.\d{1,4}$", re.IGNORECASE)
_FULL_PATTERN = re.compile(r"^[A-Z]\d{2}(\.\d{1,4})?[A-Z]?$", re.IGNORECASE)
_VALID_CODE_PATTERN = re.compile(r"^[A-Z]\d{2}(\.\d{1,4}[A-Z]?)?$", re.IGNORECASE)

# Common ICD-10-CM extension characters
EXTENSION_CHARS = {
    "A": "Initial encounter",
    "D": "Subsequent encounter",
    "S": "Sequela",
    "K": "Subsequent encounter for nonunion",
    "P": "Subsequent encounter for malunion",
    "G": "Subsequent encounter for delayed healing",
}


@dataclass(frozen=True)
class ICD10Code:
    """Parsed and validated ICD-10 code.

    Attributes:
        raw: The original code string as provided.
        normalized: Normalized code (uppercase, proper dot placement).
        letter: The alphabetic prefix (A-Z).
        numeric_part: The numeric portion after the letter.
        category_code: The 3-character category (e.g., 'E11').
        subcategory: Digits after the decimal, if present.
        extension: The 7th character extension (A/D/S), if present.
        code_category: Level of specificity.
        chapter: The ICD-10 chapter this code belongs to.
        is_valid_format: Whether the code matches ICD-10 format rules.
    """

    raw: str
    normalized: str
    letter: str
    numeric_part: str
    category_code: str
    subcategory: Optional[str]
    extension: Optional[str]
    code_category: CodeCategory
    chapter: Optional[ICD10Chapter]
    is_valid_format: bool

    @property
    def is_billable(self) -> bool:
        """Check if this code is at the billable (most specific) level.

        In ICD-10-CM, codes must be coded to the highest level of specificity.
        Generally, codes with subcategories where further subdivision exists
        are not billable at the parent level.

        This is a heuristic — true billability requires the full code table.
        """
        if not self.is_valid_format:
            return False
        # Category-only codes (3 chars) are usually NOT billable
        # unless they have no subcategories (rare)
        if self.code_category == CodeCategory.CATEGORY:
            return False
        # Subcategory codes (4+ chars) are typically billable
        return self.code_category in (CodeCategory.SUBCATEGORY, CodeCategory.EXTENSION)

    @property
    def extension_description(self) -> str:
        """Get the description of the extension character, if any."""
        if self.extension:
            return EXTENSION_CHARS.get(self.extension.upper(), "Unknown extension")
        return ""

    def to_fhir_coding(self) -> dict:
        """Convert to a FHIR Coding resource dictionary."""
        return {
            "system": "http://hl7.org/fhir/sid/icd-10-cm",
            "code": self.normalized,
            "display": "",
        }

    def __str__(self) -> str:
        parts = [self.normalized]
        if self.chapter:
            parts.append(f"[Ch.{self.chapter.number}: {self.chapter.category}]")
        return " ".join(parts)


def parse_code(raw: str) -> ICD10Code:
    """Parse a raw ICD-10 code string into a structured ICD10Code.

    Handles various input formats:
    - 'E11' → category
    - 'E11.9' → subcategory
    - 'e119' → auto-adds dot → 'E11.9'
    - 'S52.001A' → with extension

    Args:
        raw: Raw code string to parse.

    Returns:
        Parsed ICD10Code with validation metadata.
    """
    raw = raw.strip()
    if not raw:
        return ICD10Code(
            raw=raw, normalized="", letter="", numeric_part="",
            category_code="", subcategory=None, extension=None,
            code_category=CodeCategory.CHAPTER, chapter=None,
            is_valid_format=False,
        )

    # Normalize: uppercase
    normalized = raw.upper()

    # Check if it starts with a letter
    if not normalized[0].isalpha():
        return ICD10Code(
            raw=raw, normalized=normalized, letter="", numeric_part="",
            category_code="", subcategory=None, extension=None,
            code_category=CodeCategory.CHAPTER, chapter=None,
            is_valid_format=False,
        )

    letter = normalized[0]
    rest = normalized[1:]

    # Auto-insert dot if missing (e.g., 'E119' → 'E11.9')
    if len(rest) > 2 and "." not in rest:
        rest = rest[:2] + "." + rest[2:]
        normalized = letter + rest

    # Extract parts
    parts = rest.split(".", 1)
    numeric_block = parts[0] if parts else ""
    after_dot = parts[1] if len(parts) > 1 else None

    # Category code (first 3 chars: letter + 2 digits)
    category_code = letter + numeric_block[:2] if len(numeric_block) >= 2 else letter + numeric_block

    # Check for extension character (7th position character)
    extension = None
    subcategory = after_dot
    if after_dot and len(after_dot) > 0:
        # Check if last char is an extension letter
        last_char = after_dot[-1]
        if last_char.isalpha() and len(category_code) + 1 + len(after_dot) >= 5:
            extension = last_char
            subcategory = after_dot[:-1] if len(after_dot) > 1 else after_dot

    # Determine code category
    if not numeric_block:
        code_category = CodeCategory.CHAPTER
    elif len(numeric_block) == 2 and after_dot is None:
        code_category = CodeCategory.CATEGORY
    elif after_dot is not None and extension:
        code_category = CodeCategory.EXTENSION
    elif after_dot is not None:
        code_category = CodeCategory.SUBCATEGORY
    else:
        code_category = CodeCategory.BLOCK

    # Validate format
    is_valid = bool(_VALID_CODE_PATTERN.match(normalized))
    if not is_valid and extension:
        # Check with extension
        pattern_with_ext = re.compile(r"^[A-Z]\d{2}\.\d{1,4}[A-Z]$", re.IGNORECASE)
        is_valid = bool(pattern_with_ext.match(normalized))

    # Get chapter
    chapter = get_chapter(normalized) if len(normalized) >= 3 else None

    return ICD10Code(
        raw=raw,
        normalized=normalized,
        letter=letter,
        numeric_part=rest.replace(".", ""),
        category_code=category_code,
        subcategory=subcategory,
        extension=extension,
        code_category=code_category,
        chapter=chapter,
        is_valid_format=is_valid,
    )
