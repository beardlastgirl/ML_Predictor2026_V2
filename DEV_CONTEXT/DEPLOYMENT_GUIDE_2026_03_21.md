# Production Deployment Guide
**Date:** 2026-03-21  
**Version:** 2.0.1 (With Priority Fixes)  
**Status:** ✅ Ready for Deployment

---

## Pre-Deployment Checklist

- [x] All unit tests pass (26/26)
- [x] End-to-end pipeline verified
- [x] 10 priority fixes implemented and validated
- [x] Code review findings documented
- [x] Documentation complete
- [x] Git history clean with audit trail

---

## Deployment Steps

### Step 1: Code Review & Approval
**Status:** ✅ Ready  
**Action:** Route commits 4178b4d and 5140ae8 to team for code review
```
Commits:
- 4178b4d: fix: implement 9 priority code fixes
- 5140ae8: docs: consolidate draw calibration documentation
- 2864a37: verify: end-to-end pipeline verification
```

### Step 2: Environment Setup
**On Production Server:**

1. **Activate Virtual Environment**
   ```bash
   cd /opt/ml_predictor2026_v2
   source .venv/bin/activate  # Linux/Mac
   # or
   .\.venv\Scripts\Activate.ps1  # Windows
   ```

2. **Update Dependencies (if needed)**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Installation**
   ```bash
   python -m pytest tests/test_main.py -v
   # Expected: 26 passed in ~0.88s
   ```

### Step 3: Data Preparation
**Verify Latest Data Files:**

```bash
# Check all required files exist
ls -la data/ARG.csv           # Historical matches (6,128+ rows expected)
ls -la partidos.txt           # Upcoming fixtures
ls -la Glossary.txt           # Team name mappings (129+ entries)
ls -la src/sofascore_stats.json  # Current standings (30+ teams)
```

**Expected Data Status:**
- ✓ data/ARG.csv: Latest historical data
- ✓ partidos.txt: Updated with latest fixtures
- ✓ Glossary.txt: Team mappings synchronized
- ✓ src/sofascore_stats.json: Current standings from Sofascore

### Step 4: Production Run
**Execute Pipeline:**

```bash
# Run prediction pipeline
python main.py

# Expected output:
# - [OK] Historical matches loaded: 6128+
# - [OK] Model trained. Mean Acc: 0.34+ (+/- 0.07)
# - [OK] Results saved to ./Resultados_YYYYMMDD.txt
# - [OK] Feature importance chart saved
```

**Output Files:**
- `Resultados_YYYYMMDD.txt` - Predictions report
- `feature_importance_YYYYMMDD.png` - Feature importance chart

### Step 5: Validation
**Verify Output:**

```bash
# Check results file
wc -l Resultados_YYYYMMDD.txt
# Expected: 50-100 lines

# Check predictions are valid
grep "Resultado:" Resultados_YYYYMMDD.txt
# Expected: Scorelines like "2-1 (Home Win)"

# Check chart file exists
ls -lh feature_importance_YYYYMMDD.png
# Expected: 50-100 KB PNG file
```

**Success Criteria:**
- ✓ Results file exists and is readable
- ✓ All predictions have valid scorelines (0-6 range)
- ✓ Feature chart generated successfully
- ✓ No error messages in output

---

## Monitoring During Production

### Daily Checks

**1. Pipeline Execution**
```bash
# Add to cron job (daily at 23:00):
0 23 * * * cd /opt/ml_predictor2026_v2 && python main.py >> logs/predictions.log 2>&1
```

**2. Log Monitoring**
```bash
# Check for any errors
tail -f logs/predictions.log

# Watch for specific issues:
grep -i "error" logs/predictions.log      # Any errors
grep -i "warning" logs/predictions.log    # Any warnings
grep "Division by zero" logs/predictions.log  # Should not appear
grep "NaN\|Inf" logs/predictions.log      # Should not appear
```

### Memory Monitoring
```bash
# Check memory usage doesn't grow excessively
ps aux | grep "python main.py"
# Expected: Memory stable between runs

# If memory grows:
#   → Issue: matplotlib figure not cleaning up
#   → Check: Feature importance chart generation
```

### Output Validation
```bash
# Validate predictions daily
wc -l Resultados_*.txt
# Expected: Similar line count each day (~60-80)

# Check for valid scorelines
grep "Resultado:" Resultados_*.txt
# Expected: All scorelines 0-6 range (e.g., "2-1", "0-0")
```

---

## Rollback Procedures

### If Issues Occur

**Symptom 1: Division by Zero Crash**
```
ERROR: ZeroDivisionError in form calculation

Action:
1. Check data quality in data/ARG.csv
2. Verify src/features.py line 30 has zero-check
3. Rollback: git revert 4178b4d (if fix was reverted)
```

**Symptom 2: NaN/Inf in Output**
```
ERROR: Invalid goal count in output

Action:
1. Check src/pipeline.py line 316-317 for np.clip()
2. Verify np.clip is working (test locally)
3. Rollback: git revert 4178b4d
```

