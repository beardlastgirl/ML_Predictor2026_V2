# Football Terminology — Canonical Glossary & Mapping

Version: 1.1  
Updated: 2026-07-31  
Purpose: canonical keys + common alternate labels from Football-Data (Argentina CSVs), FBref, Sofascore, and other common sources. Use this to normalize scraped headers into a single schema.

---

## Short instructions
- Use the canonical key column as your script's internal field names.
- Normalize input header strings (lowercase, strip punctuation/whitespace, replace symbols) then look them up in the mapping table.
- Apply provider-specific overrides when detecting file origin (football-data, fbref, sofascore).
- Log original header → normalized → canonical for traceability.

---

## Canonical glossary (canonical_key : short description)
- Rk: Rank (league position / final round in knockouts)
- MP: Matches Played (alias: Pld)
- W: Wins
- D: Draws
- L: Losses
- GF: Goals For (team)
- GA: Goals Against (team)
- GD: Goal Difference (GF − GA)
- Pts: Points (league points)
- Pts/MP: Points per Match (Pts divided by MP)
- Poss: Possession percentage (team average)
- Last5: Recent form — last five results (chronological left→right)
- Attendance: Average home attendance (season)
- Date: Match date
- Time: Match kick-off time
- Fixture: Scheduled match (match-level)
- Aggregate: Aggregate score (two-leg ties)
- AwayGoals: Away goals (tiebreaker, if used)
- H2H: Head-to-head (tiebreaker)
- HomeTeam: Home team name
- AwayTeam: Away team name
- Home_GF: Full-time goals scored by home team (football-data: FTHG)
- Away_GF: Full-time goals scored by away team (football-data: FTAG)
- FullTimeResult: Full-time result code (H/D/A)
- HT_Home_GF: Half-time goals scored by home team (football-data: HTHG)
- HT_Away_GF: Half-time goals scored by away team (football-data: HTAG)
- HalfTimeResult: Half-time result code (H/D/A)
- #Pl: Number of players used
- Age: Average age (weighted by minutes)
- Starts: Games started by player
- Min: Minutes played
- 90s: 90s played (Min / 90)
- Gls: Goals (player/team)
- Ast: Assists
- GplusA: Goals + Assists
- GminusPK: Non-penalty goals (G − PK goals)
- GplusAminusPK: Non-penalty goals + Assists (G+A−PK goals); FBref column G+A-PK
- PK: Penalties converted
- PKatt: Penalty attempts
- CrdY: Yellow cards
- CrdR: Red cards
- xG: Expected goals (shot probability)
- xG_90: xG per 90
- xGA: Expected goals allowed (team)
- xGD: xG difference (xG − xGA)
- npxG: Non-penalty xG (penalties excluded)
- npxG_90: npxG per 90
- xAG: Expected assisted goals (xA)
- npxG_xAG: npxG + xAG (combined non-penalty expected threat)
- PrgP: Progressive passes
- PrgC: Progressive carries
- Gls_90: Goals per 90 (FBref column Gls_1 in some tables)
- Ast_90: Assists per 90 (FBref column Ast_1 in some tables)
- GplusA_90: Goals+Assists per 90 (FBref column G+A_1 in some tables)
- GminusPK_90: Non-penalty goals per 90 (FBref column G-PK_1 in some tables)
- Shots: Total shots attempted
- SoT: Shots on target
- SoTA: Shots on target against (keeper/team)
- ShotConv: Shot conversion (Goals / Shots)
- PSxG: Post-shot xG (if available)
- SCA: Shot-creating actions
- GCA: Goal-creating actions
- KeyPasses: Key passes (lead to shot)
- Passes: Passes attempted
- PassAcc: Pass completion percentage
- PassInto3rd: Passes into final third
- PassIntoBox: Passes into penalty area
- PPDA: Passes Per Defensive Action (press measure)
- Tackles: Successful tackles
- Interceptions: Interceptions
- Blocks: Blocks
- Clearances: Clearances
- AerialWon: Aerial duels won
- Recoveries: Ball recoveries
- ErrorsToShot: Errors leading to shot/goal
- Goalkeeper: Primary keeper (most minutes)
- CS: Clean sheets
- CSpct: Clean sheet percentage
- SavePct: Save percentage
- PKsv: Penalties saved
- PKA: Penalties allowed
- PKm: Penalties missed
- DistAcc: Distribution accuracy (keeper)
- SweeperActions: Keeper actions outside penalty area
- MinutesPerGoal: Minutes per goal
- MinutesPerAssist: Minutes per assist
- xP: Expected points (modelled)
- RankPercentile: Percentile rank inside league
- Rating: Player/team rating (Sofascore)
- SubsOn: Substitutions on (Sofascore)

