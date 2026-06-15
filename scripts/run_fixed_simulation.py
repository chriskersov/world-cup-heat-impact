#!/usr/bin/env python3
"""
FIXED Monte Carlo simulation for FIFA 2026 World Cup.

Fixes:
1. climate_goal_boost now receives actual match IDs (M73, M89, etc.)
   instead of stage names (R32, R16, etc.) → real venue temperatures used.
2. Per-slot matchup tracking for Approach 1 flagged matchups with
   actual venue temperatures per match slot.

Outputs: approach1_results.json, approach2_results.json,
         approach_comparison.json, flagged_matchups.json
"""

import json
import shutil
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

# ── Config ──────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
N_SIMS = 100_000
SEED = 42
CLIMATE_COEFFICIENT = 0.032
VENUE_ACTIVATION = 22.0
HOME_GOAL_BASE, AWAY_GOAL_BASE = 1.77, 1.05
HOSTS = {'United States', 'Mexico', 'Canada'}

KOPPEN_SCORES = {
    'Af': 1.0, 'Am': 1.0, 'Aw': 1.0, 'BWh': 0.9, 'BSh': 0.9,
    'Csa': 0.5, 'Csb': 0.5, 'Cfa': 0.5, 'Cfb': 0.5,
    'Dfa': 0.2, 'Dfb': 0.2, 'Dfc': 0.2, 'Dwa': 0.2, 'Dwb': 0.2, 'Dwc': 0.2,
    'BWk': 0.4, 'BSk': 0.4, 'Cwa': 0.5, 'Cwb': 0.5, 'Cfc': 0.3,
    'ET': 0.1, 'Csc': 0.4, 'Cwc': 0.3,
}

R32_DEF = [
    ('M73','R','A','R','B'),('M74','W','E','3','ABCDF'),
    ('M75','W','F','R','C'),('M76','W','C','R','F'),
    ('M77','W','I','3','CDFGH'),('M78','R','E','R','I'),
    ('M79','W','A','3','CEFHI'),('M80','W','L','3','EHIJK'),
    ('M81','W','D','3','BEFIJ'),('M82','W','G','3','AEHIJ'),
    ('M83','R','K','R','L'),('M84','W','H','R','J'),
    ('M85','W','B','3','EFGIJ'),('M86','W','J','R','H'),
    ('M87','W','K','3','DEIJL'),('M88','R','D','R','G'),
]

R32_TO_R16 = {
    'M73':'M89','M75':'M89','M74':'M90','M77':'M90',
    'M76':'M91','M78':'M91','M79':'M92','M80':'M92',
    'M83':'M93','M84':'M93','M81':'M94','M82':'M94',
    'M86':'M95','M88':'M95','M85':'M96','M87':'M96',
}

R16_TO_QF = {
    'M89':'M97','M90':'M97','M93':'M98','M94':'M98',
    'M91':'M99','M92':'M99','M95':'M100','M96':'M100',
}

QF_TO_SF = {
    'M97':'M101','M98':'M101','M99':'M102','M100':'M102',
}

MATCH_STAGE = {}
for mid, _, _, _, _ in R32_DEF:           MATCH_STAGE[mid] = 'R32'
for mid in set(R32_TO_R16.values()):      MATCH_STAGE[mid] = 'R16'
for mid in set(R16_TO_QF.values()):       MATCH_STAGE[mid] = 'QF'
for mid in set(QF_TO_SF.values()):        MATCH_STAGE[mid] = 'SF'
MATCH_STAGE['M109'] = '3rd Place'
MATCH_STAGE['M110'] = 'Final'

with open(DATA_DIR / 'knockout_slot_temps.json') as f:
    SLOT_TEMPS = json.load(f)

