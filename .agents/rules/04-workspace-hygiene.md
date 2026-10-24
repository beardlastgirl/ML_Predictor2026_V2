# Workspace Hygiene & Clutter Prevention
 
## Core Invariant: Zero Clutter
 
1. **Keep the Workspace Clean**
- Never leave temporary scripts, scratch files, debug dumps, or one-off experiment artifacts in the project root.
- Store generated artifacts only in their designated locations (`outputs/`, `data/`, `logs/`, `Archive/`).
- The project root should contain only active source code, configuration, and documentation.
 
2. **Delete or Archive**
- **Delete:** temporary files, debug artifacts, empty directories, duplicate outputs, and obsolete test assets.
- **Archive:** historical reports, experimental scripts, and anything that may have future reference value.
- When in doubt, archive rather than delete.
 
3. **Prevent File Proliferation**
- Prefer updating existing files over creating similarly named replacements.
- Do not create versions such as `main_v2.py`, `main_fixed.py`, or `main_final.py` unless explicitly requested.
- Create new files only when they serve a distinct purpose.
 
4. **Preserve Historical Outputs**
- Move older prediction results and generated artifacts to `outputs/` or `Archive/`.
- Do not accumulate historical outputs in the project root.
 
5. **Task Completion Check**
- Remove temporary artifacts.
- Remove empty directories.
- Verify the workspace remains organized and uncluttered.
