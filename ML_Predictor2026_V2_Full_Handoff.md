# ML_Predictor2026_V2 — Project Handoff, Conversation History, Experiments, and Open Questions

**Prepared:** 2026-10-10 (America/Los_Angeles; latest user message timestamp was 2026-10-11 03:21:08Z)  
**Purpose:** Transfer the project context to another AI for an independent review and a fresh approach.  
**Project root:** `C:\Scripts\ML_Predictor2026_V2\`  
**Platform:** Windows 11 / PowerShell  
**Project:** Argentine football match prediction ML model  
**Current production decision:** Preserve the frozen baseline. Do not promote experimental market-probability changes until evaluation and metrics are independently reconciled.

> **Scope note:** This document consolidates all project history, exact figures, code paths, decisions, and assistant/user instructions available in the current conversation and retained context. It is not a verbatim export of every historical chat message or every source file. Statements reported by the user or a coding agent are labeled as reported when they have not been independently verified here. Treat contradictions as unresolved rather than silently choosing one value.

---

## 1. Executive summary

The project predicts Argentine football match outcomes (Away / Draw / Home). The user is trying to improve predictive performance without leakage, accidental overfitting, or spending time on features that lack reliable historical data.

The project has been through:
- Temporal-integrity corrections and a reproducible experiment harness.
- Sporting-form feature experiments.
- Rolling performance feature experiments.
- Feasibility audits for historical manager, squad-availability, and news features.
- A market-odds coverage audit and a controlled experiment replacing sparse/imputed bookmaker-derived Shin probabilities with a provider fallback.
- A reported mixed Phase 1.4 result: accuracy and log loss improved, but Brier score and draw recall worsened.
- A planned Phase 1.4.1 audit to resolve metric inconsistencies before any new model tuning.

**Current highest-priority issue:** establish that the baseline and Phase 1.4 candidate were evaluated on identical out-of-fold matches/folds and with the same correct metric definitions. Historical baseline Brier values around `0.6662–0.6684` conflict with Phase 1.4's reported baseline Brier `0.5448`. A separate diagnostic report also gave approximately `55.4%` accuracy and log loss `0.878–0.952`, which conflicts sharply with the frozen baseline around `43.1%` accuracy and `1.106` log loss. The project has also described its CV as both `TimeSeriesSplit(5)` and “tournament-aware CV”; this must be reconciled.

Do not accept the market-probability experiment as a proven improvement until these questions are resolved.

---

## 2. User goals and working preferences

- Project is personal / for fun, focused on Argentine football predictions.
- The user suspects extra-football information can matter: injuries, suspensions, national-team call-ups, unusual team morale or institutional news (e.g., board elections/corruption stories), and unusual score swings.
- The user wants weekly news potentially weighted into predictions, but only if there is reliable point-in-time data and measurable predictive value.
- The user uses multiple AI coding CLI tools, including Mistral Vibe, Codex, Gemini, and previously Claude Code. Token usage matters; use concise, high-value work plans and avoid repeated broad audits.
- The user often wants copy/paste-ready prompts for coding agents.
- User wants an independent, evidence-based review, not agreement for agreement’s sake. Do not change historical predictions or experimental results retroactively.
- Preserve the baseline until controlled experiments show credible out-of-fold improvement.
- Prefer one small, falsifiable experiment at a time.
- Do not spend more time implementing a data feature when no reliable timestamped historical data source exists.
- Do not stage unrelated or untracked files.
- Run Python modules from the project root using `python -m src.module_name`.

### Required agent-session instructions

At the start of each coding-agent session, read/apply:
1. `C:\Scripts\MainSkills\model-routing\SKILL.md`
2. `C:\Scripts\MainSkills\token-optimization-context-defense\SKILL.md`
3. `C:\Scripts\MainSkills\python-code-review\python-code-review-skill.md`

Before coding, read:
- `AGENTS.md`
- `ML_Predictor2026_Master_Prompt.md`

Important ownership and integrity rules:
- `src/batched_features.py` is the canonical temporal-batching implementation. Do not create a duplicate.
- `src/config.py` owns hyperparameters.
- Preserve the class encoding: `0=Away, 1=Draw, 2=Home`.
- All matches with the same timestamp must use the same pre-batch state; never update state using one match before processing another simultaneous match.
- Avoid leakage from future matches, post-match facts, or current squad values when predicting historical matches.
- Keep production defaults unchanged until a candidate passes controlled evaluation.
- Do not stage unrelated files such as scraper CSVs, `outputs/`, `jobs/`, `Partidos.txt.bak`, requirements files, or `src/sofascore_stats.json` unless explicitly intended.

---

## 3. Project layout and important code/artifact names

Known project root:

```text
C:\Scripts\ML_Predictor2026_V2\
```

Important files mentioned in project history:

```text
AGENTS.md
ML_Predictor2026_Master_Prompt.md
Partidos.txt
Glossary.txt
Resultados_20261010.txt
MANIFEST.md                         # existence not confirmed
src/
  batched_features.py               # canonical temporal batching
  config.py                         # hyperparameters/config
  pipeline.py                       # production pipeline; not changed by Phase 1.4, per report
  stats_engine.py                   # historical stats/features; prior leakage audit references it
  experiment_harness.py             # experiment runner / OOF evaluation / JSONL log
  cv_split.py                       # tournament-aware CV code was mentioned; wiring uncertain
  scrape_stats_manual.py            # manual CDP scraper; may encounter CAPTCHA
  transfermarkt_lookup.py           # manager lookup infrastructure
  normalization.py                  # canonicalize_name
  sofascore_stats.json              # unrelated/untracked file noted in prior handoff
  audit_baseline.py                  # report says this was created; exact path may be root or another location
