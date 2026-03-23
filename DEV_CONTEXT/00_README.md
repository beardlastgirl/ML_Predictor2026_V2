# ML_Predictor2026_V2 - Development Context

This directory contains the core technical documentation for the ML_Predictor2026_V2 project, a football prediction system for the Liga Profesional Argentina. These documents serve as the project's persistent memory, ensuring architectural consistency and technical integrity across development sessions.

## Active Documentation

### Core System
- **[00_README.md](./00_README.md)**: This entry point and directory index.
- **[CODEBASE_MAP.md](./CODEBASE_MAP.md)**: Comprehensive architectural overview, data flow, and module responsibilities.
- **[SYSTEM_KNOWLEDGE.md](./SYSTEM_KNOWLEDGE.md)**: Deep-dive into mathematical foundations (Poisson/Elo), API integrations, and key logic.
- **[PROJECT_STATUS.md](./PROJECT_STATUS.md)**: Current state of the application, recent major updates, and core metrics.
- **[ROADMAP.md](./ROADMAP.md)**: Planned features, performance optimizations, and historical record of milestones.

### Quality & Reliability
- **[BUG_TRACKING.md](./BUG_TRACKING.md)**: Master log of identified issues, root causes, and resolution status.
- **[CODE_REVIEW_2026_03_21.md](./CODE_REVIEW_2026_03_21.md)**: Comprehensive audit of the codebase identifying critical, high, and medium-priority improvements.
- **[FIXES_EXAMPLES.md](./FIXES_EXAMPLES.md)**: Reference implementation guide for common bug patterns and identified fixes.
- **[TIER1_ENHANCEMENTS_2026_03_22.md](./TIER1_ENHANCEMENTS_2026_03_22.md)**: Implementation summary of the data validation layer and scraper resilience infrastructure.

### Operations & Verification
- **[DEPLOYMENT_GUIDE_2026_03_21.md](./DEPLOYMENT_GUIDE_2026_03_21.md)**: Production deployment checklist, environment setup, and monitoring procedures.
- **[PIPELINE_VERIFICATION_2026_03_21.md](./PIPELINE_VERIFICATION_2026_03_21.md)**: Empirical report confirming end-to-end pipeline stability and fix validation.

---

## Directory Structure
- `DEV_CONTEXT/`: Active technical documentation (Markdown).
- `DEV_CONTEXT/archive/`: Historical AI session reports, checklists, and process-oriented logs (archived for context window efficiency).

## Maintenance Guidelines
1. **Surgical Updates**: Update these documents only when architectural changes, significant bug resolutions, or new core features are implemented.
2. **High Signal**: Maintain a technical, senior-engineer tone. Focus on *why* and *how* rather than documenting work sessions.
3. **Verification**: When fixing critical bugs or implementing Tier-1 features, ensure the corresponding `BUG_TRACKING` or `ENHANCEMENT` docs are updated to reflect the new verified state.