SLOT_META = {
    'M73':('Inglewood','SoFi Stadium'),'M74':('Houston','NRG Stadium'),
    'M75':('Foxborough','Gillette Stadium'),'M76':('Guadalupe','Estadio BBVA'),
    'M77':('Arlington','AT&T Stadium'),'M78':('East Rutherford','MetLife Stadium'),
    'M79':('Mexico City','Estadio Azteca'),'M80':('Atlanta','Mercedes-Benz Stadium'),
    'M81':('Seattle','Lumen Field'),'M82':('Santa Clara',"Levi's Stadium"),
    'M83':('Inglewood','SoFi Stadium'),'M84':('Toronto','BMO Field'),
    'M85':('Vancouver','BC Place'),'M86':('Arlington','AT&T Stadium'),
    'M87':('Miami Gardens','Hard Rock Stadium'),'M88':('Kansas City','Arrowhead Stadium'),
    'M89':('Houston','NRG Stadium'),'M90':('Philadelphia','Lincoln Financial Field'),
    'M91':('East Rutherford','MetLife Stadium'),'M92':('Mexico City','Estadio Azteca'),
    'M93':('Arlington','AT&T Stadium'),'M94':('Seattle','Lumen Field'),
    'M95':('Atlanta','Mercedes-Benz Stadium'),'M96':('Vancouver','BC Place'),
    'M97':('Foxborough','Gillette Stadium'),'M98':('Inglewood','SoFi Stadium'),
    'M99':('Miami Gardens','Hard Rock Stadium'),'M100':('Kansas City','Arrowhead Stadium'),
    'M101':('Arlington','AT&T Stadium'),'M102':('Atlanta','Mercedes-Benz Stadium'),
    'M109':('Miami Gardens','Hard Rock Stadium'),'M110':('East Rutherford','MetLife Stadium'),
}

# ── Load input data ─────────────────────────
print('Loading input data...')
elo_df = pd.read_csv(DATA_DIR / 'elo_current_2026.csv').set_index('Team')['Elo_Current']
fixtures = pd.read_csv(DATA_DIR / '2026_group_stage.csv')
climate_lookup = pd.read_csv(DATA_DIR / 'country_climate.csv').set_index('Country')

ELO_AVG = fixtures['Home_Elo'].mean()
NEUTRAL_GOAL_BASE = (HOME_GOAL_BASE + AWAY_GOAL_BASE) / 2

all_teams = sorted(set(fixtures['Home_Team'].unique()) | set(fixtures['Away_Team'].unique()))
team_idx = {t: i for i, t in enumerate(all_teams)}

base_elo = np.array([
    elo_df.get(t, fixtures.loc[fixtures['Home_Team'] == t, 'Home_Elo'].iloc[0]
               if t in fixtures['Home_Team'].values
               else fixtures.loc[fixtures['Away_Team'] == t, 'Away_Elo'].iloc[0])
    for t in all_teams
])
is_host = np.array([t in HOSTS for t in all_teams])
climate_scores = np.array([
    KOPPEN_SCORES.get(climate_lookup.loc[t, 'Koppen'] if t in climate_lookup.index else 'Cfb', 0.5)
    for t in all_teams
])
warm_climate = np.array([
    int(climate_lookup.loc[t, 'Warm_Climate']) if t in climate_lookup.index else 0
    for t in all_teams
])

teams_by_group = {}
for _, row in fixtures.iterrows():
    teams_by_group.setdefault(row['Group'], set()).update([row['Home_Team'], row['Away_Team']])

print(f'  {len(all_teams)} teams, slot temps {min(SLOT_TEMPS.values()):.1f}–{max(SLOT_TEMPS.values()):.1f}°C')


# ── Core match functions ────────────────────
def match_result(he, ae, hfa=0, climate_mult=1.0, neutral=False):
    if neutral:
        bh = ba = NEUTRAL_GOAL_BASE
    else:
        bh, ba = HOME_GOAL_BASE, AWAY_GOAL_BASE
    hl = bh * np.exp((he - ELO_AVG) / 400) * (1.0 + hfa / 2000) * climate_mult
    al = ba * np.exp((ae - ELO_AVG) / 400)
    if climate_mult > 1.0:
        al *= (1.0 / climate_mult)
    return np.random.poisson(max(0.1, hl)), np.random.poisson(max(0.1, al))