tests/
  test_form_variants.py
  test_transfermarkt.py
  test_main.py
experiments/
  results.jsonl                      # harness log
  phase14_experiment.py               # user report calls this phase14_experiment.py; exact path may be root
  phase14_market_probs_results.json
  experiment_market_probs_results.json
  baseline_audit.json
  PHASE1_3_Market_Probabilities_Report.md
  PHASE1_4_Market_Probabilities_Experiment_Report.md
MANAGER_DATA_FEASIBILITY_AUDIT.md
PHASE1_3_Market_Probabilities_Report.md
PHASE1_4_Market_Probabilities_Experiment_Report.md
baseline_audit.json
audit_baseline.py
phase14_market_probs_results.json
phase14_experiment.py
experiment_market_probs_results.json
```

**Path caution:** Some artifacts are listed at both the root and `experiments/` level because reports named them without a path. The next agent must inspect the actual repository rather than assume locations or create duplicates.

### Normal workflow
- Weekly: update `Partidos.txt`, then run `python main.py` or `.\run_model.ps1`.
- For Python modules: from project root, use `python -m src.module_name`.
- `python -m src.experiment_harness --name <exp>` is the known experiment invocation.
- Manual stats scraper: `python -m src.scrape_stats_manual`; may need a browser/CDP session and may encounter CAPTCHA.
- FBref and FootyStats have returned 403 errors in prior attempts.
- New teams may need mappings added to `Glossary.txt`.

---

## 4. Core modeling setup and evaluation standards

### Target and classes
- Three classes: Away, Draw, Home.
- Canonical encoding: `0=Away, 1=Draw, 2=Home`.
- Ensure the order of class probabilities matches this order everywhere: probability column 0 = Away, 1 = Draw, 2 = Home.

### Historical model baseline
Reported original/frozen baseline:
- Algorithm: `CatBoostClassifier`
- `random_state=42`
- Draw class weight: `0.7`
- Feature count: 24
- CV: `TimeSeriesSplit(5)` in the documented baseline/harness.
- Metrics: accuracy, log loss, multiclass Brier score.
- Main decision metrics should be OOF multiclass log loss and Brier; accuracy is secondary. Draw recall is a diagnostic, not the sole optimization target.
- Project convention: “OOF 3-class SSE” for multiclass Brier has been referenced; confirm whether the code sums squared errors over the three classes or averages over classes. Do not silently switch conventions.
- Baseline should be frozen and candidate should be compared on identical OOF matches/folds.
- Use paired comparisons and uncertainty intervals where supported.
- Do not tune hyperparameters or feature choices on the final evaluation folds.

### Experiment harness
`src/experiment_harness.py` was created and reportedly:
- Reproduces baseline predictions/metrics.
- Logs experiment name, commit, configuration, package versions, data hash, fold boundaries and counts, per-fold/aggregate metrics, confusion matrix, and errors.
- Appends to `experiments/results.jsonl`.
- Supports variant flags, including `--variant roll_windows`.
- Exact CLI for ordinary experiments: `python -m src.experiment_harness --name <exp>`.

The harness is intended to be the canonical route for fair comparisons, but the latest Phase 1.4 script may have evaluated separately. Verify that it truly uses the same harness or equivalent folds/metrics.

---

## 5. Temporal integrity and data leakage

### Phase 0.2 temporal integrity
- Reported complete and verified in commit `275d462`.
- `src/batched_features.py` is canonical.
- All matches at the same timestamp share pre-batch state.
- Matches with missing/malformed/`00:XX` times are day-batched where exact ordering cannot be trusted; a prior report mentioned 1,250 matches day-batched.
- Do not allow one simultaneous match to influence another match’s features.
- Prior code audit identified a severe leakage risk in older implementation:
  - `pipeline.py:166-168`
  - `stats_engine.py:198-225`
  - Elo ratings were computed from the full history before CV splitting, meaning validation folds could use future match outcomes.
- Temporal integrity was subsequently fixed according to user/agent reports, but every new experiment still needs to verify point-in-time validity.

### Data snapshots differ
Historical data snapshots are not identical:
- Older baseline data: `data/ARG.csv`, 6,295 rows (2012-08-03 through 2026-08-12), 6,261 eligible.
- Later data report: `data/ARG.csv`, 6,399 rows, described as spanning 2012/2013–2026.
- A later audit reported:
  - Data SHA256: `19e736b66b8b320385c3fdd83da61038404f53c03929eb05153658a0abcca351`
  - Config SHA256: `e0c13325e33f9c0f698bf160658e09350c8532302ef46a5908f6b56a7c781821`
  - Commit: `25ba09eca057b26fb396b3f9c7869849d491cbbf`
- These hashes are historical report values, not guaranteed current repository hashes.
- A later audit/handoff reported commit `25ba09e`; other historical commits include `44e1b58`, `dce9bb2`, `dc81b0e`, `25ba09e`, and `6aa996e`. Confirm current `git status` and `git log` before relying on them.

**Important:** Do not compare metrics from 6,295-row and 6,399-row datasets as if they were the same evaluation unless the experiment is rerun on a common pinned data snapshot.

---

## 6. Baseline metrics — all reported versions and discrepancies

### Baseline A: original reproduced harness baseline
Reported independently reproduced exactly across two runs:
- Data: 6,295 rows; 6,261 eligible.
- OOF samples: 5,215.
- `TimeSeriesSplit(5)`.
- Each validation fold: 1,043 rows.
- Training sizes: `[1046, 2089, 3132, 4175, 5218]`.
- Accuracy: `0.43241`.
- Log loss: `1.10278`.
- Multiclass Brier: `0.66619`.
- Accuracy variation: approximately ±0.0112; log loss variation approximately ±0.0053 in earlier summary.
- Confusion matrix (true rows / predicted columns, order Away, Draw, Home):

```text
[[334,  92,  981],
 [304,  78, 1177],
 [308,  98, 1843]]
