### Action Plan to Improve Prediction Accuracy: ML_Predictor2026_V2

This action plan is structured in prioritized phases, addressing foundational issues first, followed by model enhancements and continuous improvement.

#### **Phase 1: Critical Data Foundation & Heuristic Elimination (Immediate Priority)**

1.  **Rectify Missing `Glossary.txt` (Highest Priority - Immediate Action)**
    *   **Description**: The absence of `Glossary.txt` is a critical data quality blocker. Without proper team name normalization, all downstream features and historical data are compromised.
    *   **Action**: Locate or recreate a comprehensive `Glossary.txt` file at the project root. This file must map all known variations of team names across all data sources (historical, scraped, fixtures) to a canonical form.
    *   **Verification**: Ensure `src/data_processing.normalize_team_name` correctly applies the glossary and that historical data merges accurately. Add a test in `tests/` specifically for `normalize_team_name` using various glossary entries.
    *   **Impact**: Resolves fundamental data integrity issues, enabling accurate feature generation.

2.  **Systematically Eliminate Hardcoded Heuristics & Manual Adjustments**
    *   **Description**: The model currently relies heavily on arbitrary constants and rule-based post-processing, limiting its learning capacity and generalizability.
    *   **Actions**:
        *   **Refactor `_calculate_hybrid_goals` (High Priority)**: Replace the complex `if/elif` logic in `src/model_engine._calculate_hybrid_goals` with a more data-driven approach. Consider training a separate sub-model (e.g., a simple regression model or a decision tree) to predict score differences or exact scores based on ML and Poisson probabilities, rather than hardcoded rules.
        *   **Data-Driven Draw Calibration (High Priority)**: Re-evaluate and potentially refactor the `POISSON_DRAW_ADJUSTMENT` and `HOME_ADVANTAGE_BOOST` in `src/stats_engine.calculate_outcome_probabilities`. Instead of fixed multipliers, explore methods to learn these adjustments from data (e.g., Platt scaling, isotonic regression on probabilities, or incorporate confidence directly into ML model) or integrate them more seamlessly as features into the ML model.
        *   **Dynamic Sample Weights for Imbalance (Medium Priority)**: Replace the hardcoded `0.7` `sample_weight` for draws in `src/pipeline.train_validate` with a dynamic approach. Explore techniques like:
            *   Calculating class weights based on inverse class frequency for each fold.
            *   Using more advanced sampling techniques (e.g., SMOTE, undersampling) if the class imbalance is severe and standard weighting is insufficient.
    *   **Verification**: Implement A/B testing or backtesting to compare performance before and after heuristic removal. Ensure model output is more aligned with predicted probabilities.
    *   **Impact**: Increases model's ability to learn from data, improves generalizability, and reduces manual biases.

#### **Phase 2: Model & Feature Sophistication (Post-Foundation)**

1.  **Dynamic Parameter Estimation for Poisson (Claude-code Rec)**
    *   **Description**: The current Poisson model uses a constant `BASE_GOAL_RATE`. More sophisticated models could estimate parameters dynamically.
    *   **Action**: Investigate dynamic estimation of offensive/defensive ratings or base rates.
        *   Implement a separate model (e.g., Bayesian inference, maximum likelihood estimation) to estimate attack and defense strengths for each team based on recent performance, replacing the `avg_gf`/`avg_ga` features derived from simple trailing averages. These new, more dynamic team strengths would then feed into the xG calculation.
        *   Consider estimating league-average `BASE_GOAL_RATE` on a rolling basis or per season, rather than using a fixed constant.
    *   **Verification**: Compare xG values and Poisson probabilities from new methods against current. Evaluate impact on overall model performance.
    *   **Impact**: Improves the accuracy and adaptability of the Poisson model component.

2.  **Incorporate Temporal Dynamics & Feature Engineering Enhancements (Claude-code Rec)**
    *   **Description**: Leverage the time-series nature of data more effectively.
    *   **Actions**:
        *   **Advanced xG Features**: Explore creating more advanced xG features based on shot quality, player statistics, or game state, beyond simple Elo and `GF/GA` averages.
        *   **Player-Level Features**: If available, incorporate player form, injuries, or key player statistics as features.
        *   **Tactical/Managerial Features**: If data is available, include features for recent managerial changes, team formations, or playing styles.
        *   **Decay for Trailing Averages**: Instead of uniform `TRAILING_WINDOW`, apply exponential decay to recent matches for more responsive form metrics.
    *   **Verification**: Feature importance analysis (using generated chart) and performance gains in CV.
    *   **Impact**: Provides the model with richer, more predictive information about team performance.

3.  **Automated Hyperparameter Tuning (Claude-code Rec)**
    *   **Description**: Optimize CatBoost/LightGBM hyperparameters.
    *   **Action**: Integrate an automated hyperparameter tuning framework (e.g., Optuna, Hyperopt, GridSearchCV) into the `train_validate` function. Run tuning periodically or when significant changes to features/data occur.
    *   **Verification**: Document tuned hyperparameters and demonstrate performance improvements over fixed ones.
    *   **Impact**: Maximizes the performance of the chosen ML models.

#### **Phase 3: Evaluation & Robustness (Continuous Improvement)**

1.  **Granular Evaluation Metrics & Visualizations**
    *   **Description**: Gain deeper insights into model performance, especially for different outcomes.
    *   **Actions**:
        *   **Per-Class Metrics**: In `src/pipeline.train_validate` and `main.py`, calculate and report precision, recall, and F1-score for each class (Home Win, Draw, Away Win).
        *   **Calibration Plots**: Implement reliability diagrams (calibration plots) to visualize the calibration of predicted probabilities. This is crucial given the blending and adjustments.
        *   **Confusion Matrix**: Generate and visualize confusion matrices during evaluation.
    *   **Verification**: Targeted improvements in specific outcome predictions.
    *   **Impact**: Provides actionable insights into model strengths and weaknesses, guiding further development.

2.  **Implement Robust Error Handling & Logging (Claude-code Rec)**
    *   **Description**: Enhance the pipeline's resilience and diagnosability.
    *   **Actions**:
        *   **Strict Data Validation**: Improve `src/validation.py` to be more stringent. For critical data quality issues (e.g., missing essential columns, unparseable team names), raise errors instead of just warnings, halting the pipeline until fixed.
        *   **Detailed Logging**: Ensure all data ingestion, processing, and feature building steps log not just success/failure but also statistics (e.g., number of rows processed, number of NaNs handled, feature distributions).
        *   **Alerting**: Consider integrating basic alerting for pipeline failures in a production environment.
    *   **Verification**: Pipeline gracefully handles (or explicitly fails) expected error conditions.
    *   **Impact**: Improves pipeline reliability and reduces silent failures.