def elo_update(he, ae, hg, ag, sw=1.0, hfa=0):
    exp_h = 1.0 / (1.0 + 10.0 ** ((ae - (he + hfa)) / 400.0))
    rh = 1.0 if hg > ag else (0.0 if hg < ag else 0.5)
    K = 12 * sw * max(0.2, 1.0 - abs(exp_h - 0.5) * 1.6)
    if abs(rh - exp_h) > 0.4:
        K *= 1.5
    return he + K * (rh - exp_h), ae + K * ((1 - rh) - (1 - exp_h))


def climate_goal_boost(idx_warm, idx_cool, match_id):
    """FIXED: match_id must be e.g. 'M73', not 'R32'."""
    venue_temp = SLOT_TEMPS.get(match_id, 23.0)
    if venue_temp < VENUE_ACTIVATION:
        return 1.0
    cs_w = climate_scores[idx_warm]
    cs_c = climate_scores[idx_cool]
    diff = (cs_w - cs_c) * (venue_temp / 28.0)
    if diff <= 0:
        return 1.0
    return 1.0 + min(CLIMATE_COEFFICIENT * diff * 3, 0.10)


def compute_climate_diff(warm_idx, cool_idx, venue_temp):
    """Compute Climate_Diff_Score — respects VENUE_ACTIVATION threshold."""
    if venue_temp < VENUE_ACTIVATION:
        return 0.0
    cs_w = climate_scores[warm_idx]
    cs_c = climate_scores[cool_idx]
    diff = (cs_w - cs_c) * (venue_temp / 28.0)
    if diff <= 0:
        return 0.0
    return round(diff, 4)


def resolve_slot(stype, sval, winners, runners_up, best_thirds):
    if stype == 'W':
        return winners[sval]
    elif stype == 'R':
        return runners_up[sval]
    else:
        group_set = set(sval)
        for bt_grp, bt_team, _ in best_thirds:
            if bt_grp in group_set:
                return bt_team
        return best_thirds[0][1]


def pick_winner(t1, t2, hg, ag):
    if hg > ag:
        return t1, t2
    elif ag > hg:
        return t2, t1
    elif np.random.random() < 0.5:
        return t1, t2
    else:
        return t2, t1