**Symptom 3: Memory Leak (Increasing Memory)**
```
ERROR: Memory usage growing each day

Action:
1. Check feature importance chart generation
2. Verify try-finally block in src/pipeline.py:289
3. Restart process: systemctl restart ml_predictor
4. Rollback: git revert 4178b4d
```

**Rollback Command:**
```bash
git revert <commit_hash>
pip install -r requirements.txt  # Reinstall if needed
python -m pytest tests/test_main.py  # Verify tests still pass
python main.py  # Test run
```

---

## Performance Baselines

**Expected Performance (on production data):**

| Metric | Baseline | Note |
|--------|----------|------|
| Pipeline execution time | ~30-60 sec | Depends on data size |
| Memory usage | <500 MB | Peak during training |
| Model accuracy | 34% ±7% | Cross-validation estimate |
| Fixtures per run | 10-20 | Varies with season |

---

## Post-Deployment Monitoring (First Week)

### Day 1-3: Intensive Monitoring
- [ ] Run pipeline at least 2x daily
- [ ] Monitor all log output
- [ ] Verify output files are valid
- [ ] Check memory usage patterns

### Day 4-7: Regular Monitoring
- [ ] Run pipeline once daily
- [ ] Review logs for warnings
- [ ] Compare predictions across days
- [ ] Document any issues

### Issues to Watch For
- ⚠️ Any division by zero errors (fix: src/features.py:30)
- ⚠️ NaN/Inf values in predictions (fix: src/pipeline.py:316)
- ⚠️ Memory growth over time (fix: src/pipeline.py:294)
- ⚠️ Crashes on edge cases (fixed by priority fixes)

---

## Production Configuration

### recommended.config.py Settings
```python
# No changes needed - production-ready defaults are set:

BASE_ELO = 1500              # Standard Elo start
K_FACTOR = 30                # Standard Elo update rate
HOME_ADVANTAGE = 65          # Liga Profesional calibration
POISSON_DRAW_ADJUSTMENT = 0.85  # Reduce draws to ~26%
ML_POISSON_BLEND_RATIO = 0.6    # 60% ML, 40% Poisson

# Model: CatBoost (default)
# Features: 24 (Elo, Poisson, trailing, Sofascore)
# Training: 5-fold time-series CV
```

---

## Alert Thresholds

**Set up monitoring alerts for:**

1. **Pipeline Failure**
   - If `main.py` exits with non-zero status
   - Action: Check logs, verify data files exist

2. **Output Missing**
   - If `Resultados_*.txt` not generated
   - Action: Check disk space, check error logs

3. **Model Accuracy Drop**
   - If CV accuracy drops below 30%
   - Action: Check recent data quality, compare with baseline

4. **Memory Spike**
   - If memory usage exceeds 1 GB
   - Action: Check for matplotlib leaks, restart process

5. **Execution Time Increase**
   - If pipeline takes >120 seconds (2x baseline)
   - Action: Check system load, check data size

---

## Support & Escalation

### Issue Resolution Path

```
Issue detected in logs
    ↓
Check DEV_CONTEXT/PIPELINE_VERIFICATION_2026_03_21.md (validate expected behavior)
    ↓
Check .planning/codebase/CONCERNS.md (known issues list)
    ↓
Review FIXES_IMPLEMENTED_2026_03_21.md (understanding fixes)
    ↓
If not resolved: Check git log for recent changes
    ↓
If critical: Consider rollback (git revert <commit>)
    ↓
Escalate: Contact development team with logs
```

### Quick Reference
- **Code Review:** `DEV_CONTEXT/CODE_REVIEW_2026_03_21.md`
- **Fixes Applied:** `DEV_CONTEXT/FIXES_IMPLEMENTED_2026_03_21.md`
- **Issues Found:** `.planning/codebase/CONCERNS.md`
- **Verification:** `DEV_CONTEXT/PIPELINE_VERIFICATION_2026_03_21.md`

---

## Success Criteria

✅ **Deployment Successful When:**
- Pipeline runs daily without errors
- Output files generated with valid predictions
- Memory usage stays stable
- No crashes or warnings in logs
- Predictions align with expected accuracy (~34%)

---

## Next Steps (Post-Deployment)

### Week 1
- [ ] Collect performance data
- [ ] Validate predictions against actual results
- [ ] Document any edge cases encountered

### Week 2-4
- [ ] Implement additional medium-priority fixes
- [ ] Add comprehensive edge case tests
- [ ] Consider betting odds integration

### Month 2+
- [ ] Plan Coordinator-Worker agent architecture
- [ ] Evaluate multi-league expansion
- [ ] Performance optimization passes

---

**Deployment Status:** ✅ READY  
**Next Action:** Code review → Approval → Deploy

For questions, refer to documentation in `DEV_CONTEXT/` and `.planning/codebase/`
