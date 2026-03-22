# DEV_CONTEXT Directory

This directory serves as the persistent memory and context foundation for the ML_Predictor2026_V2 project. It maintains crucial information about the project's current state, future plans, and technical nuances.

## Purpose

The files in this directory provide AI assistants and developers with immediate context about the project's architecture, recent updates, and known issues. This ensures continuity across development sessions.

## Contents

1. **[PROJECT_STATUS.md](./PROJECT_STATUS.md)**: Details the current state of the application, recent major updates, and core configurations.
2. **[ROADMAP.md](./ROADMAP.md)**: Outlines planned features, performance optimizations, and future enhancements.
3. **[SYSTEM_KNOWLEDGE.md](./SYSTEM_KNOWLEDGE.md)**: Contains critical technical specificities, dependency notes, and troubleshooting guidelines.
4. **[DEBUGGING_METHODOLOGY.md](./DEBUGGING_METHODOLOGY.md)**: Expert debugging framework with systematic root cause analysis procedures.
5. **[BUG_TRACKING.md](./BUG_TRACKING.md)**: Bug tracking template and resolution log for documenting issues and fixes.
6. **[CODE_REVIEW_2026_03_21.md](./CODE_REVIEW_2026_03_21.md)**: Comprehensive code review findings (29 issues: 3 critical, 5 high, 12 medium, 9 low).
7. **[FIXES_EXAMPLES.md](./FIXES_EXAMPLES.md)**: Production-ready before/after code for top 10 priority fixes.

## Guidelines for Updates

- Update these documents whenever significant architectural changes occur.
- Record any recurring bugs or unique system behaviors in `SYSTEM_KNOWLEDGE.md`.
- Move completed items from `ROADMAP.md` to `PROJECT_STATUS.md`.
- Document all bug investigations and fixes in `BUG_TRACKING.md` using the provided template.
- Update `DEBUGGING_METHODOLOGY.md` when new debugging techniques or tools are implemented.
- Add code review findings to `CODE_REVIEW_*.md` with specific file references and production-ready fixes in `FIXES_EXAMPLES.md`.
- Review and update bug statistics monthly to identify patterns and improvement opportunities.

## Latest Findings (2026-03-21)

A comprehensive code review identified **29 issues** across the codebase:
- **3 Critical**: Division by zero, unsafe conversions, probability normalization
- **5 High**: Memory leaks, data misalignment, resource cleanup
- **12 Medium**: Exception handling, numeric bounds, validation gaps
- **9 Low**: Code quality, tech debt, documentation

**Action**: See CODE_REVIEW_2026_03_21.md for full details and FIXES_EXAMPLES.md for production-ready fixes.