# ── Full tournament simulation ──────────────
def run_tournament(climate_adjusted, slot_matchups=None):
    """
    Run one tournament. Returns team-stage counts dict.
    If climate_adjusted and slot_matchups is provided, tracks per-slot warm-vs-cool
    matchups in slot_matchups[mid][(warm_team, cool_team)] += 1.
    """
    stages = ['Group', 'R32', 'R16', 'QF', 'SF', 'Final', 'Winner']
    counts = {t: {s: 0 for s in stages} for t in all_teams}
    elos = base_elo.copy()
    track = climate_adjusted and slot_matchups is not None

    # ── Group stage ──────────────────────────
    standings = {grp: {t: {'Pts': 0, 'GF': 0, 'GA': 0, 'GD': 0} for t in teams}
                 for grp, teams in teams_by_group.items()}
    for _, row in fixtures.iterrows():
        grp, h, a = row['Group'], row['Home_Team'], row['Away_Team']
        hi, ai = team_idx[h], team_idx[a]
        hfa = 100 if is_host[hi] else 0
        hg, ag = match_result(elos[hi], elos[ai], hfa)
        elos[hi], elos[ai] = elo_update(elos[hi], elos[ai], hg, ag, 0.5, hfa)
        standings[grp][h]['GF'] += hg; standings[grp][h]['GA'] += ag
        standings[grp][a]['GF'] += ag; standings[grp][a]['GA'] += hg
        standings[grp][h]['GD'] = standings[grp][h]['GF'] - standings[grp][h]['GA']
        standings[grp][a]['GD'] = standings[grp][a]['GF'] - standings[grp][a]['GA']
        pts = (3, 0) if hg > ag else ((0, 3) if ag > hg else (1, 1))
        standings[grp][h]['Pts'] += pts[0]; standings[grp][a]['Pts'] += pts[1]

    ranked = {grp: sorted(d.items(), key=lambda x: (x[1]['Pts'], x[1]['GD'], x[1]['GF']),
                          reverse=True) for grp, d in standings.items()}
    thirds = [(grp, order[2][0], order[2][1]) for grp, order in ranked.items()]
    thirds.sort(key=lambda x: (x[2]['Pts'], x[2]['GD'], x[2]['GF']), reverse=True)
    best_thirds = thirds[:8]

    winners = {grp: order[0][0] for grp, order in ranked.items()}
    runners_up = {grp: order[1][0] for grp, order in ranked.items()}

    for _, order in ranked.items():
        for team, _ in order:
            counts[team]['Group'] += 1

    # ── R32 ──────────────────────────────────
    r32_results = {}  # mid -> winner
    r32_losers = {}   # mid -> loser
    for mid, s1t, s1v, s2t, s2v in R32_DEF:
        t1 = resolve_slot(s1t, s1v, winners, runners_up, best_thirds)
        t2 = resolve_slot(s2t, s2v, winners, runners_up, best_thirds)
        i1, i2 = team_idx[t1], team_idx[t2]
        e1, e2 = elos[i1], elos[i2]
        w1, w2 = warm_climate[i1], warm_climate[i2]

        boost = 1.0
        if climate_adjusted:
            if w1 == 1 and w2 == 0:
                boost = climate_goal_boost(i1, i2, mid)  # FIXED
            elif w2 == 1 and w1 == 0:
                boost = climate_goal_boost(i2, i1, mid)  # FIXED

        if climate_adjusted and w2 == 1 and w1 == 0:
            ag, hg = match_result(e2, e1, 0, boost, neutral=True)
        else:
            hg, ag = match_result(e1, e2, 0, boost, neutral=True)
        elos[i1], elos[i2] = elo_update(e1, e2, hg, ag, 0.75)
        win, lose = pick_winner(t1, t2, hg, ag)
        r32_results[mid] = win
        r32_losers[mid] = lose
        counts[t1]['R32'] += 1
        counts[t2]['R32'] += 1

        if track:
            wt = t1 if w1 == 1 else (t2 if w2 == 1 else None)
            ct = t1 if w1 == 0 else (t2 if w2 == 0 else None)
            if wt and ct:
                slot_matchups[mid][(wt, ct)] += 1

    # ── R16, QF, SF ──────────────────────────
    current_winners = r32_results
    current_losers = r32_losers
    stage_maps = [
        (R32_TO_R16, 1.0, 'R16'),
        (R16_TO_QF, 1.25, 'QF'),
        (QF_TO_SF, 1.5, 'SF'),
    ]
    sf_winners = {}  # M101 -> winner, M102 -> winner
    sf_losers = {}   # M101 -> loser, M102 -> loser

    for stage_map, sw, stage_name in stage_maps:
        nxt_winners = {}
        nxt_losers = {}
        is_sf = (stage_name == 'SF')

        for in_m, out_m in stage_map.items():
            if in_m not in current_winners:
                continue
            t1 = current_winners[in_m]
            if out_m not in nxt_winners:
                nxt_winners[out_m] = t1
            else:
                t2 = nxt_winners[out_m]
                i1, i2 = team_idx[t1], team_idx[t2]
                e1, e2 = elos[i1], elos[i2]
                w1, w2 = warm_climate[i1], warm_climate[i2]

                boost = 1.0
                if climate_adjusted:
                    if w1 == 1 and w2 == 0:
                        boost = climate_goal_boost(i1, i2, out_m)  # FIXED
                    elif w2 == 1 and w1 == 0:
                        boost = climate_goal_boost(i2, i1, out_m)  # FIXED

                if climate_adjusted and w2 == 1 and w1 == 0:
                    ag, hg = match_result(e2, e1, 0, boost, neutral=True)
                else:
                    hg, ag = match_result(e1, e2, 0, boost, neutral=True)
                elos[i1], elos[i2] = elo_update(e1, e2, hg, ag, sw)
                win, lose = pick_winner(t1, t2, hg, ag)
                nxt_winners[out_m] = win
                nxt_losers[out_m] = lose
                counts[t1][stage_name] += 1
                counts[t2][stage_name] += 1

                if is_sf:
                    sf_winners[out_m] = win
                    sf_losers[out_m] = lose

                if track:
                    wt = t1 if w1 == 1 else (t2 if w2 == 1 else None)
                    ct = t1 if w1 == 0 else (t2 if w2 == 0 else None)
                    if wt and ct:
                        slot_matchups[out_m][(wt, ct)] += 1

        current_winners = nxt_winners
        current_losers = nxt_losers

    # ── M109: 3rd place match ────────────────
    t1 = sf_losers.get('M101')
    t2 = sf_losers.get('M102')
    if t1 and t2:
        i1, i2 = team_idx[t1], team_idx[t2]
        e1, e2 = elos[i1], elos[i2]
        w1, w2 = warm_climate[i1], warm_climate[i2]

        boost = 1.0
        if climate_adjusted:
            if w1 == 1 and w2 == 0:
                boost = climate_goal_boost(i1, i2, 'M109')  # FIXED
            elif w2 == 1 and w1 == 0:
                boost = climate_goal_boost(i2, i1, 'M109')  # FIXED

        if climate_adjusted and w2 == 1 and w1 == 0:
            ag, hg = match_result(e2, e1, 0, boost, neutral=True)
        else:
            hg, ag = match_result(e1, e2, 0, boost, neutral=True)
        elos[i1], elos[i2] = elo_update(e1, e2, hg, ag, 1.0)
        # 3rd place doesn't affect win prob counts, just track matchup
        if track:
            wt = t1 if w1 == 1 else (t2 if w2 == 1 else None)
            ct = t1 if w1 == 0 else (t2 if w2 == 0 else None)
            if wt and ct:
                slot_matchups['M109'][(wt, ct)] += 1

    # ── M110: Final ──────────────────────────
    t1 = sf_winners.get('M101')
    t2 = sf_winners.get('M102')
    if t1 and t2:
        i1, i2 = team_idx[t1], team_idx[t2]
        e1, e2 = elos[i1], elos[i2]
        w1, w2 = warm_climate[i1], warm_climate[i2]

        boost = 1.0
        if climate_adjusted:
            if w1 == 1 and w2 == 0:
                boost = climate_goal_boost(i1, i2, 'M110')  # FIXED
            elif w2 == 1 and w1 == 0:
                boost = climate_goal_boost(i2, i1, 'M110')  # FIXED

        if climate_adjusted and w2 == 1 and w1 == 0:
            ag, hg = match_result(e2, e1, 0, boost, neutral=True)
        else:
            hg, ag = match_result(e1, e2, 0, boost, neutral=True)
        elos[i1], elos[i2] = elo_update(e1, e2, hg, ag, 2.0)
        champ, runner = pick_winner(t1, t2, hg, ag)
        counts[t1]['Final'] += 1
        counts[t2]['Final'] += 1
        counts[champ]['Winner'] += 1

        if track:
            wt = t1 if w1 == 1 else (t2 if w2 == 1 else None)
            ct = t1 if w1 == 0 else (t2 if w2 == 0 else None)
            if wt and ct:
                slot_matchups['M110'][(wt, ct)] += 1

    return counts


