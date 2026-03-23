# AI Product Integration Setup

This document summarizes the AI assistant configurations available in this repository.

## Overview

The repository is configured for use with multiple AI products, each with specialized agents for different tasks:

### Products Configured

1. **Claude** (`.claude/`)
2. **Codex** (`.codex/`)
3. **Gemini** (`.gemini/`)
4. **OpenCode** (`.opencode/`)
5. **GitHub Copilot CLI** (root `.github/copilot-instructions.md`)
6. **Qodo Merge / PR-Agent** (`.qodo/` & `.github/workflows/pr_agent.yml`)

All products have access to:
- **GSD (Get-Shit-Done) Agents** - 17 specialized agents (including Qodo Merge) for project planning, execution, and verification
- **Project-Specific Agents** - Python development and MCP server expertise

---

## Shared Agents (All Products)

### GSD Workflow Agents (16 total)

All products include these get-shit-done agents in their `agents/` directories:

- **gsd-codebase-mapper** - Explores codebase and writes structured analysis documents
- **gsd-debugger** - Investigates bugs using scientific method with checkpoint management
- **gsd-executor** - Executes plans with atomic commits and deviation handling
- **gsd-integration-checker** - Verifies cross-phase integration and E2E flows
- **gsd-nyquist-auditor** - Fills validation gaps and generates tests for coverage
- **gsd-phase-researcher** - Researches implementation approaches before planning
- **gsd-plan-checker** - Verifies plan quality through goal-backward analysis
- **gsd-planner** - Creates executable phase plans with task breakdown
- **gsd-project-researcher** - Researches domain ecosystem before roadmap
- **gsd-research-synthesizer** - Synthesizes research into summary documents
- **gsd-roadmapper** - Creates project roadmaps with phase breakdown
- **gsd-ui-auditor** - 6-pillar visual audit of frontend code
- **gsd-ui-checker** - Validates UI specifications against quality dimensions
- **gsd-ui-researcher** - Produces UI design contracts
- **gsd-user-profiler** - Analyzes developer behavior patterns
- **gsd-verifier** - Verifies phase goal achievement
- **qodo-merge** - AI-powered PR reviews and code analysis using Qodo Merge (PR-Agent)

### Project-Specific Agents

#### python-pro
**Use when:** Building production-ready Python code, optimizing data pipelines, modernizing legacy code

**Expertise:**
- Type-safe Python 3.11+ development
- FastAPI, Django, Flask web services
- Data science with pandas, NumPy, SciPy, scikit-learn
- Performance profiling and optimization
- Async/await patterns and best practices
- Testing with pytest and comprehensive coverage
- Security scanning with bandit

**Key Strengths:**
- Complete working code ready to run
- Pythonic patterns and idiomatic solutions
- Performance benchmarks and optimization advice
- Trade-off analysis and design decisions

#### python-mcp-expert
**Use when:** Building Model Context Protocol (MCP) servers in Python

**Expertise:**
- FastMCP and low-level MCP SDK
- Type-safe tool design with Pydantic
- Async programming patterns
- Transport configuration (stdio and HTTP)
- Resource and prompt development
- Integration with Starlette/FastAPI
- Debugging MCP-specific issues

**Key Strengths:**
- Complete working MCP servers
- Type safety-first approach
- Testing with MCP Inspector
- Production-ready error handling

---

## Product-Specific Configurations

### Claude (.claude/)
- **Setup**: GSD hooks for session monitoring and updates
- **MCP Servers**: Configured with Colab MCP support
- **Features**: Project-specific agents + full GSD workflow

### Codex (.codex/)
- **Setup**: TOML-based configuration with multi-agent support
- **Hooks**: GSD update checking on session start
- **Features**: Full GSD workflow + project agents

### Gemini (.gemini/)
- **Setup**: GSD workflow integrated
- **Features**: All 16 GSD agents + project-specific agents

### OpenCode (.opencode/)
- **Setup**: JSON configuration with GSD integration
- **Features**: Full agent suite for project management

### GitHub Copilot CLI (Root)
- **Documentation**: `.github/copilot-instructions.md`
- **Focus**: Repository-specific development practices
- **MCP Servers**: Configured in `.github/mcp-servers.json`
- **Features**: Playwright and Python MCP support

---

## Quick Start by Product

### Using Claude
```
Claude will auto-load GSD agents and project-specific agents.
Invoke: "I need to build a Python scraper" → python-pro
Invoke: "Set up an MCP server for..." → python-mcp-expert
Invoke: "Plan the next phase" → gsd-planner
```

### Using GitHub Copilot CLI
```
Read .github/copilot-instructions.md for project context
Available: Playwright MCP for browser automation
Available: Python MCP for code analysis
Build commands: python main.py, .\run_model.ps1
```

### Using Codex/Gemini/OpenCode
```
All agents available in their respective agent/ directories
Same agent capabilities as Claude
Configuration format varies (TOML for Codex, JSON/MD for others)
```

---

## Data Sources & Key Files

**Input Data:**
- `data/ARG.csv` - Historical matches (6049 samples)
- `partidos.txt` - Upcoming fixtures (from TyC Sports)
- `src/sofascore_stats.json` - Current standings
- `Glossary.txt` - Team name canonicalization

**Key Modules:**
- `src/pipeline.py` - Main orchestration
- `src/stats_engine.py` - Elo/Poisson math
- `src/model_engine.py` - ML predictions
- `src/data_processing.py` - Data normalization
- `src/config.py` - Hyperparameters

**Tests:**
- `tests/test_main.py` - Pytest suite for math/features

---

## Development with AI Assistants

### For Code Changes
1. Use **python-pro** for implementation
2. Use GitHub Copilot CLI for quick edits
3. Reference `.github/copilot-instructions.md` for conventions

### For Planning
1. Use **gsd-planner** to create phase plans
2. Use **gsd-codebase-mapper** to understand architecture
3. Use **gsd-integration-checker** to verify connectivity

### For Web Automation
1. Use **Playwright MCP** (configured in `.github/mcp-servers.json`)
2. Use Playwright scraper agents in product configs
3. Reference `scrape_*.py` files for patterns

### For MCP Development
1. Use **python-mcp-expert** for server creation
2. Reference existing MCP patterns in `.claude/agents/`
3. Use MCP Inspector: `uv run mcp dev`

---

## Notes

- All configurations include GSD workflow support for structured project management
- Project-specific agents (python-pro, python-mcp-expert) are available across all products
- For development guidelines, see `.github/copilot-instructions.md`
- For AI-specific integration details, check CLAUDE.md and AGENTS.md
- MCP servers are configured in `.github/mcp-servers.json` for Copilot CLI

---

*Last Updated: 2026-03-21*