```

This matrix indicates very few predictions of Draw. Actual Draws are mostly predicted as Home.

### Baseline B: later 6,399-row audit
A report dated 2026-10-10 states:
- Data: `data/ARG.csv`, 6,399 matches.
- CatBoost, 24 features.
- CV accuracy: 43.1% (±1.5 percentage points).
- CV log loss: 1.106.
- Per-fold results:

| Fold | Accuracy | Log loss |
|---|---:|---:|
| F1 | 0.441 | 1.108 |
| F2 | 0.441 | 1.107 |
| F3 | 0.440 | 1.106 |
| F4 | 0.433 | 1.101 |
| F5 | 0.402 | 1.111 |

- The audit claims no leakage, trailing window = 8, and Elo updated batch-by-batch.
- Odds columns reported:
  - B365 triplet coverage: 613/6,399 (9.6%), mostly 2025–2026.
  - PS triplet: 92.6% (5,928/6,399).
  - Max and Avg triplets: 100%, though Max has some extreme values.
- Baseline Brier in another fresh comparison was `0.6684`.

### Unresolved comparison issues
- `0.66619`, `0.6684`, and Phase 1.4's `0.5448` are not interchangeable without explaining metric formula, normalization, sample, and aggregation.
- The 6,295-row baseline and 6,399-row baseline differ.
- Earlier baseline CV was described as `TimeSeriesSplit(5)`, but later diagnostic text says “tournament-aware CV.” `src/cv_split.py` reportedly exists, but prior notes say it was not wired into `train_validate`. Confirm which splitter the baseline, diagnostics, and Phase 1.4 script actually use.
- Do not treat a report's claim of reproducibility as independently verified until OOF predictions, fold boundaries, hashes, and formulas are checked.

---

## 7. Feature set (reported 24 features)

The later baseline audit listed:
1. `Home_Elo`
2. `Away_Elo`
3. `Elo_Diff`
4. `Home_Avg_GF`
5. `Away_Avg_GF`
6. `Home_Avg_GA`
7. `Away_Avg_GA`
8. `Home_Form`
9. `Away_Form`
10. `Attack_Balance`
11. `Def_Balance`
12. `Form_Balance`
13. `xG_home`
14. `xG_away`
15. `xG_diff`
16. `Poisson_Home_Win`
17. `Poisson_Draw`
18. `Poisson_Away_Win`
19. `Expected_Home_Goals`
20. `Expected_Away_Goals`
21. `Expected_Total_Goals`
22. `Shin_Prob_H`
23. `Shin_Prob_D`
24. `Shin_Prob_A`

**Potential integration issue:** the market probabilities already exist as three features. Phase 1.4 should have replaced their values, not added duplicate probability columns. Verify the implementation.

---

## 8. Phase 1.0 — Experiment harness

Reported complete:
- `src/experiment_harness.py`.
- Logs commit/config/package versions/data hash/fold boundaries/metrics/confusion matrix/errors to `experiments/results.jsonl`.
- Reproduced baseline exactly in two runs.
- Baseline figures are listed in Section 6.
- Commit reported as `44e1b58` for the harness.
- This is intended to support paired, repeatable feature experiments.

---

## 9. Phase 1.1 — Sporting-form features

Experimented with:
- EWMA half-life 2, 4, and 8.
- Venue-split form.

Reported result:
- Log-loss deltas were slightly favorable in some tests, but 95% confidence intervals crossed zero.
- No credible improvement.
- **Decision: NO-GO; retain baseline.**

Do not resurrect these variants without a new hypothesis and a reason to believe the previous experiment was flawed.

---

## 10. Phase 1.2 — Rolling performance features

Candidates:
- Points per game over 5 and 10 matches (`PPG@5`, `PPG@10`).
- Goal difference over 5 and 10 matches (`GD@5`, `GD@10`).
- Candidate implementation in `src/batched_features.py`.
- Config: `ROLLING_WINDOW_CANDIDATES = [5,10]`.
- Tests: `tests/test_form_variants.py`.
- Harness flag: `--variant roll_windows`.

Reported correlations with existing features / rejected EWMA variants: approximately 0.85–0.95, suggesting substantial redundancy.

Reported fresh comparison:
- Baseline LL: `1.1064`; Brier `0.6684`; accuracy `0.4311`.
- `roll_w5_w10` LL: `1.1021`; Brier `0.6654`; accuracy `0.4291`.
- Paired bootstrap LL delta: `-0.00425`, 95% CI `[-0.00865, +0.00019]` (crosses zero).
- **Decision: NO-GO.** Candidate remains inactive unless `--variant roll_windows` is explicitly requested.
- The result is not a proven improvement because the confidence interval crosses zero and accuracy decreased slightly.

---

## 11. Phase 1.3 — Market probability coverage audit

### Context
B365-derived Shin probabilities were available for only a small fraction of matches. The model apparently used neutral `1/3, 1/3, 1/3` probabilities where B365 odds were missing, discarding other available market odds.

### Reported odds coverage

| Provider | Columns | Reported coverage | Notes |
|---|---|---:|---|
| Bet365 | `B365CH/B365CD/B365CA` | 613/6,399 (9.6%) | Mostly 2025–2026 |
| PS | `PSCH/PSCD/PSCA` | 5,928/6,399 (92.6%) | Described as primary fallback |
| Max | `MaxCH/MaxCD/MaxCA` | 6,399/6,399 (100%) | Some extreme values |
| Avg | `AvgCH/AvgCD/AvgCA` | 6,399/6,399 (100%) | Described as reasonable ranges |

Reported fallback counts:
- B365: 613 matches (9.6%).
- PS: 5,778 matches (90.3%).
- Max: 8 matches (0.1%).
- Avg: 0.
- Fully imputed: 0.

**Discrepancy to resolve:** PS reported coverage is 5,928 matches, while actual fallback usage is reported as 5,778. Since 613 + 5,778 + 8 = 6,399, there are 150 PS-covered matches not used as fallback, likely because B365 takes priority for matches with B365 values, but exact provider precedence and the definition of “coverage” need to be documented and checked. A complete triplet, not just individual non-null columns, must define provider coverage.

### Phase 1.3 reported conclusion
- Coverage improved from 9.6% to 100%.
- `baseline_audit.json` preserved unchanged at 43.1% accuracy / 1.106 log loss.
- Files reported created:
  - `PHASE1_3_Market_Probabilities_Report.md`
  - `experiment_market_probs_results.json`
  - `baseline_audit.json`
  - `audit_baseline.py`
- The report's coverage improvement is useful, but coverage alone does not prove predictive improvement.
- There was ambiguity about whether Phase 1.3 merely audited coverage or trained a model. Phase 1.4.1 should inspect code and artifacts to establish exactly what Phase 1.3 tested.

---

## 12. Fold-level diagnostic report — inconsistency to resolve

A separate “Diagnostic Report: Fold-Level Performance & Class Analysis” was supplied by the user. It reported:
- Mean accuracy: **55.4%**.
- Draw recall: **8.9%**, with fold range 5.8%–14.7%.
- Draw precision: **1.000 in every fold**.
- Log loss around `0.878–0.952`.
- Fold summaries:

| Fold | Accuracy | Log loss | Draw recall |
|---|---:|---:|---:|
| F1 | 0.579 | 0.898 | 8.6% |
| F2 | 0.558 | 0.924 | 7.0% |
| F3 | 0.532 | 0.940 | 8.4% |
| F4 | 0.523 | 0.952 | 5.8% |
| F5 | 0.578 | 0.878 | 14.7% |

Sample Fold 1 confusion matrix, true rows and predicted columns Away / Draw / Home:

```text
True Away: [137, 0, 155]
True Draw: [ 48,25, 219]
True Home: [ 23, 1, 452]
```

From this matrix:
- Draw recall = `25 / (48 + 25 + 219) = 25/292 ≈ 8.56%`, consistent with 8.6%.
- Predicted Draw count = `0 + 25 + 1 = 26`.
- Draw precision = `25/26 ≈ 96.15%`, **not 100%**.
- Therefore the report’s “draw precision = 1.000” contradicts its own displayed confusion matrix, assuming the matrix is complete and class ordering is as stated.
- The 55.4% accuracy / low log loss figures are dramatically better than the frozen baseline (43.1% / 1.106). Possible causes include different data, splitter, fold sizes, target/class order, scoring implementation, leakage, or a different model.
- Do not assume this diagnostic describes the same model/evaluation as the frozen baseline until proven.

Earlier assistant advice: don’t over-optimize draw recall in isolation; log loss and Brier should remain primary, accuracy secondary, with draw precision/recall and counts used diagnostically.

---

## 13. Phase 1.4 — Controlled market-probability experiment

### User-supplied report (not independently verified)
The user reported Phase 1.4 complete, with these results:

| Metric | Baseline | Candidate | Reported delta |
|---|---:|---:|---:|
| Mean CV Accuracy | 43.1% | 44.8% | +1.7 percentage points (+3.9%) |
| Mean CV Log Loss | 1.106 | 1.088 | -0.019 (reported as -1.7%) |
| Mean Brier Score | 0.5448 | 0.6551 | +0.1102 (+20.2%) |
| Mean Draw Recall | 8.9% | 5.2% | -3.7 percentage points |
| Shin method coverage | 9.6% | 100% | +90.4 percentage points |

The report says:
- Accuracy improved consistently across all five folds.
- Log loss improved consistently across all five folds.
- Brier score degraded significantly.
- Draw recall worsened.
- **Decision: NO-GO** for production default.
- Production files `src/pipeline.py` and `src/config.py` were reportedly NOT modified.
- Files reportedly created/modified:
  - `phase14_market_probs_results.json`
  - `phase14_experiment.py`
  - `PHASE1_4_Market_Probabilities_Experiment_Report.md`
  - `baseline_audit.json` preserved unchanged
  - `PHASE1_3_Market_Probabilities_Report.md`

### Arithmetic / definition concern
- Baseline Brier `0.5448` differs sharply from earlier values around `0.66619` and `0.6684`.
- Candidate Brier `0.6551` is worse than 0.5448, but still lower than earlier baseline values. This could arise from a different Brier definition, normalization, aggregation, sample, fold setup, or a bug.
- Accuracy and log loss could be genuine improvements, but they are not enough to retain the candidate if Brier degradation is real under the same definition and evaluation.
- The Phase 1.4 report claims consistent improvements across folds; verify actual fold-level results and OOF predictions, not just the summary.
- Phase 1.4 might have used its own script instead of the canonical harness. Verify that both variants use identical folds and OOF rows.
- Candidate integration must be checked: it should replace the existing `Shin_Prob_H/D/A` values, not add duplicate columns or alter target labels/sample selection.

### Current decision
**Keep the production baseline unchanged.** The candidate is NO-GO until a metric integrity audit is passed and the candidate’s results can be reproduced fairly.

---

## 14. Previous recommended Phase 1.4.1 — Audit metrics before more modeling

The latest advice given to the user was not to proceed immediately to calibration tuning. Instead, run a targeted audit.

Copy/paste prompt for the coding agent:

```text
# Phase 1.4.1 — Audit Metrics Before Further Experiments