# ── Run simulations ─────────────────────────
def run_sim(label, climate_adjusted, track_matchups=False):
    print(f'\n{"="*60}')
    print(f'{label}: {N_SIMS:,} tournaments')
    print(f'{"="*60}')
    stages = ['Group', 'R32', 'R16', 'QF', 'SF', 'Final', 'Winner']
    totals = {t: {s: 0 for s in stages} for t in all_teams}
    slot_m = defaultdict(lambda: defaultdict(int)) if track_matchups else None
    start = time.time()

    for sim in range(N_SIMS):
        tc = run_tournament(climate_adjusted, slot_m)
        for t in all_teams:
            for s in stages:
                totals[t][s] += tc[t][s]
        if (sim + 1) % 25000 == 0:
            elapsed = time.time() - start
            print(f'  {sim+1:>7,}/{N_SIMS:,}  ({elapsed:.0f}s)')

    elapsed = time.time() - start
    print(f'Done: {elapsed:.0f}s')
    return totals, slot_m, elapsed


# Create results dirs
for subdir in ['report/data', 'public/data']:
    (DATA_DIR.parent / subdir).mkdir(parents=True, exist_ok=True)

# ── A1: Pure Elo ──
np.random.seed(SEED)
results_a1, _, t_a1 = run_sim('A1: Pure Elo (no climate boost)', climate_adjusted=False)

