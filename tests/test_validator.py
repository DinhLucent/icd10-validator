"""Comprehensive tests for icd10-validator."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src.chapters import ICD10Chapter, get_chapter, get_all_chapters
from src.codes import ICD10Code, CodeCategory, parse_code, EXTENSION_CHARS
from src.validator import ICD10Validator, ValidationResult, ValidationSeverity, ValidationFinding


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Chapter Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestChapters:
    def test_all_chapters_count(self):
        assert len(get_all_chapters()) == 22

    def test_chapter_infectious(self):
        ch = get_chapter("A00")
        assert ch is not None
        assert ch.number == "I"
        assert ch.category == "Infectious"

    def test_chapter_neoplasms(self):
        ch = get_chapter("C50")
        assert ch is not None
        assert ch.number == "II"

    def test_chapter_endocrine(self):
        ch = get_chapter("E11")
        assert ch is not None
        assert ch.number == "IV"
        assert ch.category == "Endocrine"

    def test_chapter_mental(self):
        ch = get_chapter("F32")
        assert ch is not None
        assert ch.number == "V"

    def test_chapter_cardiovascular(self):
        ch = get_chapter("I21")
        assert ch is not None
        assert ch.number == "IX"

    def test_chapter_respiratory(self):
        ch = get_chapter("J45")
        assert ch is not None
        assert ch.number == "X"

    def test_chapter_injury(self):
        ch = get_chapter("S52")
        assert ch is not None
        assert ch.number == "XIX"

    def test_chapter_health_status(self):
        ch = get_chapter("Z00")
        assert ch is not None
        assert ch.number == "XXI"

    def test_chapter_special(self):
        ch = get_chapter("U07")
        assert ch is not None
        assert ch.number == "XXII"

    def test_chapter_none_for_invalid(self):
        ch = get_chapter("123")
        assert ch is None

    def test_chapter_none_for_empty(self):
        ch = get_chapter("")
        assert ch is None

    def test_hematologic_chapter(self):
        ch = get_chapter("D50")
        assert ch is not None
        assert ch.category == "Hematologic"

    def test_chapter_distinction_D_codes(self):
        # D00-D49 = Neoplasms, D50-D89 = Hematologic
        neoplasm = get_chapter("D10")
        hema = get_chapter("D65")
        assert neoplasm.number == "II"
        assert hema.number == "III"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Code Parsing Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCodeParsing:
    def test_simple_category(self):
        code = parse_code("E11")
        assert code.normalized == "E11"
        assert code.letter == "E"
        assert code.category_code == "E11"
        assert code.code_category == CodeCategory.CATEGORY
        assert code.is_valid_format is True

    def test_subcategory(self):
        code = parse_code("E11.9")
        assert code.normalized == "E11.9"
        assert code.subcategory is not None
        assert code.code_category == CodeCategory.SUBCATEGORY

    def test_auto_dot_insertion(self):
        code = parse_code("E119")
        assert code.normalized == "E11.9"

    def test_case_normalization(self):
        code = parse_code("e11.9")
        assert code.normalized == "E11.9"

    def test_extension_initial(self):
        code = parse_code("S52.001A")
        assert code.extension == "A"
        assert code.extension_description == "Initial encounter"

    def test_extension_subsequent(self):
        code = parse_code("S52.001D")
        assert code.extension == "D"
        assert code.extension_description == "Subsequent encounter"

    def test_extension_sequela(self):
        code = parse_code("S52.001S")
        assert code.extension == "S"

    def test_empty_code(self):
        code = parse_code("")
        assert code.is_valid_format is False

    def test_numeric_only(self):
        code = parse_code("123")
        assert code.is_valid_format is False

    def test_billable_subcategory(self):
        code = parse_code("E11.9")
        assert code.is_billable is True

    def test_not_billable_category(self):
        code = parse_code("E11")
        assert code.is_billable is False

    def test_not_billable_if_invalid(self):
        code = parse_code("123")
        assert code.is_billable is False

    def test_fhir_coding(self):
        code = parse_code("E11.9")
        fhir = code.to_fhir_coding()
        assert fhir["system"] == "http://hl7.org/fhir/sid/icd-10-cm"
        assert fhir["code"] == "E11.9"

    def test_str_repr(self):
        code = parse_code("E11.9")
        s = str(code)
        assert "E11.9" in s
        assert "Endocrine" in s

    def test_raw_preserved(self):
        code = parse_code("  e119  ")
        assert code.raw == "e119"

    def test_long_subcategory(self):
        code = parse_code("S52.0010")
        assert code.is_valid_format is True

    def test_chapter_assignment(self):
        code = parse_code("J45.0")
        assert code.chapter is not None
        assert code.chapter.category == "Respiratory"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Validator Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestValidator:
    @pytest.fixture
    def validator(self):
        return ICD10Validator()

    @pytest.fixture
    def strict_validator(self):
        return ICD10Validator(strict=True)

    def test_valid_subcategory(self, validator):
        result = validator.validate("E11.9")
        assert result.is_valid is True

    def test_valid_category_with_warning(self, validator):
        result = validator.validate("E11")
        assert result.is_valid is True  # Valid but has warning
        assert len(result.warnings) > 0

    def test_strict_category_invalid(self, strict_validator):
        result = strict_validator.validate("E11")
        assert result.is_valid is False

    def test_empty_code_invalid(self, validator):
        result = validator.validate("")
        assert result.is_valid is False
        assert any(f.rule == "E001_EMPTY" for f in result.findings)

    def test_numeric_code_invalid(self, validator):
        result = validator.validate("123")
        assert result.is_valid is False
        assert any(f.rule == "E002_NO_LETTER" for f in result.findings)

    def test_bad_format(self, validator):
        result = validator.validate("XXXX")
        assert result.is_valid is False

    def test_chapter_info(self, validator):
        result = validator.validate("E11.9")
        info_findings = [f for f in result.findings if f.severity == ValidationSeverity.INFO]
        assert len(info_findings) >= 1
        assert "Endocrine" in info_findings[0].message

    def test_batch_validation(self, validator):
        results = validator.validate_batch(["E11.9", "J45", "", "123"])
        assert len(results) == 4
        assert results[0].is_valid is True
        assert results[1].is_valid is True
        assert results[2].is_valid is False
        assert results[3].is_valid is False

    def test_is_valid_quick(self, validator):
        assert validator.is_valid("E11.9") is True
        assert validator.is_valid("") is False

    def test_classify(self, validator):
        info = validator.classify("E11.9")
        assert info["code"] == "E11.9"
        assert info["is_billable"] is True
        assert info["chapter"]["category"] == "Endocrine"

    def test_classify_with_extension(self, validator):
        info = validator.classify("S52.001A")
        assert info["extension"] == "A"
        assert info["extension_description"] == "Initial encounter"

    def test_to_dict(self, validator):
        result = validator.validate("E11.9")
        d = result.to_dict()
        assert d["code"] == "E11.9"
        assert d["is_valid"] is True
        assert isinstance(d["findings"], list)

    def test_errors_property(self, validator):
        result = validator.validate("")
        assert len(result.errors) > 0
        assert len(result.warnings) == 0

    def test_various_valid_codes(self, validator):
        valid_codes = ["A00", "B99", "C50.9", "D10", "E11.65", "F32.1",
                       "G40.0", "I21.9", "J45.0", "K50.1", "M06.9", "N18.9",
                       "R10.9", "Z00.0"]
        for code in valid_codes:
            result = validator.validate(code)
            assert result.is_valid, f"Expected {code} to be valid but got: {[f.message for f in result.errors]}"

    def test_covid_code(self, validator):
        result = validator.validate("U07.1")
        assert result.is_valid is True
        assert result.code.chapter.number == "XXII"

    def test_injury_code_with_extension(self, validator):
        result = validator.validate("S52.001A")
        assert result.is_valid is True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCLI:
    def test_parser(self):
        from src.cli import create_parser
        parser = create_parser()
        args = parser.parse_args(["validate", "E11.9"])
        assert args.command == "validate"

    def test_validate_command(self, capsys):
        from src.cli import main
        main(["validate", "E11.9"])
        captured = capsys.readouterr()
        assert "VALID" in captured.out

    def test_validate_json(self, capsys):
        from src.cli import main
        main(["validate", "E11.9", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert data[0]["is_valid"] is True

    def test_classify_command(self, capsys):
        from src.cli import main
        main(["classify", "E11.9"])
        captured = capsys.readouterr()
        assert "Endocrine" in captured.out

    def test_chapters_command(self, capsys):
        from src.cli import main
        main(["chapters"])
        captured = capsys.readouterr()
        assert "22 chapters" in captured.out

    def test_check_valid(self, capsys):
        from src.cli import main
        with pytest.raises(SystemExit) as exc:
            main(["check", "E11.9"])
        assert exc.value.code == 0

    def test_check_invalid(self, capsys):
        from src.cli import main
        with pytest.raises(SystemExit) as exc:
            main(["check", "123"])
        assert exc.value.code == 1

    def test_no_command(self, capsys):
        from src.cli import main
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 0

    def test_multiple_validate(self, capsys):
        from src.cli import main
        main(["validate", "E11.9", "J45", "A00.1"])
        captured = capsys.readouterr()
        assert "3/3" in captured.out


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Extension Data Tests
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestExtensions:
    def test_extension_chars_defined(self):
        assert "A" in EXTENSION_CHARS
        assert "D" in EXTENSION_CHARS
        assert "S" in EXTENSION_CHARS

    def test_initial_encounter(self):
        assert EXTENSION_CHARS["A"] == "Initial encounter"

    def test_subsequent_encounter(self):
        assert EXTENSION_CHARS["D"] == "Subsequent encounter"

    def test_sequela(self):
        assert EXTENSION_CHARS["S"] == "Sequela"
