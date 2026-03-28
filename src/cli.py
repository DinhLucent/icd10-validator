"""Command-line interface for icd10-validator."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from .validator import ICD10Validator, ValidationSeverity
from .chapters import get_all_chapters
from .codes import parse_code


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="icd10-validator",
        description="Validate and classify ICD-10 codes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s validate E11.9
  %(prog)s validate E11 J45.0 I21.9 --json
  %(prog)s classify E11.9
  %(prog)s chapters
  %(prog)s check E11.9 --strict
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # validate
    val_parser = subparsers.add_parser("validate", help="Validate ICD-10 codes")
    val_parser.add_argument("codes", nargs="+", help="One or more ICD-10 codes")
    val_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    val_parser.add_argument("--json", action="store_true", help="JSON output")

    # classify
    cls_parser = subparsers.add_parser("classify", help="Classify a code")
    cls_parser.add_argument("code", help="ICD-10 code to classify")
    cls_parser.add_argument("--json", action="store_true", help="JSON output")

    # chapters
    subparsers.add_parser("chapters", help="List all ICD-10 chapters")

    # check (quick bool check)
    chk_parser = subparsers.add_parser("check", help="Quick validity check")
    chk_parser.add_argument("codes", nargs="+", help="Codes to check")
    chk_parser.add_argument("--strict", action="store_true")

    return parser


def cmd_validate(args: argparse.Namespace) -> None:
    validator = ICD10Validator(strict=args.strict)
    results = validator.validate_batch(args.codes)

    if getattr(args, "json", False):
        print(json.dumps([r.to_dict() for r in results], indent=2))
        return

    for result in results:
        status = "✓ VALID" if result.is_valid else "✗ INVALID"
        chapter_info = f" [Ch.{result.code.chapter.number}: {result.code.chapter.category}]" if result.code.chapter else ""
        billable = " (billable)" if result.code.is_billable else " (not billable)"

        print(f"\n  {result.code.normalized:12s}  {status}{chapter_info}{billable}")

        for f in result.findings:
            if f.severity == ValidationSeverity.ERROR:
                icon = "  ✗"
            elif f.severity == ValidationSeverity.WARNING:
                icon = "  ⚠"
            else:
                icon = "  ℹ"
            print(f"    {icon} [{f.rule}] {f.message}")

    print()
    valid_count = sum(1 for r in results if r.is_valid)
    print(f"  Result: {valid_count}/{len(results)} codes valid")


def cmd_classify(args: argparse.Namespace) -> None:
    validator = ICD10Validator()
    info = validator.classify(args.code)

    if getattr(args, "json", False):
        print(json.dumps(info, indent=2))
        return

    print(f"\n  Code:       {info['code']}")
    print(f"  Level:      {info['code_level']}")
    print(f"  Category:   {info['category_code']}")
    print(f"  Billable:   {'Yes' if info['is_billable'] else 'No'}")
    if info["extension"]:
        print(f"  Extension:  {info['extension']} ({info['extension_description']})")
    if info["chapter"]:
        ch = info["chapter"]
        print(f"  Chapter:    {ch['number']} — {ch['title']}")
        print(f"  Range:      {ch['code_range']}")
        print(f"  Category:   {ch['category']}")
    print()


def cmd_chapters() -> None:
    chapters = get_all_chapters()
    print(f"\n  {'#':5s}  {'Range':10s}  {'Category':20s}  Title")
    print(f"  {'─'*5}  {'─'*10}  {'─'*20}  {'─'*40}")
    for ch in chapters:
        print(f"  {ch.number:5s}  {ch.code_range:10s}  {ch.category:20s}  {ch.title}")
    print(f"\n  Total: {len(chapters)} chapters\n")


def cmd_check(args: argparse.Namespace) -> None:
    validator = ICD10Validator(strict=args.strict)
    all_valid = True
    for code in args.codes:
        valid = validator.is_valid(code)
        if not valid:
            all_valid = False
        status = "✓" if valid else "✗"
        print(f"  {status} {code}")
    sys.exit(0 if all_valid else 1)


def main(argv: Optional[list[str]] = None) -> None:
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    handlers = {
        "validate": lambda: cmd_validate(args),
        "classify": lambda: cmd_classify(args),
        "chapters": lambda: cmd_chapters(),
        "check": lambda: cmd_check(args),
    }

    handler = handlers.get(args.command)
    if handler:
        handler()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
