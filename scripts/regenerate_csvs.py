#!/usr/bin/env python3
"""Regenerate CSV files from fresh JSON simulation data."""
import json, math, os
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
REPORT_DATA = ROOT / 'report' / 'data'
N_SIMS = 100_000

# Load fresh JSON
a1 = json.load(open(DATA / 'approach1_results.json'))
a2 = json.load(open(DATA / 'approach2_results.json'))
comp = json.load(open(DATA / 'approach_comparison.json'))
flagged = json.load(open(DATA / 'flagged_matchups.json'))
team_climate = json.load(open(DATA / 'team_climate.json'))

# ── 2026_monte_carlo_results.csv ──
a1_df = pd.DataFrame(a1)
a1_df.to_csv(DATA / '2026_monte_carlo_results.csv', index=False)
print(f'monte_carlo_results.csv: {len(a1_df)} rows')

# ── 2026_approach2_results.csv ──
a2_df = pd.DataFrame(a2)
a2_df.to_csv(DATA / '2026_approach2_results.csv', index=False)
print(f'approach2_results.csv: {len(a2_df)} rows')

# ── 2026_approach1_vs_approach2_comparison.csv ──
comp_df = pd.DataFrame(comp)
comp_df.to_csv(DATA / '2026_approach1_vs_approach2_comparison.csv', index=False)
print(f'approach1_vs_approach2_comparison.csv: {len(comp_df)} rows')

# ── 2026_climate_impact_significance.csv ──
significant = []
for t in comp:
    p1 = t['A1_Winner'] / 100
    p2 = t['A2_Winner'] / 100
    delta_pp = t['Winner_Delta']
    se = math.sqrt(p1 * (1 - p1) / N_SIMS + p2 * (1 - p2) / N_SIMS)
    if se > 0:
        z = (p2 - p1) / se
        p_val = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    else:
        z = 0
        p_val = 1.0
    significant.append({
        'Team': t['Team'],
        'A1_Win_Prob': round(p1 * 100, 2),
        'A2_Win_Prob': round(p2 * 100, 2),
        'Delta_pp': round(delta_pp, 2),
        'Z_stat': round(z, 2),
        'P_value': round(p_val, 6),
        'Significant': abs(z) > 1.96
    })
sig_df = pd.DataFrame(significant)
sig_df.to_csv(DATA / '2026_climate_impact_significance.csv', index=False)
print(f'climate_impact_significance.csv: {len(sig_df)} rows')

# ── 2026_climate_flagged_matchups.csv ──
# Build the schema expected by generate_figures.py
fl_rows = []
for m in flagged:
    warm_t = m.get('Warm_Team', '')
    cool_t = m.get('Cool_Team', '')
    prob = m.get('Prob_Pct', 0) / 100.0  # convert from percentage to ratio
    elo_w = m.get('Elo_Warm', 0)
    elo_c = m.get('Elo_Cool', 0)
    
    koppen_w = team_climate.get(warm_t, {}).get('koppen', '')
    koppen_c = team_climate.get(cool_t, {}).get('koppen', '')
    zone_w = team_climate.get(warm_t, {}).get('zone', '')
    zone_c = team_climate.get(cool_t, {}).get('zone', '')
    
    # Climate scores (from run_fixed_simulation.py KOPPEN_SCORES)
    koppen_scores = {
        'Af': 1.0, 'Am': 1.0, 'Aw': 1.0, 'BWh': 0.9, 'BSh': 0.9,
        'Csa': 0.5, 'Csb': 0.5, 'Cfa': 0.5, 'Cfb': 0.5,
        'Dfa': 0.2, 'Dfb': 0.2, 'Dfc': 0.2, 'Dwa': 0.2, 'Dwb': 0.2, 'Dwc': 0.2,
        'BWk': 0.4, 'BSk': 0.4, 'Cwa': 0.5, 'Cwb': 0.5, 'Cfc': 0.3,
        'ET': 0.1, 'Csc': 0.4, 'Cwc': 0.3,
    }
    score_w = koppen_scores.get(koppen_w, 0.5)
    score_c = koppen_scores.get(koppen_c, 0.5)
    
    fl_rows.append({
        'Team_A': warm_t,
        'Team_B': cool_t,
        'Probability': round(prob, 4),
        'Elo_A': elo_w,
        'Elo_B': elo_c,
        'Elo_Diff': round(elo_w - elo_c, 1),
        'Warm_A': 1,  # warm team is always in A position
        'Warm_B': 0,
        'Koppen_A': koppen_w,
        'Koppen_B': koppen_c,
        'Climate_Zone_A': zone_w,
        'Climate_Zone_B': zone_c,
        'Is_Climate_Clash': 1,
        'Warm_Team': warm_t,
        'Cool_Team': cool_t,
        'Climate_Score_A': score_w,
        'Climate_Score_B': score_c,
        'Venue_Temp_C': m.get('Venue_Temp_C', 0),
        'Climate_Diff_Score': m.get('Climate_Diff_Score', 0),
        'p_adjustment': round(0.032 * m.get('Climate_Diff_Score', 0), 4),
        'Climate_Flag_Tier': m.get('Climate_Flag_Tier', 'None'),
    })

fl_df = pd.DataFrame(fl_rows)
fl_df.to_csv(DATA / '2026_climate_flagged_matchups.csv', index=False)
print(f'climate_flagged_matchups.csv: {len(fl_df)} rows')

# ── Copy to report/data/ for generate_figures.py ──
REPORT_DATA.mkdir(parents=True, exist_ok=True)
for fname in ['2026_monte_carlo_results.csv', '2026_approach2_results.csv',
              '2026_approach1_vs_approach2_comparison.csv', 
              '2026_climate_impact_significance.csv',
              '2026_climate_flagged_matchups.csv']:
    src = DATA / fname
    dst = REPORT_DATA / fname
    if src.exists():
        dst.write_text(src.read_text())
        print(f'Copied {fname} -> report/data/')

# ── Report top deltas ──
print('\nTop 5 most significant:')
top = sorted(significant, key=lambda t: abs(t['Z_stat']), reverse=True)[:8]
for t in top:
    print(f"  {t['Team']:<14} A1={t['A1_Win_Prob']:>6.2f}%  A2={t['A2_Win_Prob']:>6.2f}%  delta={t['Delta_pp']:+.2f}pp  Z={t['Z_stat']:+.2f}")

# Tier counts
tiers = {}
for m in flagged:
    t = m.get('Climate_Flag_Tier', 'None')
    tiers[t] = tiers.get(t, 0) + 1
print(f'\nFlagged matchups: {tiers}')

print('\nDone.')