Project: ML_Predictor2026_V2

Follow AGENTS.md, ML_Predictor2026_Master_Prompt.md, and the required session skills. Conserve tokens. Audit first; do not tune the model or change production code.

## 1. Verify the exact experiment
Inspect phase14_experiment.py, phase14_market_probs_results.json, baseline_audit.json, the Phase 1.3 report, and the existing experiment harness.

Confirm that baseline and candidate use:
- Identical eligible matches, OOF predictions, and fold boundaries.
- Identical class order: 0=Away, 1=Draw, 2=Home.
- The same model configuration, sample weights, and metric implementations.
- Probabilities in the expected class order, with finite values that sum to 1.

Report any differences explicitly.

## 2. Resolve the Brier-score discrepancy
The latest report gives baseline Brier 0.5448 and candidate 0.6551. Earlier reports gave approximately 0.6662 or 0.6684 for the baseline.

Determine whether these numbers use different:
- Brier definitions or normalization factors.
- Evaluation samples or folds.
- Probability arrays, class ordering, or aggregation methods.
- Sample weights or metric libraries.

Calculate baseline and candidate Brier scores independently from the saved OOF probability predictions using the project's documented convention. For this project, preserve the established three-class OOF squared-error convention; explicitly document whether it is the sum or mean over classes.

