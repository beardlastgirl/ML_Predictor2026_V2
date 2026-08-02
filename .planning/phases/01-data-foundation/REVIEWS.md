# Phase 1 Reviews

**Phase:** 1 - Data Foundation  
**Generated:** 2026-07-17

## CLI Availability Issues

| CLI | Status | Notes |
|-----|--------|-------|
| Gemini | ❌ BLOCKED | Tier unsupported - needs migration to Antigravity |
| Claude | ⏭️ SKIPPED | Running in Claude Code - skip for independence |
| Codex | ⏱️ TIMEOUT | Hangs on large prompts (>60s) |
| OpenCode | ⏱️ TIMEOUT | Hangs on any prompt |
| Qwen | ⏱️ TIMEOUT | CLI returns empty output |
| Ollama | ❌ EMPTY | API responded but with empty content (tried both endpoints) |
| Cursor | Not tested | Requires GUI environment |

**Fallback:** Manual review conducted based on codebase analysis.

---

## Manual Review (System Analysis)

### Summary

Phase 1 research provides solid foundation for odds integration and leakage prevention, but has gaps in implementation specificity and validation strategy. The research correctly identifies key risks (forward-looking bias, CV contamination) and recommends proven libraries (odds-converter, statsmodels). However, the phase lacks concrete test cases and implementation timelines.

### Strengths

- ✅ **Correct problem identification**: Forward-looking bias in odds is a real risk
- ✅ **Proven library choices**: odds-converter and statsmodels are industry standards
- ✅ **Comprehensive anti-patterns**: Clear guidance on what NOT to do
- ✅ **Existing codebase alignment**: Validates shift(1) usage in current features.py
- ✅ **Test map provided**: Maps requirements to specific test files

### Concerns

- **MEDIUM**: No implementation timeline or task breakdown
  - Research doesn't specify build order (odds_engine → validation → integration)
  - No wave/ticket breakdown for the Wave 0 gaps listed

- **MEDIUM**: Missing edge case for odds validation
  - What happens when odds columns are NaN for historical matches?
  - No fallback strategy documented

- **LOW**: ARG.csv odds column verification needed
  - Research assumes columns exist but doesn't verify current data
  - Need to confirm PSCH/PSCD/PSCA have sufficient coverage

- **LOW**: No mention of odds margin removal
  - "Normalize to sum to 1.0" is mentioned but bookmaker-specific margins not addressed
  - Different bookmakers have different margin profiles

### Suggestions

1. **Add implementation timeline**: Break into 2-week sprints with concrete deliverables
2. **Test null handling**: Add test case for matches without odds data
3. **Verify data coverage**: Run quick analysis on ARG.csv odds column completeness
4. **Document bookmaker profiles**: Betfair (exchange) vs Bet365 (bookmaker) have different characteristics
5. **Add validation threshold**: At what coverage % (e.g., >80%) should odds features be included?

### Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Implementation delays | MEDIUM | Add weekly milestones |
| Data quality issues | MEDIUM | Pre-flight odds coverage check |
| CV contamination | LOW | Already using TimeSeriesSplit |
| Forward-looking bias | LOW | Timestamp validation pattern provided |

**Overall Risk Level:** MEDIUM

---

## Next Steps

1. Run data coverage check on ARG.csv odds columns
2. Create implementation task breakdown
3. Add null-handling tests to validation strategy
4. Re-run review when CLI timeouts resolved