---

## Mapping table — common alternate labels → canonical key

Notes:
- Normalization rules: lowercase, remove spaces, underscores, slashes, percent signs, and punctuation. Replace "+" with "plus", "-" with "minus" if helpful.
- The left column shows common normalized input forms you may encounter. The right column is the canonical key your script should use.

Use provider-specific overrides first (football-data, fbref, sofascore), then fall back to the general mapping.

Normalized input form → canonical key

- rk, pos, position, rank → Rk
- mp, pld, played, matchesplayed, matches, gp → MP
- w, won, wins → W
- d, draw, draws, t → D
- l, loss, losses → L
- gf, f, goalsfor, for, gf_team → GF
- ga, a, goalsagainst, against, ga_team → GA
- gd, goaldiff, goaldifference, gdiff, plusminus → GD
- pts, points, p, pt → Pts
- ptspermatch, ptsmp, pointspermatch, ppm, pointspergame, ppg → Pts/MP
- poss, possession, possessionpct → Poss
- last5, last5matches, form, formlast5 → Last5
- attendance, att, avgattendance, attendancegame → Attendance
- date → Date
- time → Time
- fixture, match, game → Fixture
- aggregate, agg, aggregatescore → Aggregate
- awaygoals, ag, awayg → AwayGoals
- h2h, headtohead, head-to-head → H2H
- hometeam, home → HomeTeam
- awayteam, away → AwayTeam
- homegf, fthg, hg → Home_GF
- awaygf, ftag, ag_goals → Away_GF
- fulltimeresult, ftr, res, result → FullTimeResult
- hthomegf, hthg → HT_Home_GF
- htawaygf, htag → HT_Away_GF
- halftimeresult, htr → HalfTimeResult
- #pl, #players, playersused, usedplayers → #Pl
- age, avgage, ageavg → Age
- starts, gamesstarted, gs → Starts
- min, minutes, mins, timeplayed → Min
- 90s, 90splayed, 90_played, 90m → 90s
- gls, goals, g, scored → Gls
- ast, assists → Ast
- gplusa, gplus_a, goalsplusassists → GplusA
- gplusaminuspk, gplusaminuspk → GplusAminusPK
- gminuspk, nonpkgoals, non-penalty-goals → GminusPK
- pk, pen, pens, penalties, penalties_converted → PK
- pkatt, penatt, penaltyattempts, pkattempts → PKatt
- crdy, yellow, yc, yellowcards → CrdY
- crdr, red, rc, redcards → CrdR
- xg, expected_goals, expg → xG
- xg90, xg/90, xg_90 → xG_90
- xga, xgallowed, xg_against → xGA
- xgd, xgdiff, xg_difference, xg_plus_minus → xGD
- npxg, npxg_total, nonpenxg, non_pen_xg → npxG
- npxg90, npxg/90, npxg_90 → npxG_90
- xa, xag, x_assists, expected_assists → xAG
- npxg+xag, npxg_xag, npxg_plus_xag → npxG_xAG
- prgp, prgpass, progressivepasses, progp → PrgP
- prgc, prgcarry, progressivecarries, progc → PrgC
- gls/90, gls_90, goals/90, gls_1 → Gls_90
- ast/90, ast_90, assists/90, ast_1 → Ast_90
- g+a/90, gplusa_90, gplusa/90, gplusa_1 → GplusA_90
- g-pk/90, gminuspk_90, gminuspk_1 → GminusPK_90
- shots, sh, totalshots, attempts → Shots
- sot, s.o.t, shotsontarget, shotsontarget_count → SoT
- sota, s.o.t.a, shotsontargetagainst, shots_on_target_against → SoTA
- shot%, shotconv, conversion%, goalspershot, goals_per_shot → ShotConv
- psxg, postshotxg, post-shot-xg → PSxG
- sca, shotcreatingactions, shot-creating-actions → SCA
- gca, goalcreatingactions, goal-creating-actions → GCA
- keypasses, kp, key_pass → KeyPasses
- passes, pass, passatt, passesattempted → Passes
- pass%, passacc, passcompletion, passcompletion% → PassAcc
- passinto3rd, passesintofinalthird, into3rd → PassInto3rd
- passintobox, passesintobox, into_box → PassIntoBox
- ppda, passesperdefensiveaction, ppda_value → PPDA
- tackles, tkl, tackleswon → Tackles
- interceptions, int, intercepts → Interceptions
- blocks, blk, blocked → Blocks
- clearances, clr, clear → Clearances
- aerialwon, aerialswon, aerialduelswon → AerialWon
- recoveries, recov, ballrecoveries → Recoveries
- errorstoshot, errortoshot, error_leading_to_shot → ErrorsToShot
- goalkeeper, gk, keeper → Goalkeeper
- cs, cleansheets, shutouts → CS
- cs%, cleansheet%, cleansheetpct → CSpct
- save%, savepct, sv%, saves% → SavePct
- pksv, pensaves, penaltiessaved → PKsv
- pka, penallowed, pensallowed → PKA
- pkm, penmissed, penaltiesmissed → PKm
- distacc, distributionacc, longpassacc, gkpassacc → DistAcc
- sweeperactions, keeperoutsideboxactions, sweeper → SweeperActions
- minpergoal, minutespergoal, mpg → MinutesPerGoal
- minperassist, minutesperassist → MinutesPerAssist
- xp, xpoints, expectedpoints → xP
- rankpercentile, rankpct, percentrank → RankPercentile
- rating, player_rating → Rating
- subson, subs_on, substitutions_in → SubsOn