Do not compare scores computed under different conventions.

## 3. Recompute every reported metric
From the same saved OOF predictions, independently recompute:
- Multiclass log loss.
- Multiclass Brier score.
- Accuracy.
- Draw precision, recall, and predicted-draw count.
- Complete confusion matrices, with true classes as rows and predicted classes as columns.
- Per-fold and aggregate metrics.

Check that the stated deltas and percentage changes are arithmetically correct. Explain any mismatch.

## 4. Verify market-probability integration
Confirm that Phase 1.4 actually replaced the three existing Shin probability feature values, rather than accidentally changing targets, sample selection, class order, or other features.

Verify provider fallback counts and confirm each match uses a complete odds triplet from one provider. Check whether the market-probability features are point-in-time valid for every evaluated match.

## 5. Deliver a concise audit report
Include:
- Confirmed baseline and candidate metrics.
- Exact metric formulas and class order.
- Data/config hashes and fold boundaries.
- Any bugs, mismatches, or unresolved uncertainties.
- Whether the claimed improvement is reproducible.
- A clear GO/NO-GO recommendation for further experimentation.

Do not modify src/pipeline.py, src/config.py, or production defaults. Do not launch Phase 1.5 until this audit passes. Do not stage unrelated files. Run Python modules from the project root using python -m src.module_name.
```

### Expected decision after Phase 1.4.1
- If the audit confirms gains: a calibration experiment may be designed, with calibration fitted only on training/OOF data and never on held-out folds.
- If a metric/evaluation bug is found: fix the experiment harness and rerun baseline and candidate first.
- If evidence remains mixed: retain production baseline and document the coverage finding only.

---

## 15. Model E — Historical manager features

Feasibility work reportedly created:
- `transfermarkt_urls.txt` with 30 club IDs/URLs.
- `src/transfermarkt_lookup.py`, reusing `canonicalize_name` from `src/normalization.py`.
- `tests/test_transfermarkt.py` (41 focused tests).
- `MANAGER_DATA_FEASIBILITY_AUDIT.md`.

Reports mention 41 focused lookup tests passing and 34 tests in `tests/test_main.py`; do not combine these into one global test count without rerunning the suite.

Finding:
- Manager-history coverage was reported around 0.3% in the user's feasibility decision context (other audit notes suggested coaching may be conditionally feasible in modern years, but exact coverage estimates differ).
- Insufficient reliable historical point-in-time data for the league.
- **Decision: reject Model E for now.**
- The lookup infrastructure can remain as a club reference; no need to remove it.
- Important data rule: distinguish actual appointment/effective date from when the appointment was publicly known. A later appointment record must not leak into an earlier match prediction.

---

## 16. Model C — Squad availability (injuries, suspensions, call-ups)

Audit finding:
- `ARG.csv` has match data, scores/results, and odds, but no historical injury, suspension, national-team call-up, or card-accumulation features.
- No free, reliable, point-in-time historical source was found with sufficient coverage across the Argentine league.
- FBref / FootyStats attempts returned 403; Sofascore material appears limited to current season in prior attempts.
- **Decision: reject Model C for now.**
- Do not implement without reliable timestamped historical data.

---

## 17. Model G — News / sentiment / extra-football events

Audit finding:
- No free structured historical news source with pre-kickoff publication timestamps and enough league-wide coverage was identified.
- Existing Elo/form/market odds may already reflect some news effects; do not claim they perfectly capture all news.
- The project Master Prompt prohibits sentiment-only news features and retrospective explanations.
- **Decision: reject Model G for now due to data limitations and lack of demonstrated incremental value.**
- Do not spend more time on external-data features until there is a concrete source with timestamps, coverage, and point-in-time availability.

---

## 18. Other historical concerns / workflow notes

### Odds data
- A later audit found B365 odds in only 613/6,399 matches, mostly 2025–2026.
- PS triplet coverage was reported as 5,928/6,399.
- Max/Avg triplets were reported as complete; Max had some extreme values.
- Earlier code apparently neutral-imputed missing B365-derived Shin probabilities to 1/3 each.
- Phase 1.3 introduced a B365 → PS → Max → Avg fallback and reported 100% coverage.
- Verify provider triplets are complete, valid, and from one provider per match. Never combine home/draw/away prices across providers without a defensible explicit rule.
- Ensure odds were known before kickoff and are not accidentally using post-match prices.
- Market probabilities are only useful if their construction, time validity, and evaluation are correct.

### Class imbalance / draw issue
- The model reportedly predicts Draw infrequently.
- Earlier baseline confusion matrix shows actual draws mostly predicted Home.
- A separate diagnostic claimed draw recall 8.9% and precision 1.0, but its own Fold 1 matrix implies precision about 96.15%, not 100%.
- Candidate Phase 1.4 reported draw recall dropping from 8.9% to 5.2%.
- Do not optimize only for draw recall; check log loss, Brier, calibration, classwise performance, and the full confusion matrix.
- Do not apply class weighting or calibration blindly; test one controlled hypothesis at a time.

### Git hygiene
- Check `git status --short`, `git diff`, and recent log before modifying anything.
- Keep unrelated/untracked files out of commits.
- Do not stage scraper CSVs, `outputs/`, `jobs/`, `Partidos.txt.bak`, requirements files, or `src/sofascore_stats.json` unless explicitly required.
- Preserve experimental artifacts and baseline audit records; do not overwrite baseline outputs with candidate results.
- Current commit must be confirmed from the repository; historical commit hashes are not proof of current state.

---

## 19. Chronological conversation / decision log

This is a chronological summary of the available conversation and project context. It is not a verbatim transcript.

### Earlier project motivation
- The user asked for an audit/review prompt because the project had gone through many changes and the best path forward was unclear.
- The user wondered whether extra-football Argentine football news could explain low accuracy: club board elections/corruption, injuries, suspensions, national-team absences, morale, and unusual scorelines.
- User wanted to compare models/approaches rather than implement speculative features without evidence.
- The user uses several AI coding agents and often needs concise, token-efficient prompts.

### Phase 0 / temporal integrity
- A serious leakage issue was found in old Elo calculations, which used full match history before CV split.
- Phase 0.2 reportedly fixed temporal integrity and same-timestamp batching in commit `275d462`.
- `src/batched_features.py` was designated canonical for batching.
- The baseline was frozen and the project set rules for controlled experiments.

### Phase 1.0 / baseline harness
- A reproducible harness was created, reported at commit `44e1b58`.
- Baseline on 6,295-row dataset: accuracy 0.43241, log loss 1.10278, Brier 0.66619, OOF n=5,215, five validation folds of 1,043 each.
- Confusion matrix documented in Section 6.

### Phase 1.1 / sporting form
- EWMA half-life 2/4/8 and venue splits were tested.
- Small favorable log-loss movements were inconclusive; 95% CIs crossed zero.
- No-go.

### Phase 1.2 / rolling performance
- PPG and goal-difference windows 5 and 10 were added as inactive candidates.
- High correlation with existing features, 0.85–0.95.
- Candidate log loss slightly better, but paired CI crossed zero and accuracy slipped.
- No-go.

### Model E / manager-history feasibility
- Transfermarkt lookup tools and tests were created.
- Historical point-in-time coverage was judged inadequate.
- No-go for manager feature.

### Model C / squad availability feasibility
- No sufficiently reliable free historical timestamped injury/suspension/call-up source.
- No-go.

### Model G / news feasibility
- No adequate structured historical news source with pre-kickoff timestamps and broad coverage.
- No-go.

### 2026-10-10 baseline audit
- Newer dataset described as 6,399 matches.
- Baseline audit gave 43.1% accuracy and 1.106 log loss.
- Market odds coverage discrepancy surfaced: B365 only 9.6%, while PS/Max/Avg had much higher reported coverage.
- A separate diagnostic reported 55.4% accuracy and 0.878–0.952 log loss, plus draw recall 8.9%; this conflicts with baseline and contains an internal draw-precision/confusion-matrix mismatch.

### Phase 1.3 / market coverage
- A fallback strategy reportedly raised Shin probability coverage from 9.6% to 100%.
- Provider fallback counts reported: B365 613, PS 5,778, Max 8, Avg 0, imputed 0.
- The PS coverage total (5,928) does not equal reported PS fallback usage (5,778), likely because B365 priority supersedes PS where B365 is available, but exact counting needs verification.
- Coverage improvement is not by itself evidence of predictive gain.

### Phase 1.4 / controlled market-probability experiment
- Candidate reportedly replaced existing Shin probability feature values using B365 plus PS/Max/Avg fallback.
- Reported accuracy: 43.1% → 44.8%.
- Reported log loss: 1.106 → 1.088.
- Reported Brier: 0.5448 → 0.6551.
- Reported draw recall: 8.9% → 5.2%.
- Reported consistent accuracy/log-loss gains across five folds, but Brier score deterioration and draw-recall drop led to no-go.
- Production `src/pipeline.py` and `src/config.py` reportedly untouched.
- Main unresolved issue is whether the Brier values are comparable and whether the candidate was evaluated on the same OOF rows/folds.

### Phase 1.4.1 / current next step
- User was advised to perform a metric/experiment integrity audit before Phase 1.5.
- Audit must check the exact script, saved OOF predictions, same eligible matches/folds, class order, metric formula, probability arrays, sample weights, provider fallback logic, and point-in-time validity.
- Do not tune calibration or draw-specific features until this audit passes.
- Latest user request: create an MD with full conversation history, notes, code, attempts, and results to consult another AI for a fresh/different approach. This document is that handoff.

---

## 20. Questions the next AI must answer

Prioritize these in order. Do not begin with feature brainstorming.

1. **Are Phase 1.4 baseline and candidate metrics comparable?**
   - Are the same eligible matches, OOF rows, and folds used?
   - Is the Brier definition identical?
   - Can metrics be recomputed from saved OOF probability arrays?
   - Do saved OOF predictions exist for both variants?

2. **Why are the Brier values different?**
   - Earlier baseline `0.66619` / `0.6684` versus Phase 1.4 baseline `0.5448`.
   - Identify formula, normalization, weighting, aggregation, sample, or implementation differences.

3. **Why does one diagnostic report 55.4% accuracy and log loss below 0.96?**
   - Compare splitter, fold sizes, dataset hash, leakage guards, model, class labels, and metric implementation.
   - Reconcile `TimeSeriesSplit(5)` with “tournament-aware CV” and inspect whether `src/cv_split.py` is actually used.

4. **Was Phase 1.4 a clean feature-value replacement?**
   - Ensure only `Shin_Prob_H`, `Shin_Prob_D`, and `Shin_Prob_A` changed.
   - Confirm no duplicate columns, changed targets, changed row selection, or other hidden differences.

5. **Are provider fallback counts correct?**
   - B365 613; PS coverage 5,928 but PS fallback usage 5,778; Max 8; Avg 0; imputed 0.
   - Distinguish complete-triplet availability from individual-column availability.
   - Validate the same-provider triplet rule and odds quality/time validity.

6. **What should happen after the audit?**
   - If the experiment is valid, consider a single controlled experiment only after the baseline/candidate comparison is reproducible.
   - Calibration should be trained only on training/OOF data, not the held-out fold.
   - If metrics are not comparable or evidence is mixed, preserve the baseline and stop feature work until evaluation is fixed.

---

## 21. Suggested instructions for the new AI

You may paste this as the opening instruction to the next AI:

> You are reviewing my Argentine football prediction project `ML_Predictor2026_V2` at `C:\Scripts\ML_Predictor2026_V2\`. Read this handoff carefully. Do not assume the reports are correct just because an earlier agent generated them. Distinguish verified code facts from reported claims. Your first task is an independent, minimal-cost audit of Phase 1.4 evaluation integrity—not feature brainstorming. Reconcile baseline and candidate OOF rows/folds, class order, log loss, Brier formula, accuracy, draw metrics, dataset/config hashes, and odds fallback counts. Specifically explain why historical baseline Brier values are around 0.666–0.668 while Phase 1.4 reports 0.5448, and why a separate diagnostic reported 55.4% accuracy / 0.878–0.952 log loss while the frozen baseline is around 43.1% / 1.106. Verify whether `src/cv_split.py` is used or whether evaluation is `TimeSeriesSplit(5)`. Do not change production code or promote the market candidate until you can reproduce the comparison. Preserve temporal batching in `src/batched_features.py`, class encoding `0=Away, 1=Draw, 2=Home`, and all project session skills. Run modules from the project root using `python -m src.module_name`. Return concise findings with file/line references, commands run, evidence, and a GO/NO-GO decision.

---

## 22. Final state / decisions at handoff

- **Production baseline:** retain unchanged.
- **Phase 0.2 temporal integrity:** reported complete; verify no regressions.
- **Phase 1.0 harness:** reported complete and reproducible on older data snapshot.
- **Phase 1.1 sporting-form variants:** no-go; inconclusive.
- **Phase 1.2 rolling form:** no-go; inconclusive paired log-loss result and slightly lower accuracy.
- **Model E manager history:** no-go due to insufficient reliable point-in-time coverage.
- **Model C squad availability:** no-go due to insufficient reliable historical timestamped data.
- **Model G news features:** no-go due to data limitations and no demonstrated incremental value.
- **Phase 1.3 market odds coverage:** reported 100% probability coverage via fallback, but fallback accounting requires verification.
- **Phase 1.4 market probabilities:** reported mixed results and no-go; metrics are not trusted until the Brier/evaluation discrepancy is resolved.
- **Next step:** Phase 1.4.1 metric and experiment integrity audit.
- **Do not start Phase 1.5 calibration tuning yet.**
