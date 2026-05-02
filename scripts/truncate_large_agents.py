#!/usr/bin/env python3
"""
Truncate oversized agent descriptions in Claude Code plugins.

This script reduces token overhead from large agent descriptions by:
1. Preserving frontmatter (name, description, type)
2. Keeping the first ~200 lines of actual content
3. Adding a truncation note

Run with --dry-run to preview changes first.
"""

import argparse
import os
import re
from pathlib import Path

# Claude token estimate: ~4 chars per token
MAX_BYTES = 8000  # ~2000 tokens
TRUNCATE_LINE_COUNT = 200


def get_plugin_dirs() -> list[Path]:
    """Find all plugin directories in Claude Code."""
    # Handle Windows path properly
    home = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", "")))
    if not home or not home.exists():
        # Fallback: try to construct path
        home = Path("C:/Users") / os.environ.get("USERNAME", "argen")
    claude_dir = home / ".claude" / "plugins" / "cache"
    if not claude_dir.exists():
        print(f"Warning: Plugin cache not found at {claude_dir}")
        return []

    # Use rglob to find all agents directories recursively
    dirs = list(claude_dir.rglob("agents"))
    # Filter to only actual agent directories (not .claude/agents or .github/agents)
    dirs = [d for d in dirs if d.parent.name not in (".claude", ".github", "src")]
    return dirs


def find_large_agents(threshold_bytes: int = MAX_BYTES) -> dict[Path, int]:
    """Find agent files exceeding size threshold."""
    large_files = {}
    for agents_dir in get_plugin_dirs():
        for md_file in agents_dir.rglob("*.md"):
            size = md_file.stat().st_size
            if size > threshold_bytes:
                large_files[md_file] = size
    return dict(sorted(large_files.items(), key=lambda x: x[1], reverse=True))


def truncate_agent_file(file_path: Path, max_lines: int = TRUNCATE_LINE_COUNT, dry_run: bool = True) -> bool:
    """Truncate an agent file while preserving frontmatter."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  [ERROR] Could not read {file_path.name}: {e}")
        return False

    lines = content.split("\n")
    original_line_count = len(lines)

    # Find frontmatter end (--- delimiter)
    frontmatter_end = 0
    if lines and lines[0] == "---":
        for i, line in enumerate(lines[1:], 1):
            if line == "---":
                frontmatter_end = i + 1
                break

    # If already under limit, skip
    if original_line_count <= max_lines:
        print(f"  [SKIP] Already under {max_lines} lines ({original_line_count})")
        return False

    # Truncate: keep frontmatter + first N lines
    truncated_lines = lines[:frontmatter_end] + lines[frontmatter_end:max_lines]
    truncated_lines.append("")
    truncated_lines.append("---")
    truncated_lines.append(f"_This file was truncated by scripts/truncate_large_agents.py. Original had {original_line_count} lines._")
    truncated_lines.append("---")

    new_content = "\n".join(truncated_lines)

    if dry_run:
        print(f"  [DRY-RUN] Would truncate {file_path.name}: {original_line_count} -> {len(truncated_lines)} lines")
        return True

    # Write truncated version
    backup_path = file_path.with_suffix(".md.bak")
    backup_path.write_text(content, encoding="utf-8")
    file_path.write_text(new_content, encoding="utf-8")
    print(f"  [DONE] Truncated {file_path.name}: {original_line_count} -> {len(truncated_lines)} lines (backup: {backup_path.name})")
    return True


def main():
    parser = argparse.ArgumentParser(description="Truncate oversized agent descriptions")
    parser.add_argument("--threshold-bytes", type=int, default=MAX_BYTES, help="Size threshold in bytes")
    parser.add_argument("--max-lines", type=int, default=TRUNCATE_LINE_COUNT, help="Max lines to keep")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    print("=" * 60)
    print("Claude Code Agent Truncation Script")
    print("=" * 60)
    print()

    # Find large files
    large_files = find_large_agents(args.threshold_bytes)

    if not large_files:
        print("No agent files exceed the size threshold.")
        return

    print(f"Found {len(large_files)} large agent files:")
    total_bytes = 0
    for fp, size in large_files.items():
        print(f"  {fp.relative_to(fp.parents[3])}: {size:,} bytes ({size//4:,} tokens est.)")
        total_bytes += size
    print(f"Total: {total_bytes:,} bytes ({total_bytes//4:,} tokens est.)")
    print()

    if args.dry_run:
        print("Running in DRY-RUN mode. No changes will be made.")
    elif not args.yes:
        response = input(f"Truncate {len(large_files)} files? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            return

    print()
    print("Processing files...")
    print()

    for fp, size in large_files.items():
        print(f"{fp.relative_to(fp.parents[3])}:")
        truncate_agent_file(fp, args.max_lines, args.dry_run)

    print()
    if args.dry_run:
        print("Dry run complete. Run without --dry-run to apply changes.")
    else:
        print("Truncation complete. Backup files saved with .md.bak extension.")
        print("You can delete them after verifying the changes work correctly.")


if __name__ == "__main__":
    main()