# ── A2: Climate-adjusted (FIXED) ──
np.random.seed(SEED)  # Same seed = same group stage outcomes
results_a2, slot_matchups, t_a2 = run_sim(
    'A2: Climate-Adjusted (FIXED venue temps)',
    climate_adjusted=True, track_matchups=True
)

# ── Build output ────────────────────────────
print(f'\n{"="*60}')
print('BUILDING OUTPUT FILES')
print(f'{"="*60}')

stages = ['Group', 'R32', 'R16', 'QF', 'SF', 'Final', 'Winner']

# approach1_results.json
a1_out = []
for t in all_teams:
    row = {'Team': t}
    for s in stages:
        row[s] = results_a1[t][s]
        row[f'{s}_Prob'] = round(results_a1[t][s] / N_SIMS, 4)
    a1_out.append(row)
a1_out.sort(key=lambda x: x['Winner_Prob'], reverse=True)

# approach2_results.json
a2_out = []
for t in all_teams:
    row = {'Team': t}
    for s in stages:
        row[s] = results_a2[t][s]
        row[f'{s}_Prob'] = round(results_a2[t][s] / N_SIMS, 4)
    a2_out.append(row)
a2_out.sort(key=lambda x: x['Winner_Prob'], reverse=True)

# approach_comparison.json
warm_map = {t: 'WARM' if warm_climate[team_idx[t]] == 1 else 'COOL' for t in all_teams}
comparison = []
for t in all_teams:
    a1r = next(r for r in a1_out if r['Team'] == t)
    a2r = next(r for r in a2_out if r['Team'] == t)
    row = {'Team': t}
    for s in ['QF', 'SF', 'Final', 'Winner']:
        a1p = a1r[f'{s}_Prob']
        a2p = a2r[f'{s}_Prob']
        row[f'A1_{s}'] = round(a1p * 100, 2)
        row[f'A2_{s}'] = round(a2p * 100, 2)
        row[f'{s}_Delta'] = round((a2p - a1p) * 100, 2)
    row['Warm'] = warm_map[t]
    row['Elo'] = round(base_elo[team_idx[t]], 0)
    d = a2r['Winner_Prob'] - a1r['Winner_Prob']
    row['Direction'] = 'Benefited' if d > 0.005 else ('Hurt' if d < -0.005 else 'Neutral')
    comparison.append(row)
comparison.sort(key=lambda x: x['Winner_Delta'], reverse=True)