---

## Football-Data (football-data.co.uk) specific headers & match-level keys

Football-Data CSVs often use match-level headers like FTHG, FTAG, FTR. Map them as follows:

- date → Date
- time → Time
- hometeam → HomeTeam
- awayteam → AwayTeam
- home → HomeTeam
- away → AwayTeam
- fthg → Home_GF
- hg → Home_GF
- ftag → Away_GF
- ag → Away_GF
- ftr → FullTimeResult (values often H/D/A — map to standardized result codes)
- hthg → HT_Home_GF
- htag → HT_Away_GF
- htr → HalfTimeResult
- b365h → Odds_b365_H
- b365d → Odds_b365_D
- b365a → Odds_b365_A
- similarly: bwh, bwd, bwa → Odds_bw_H/D/A; psH/psD/psA for Pinnacle, etc. (normalize bookmaker names)

When parsing football-data files:
- Detect presence of FTHG/FTAG as priority to extract match score.
- Use bookmaker prefixes to group odds into Odds_{bookie}_{outcome}.

---

## FBref common patterns (mapping notes)
- FBref uses xG, npxG, xA, SCA, GCA and per-90 variants like xG/90. Map:
  - xG → xG
  - npxG → npxG
  - xA → xAG
  - SCA → SCA
  - GCA → GCA
  - xG/90 → xG_90
  - npxG/90 → npxG_90
  - Poss → Poss
- FBref may use per-90 suffixes with slash or space; normalize to underscore form.
- FBref advanced stats tables use `_1` as a per-90 suffix on some columns (e.g. `Gls_1`, `Ast_1`, `G+A_1`, `G-PK_1`). These map to the `_90` canonical keys:
  - Gls_1 → Gls_90
  - Ast_1 → Ast_90
  - G+A_1 → GplusA_90
  - G-PK_1 → GminusPK_90
- FBref uses `G+A-PK` for combined non-penalty goals + assists (maps to GplusAminusPK).
- FBref squad abbreviations used in CSV files (e.g. `Cen. Córdoba–SdE`, `Gimnasia–LP`, `Gimnasia–M`, `Sarmiento–J`, `Estudiantes–LP`, `Estudiantes–RC`, `Talleres–C`, `Ind. Rivadavia`, `Atlé Tucumán`, `Arg Juniors`) should be resolved via Glossary.txt before header normalization.

---

## Sofascore notes
- Sofascore output may include ratings, live events, player minutes, substitutions. Common mappings:
  - rating, player_rating → Rating
  - min, minutes → Min
  - subs_on, substitutions_in → SubsOn
  - ratings may be floats (validate numeric)
- Sofascore standings rows use different field names from the canonical schema. The `load_sofascore_data()` function handles the translation:
  - matches → MP
  - wins → W
  - draws → D
  - losses → L
  - scoresFor → GF (goals for)
  - scoresAgainst → GA (goals against)
  - scoreDiffFormatted → string representation of GD (e.g. "+10", "-3"); parse to int for calculations
  - points → Pts
  - pointsPerGame → Pts/MP (float)
  - position → Rk
- Sofascore team objects include `nameCode` (3-letter code, e.g. "ELP", "BOC") which can aid disambiguation.
- Team names from Sofascore are full Spanish names (e.g. "Gimnasia y Esgrima Mendoza", "Estudiantes de Río Cuarto") — resolve via Glossary.txt.

