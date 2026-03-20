# Feature Landscape

**Domain:** Football Match Prediction (Sports Betting / Analytics)
**Researched:** 2026-03-19

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| 1X2 Probabilities | Core output for match outcome prediction. | Low | Must be calibrated to real-world frequencies. |
| Scoreline Probabilities | Required for Exact Score and Over/Under markets. | Medium | Use Poisson/Dixon-Coles models. |
| Elo / Power Ratings | Baseline measure of team strength. | Low | Needs constant updating after every match. |
| Recent Form (Last N) | Captures momentum and short-term trends. | Low | Use rolling averages with time-decay. |
| Home Advantage | Major factor in match outcomes (crowd, travel). | Low | Varies by league and crowd presence. |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Expected Goals (xG) | Measures quality of chances created, not just goals. | High | Requires event-level data (shots, location). |
| Expected Threat (xT) | Measures action impact on goal probability. | High | Needs granular tracking/event data. |
| Closing Line Value (CLV) | Benchmarks model against market's "sharpest" price. | Medium | Requires historical odds from multiple bookies. |
| Player Availability | Captures impact of injuries/suspensions to key players. | High | Hard to automate; needs reliable news scraping. |
| Rest & Congestion | Impact of travel and days between matches. | Medium | Critical for teams in multiple competitions (e.g., Copa Libertadores). |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| "Lock" / "Sure Bet" | Deceptive and unprofessional in probability. | Use "Expected Value (EV)" and "Edge". |
| Direct Classification | Categorical W/D/L prediction ignores probability spread. | Always output calibrated probabilities. |
| Static Poisson | Simple Poisson ignores home/away goal correlation. | Use Bivariate Poisson / Dixon-Coles. |

## Feature Dependencies

```
Historical Results → Elo Ratings
Event Data → xG / xT
Historical Odds → Calibration Layer (CLV)
Scraping Agent → Real-time Injury Data
```

## MVP Recommendation

Prioritize:
1. **Calibrated 1X2 Probabilities**: Using Elo + Form as features.
2. **Dixon-Coles Scoreline Engine**: For realistic probability spreads.
3. **Closing Odds Integration**: To benchmark model accuracy vs. market consensus.

Defer: **xT / Kinematic Features**: High data cost for marginal gains in early development phases.

## Sources

- [Pinnacle: The Importance of Closing Line Value](https://www.pinnacle.com/en/betting-resources/)
- [Soccermatics (David Sumpter): xG and Advanced Metrics](https://soccermatics.org/)
- [EconPapers: The Bivariate Poisson Distribution in Football Modeling](https://econpapers.repec.org/)
