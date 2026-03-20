# BUG_TRACKING.md

## Bug Tracking Template

| ID | Date | Description | Root Cause | Resolution | Status |
|----|------|-------------|------------|------------|--------|
| B001 | 2026-02-27 | json module not defined in load_sofascore_data() | json import was missing in main.py | Added `import json` to imports section | Fixed |
| B002 | 2026-02-27 | Sofascore Apify data not loading correctly | load_sofascore_data() expected manual format, not Apify format | Updated function to handle both Apify and manual JSON formats | Fixed |
| B003 | 2026-02-27 | All scores were 2-1 or 1-2, no draws | Score generation forced home/away wins regardless of Poisson probabilities | Rewrote score logic to use actual Poisson most-likely scoreline, only adjust with high confidence threshold | Fixed |
| B004 | 2026-02-27 | Prediction_Label didn't match Predicted scores | Label was based on ML prediction, not actual predicted scores | Changed to derive label from actual predicted goals (Pred_Home_Goals vs Pred_Away_Goals) | Fixed |

## 2026-02-27 Bug Details

### B001: json module not defined
**Date**: 2026-02-27
**Description**: When running main.py, Sofascore data loading failed with "name 'json' is not defined"
**Root Cause**: The load_sofascore_data() function used json.load() but json module was not imported
**Resolution**: Added `import json` to the imports section in main.py
**Status**: Fixed

### B002: Sofascore Apify data format mismatch
**Date**: 2026-02-27
**Description**: Apify scraper outputs data in a nested format with "standings" key, but load_sofascore_data() expected flat array with "normalized" field
**Root Cause**: The function was written for manual JSON format only
**Resolution**: Updated load_sofascore_data() to detect format and parse accordingly:
- Apify format: Extract from teams[].standings[].rows[]
- Manual format: Use teams[] array directly with normalized field
**Status**: Fixed

## Previous Bugs (from V1)

See ML_Predictor2026 DEV_CONTEXT/BUG_TRACKING.md for historical bugs.
