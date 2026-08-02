#!/usr/bin/env python
"""Analyze .codex/agents TOML files and produce a Markdown validation report.

This script validates TOML syntax, detects duplicate keys, checks for a minimal set
of required fields, and reports table/header structure. It does not modify any files.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    import tomllib
except ImportError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        raise SystemExit(
            "Python 3.11+ or the 'tomli' package is required to run this script. "
            "Install tomli with: pip install tomli"
        )

KEY_ASSIGNMENT_RE = re.compile(
    r"^\s*(?P<key>('[^']*'|\"[^\"]*\"|[A-Za-z0-9_-]+)(\s*\.\s*('[^']*'|\"[^\"]*\"|[A-Za-z0-9_-]+))*)\s*="
)
TABLE_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
ARRAY_TABLE_RE = re.compile(r"^\s*\[\[([^\]]+)\]\]\s*$")
TRIPLE_SINGLE = "'''"
TRIPLE_DOUBLE = '"""'
REQUIRED_FIELDS = ["sandbox_mode", "developer_instructions"]


@dataclass
class TomlFileReport:
    path: pathlib.Path
    valid: bool = True
    syntax_error: Optional[str] = None
    syntax_error_line: Optional[int] = None
    syntax_error_column: Optional[int] = None
    duplicate_keys: List[Dict[str, object]] = field(default_factory=list)
    missing_required_fields: List[str] = field(default_factory=list)
    empty_required_fields: List[str] = field(default_factory=list)
    top_level_keys: List[str] = field(default_factory=list)
    table_headers: List[str] = field(default_factory=list)
    array_table_headers: List[str] = field(default_factory=list)
    inferred_schema_note: Optional[str] = None


