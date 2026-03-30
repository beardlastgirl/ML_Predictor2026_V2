# Football Terminology — Canonical Glossary & Mapping

Version: 1.0  
Updated: 2026-03-28  
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
- Last5: Recent form — last five results (chronological left→right)
- Attendance: Average home attendance (season)
- Fixture: Scheduled match (match-level)
- Aggregate: Aggregate score (two-leg ties)
- AwayGoals: Away goals (tiebreaker, if used)
- H2H: Head-to-head (tiebreaker)
- #Pl: Number of players used
- Age: Average age (weighted by minutes)
- Starts: Games started by player
- Min: Minutes played
- 90s: 90s played (Min / 90)
- Gls: Goals (player/team)
- Ast: Assists
- GplusA: Goals + Assists
- GminusPK: Non-penalty goals (G − PK goals)
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
- Gls_90: Goals per 90
- Ast_90: Assists per 90
- GplusA_90: Goals+Assists per 90
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
- ptspermatch, ptsmp, pointspermatch, ppm → Pts/MP
- last5, last5matches, form, formlast5 → Last5
- attendance, att, avgattendance, attendancegame → Attendance
- fixture, match, game → Fixture
- aggregate, agg, aggregatescore → Aggregate
- awaygoals, ag, awayg → AwayGoals
- h2h, headtohead, head-to-head → H2H
- #pl, #players, playersused, usedplayers → #Pl
- age, avgage, ageavg → Age
- starts, gamesstarted, gs → Starts
- min, minutes, mins, timeplayed → Min
- 90s, 90splayed, 90_played, 90m → 90s
- gls, goals, g, scored → Gls
- ast, assists, a → Ast
- g+a, gplusa, g_plus_a, g_a, goalsplusassists → GplusA
- g-pk, gminuspk, nonpkgoals, non-penalty-goals → GminusPK
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
- gls/90, gls_90, goals/90 → Gls_90
- ast/90, ast_90, assists/90 → Ast_90
- g+a/90, gplusa_90, gplusa/90 → GplusA_90
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
- pkm, penmissed, penaltiessissed → PKm
- distacc, distributionacc, longpassacc, gkpassacc → DistAcc
- sweeperactions, keeperoutsideboxactions, sweeper → SweeperActions
- minpergoal, minutespergoal, mpg → MinutesPerGoal
- minperassist, minutesperassist → MinutesPerAssist
- xp, xpoints, expectedpoints → xP
- rankpercentile, rankpct, percentrank → RankPercentile

---

## Football-Data (football-data.co.uk) specific headers & match-level keys

Football-Data CSVs often use match-level headers like FTHG, FTAG, FTR. Map them as follows:

- date → Date
- hometeam → HomeTeam
- awayteam → AwayTeam
- fthg → Home_GF
- ftag → Away_GF
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
- FBref may use per-90 suffixes with slash or space; normalize to underscore form.

---

## Sofascore notes
- Sofascore output may include ratings, live events, player minutes, substitutions. Common mappings:
  - rating, player_rating → Rating
  - min, minutes → Min
  - subs_on, substitutions_in → SubsOn
  - ratings may be floats (validate numeric)

---

## Ambiguities and conflict resolution
- Single-letter headers (A, G, S) can be ambiguous:
  - "A" can be Assists or Away depending on context. If header set contains Home/Away columns or team context, interpret "A" as Away; else prefer Assists.
  - "G" sometimes used for goals or goals conceded. Use adjacency or other headers (GF/GA, Home/Away) to disambiguate.
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
- FBref: xA → xAG, npxG → npxG, xG/90 → xG_90.
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
