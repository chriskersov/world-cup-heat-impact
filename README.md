# Climate Advantage at the FIFA World Cup 2026

**Historical Evidence and Predictive Implications**

> **Interactive dashboard:** [world-cup-heat-impact.vercel.app](https://world-cup-heat-impact.vercel.app)

---

## Overview

Investigates whether warm-climate national teams hold a systematic advantage over cool-climate teams at FIFA World Cups, combining 90 years of historical data (1930-2022, n=964 matches) with Monte Carlo simulations of the 2026 tournament across USA, Canada, and Mexico.

Methods: Koppen-Geiger climate classification, Elo-adjusted performance analysis, permutation testing, and 100,000 full-tournament climate-adjusted simulations.

---

## Historical Finding

| Metric                              | Value           |
| ----------------------------------- | --------------- |
| Warm team win rate in warm Cups     | 52.5%           |
| Warm team win rate in cool Cups     | 46.1%           |
| Gap                                 | +6.4pp          |
| p-value (permutation)               | 0.02            |
| Cohen's d                           | 0.15            |
| Post-1990 climate boost coefficient | +3.2% per match |
| Tournaments analysed                | 22 (1930-2022)  |

---

## Two Approaches

**Approach 1: Climate Flagging**

Flags knock-out matchups where venue temp >22C and a warm-climate team faces a cool-climate opponent. Result: 10 Tier 1 (Strong), 28 Tier 2 (Moderate), 2,134 Tier 3 (Weak) flagged matchups.

**Approach 2: Climate-Adjusted Monte Carlo**

100,000 full-tournament simulations applying the +3.2% post-1990 boost to warm teams vs cool teams in venues >22C. Compared against a pure Elo baseline.

---

## Top Winners (Approach 2, Climate-Adjusted)

| Rank | Team      | Win Prob | Climate Delta |
| ---- | --------- | :------: | :-----------: |
| 1    | Spain     |  17.0%   |    +0.1pp     |
| 2    | Argentina |  13.9%   |    +0.1pp     |
| 3    | France    |  10.8%   |    -0.6pp     |
| 4    | Brazil    |   5.9%   |    +0.6pp     |
| 5    | Colombia  |   5.3%   |    +0.4pp     |

**Largest climate beneficiaries:** Brazil (+0.6pp), Ecuador (+0.6pp), Colombia (+0.4pp)
**Largest climate penalties:** France (-0.6pp), Norway (-0.5pp)

---

## Pipeline

Historical Data → Climate Classification → Elo-Adjusted Performance → Permutation Testing → 2026 Dataset Construction → Knockout Matchup Probabilities → Approach 1 (Flagging) → Approach 2 (Climate-Adjusted Simulation)

---

## Data Sources

- FIFA World Cup match data (1930-2022)
- Elo ratings from eloratings.net
- Koppen-Geiger climate classification per country
- Host city/venue temperature data for 2026

---

## Project Structure

```
report/
  01_historical_climate_analysis.ipynb     # 90-year climate performance analysis
  02_elo_adjusted_performance.ipynb        # Elo-adjusted warm/cool comparison
  03_2026_dataset_and_monte_carlo.ipynb    # Group stage and Monte Carlo baseline
  04_knockout_matchup_probabilities.ipynb  # Knockout matchup probabilities
  05_climate_flagging_and_predictive...    # Approach 1: Climate flagging
  06_approach2_climate_adjusted...         # Approach 2: Climate-adjusted simulation
  generate_figures.py                      # Generate all 15 publication figures
  figures/                                 # Publication-quality PNGs

data/                                      # Raw and derived datasets, simulation exports

public/                                    # Interactive web dashboard (React + Chart.js)
  index.html
  data/
```

---

## Reproduction

1. `pip install numpy pandas matplotlib seaborn scipy jupyter`
2. Run report notebooks in order: `01` → `02` → `03` → `04` → `05` → `06`
3. Regenerate figures: `python report/generate_figures.py`
4. View dashboard: open `public/index.html`
