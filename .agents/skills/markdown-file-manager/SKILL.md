---
name: markdown-file-manager
description: Use when asked to modify, update, insert, replace, reorganize, or delete Markdown (.md) files such as README.md, CLAUDE.md, docs files, notes, and documentation pages. Preserve Markdown structure, change only the requested scope, and ask for clarification when the target section or file is ambiguous.
---

# Markdown File Manager

## Purpose

Safely manage Markdown files in a project repository with minimal, precise changes.

## Use this skill when

- The user asks to edit a README.md file
- The user asks to update a section in a Markdown document
- The user asks to insert content into a `.md` file
- The user asks to replace or rewrite a specific Markdown section
- The user asks to delete a Markdown file
- The user asks to reorganize Markdown formatting without changing meaning

## Core rules

- Only act on `.md` files unless the user explicitly expands scope
- Preserve valid Markdown formatting
- Preserve heading hierarchy unless asked to change it
- Do not rewrite unrelated sections
- Do not change tone or wording beyond the requested scope
- If the target file, heading, or section is ambiguous, ask for clarification
- If deleting a file, require an explicit delete instruction and confirm the exact path first
- Never infer deletion from vague instructions like "clean up" or "remove stuff"

## Update behavior

- Modify only the requested section or block
- If inserting content, place it exactly where requested
- If replacing a section, replace only that section
- Keep all unrelated content untouched
- Preserve lists, code fences, links, tables, and frontmatter unless asked to edit them

## Delete behavior

- Delete only the explicitly named Markdown file
- Never delete multiple files unless explicitly requested
- Confirm the file path before deletion
- If a safer alternative exists, prefer proposing it before destructive changes

## Recommended workflow

1. Read the target Markdown file first
2. Identify the exact section or block to change
3. Apply the smallest valid change
4. Preserve formatting and surrounding context
5. Return the updated content or changed section clearly

## Output format

Always provide:

1. Action: MODIFY, UPDATE, INSERT, REPLACE, or DELETE
2. Target file path
3. Scope of change
4. Resulting Markdown content or changed section
5. Brief confirmation

## Examples

### Example 1

User request:
Update the Installation section in README.md with new setup steps

Expected behavior:
- Find the Installation section
- Replace only that section
- Leave the rest of README.md unchanged

### Example 2

User request:
Insert a new "Troubleshooting" section after "Usage" in docs/setup.md

Expected behavior:
- Insert the new section in the exact requested location
- Preserve heading levels and formatting

### Example 3

User request:
Delete docs/old-notes.md

Expected behavior:
- Confirm the exact file path
- Delete only that file