API Documentation - ML_Predictor2026_V2

Overview
--------
Quick reference for exported functions and public APIs in src/.

Files and key exports
---------------------
- main.py
  - main(): entry point; calls src.pipeline.run_pipeline() and prints a short summary.

- src/pipeline.py
  - run_pipeline(glossary_path, sofascore_path, fixtures_path, historical_path, model_type, output_dir) -> PipelineResult
  - load_data(glossary_path, sofascore_path, fixtures_path, historical_path) -> (glossary, sofascore_data, matches, fixtures)
  - build_features(matches) -> (matches_with_features, elo_ratings)
  - train_validate(df, features, model_type, n_splits) -> (model, cv_accuracies, cv_log_losses)
  - predict_fixtures(fixtures, elo_ratings, model, features, df_mean, historical_matches, sofascore_data) -> fixtures_with_predictions
  - write_outputs(fixtures, feature_importance, output_dir) -> output_path

- src/stats_engine.py
  - expected_result(elo_team, elo_opp)
  - update_elo(home_elo, away_elo, result)
  - calculate_expected_goals(elo_home, elo_away, avg_gf_home, avg_gf_away, avg_ga_home, avg_ga_away)
  - calculate_outcome_probabilities(xG_home, xG_away, max_goals=MAX_GOALS)
  - calculate_poisson_features(elo_home, elo_away, avg_gf_home, avg_gf_away, avg_ga_home, avg_ga_away)
  - calculate_all_elo_ratings(matches_df, base_elo=BASE_ELO)
  - shin_method(odds)

- src/model_engine.py
  - create_model(model_type, class_weights=None)
  - predict_gameweek(fixtures_df, elo_ratings, model, features, df_mean=None, historical_matches=None, sofascore_data=None)

- src/data_processing.py
  - load_glossary(filepath="Glossary.txt")
  - normalize_team_name(name, glossary=None)
  - load_sofascore_data(filepath="src/sofascore_stats.json", glossary=None)
  - clean_partidos_file(path, glossary=None)
  - parse_fixtures(filepath, glossary=None)

- src/features.py
  - get_team_trailing_stats(history, window)
  - compute_trailing_features(matches_df, window=8)
  - get_all_teams_latest_stats(matches_df, window=8)
  - get_team_stats_from_history(matches_df, team_name, window=8)

- src/utils.py
  - log_info(message), log_ok(message), log_error(message), log_warning(message)
  - find_latest_file(pattern)

Notes and recommendations
-------------------------
- Docstrings were added/expanded in stats_engine.py and utils.py; consider adding similar docstrings to other modules for completeness.
- README.md updated with API_DOCS link and last updated date.
- Complex logic areas worth reviewing: Poisson draw calibration (stats_engine.calculate_outcome_probabilities) and ML/Poisson ensemble blending (model_engine.predict_gameweek).

Suggested next steps
--------------------
- Run test suite: `python -m pytest tests/test_main.py` to ensure no regressions.
- Add missing docstrings for pipeline/model_engine/data_processing modules (optional follow-up).
- Consider exporting a small developer HOWTO in DEV_CONTEXT/ for adding glossary entries and running scrapers.