def normalize_key_segment(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and ((raw[0] == raw[-1] == '"') or (raw[0] == raw[-1] == "'")):
        return raw[1:-1]
    return raw


def split_dotted_key(raw: str) -> List[str]:
    raw = raw.strip()
    if not raw:
        return []

    parts: List[str] = []
    current = []
    in_quotes = False
    quote_char = ""
    for ch in raw:
        if in_quotes:
            current.append(ch)
            if ch == quote_char:
                in_quotes = False
        elif ch in ('"', "'"):
            in_quotes = True
            quote_char = ch
            current.append(ch)
        elif ch == "." and not in_quotes:
            parts.append(normalize_key_segment("".join(current)))
            current = []
        else:
            current.append(ch)

    if current:
        parts.append(normalize_key_segment("".join(current)))
    return parts


def scan_toml_file_structure(raw_text: str) -> Tuple[List[str], List[str], List[Dict[str, object]]]:
    duplicates: List[Dict[str, object]] = []
    seen_paths: set[Tuple[str, ...]] = set()
    current_table: List[str] = []
    in_multiline: Optional[str] = None

    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        if in_multiline:
            if in_multiline in line:
                in_multiline = None
            continue

        if stripped.startswith("#"):
            continue

        if TRIPLE_SINGLE in line or TRIPLE_DOUBLE in line:
            # Enter or exit a TOML multiline string. This heuristic ignores content inside.
            if TRIPLE_SINGLE in line and line.count(TRIPLE_SINGLE) % 2 == 1:
                in_multiline = TRIPLE_SINGLE
                continue
            if TRIPLE_DOUBLE in line and line.count(TRIPLE_DOUBLE) % 2 == 1:
                in_multiline = TRIPLE_DOUBLE
                continue

        table_match = TABLE_RE.match(line)
        if table_match:
            current_table = split_dotted_key(table_match.group(1))
            continue

        array_table_match = ARRAY_TABLE_RE.match(line)
        if array_table_match:
            current_table = split_dotted_key(array_table_match.group(1))
            continue

        code = line.split("#", 1)[0]
        key_match = KEY_ASSIGNMENT_RE.match(code)
        if key_match:
            key = key_match.group("key")
            key_path = tuple(current_table + split_dotted_key(key))
            if key_path in seen_paths:
                duplicates.append(
                    {
                        "line": line_number,
                        "key": ".".join(key_path),
                        "table": ".".join(current_table) if current_table else "<root>",
                    }
                )
            else:
                seen_paths.add(key_path)

    # Collect table headers and array table headers separately for reporting.
    table_headers = [m.group(1).strip() for m in TABLE_RE.finditer(raw_text)]
    array_table_headers = [m.group(1).strip() for m in ARRAY_TABLE_RE.finditer(raw_text)]
    return table_headers, array_table_headers, duplicates


def load_toml(path: pathlib.Path) -> Tuple[Optional[dict], Optional[Exception]]:
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
        return data, None
    except Exception as exc:
        return None, exc


def analyze_file(path: pathlib.Path) -> TomlFileReport:
    raw_text = path.read_text(encoding="utf-8")
    table_headers, array_table_headers, duplicates = scan_toml_file_structure(raw_text)
    report = TomlFileReport(path=path)
    report.table_headers = table_headers
    report.array_table_headers = array_table_headers
    report.duplicate_keys = duplicates

    data, error = load_toml(path)
    if error is not None:
        report.valid = False
        msg = str(error)
        report.syntax_error = msg
        if hasattr(error, "lineno"):
            report.syntax_error_line = getattr(error, "lineno")
        if hasattr(error, "colno"):
            report.syntax_error_column = getattr(error, "colno")
        elif hasattr(error, "col"):
            report.syntax_error_column = getattr(error, "col")
        return report

    report.top_level_keys = list(data.keys())
    for required in REQUIRED_FIELDS:
        if required not in data:
            report.missing_required_fields.append(required)
        else:
            value = data[required]
            if isinstance(value, str) and not value.strip():
                report.empty_required_fields.append(required)

    if not report.table_headers and not report.array_table_headers:
        report.inferred_schema_note = (
            "No explicit TOML tables were found in this file. "
            "Validation is limited to scalar keys and syntax."
        )
    else:
        report.inferred_schema_note = (
            "Table headers were detected, but no formal schema is available. "
            "The report lists table paths without asserting semantic correctness."
        )

    return report


def build_markdown_report(reports: List[TomlFileReport], root_dir: pathlib.Path) -> str:
    total_files = len(reports)
    valid_count = sum(1 for report in reports if report.valid)
    invalid_count = total_files - valid_count
    duplicate_count = sum(1 for report in reports if report.duplicate_keys)
    missing_required_count = sum(1 for report in reports if report.missing_required_fields)
    empty_required_count = sum(1 for report in reports if report.empty_required_fields)

    candidate_required_fields = [
        key
        for key in REQUIRED_FIELDS
        if all(key in report.top_level_keys for report in reports if report.valid)
    ]

    lines: List[str] = [
        "# .codex/agents TOML Analysis Report",
        "",
        f"Generated by `python {pathlib.Path(__file__).name}`.",
        "",
        "## Summary",
        "",
        f"- Total TOML files analyzed: **{total_files}**",
        f"- Syntactically valid files: **{valid_count}**",
        f"- Files with syntax errors: **{invalid_count}**",
        f"- Files with duplicate keys: **{duplicate_count}**",
        f"- Files missing required fields: **{missing_required_count}**",
        f"- Files with empty required values: **{empty_required_count}**",
        "",
        "## Inferred validation assumptions",
        "",
        "- Required fields checked by this script: `sandbox_mode`, `developer_instructions`.",
        "- These required fields are inferred from the current file set and may not reflect a formal agent schema.",
    ]

    if candidate_required_fields:
        lines.append(
            "- Candidate required fields present in all valid files: "
            + ", ".join(f"`{k}`" for k in candidate_required_fields)
            + "."
        )
    else:
        lines.append("- No consistent required-field set was inferable across all valid files.")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This report validates syntax, duplicate keys, and the minimal required fields listed above.",
            "- It does not modify any TOML files.",
            "- Table header structure is reported, but schema correctness is not asserted without a formal schema.",
            "",
        ]
    )

    for report in reports:
        rel_path = report.path.relative_to(root_dir)
        lines.extend(
            [
                f"---",
                "",
                f"### `{rel_path}`",
                "",
                f"- Path: `{report.path}`",
                f"- Syntax valid: **{report.valid}**",
            ]
        )

        if report.syntax_error:
            error_location = (
                f"line {report.syntax_error_line}, column {report.syntax_error_column}"
                if report.syntax_error_line is not None
                else "unknown location"
            )
            lines.append(f"- Syntax error: **{report.syntax_error}** ({error_location})")

        if report.duplicate_keys:
            lines.append(f"- Duplicate keys detected: **{len(report.duplicate_keys)}**")
            for duplicate in report.duplicate_keys:
                lines.append(
                    f"  - Line {duplicate['line']}: `{duplicate['key']}` (table: `{duplicate['table']}`)"
                )

        if report.missing_required_fields:
            for field in report.missing_required_fields:
                lines.append(f"- Missing required field: `{field}`")

        if report.empty_required_fields:
            for field in report.empty_required_fields:
                lines.append(f"- Empty required field: `{field}`")

        lines.append(f"- Top-level keys: {', '.join(f'`{key}`' for key in report.top_level_keys) or '*none*'}")

        if report.table_headers:
            lines.append(
                f"- Table headers: {', '.join(f'`{h}`' for h in report.table_headers)}"
            )
        if report.array_table_headers:
            lines.append(
                f"- Array table headers: {', '.join(f'`{h}`' for h in report.array_table_headers)}"
            )

        if report.inferred_schema_note:
            lines.append(f"- Note: {report.inferred_schema_note}")

        lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze .codex/agents TOML files and generate a Markdown report."
    )
    parser.add_argument(
        "--directory",
        default=".codex/agents",
        help="Directory containing .toml files to analyze (default: .codex/agents).",
    )
    parser.add_argument(
        "--output",
        default="toml_analysis_report.md",
        help="Optional markdown report file to write (default: toml_analysis_report.md).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = pathlib.Path(args.directory)
    if not root.exists() or not root.is_dir():
        print(f"Error: directory not found: {root}", file=sys.stderr)
        return 1

    toml_files = sorted(root.glob("*.toml"))
    if not toml_files:
        print(f"No .toml files found under {root}", file=sys.stderr)
        return 1

    reports = [analyze_file(path) for path in toml_files]
    report_text = build_markdown_report(reports, root)

    output_path = pathlib.Path(args.output)
    output_path.write_text(report_text, encoding="utf-8")
    print(f"Report written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
