"""ICD-10 chapter definitions and classification.

The ICD-10 classification is organized into 22 chapters (I-XXII) based on
the alphabetic code prefix. This module maps every valid code prefix to its
chapter and provides lookup functions.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


@dataclass(frozen=True)
class ICD10Chapter:
    """An ICD-10 chapter with its code range and description.

    Attributes:
        number: Roman numeral chapter number (I-XXII).
        title: Full chapter title.
        code_range: Code range as a string (e.g., 'A00-B99').
        start: First letter/code prefix.
        end: Last letter/code prefix.
        category: High-level disease category.
    """

    number: str
    title: str
    code_range: str
    start: str
    end: str
    category: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Complete ICD-10 Chapter Definitions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CHAPTERS: list[ICD10Chapter] = [
    ICD10Chapter("I", "Certain infectious and parasitic diseases", "A00-B99", "A00", "B99", "Infectious"),
    ICD10Chapter("II", "Neoplasms", "C00-D49", "C00", "D49", "Neoplasms"),
    ICD10Chapter("III", "Diseases of the blood and blood-forming organs", "D50-D89", "D50", "D89", "Hematologic"),
    ICD10Chapter("IV", "Endocrine, nutritional and metabolic diseases", "E00-E89", "E00", "E89", "Endocrine"),
    ICD10Chapter("V", "Mental, behavioural and neurodevelopmental disorders", "F01-F99", "F01", "F99", "Mental Health"),
    ICD10Chapter("VI", "Diseases of the nervous system", "G00-G99", "G00", "G99", "Neurological"),
    ICD10Chapter("VII", "Diseases of the eye and adnexa", "H00-H59", "H00", "H59", "Ophthalmologic"),
    ICD10Chapter("VIII", "Diseases of the ear and mastoid process", "H60-H95", "H60", "H95", "Otologic"),
    ICD10Chapter("IX", "Diseases of the circulatory system", "I00-I99", "I00", "I99", "Cardiovascular"),
    ICD10Chapter("X", "Diseases of the respiratory system", "J00-J99", "J00", "J99", "Respiratory"),
    ICD10Chapter("XI", "Diseases of the digestive system", "K00-K95", "K00", "K95", "Gastrointestinal"),
    ICD10Chapter("XII", "Diseases of the skin and subcutaneous tissue", "L00-L99", "L00", "L99", "Dermatologic"),
    ICD10Chapter("XIII", "Diseases of the musculoskeletal system", "M00-M99", "M00", "M99", "Musculoskeletal"),
    ICD10Chapter("XIV", "Diseases of the genitourinary system", "N00-N99", "N00", "N99", "Genitourinary"),
    ICD10Chapter("XV", "Pregnancy, childbirth and the puerperium", "O00-O9A", "O00", "O9A", "Obstetric"),
    ICD10Chapter("XVI", "Certain conditions originating in the perinatal period", "P00-P96", "P00", "P96", "Perinatal"),
    ICD10Chapter("XVII", "Congenital malformations and chromosomal abnormalities", "Q00-Q99", "Q00", "Q99", "Congenital"),
    ICD10Chapter("XVIII", "Symptoms, signs and abnormal clinical findings", "R00-R99", "R00", "R99", "Symptoms"),
    ICD10Chapter("XIX", "Injury, poisoning and external causes", "S00-T88", "S00", "T88", "Injury"),
    ICD10Chapter("XX", "External causes of morbidity", "V00-Y99", "V00", "Y99", "External Causes"),
    ICD10Chapter("XXI", "Factors influencing health status", "Z00-Z99", "Z00", "Z99", "Health Status"),
    ICD10Chapter("XXII", "Codes for special purposes", "U00-U85", "U00", "U85", "Special"),
]

# Build lookup: letter → chapter(s)
_LETTER_TO_CHAPTERS: dict[str, list[ICD10Chapter]] = {}
for chapter in CHAPTERS:
    start_letter = chapter.start[0]
    end_letter = chapter.end[0]
    for ord_val in range(ord(start_letter), ord(end_letter) + 1):
        letter = chr(ord_val)
        _LETTER_TO_CHAPTERS.setdefault(letter, []).append(chapter)


def get_chapter(code: str) -> ICD10Chapter | None:
    """Get the ICD-10 chapter for a given code.

    Args:
        code: An ICD-10 code (e.g., 'E11.9', 'J45', 'A00').

    Returns:
        The matching ICD10Chapter, or None if no chapter matches.
    """
    if not code or not code[0].isalpha():
        return None

    letter = code[0].upper()
    candidates = _LETTER_TO_CHAPTERS.get(letter, [])

    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0]

    # Multiple chapters share the same letter (e.g., D, H, O, S/T, V/Y)
    # Need to check numeric range
    numeric_part = code[1:3].replace(".", "") if len(code) > 1 else "00"
    numeric_part = numeric_part.ljust(2, "0")

    for chapter in candidates:
        start_num = chapter.start[1:].ljust(2, "0")
        end_num = chapter.end[1:].ljust(2, "0")

        # Handle alphanumeric endings like O9A
        try:
            code_n = int(numeric_part[:2])
        except ValueError:
            code_n = 99
        try:
            start_n = int(start_num[:2])
        except ValueError:
            start_n = 0
        try:
            end_n = int(end_num[:2])
        except ValueError:
            end_n = 99

        if start_n <= code_n <= end_n:
            return chapter

    return candidates[0] if candidates else None


def get_all_chapters() -> list[ICD10Chapter]:
    """Return all 22 ICD-10 chapters."""
    return list(CHAPTERS)