---

## Ambiguities and conflict resolution
- Single-letter headers (A, G, S) can be ambiguous:
  - "A" can be Assists or Away-goals depending on context. If header set contains Home/Away columns or team context, interpret "A" as GA (goals against/away); else prefer Assists. Note: the general mapping maps `a` → GA; for player-level tables where no HomeTeam/AwayTeam context exists, apply provider-specific override to map to Ast.
  - "G" sometimes used for goals or goals conceded. Use adjacency or other headers (GF/GA, Home/Away) to disambiguate.
- FBref per-90 suffix collision: `_1` suffix (e.g. Gls_1) means "per 90" in FBref advanced stats tables, NOT a first-instance indicator. Always check if file origin is fbref before treating `_1` as per-90.
- When both "xG" and "npxG" present, keep both with canonical keys xG and npxG.
- When two candidate input headers normalize to same canonical key, prefer provider-specific mapping order; if still ambiguous, keep both fields with provenance suffix (e.g., Gls_providerA vs Gls_providerB) or log a conflict.
- Keep provenance: original header name and provider in your parsed object (e.g., meta.original_header, meta.provider).

---

## Normalization & matching strategy (recommended)
1. Preprocess header string:
   - header_norm = header.lower()
   - header_norm = header_norm.replace('%','pct').replace('+','plus').replace('-','minus')
   - header_norm = re.sub(r'[^a-z0-9]', '', header_norm)  # remove punctuation, spaces, slashes, underscores
2. Attempt exact lookup in provider-specific mapping (if provider known).
3. If not found, attempt exact lookup in general mapping table above.
4. If still not found, attempt fuzzy match:
   - Token overlap (Jaccard) or Levenshtein ratio; conservative thresholds (e.g., ratio ≥ 0.8).
5. If still unresolved, mark as Unmapped and store original header. Emit a warning for critical fields (Date, HomeTeam, AwayTeam, FTHG/FTAG).
6. Maintain a mapping_log entry: { original_header, normalized, canonical_or_null, provider_guess }.

---

## Validation & leaderboard qualification rules
- Default qualification thresholds (configurable):
  - Minimum minutes: 900 minutes for season leaderboards.
  - Or: 30 minutes per squad match (as alternate).
- For per-90 rates, compute only if minutes > 0; consider a minimum minutes threshold when ranking.
- For keeper metrics (CS, SavePct), clarify whether penalty events are included/excluded for your data source; default convention: SavePct excludes penalties unless provider states otherwise.

---

## Example mapping pseudocode (Python-style)
- Normalize:
  - def normalize(header): 
      s = header.lower()
      s = s.replace('%','pct').replace('+','plus').replace('/','').replace('_','').replace(' ','')
      s = re.sub(r'[^a-z0-9]','', s)
      return s
- Map:
  - norm = normalize(header)
  - if provider and norm in provider_map[provider]: canonical = provider_map[provider][norm]
  - elif norm in general_map: canonical = general_map[norm]
  - else: canonical = fuzzy_match(norm, general_map) or None

---

## Examples / corner cases
- Football-Data CSV: FTHG → Home_GF, FTAG → Away_GF, FTR → FullTimeResult. Bookmaker columns like B365H → Odds_b365_H.
- FBref league table: Rk, Squad, MP, W, D, L, GF, GA, GD, Pts, Pts/MP — all map directly.
- FBref advanced stats: `Poss` → Poss; `G+A-PK` → GplusAminusPK; `Gls_1` → Gls_90; `Ast_1` → Ast_90; `G+A_1` → GplusA_90; `G-PK_1` → GminusPK_90.
- FBref: xA → xAG, npxG → npxG, xG/90 → xG_90.
- Sofascore standings: `scoresFor` → GF, `scoresAgainst` → GA, `scoreDiffFormatted` → GD (parse string), `matches` → MP, `pointsPerGame` → Pts/MP.
- If a file has both "A" and "Ast", prefer the explicit "Ast" mapping and treat "A" as ambiguous; consult provider context.
- When encountering "G/P" or similar mixed headers, split tokens and map each piece individually where possible.

---

## Recommended deliverables for your repo (optional)
- general_mapping.json (normalized-form → canonical key)
- football_data_mapping.json (provider overrides)
- fbref_mapping.json (provider overrides)
- sofascore_mapping.json (provider overrides)
- schema_readme.md (this file)
- parse_log format example (specify fields for provenance and warnings)
