"""Build Elo ratings for World Cup matches.

Downloads international results from martj42's GitHub, computes Elo ratings
chronologically, and adds pre-match Elo for both teams in every World Cup match.
"""

import pandas as pd
import numpy as np
import requests
from pathlib import Path

from io import StringIO

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

RESULTS_URL = 'https://raw.githubusercontent.com/martj42/international_results/master/results.csv'
MATCHES_CSV = DATA_DIR / 'fifa_world_cup_matches_enriched.csv'
OUTPUT = DATA_DIR / 'elo_ratings.csv'

BASE_RATING = 1500
HOME_ADVANTAGE = 100


def get_k_factor(tournament, year):
    t = str(tournament).lower()
    if 'fifa world cup' in t and 'qualif' not in t:
        return 60
    elif 'continental' in t or 'euro' in t or 'copa' in t or 'africa cup' in t or 'asian cup' in t or 'gold cup' in t:
        return 50
    elif 'qualif' in t or 'nation' in t:
        return 40
    elif 'confederations' in t:
        return 50
    return 30


def goal_multiplier(diff):
    if diff <= 1:
        return 1.0
    if diff == 2:
        return 1.5
    return (11 + diff) / 8


def expected(ra, rb):
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def main():
    # ---- 1. Load World Cup matches ----
    wc = pd.read_csv(MATCHES_CSV, parse_dates=['Date'], keep_default_na=False)
    print(f'World Cup matches: {len(wc)}')

    # Build lookup: for each WC match date and team, we need Elo BEFORE matches on that day
    needed = set()
    for _, row in wc.iterrows():
        d = row['Date'].strftime('%Y-%m-%d')
        needed.add((d, row['Home_Team'].strip()))
        needed.add((d, row['Away_Team'].strip()))

    # ---- 2. Download international results ----
    print('Downloading international match history...')
    resp = requests.get(RESULTS_URL, timeout=60)
    df = pd.read_csv(StringIO(resp.text))

    df['date'] = pd.to_datetime(df['date'])
    df = df.dropna(subset=['home_score', 'away_score'])
    df['home_score'] = df['home_score'].astype(int)
    df['away_score'] = df['away_score'].astype(int)
    df = df.sort_values('date').reset_index(drop=True)

    # Name standardization to match our World Cup data
    fixes = {
        'USA': 'United States', 'Czech Republic': 'Czech Republic',
        'Czechoslovakia': 'Czechoslovakia', 'Germany DR': 'East Germany',
        'Germany FR': 'West Germany', 'USSR': 'Soviet Union',
        'Serbia & Montenegro': 'Serbia and Montenegro',
        'Bosnia': 'Bosnia and Herzegovina', 'Macedonia': 'North Macedonia',
        'Côte d\'Ivoire': 'Ivory Coast', 'Cote d\'Ivoire': 'Ivory Coast',
        'Korea Republic': 'South Korea', 'Korea DPR': 'North Korea',
        'IR Iran': 'Iran', 'DR Congo': 'Zaire', 'Congo DR': 'Zaire',
        'Indonesia': 'Dutch East Indies',
    }
    for col in ['home_team', 'away_team']:
        df[col] = df[col].str.strip().replace(fixes)
    df = df[~df['home_team'].str.contains(r'\d', na=False)]
    df = df[~df['away_team'].str.contains(r'\d', na=False)]

    print(f'Processing {len(df):,} international matches...')

    # ---- 3. Play through history, capture Elo for WC matches ----
    ratings = {}
    elo_lookup = {}
    seen_dates = set()
    processed = 0

    for _, row in df.iterrows():
        home = row['home_team']
        away = row['away_team']
        date = row['date']
        d_str = date.strftime('%Y-%m-%d')
        h_score = row['home_score']
        a_score = row['away_score']
        tournament = row.get('tournament', '')

        # Init ratings
        if home not in ratings:
            ratings[home] = BASE_RATING
        if away not in ratings:
            ratings[away] = BASE_RATING

        # On a WC date, capture needed Elo values BEFORE any matches on this day
        if d_str not in seen_dates:
            seen_dates.add(d_str)
            for (ed, team) in needed:
                if ed == d_str and team in ratings:
                    elo_lookup[(ed, team)] = ratings[team]

        home_elo = ratings[home]
        away_elo = ratings[away]

        # Update ratings
        exp_h = expected(home_elo + HOME_ADVANTAGE, away_elo)
        exp_a = 1.0 - exp_h

        if h_score > a_score:
            rh, ra = 1.0, 0.0
        elif h_score < a_score:
            rh, ra = 0.0, 1.0
        else:
            rh, ra = 0.5, 0.5

        K = get_k_factor(tournament, date.year) * goal_multiplier(abs(h_score - a_score))
        ratings[home] = home_elo + K * (rh - exp_h)
        ratings[away] = away_elo + K * (ra - exp_a)

        processed += 1
        if processed % 10000 == 0:
            print(f'  {processed:,}/{len(df):,}')

    # ---- 4. Merge Elo into WC matches ----
    print(f'\nElo captured for {len(elo_lookup)} (date, team) pairs')
    print(f'Needed {len(needed)}, missing {len(needed) - len(elo_lookup)}')

    wc['Home_Elo'] = wc.apply(
        lambda r: elo_lookup.get((r['Date'].strftime('%Y-%m-%d'), r['Home_Team'].strip())), axis=1)
    wc['Away_Elo'] = wc.apply(
        lambda r: elo_lookup.get((r['Date'].strftime('%Y-%m-%d'), r['Away_Team'].strip())), axis=1)

    missing_h = wc['Home_Elo'].isna().sum()
    missing_a = wc['Away_Elo'].isna().sum()
    print(f'Missing Home_Elo: {missing_h}, Missing Away_Elo: {missing_a}')

    if missing_h > 0 or missing_a > 0:
        median = pd.Series(list(elo_lookup.values())).median()
        wc['Home_Elo'] = wc['Home_Elo'].fillna(median)
        wc['Away_Elo'] = wc['Away_Elo'].fillna(median)
        print(f'  Filled with median Elo: {median:.0f}')

    wc['Home_Elo_Advantage'] = (wc['Home_Elo'] - wc['Away_Elo']).round(1)
    wc['Home_Elo'] = wc['Home_Elo'].round(1)
    wc['Away_Elo'] = wc['Away_Elo'].round(1)

    # Expected result based on Elo
    wc['Home_Elo_Expected'] = wc.apply(
        lambda r: 1.0 / (1.0 + 10.0 ** ((r['Away_Elo'] - (r['Home_Elo'] + HOME_ADVANTAGE)) / 400.0)), axis=1
    ).round(3)

    # Save
    wc.to_csv(MATCHES_CSV, index=False)
    print(f'\nSaved {len(wc.columns)} columns to {MATCHES_CSV}')
    print(f'New Elo columns: Home_Elo, Away_Elo, Home_Elo_Advantage, Home_Elo_Expected')
    print(f'Home Elo range: {wc["Home_Elo"].min():.0f} - {wc["Home_Elo"].max():.0f}')
    print(f'Away Elo range: {wc["Away_Elo"].min():.0f} - {wc["Away_Elo"].max():.0f}')

    # Save standalone Elo timeline
    timeline = pd.DataFrame([
        {'Date': k[0], 'Team': k[1], 'Elo': v}
        for k, v in elo_lookup.items()
    ])
    timeline.to_csv(OUTPUT, index=False)
    print(f'Saved {OUTPUT} ({len(timeline)} records)')


if __name__ == '__main__':
    main()