# flagged_matchups.json (per-slot, warm-vs-cool)
flagged = []
for mid in sorted(slot_matchups.keys(), key=lambda m: (list(MATCH_STAGE.keys()).index(m) if m in MATCH_STAGE else 99, m)):
    pair_counts = slot_matchups[mid]
    city, stadium = SLOT_META.get(mid, ('', ''))
    venue_temp = SLOT_TEMPS.get(mid, 23.0)
    stage = MATCH_STAGE.get(mid, 'Unknown')

    for (warm_team, cool_team), count in pair_counts.items():
        prob = round(count / N_SIMS * 100, 2)
        if prob < 0.05:
            continue
        wi, ci = team_idx.get(warm_team), team_idx.get(cool_team)
        if wi is None or ci is None:
            continue
        elo_w = round(base_elo[wi], 0)
        elo_c = round(base_elo[ci], 0)
        diff_score = compute_climate_diff(wi, ci, venue_temp)

        if prob >= 7 and diff_score > 0.20:
            tier = 'Tier 1 (Strong)'
        elif prob >= 3 and diff_score > 0.10:
            tier = 'Tier 2 (Moderate)'
        else:
            tier = 'Tier 3 (Weak)'

        flagged.append({
            'Warm_Team': warm_team,
            'Cool_Team': cool_team,
            'Match_ID': mid,
            'Stage': stage,
            'City': city,
            'Stadium': stadium,
            'Prob_Pct': prob,
            'Venue_Temp_C': round(venue_temp, 1),
            'Climate_Diff_Score': diff_score,
            'Elo_Warm': elo_w,
            'Elo_Cool': elo_c,
            'Elo_Diff': elo_w - elo_c,
            'Climate_Flag_Tier': tier,
        })

tier_order = {'Tier 1 (Strong)': 0, 'Tier 2 (Moderate)': 1, 'Tier 3 (Weak)': 2}
flagged.sort(key=lambda x: (tier_order.get(x['Climate_Flag_Tier'], 9), -x['Prob_Pct']))

print(f'  A1 records: {len(a1_out)}')
print(f'  A2 records: {len(a2_out)}')
print(f'  Comparison records: {len(comparison)}')
print(f'  Flagged matchups (per-slot): {len(flagged)}')
tcs = defaultdict(int)
for f in flagged:
    tcs[f['Climate_Flag_Tier']] += 1
for t, c in sorted(tcs.items()):
    print(f'    {t}: {c}')

# ── Save ────────────────────────────────────
outputs = {
    'approach1_results.json': a1_out,
    'approach2_results.json': a2_out,
    'approach_comparison.json': comparison,
    'flagged_matchups.json': flagged,
}

for fname, data in outputs.items():
    path = DATA_DIR / fname
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f'  Saved {path} ({len(data)} records)')

for subdir in ['report/data', 'public/data']:
    dst_dir = DATA_DIR.parent / subdir
    for fname in outputs:
        dst = dst_dir / fname
        shutil.copy(DATA_DIR / fname, dst)
    print(f'  Copied to {dst_dir}/')

print(f'\n{"="*60}')
print('ALL DONE')
print(f'  A1: {t_a1:.0f}s  |  A2: {t_a2:.0f}s  |  Total: {t_a1 + t_a2:.0f}s')
print(f'{"="*60}')

# Quick verification
print('\nVERIFICATION:')
flag_temps = sorted(set(f['Venue_Temp_C'] for f in flagged))
print(f'  Flagged venue temps ({len(flag_temps)} unique): {flag_temps}')
sp_a1 = next(r for r in a1_out if r['Team'] == 'Spain')
sp_a2 = next(r for r in a2_out if r['Team'] == 'Spain')
print(f'  Spain A1 Winner: {sp_a1["Winner_Prob"]*100:.2f}%')
print(f'  Spain A2 Winner: {sp_a2["Winner_Prob"]*100:.2f}%')
print(f'  Spain delta: {(sp_a2["Winner_Prob"] - sp_a1["Winner_Prob"])*100:+.1f}pp')
# Show sample flagged matchup
if flagged:
    f0 = flagged[0]
    print(f'  Sample flagged: {f0["Warm_Team"]} vs {f0["Cool_Team"]} at {f0["City"]} ({f0["Venue_Temp_C"]}°C) [{f0["Match_ID"]}]')
