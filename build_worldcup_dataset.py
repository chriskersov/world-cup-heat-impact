#!/usr/bin/env python3
"""
Compile a clean CSV of every FIFA Men's World Cup match (1930–2022).

Data source: Wikipedia tournament pages.
Output:      fifa_world_cup_matches_1930_2022.csv

Dependencies: requests, beautifulsoup4, pandas
Install with: pip install requests beautifulsoup4 pandas
"""

import requests
from bs4 import BeautifulSoup, Tag
import pandas as pd
import re
import time
import sys
from io import StringIO

# ---------------------------------------------------------------------------
# Tournament definitions
# ---------------------------------------------------------------------------
WORLD_CUPS = [
    (1930, 'Uruguay'),
    (1934, 'Italy'),
    (1938, 'France'),
    (1950, 'Brazil'),
    (1954, 'Switzerland'),
    (1958, 'Sweden'),
    (1962, 'Chile'),
    (1966, 'England'),
    (1970, 'Mexico'),
    (1974, 'West Germany'),
    (1978, 'Argentina'),
    (1982, 'Spain'),
    (1986, 'Mexico'),
    (1990, 'Italy'),
    (1994, 'United States'),
    (1998, 'France'),
    (2002, 'South Korea, Japan'),
    (2006, 'Germany'),
    (2010, 'South Africa'),
    (2014, 'Brazil'),
    (2018, 'Russia'),
    (2022, 'Qatar'),
]

EXPECTED_MATCHES = {
    1930: 18, 1934: 17, 1938: 18, 1950: 22, 1954: 26,
    1958: 35, 1962: 32, 1966: 32, 1970: 32, 1974: 38,
    1978: 38, 1982: 52, 1986: 52, 1990: 52, 1994: 52,
    1998: 64, 2002: 64, 2006: 64, 2010: 64, 2014: 64,
    2018: 64, 2022: 64,
}

# ---------------------------------------------------------------------------
# Country name standardisation
# ---------------------------------------------------------------------------
COUNTRY_CLEAN = {
    'West Germany': 'West Germany',
    'East Germany': 'East Germany',
    'Soviet Union': 'Soviet Union',
    'Czechoslovakia': 'Czechoslovakia',
    'Yugoslavia': 'Yugoslavia',
    'FR Yugoslavia': 'Yugoslavia',
    'Serbia and Montenegro': 'Serbia and Montenegro',
    'Zaire': 'Zaire',
    "Côte d'Ivoire": 'Ivory Coast',
    'Korea Republic': 'South Korea',
    'Korea DPR': 'North Korea',
    'IR Iran': 'Iran',
    'USA': 'United States',
    'Dutch East Indies': 'Dutch East Indies',
    'Trinidad and Tobago': 'Trinidad and Tobago',
    'Saint Kitts and Nevis': 'Saint Kitts and Nevis',
}


def fetch_page(url: str, retries: int = 5) -> str:
    """Fetch a Wikipedia page with a sensible User-Agent and backoff."""
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
    }
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.HTTPError as e:
            if resp.status_code == 429 or resp.status_code == 403:
                wait = 5 * (2 ** (attempt - 1))
                print(f'(rate-limited, waiting {wait}s...) ', end='', flush=True)
                time.sleep(wait)
                if attempt == retries:
                    raise
            else:
                raise
        except requests.RequestException as e:
            if attempt == retries:
                raise
            time.sleep(2 * attempt)
    return ''


def _clean_team_name(raw: str) -> str:
    """Extract a clean team name from Wikipedia cell text."""
    if not raw:
        return ''
    text = raw.strip()
    # Remove bracketed notes like "[a]", "[b]", "[note 1]" etc.
    text = re.sub(r'\s*\[[a-z0-9\s]+\]\s*', '', text)
    # Remove parenthetical notes that are NOT part of the name
    text = re.sub(r'\s*\([^)]*\b(H|hosts|neutral|awarded|w\.o\.|walkover)\b[^)]*\)\s*', '', text, flags=re.IGNORECASE)
    # Collapse whitespace
    text = ' '.join(text.split())
    # Apply standardisation map
    if text in COUNTRY_CLEAN:
        text = COUNTRY_CLEAN[text]
    return text.strip()


def _parse_score(score_text: str) -> tuple[int, int]:
    """Parse a score string like '3–1' or '1–0 (a.e.t.)' into (home, away) ints."""
    if not score_text or not isinstance(score_text, str):
        return (0, 0)
    text = score_text.strip()
    if 'w/o' in text.lower() or 'walkover' in text.lower():
        return (0, 0)
    m = re.search(r'(\d+)\s*[–\-]\s*(\d+)', text)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (0, 0)


def _extract_city(venue_text: str, host_country: str) -> str:
    """Extract the host city from a venue/fright string."""
    if not venue_text or not isinstance(venue_text, str):
        return host_country

    text = venue_text.strip()

    # Truncate at "Attendance" or "Referee" – we only want venue info
    text = re.split(r'\bAttendance\b|\bReferee\b|\bAtt\.\b', text, flags=re.IGNORECASE)[0].strip()

    # Format is typically "Stadium Name, City" or "City, Country"
    if ',' in text:
        parts = [p.strip() for p in text.split(',')]
        # The city is usually the last part (not the stadium name)
        candidate = parts[-1]
        candidate = re.sub(r'\d[\d,]*$', '', candidate).strip().rstrip('.')
        if candidate and len(candidate) > 1:
            return candidate

    return text.strip()


def _get_section_context(element: Tag) -> str:
    """Find the nearest preceding heading and return the inferred stage."""
    prev_heading = element.find_previous(['h2', 'h3', 'h4', 'h5'])
    if prev_heading:
        return _infer_stage(prev_heading.get_text(strip=True))
    return 'Group Stage'


def _infer_stage(heading_text: str) -> str:
    """Map a Wikipedia section heading to a standardised stage name."""
    t = heading_text.lower().strip()
    if 'third place' in t or '3rd place' in t or 'bronze' in t:
        return 'Third place play-off'
    # "Final" (single match) – exclude "final round" / "final group"
    if ('final' in t and 'quarter' not in t and 'semi' not in t
            and 'round' not in t and 'group' not in t):
        return 'Final'
    if 'semi-final' in t or 'semifinal' in t:
        return 'Semi-final'
    if 'quarter-final' in t or 'quarterfinal' in t:
        return 'Quarter-final'
    if 'round of 16' in t:
        return 'Round of 16'
    if 'round of 32' in t:
        return 'Round of 32'
    if 'knockout' in t:
        return 'Knockout stage'
    # Specific group-like stages before the generic "group" check
    if 'final round' in t or 'final group' in t:
        return 'Final round'
    if 'first round' in t or 'round 1' in t or 'round one' in t:
        return 'First round'
    if 'second round' in t or 'round 2' in t or 'second group' in t:
        return 'Second round'
    if 'group' in t:
        return 'Group Stage'
    if 'play-off' in t or 'playoff' in t:
        return 'Play-off'
    if 'preliminary' in t:
        return 'Preliminary round'
    return 'Group Stage'


# ---------------------------------------------------------------------------
# Parser: footballbox div  (used for all knockout matches and pre-1998 group matches)
# ---------------------------------------------------------------------------
def parse_footballbox(fb_div: Tag, year: int, host: str, stage: str) -> dict | None:
    """
    Parse a single <div class="footballbox"> into a match dictionary.
    
    Structure:
      div.fleft > time > span.bday        → ISO date
      table.fevent > tr > th.fhome        → home team
                     > tr > th (middle)   → score
                     > tr > th.faway      → away team
      div.fright                          → venue + city
    """
    # --- Date ---
    date_str = ''
    bday_span = fb_div.find('span', class_='bday')
    if bday_span:
        date_str = bday_span.get_text(strip=True)  # e.g. "1930-07-13"
    else:
        fdate_div = fb_div.find('div', class_='fdate')
        if fdate_div:
            date_str = fdate_div.get_text(strip=True)

    # Normalise date
    if date_str:
        date_str = date_str.strip()
        # Sometimes bday contains just the date, sometimes extra text
        m = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
        if m:
            date_str = m.group(1)
        else:
            # Try to parse readable date
            try:
                from datetime import datetime
                for fmt in ['%d %B %Y', '%B %d, %Y', '%d %b %Y', '%Y-%m-%d']:
                    try:
                        date_str = datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

    # --- Teams and score ---
    fevent_table = fb_div.find('table', class_='fevent')
    if not fevent_table:
        return None

    # First row has the main info
    first_row = fevent_table.find('tr')
    if not first_row:
        return None

    ths = first_row.find_all('th')
    if len(ths) < 3:
        return None

    home_th = first_row.find('th', class_='fhome')
    away_th = first_row.find('th', class_='faway')

    if home_th and away_th:
        home_team = _clean_team_name(home_th.get_text())
        away_team = _clean_team_name(away_th.get_text())
        # Score is the remaining th
        for th in ths:
            if th != home_th and th != away_th:
                score_text = th.get_text(strip=True)
                home_score, away_score = _parse_score(score_text)
                break
        else:
            home_score, away_score = 0, 0
    else:
        # Fallback: use positions (th[0] = home, th[1] = score, th[2] = away)
        home_team = _clean_team_name(ths[0].get_text())
        away_team = _clean_team_name(ths[2].get_text())
        home_score, away_score = _parse_score(ths[1].get_text(strip=True))

    if not home_team or not away_team:
        return None

    # --- Walkover / cancelled check ---
    fevent_text = fevent_table.get_text().lower()
    skip_keywords = ['cancelled', 'canceled', 'w/o', 'walkover', 'walk over',
                     'abandoned', 'void', 'not played']
    if any(kw in fevent_text for kw in skip_keywords):
        return None

    # --- Penalty shootout ---
    penalties = 0
    pen_home = 0
    pen_away = 0

    rows = fevent_table.find_all('tr')
    for i, row in enumerate(rows):
        ths_in_row = row.find_all('th')
        row_text = row.get_text(strip=True).lower()
        if 'penalties' in row_text:
            penalties = 1
            if i + 1 < len(rows):
                next_row = rows[i + 1]
                pen_score_th = next_row.find('th')
                if pen_score_th:
                    pen_text = pen_score_th.get_text(strip=True)
                    pen_match = re.search(r'(\d+)\s*[–\-]\s*(\d+)', pen_text)
                    if pen_match:
                        pen_home = int(pen_match.group(1))
                        pen_away = int(pen_match.group(2))
            break

    # --- Winner ---
    winner = ''
    if penalties:
        winner = home_team if pen_home > pen_away else away_team
    elif home_score != away_score:
        winner = home_team if home_score > away_score else away_team

    # --- Venue / City ---
    fright_div = fb_div.find('div', class_='fright')
    venue_text = fright_div.get_text(' ', strip=True) if fright_div else ''
    city = _extract_city(venue_text, host)

    return {
        'Year': year,
        'Date': date_str,
        'Host_Country': host,
        'Host_City': city,
        'Stage': stage,
        'Home_Team': home_team,
        'Away_Team': away_team,
        'Home_Score': home_score,
        'Away_Score': away_score,
        'Penalties': penalties,
        'Penalties_Home_Score': pen_home,
        'Penalties_Away_Score': pen_away,
        'Winner': winner,
        'Draw': 1 if home_score == away_score else 0,
    }


# ---------------------------------------------------------------------------
# Parser: col1right col2center table  (group stage matches, 1998–2022)
# ---------------------------------------------------------------------------
def parse_col1right_table(table: Tag, year: int, host: str, stage: str) -> list[dict]:
    """
    Parse a group-stage match table (class ~ col1right col2center).

    Structure:
      <tr><td> Date </td></tr>                              ← date row (1 cell)
      <tr><td>Team 1</td><td>Score</td><td>Team 2</td><td>Venue</td></tr>  ← match row (4 cells)
      ... (alternating)
    """
    matches: list[dict] = []
    rows = table.find_all('tr')
    current_date = ''

    for row in rows:
        cells = row.find_all(['td', 'th'])

        # Skip header rows (all <th> cells)
        if all(c.name == 'th' for c in cells):
            continue

        # Date row: single cell
        if len(cells) == 1:
            date_text = cells[0].get_text(strip=True)
            try:
                from datetime import datetime
                for fmt in ['%d %B %Y', '%d %b %Y', '%B %d, %Y', '%Y-%m-%d']:
                    try:
                        current_date = datetime.strptime(date_text, fmt).strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
            except Exception:
                current_date = date_text
            continue

        # Match row: 4 cells (Team1, Score, Team2, Venue)
        if len(cells) == 4 and cells[0].name == 'td':
            home_team = _clean_team_name(cells[0].get_text())
            score_text = cells[1].get_text(strip=True)
            away_team = _clean_team_name(cells[2].get_text())
            venue_text = cells[3].get_text(strip=True)

            if not home_team or not away_team:
                continue
            if home_team.lower() in ('team', 'team 1', 'home', 'match'):
                continue

            home_score, away_score = _parse_score(score_text)
            city = _extract_city(venue_text, host)

            matches.append({
                'Year': year,
                'Date': current_date,
                'Host_Country': host,
                'Host_City': city,
                'Stage': stage,
                'Home_Team': home_team,
                'Away_Team': away_team,
                'Home_Score': home_score,
                'Away_Score': away_score,
                'Penalties': 0,
                'Penalties_Home_Score': 0,
                'Penalties_Away_Score': 0,
                'Winner': home_team if home_score > away_score else (away_team if away_score > home_score else ''),
                'Draw': 1 if home_score == away_score else 0,
            })

    return matches


# (section context handled by _get_section_context defined above)


# ---------------------------------------------------------------------------
# Main tournament scraper
# ---------------------------------------------------------------------------
def scrape_tournament(year: int, host: str) -> list[dict]:
    """Scrape all matches for a single World Cup tournament."""
    url = f'https://en.wikipedia.org/wiki/{year}_FIFA_World_Cup'
    print(f'  {year} ... ', end='', flush=True)

    try:
        html = fetch_page(url)
    except Exception as e:
        print(f'FAILED ({e})')
        return []

    soup = BeautifulSoup(html, 'html.parser')
    all_matches: list[dict] = []
    seen = set()

    # ------------------------------------------------------------------
    # 1. Parse footballbox divs (knockout matches for all years,
    #    plus group matches for pre-1998)
    # ------------------------------------------------------------------
    fb_divs = soup.find_all('div', class_='footballbox')
    for fb in fb_divs:
        stage = _get_section_context(fb)
        match = parse_footballbox(fb, year, host, stage)
        if match:
            key = (match['Home_Team'], match['Away_Team'], match['Home_Score'], match['Away_Score'])
            if key not in seen:
                seen.add(key)
                all_matches.append(match)

    # ------------------------------------------------------------------
    # 2. Parse col1right tables (group stage matches, 1998–2022)
    # ------------------------------------------------------------------
    group_tables = soup.find_all('table', class_='col1right')
    for table in group_tables:
        stage = _get_section_context(table)
        matches = parse_col1right_table(table, year, host, stage)
        for match in matches:
            key = (match['Home_Team'], match['Away_Team'], match['Home_Score'], match['Away_Score'])
            if key not in seen:
                seen.add(key)
                all_matches.append(match)

    # ------------------------------------------------------------------
    # 3. Fallback: scan any remaining wikitable tables that have score
    #    patterns but aren't standings tables (edge cases)
    # ------------------------------------------------------------------
    if len(all_matches) < EXPECTED_MATCHES.get(year, 999) * 0.5:
        for table in soup.find_all('table'):
            if table in group_tables:
                continue
            if 'wikitable' not in (table.get('class') or []):
                continue
            txt = table.get_text()
            if 'Pts' in txt or 'Pld' in txt:
                continue
            scores = re.findall(r'\d+\s*[–\-]\s*\d+', txt)
            if not scores:
                continue

            stage = _get_section_context(table)
            # Try pd.read_html as a last resort
            try:
                df = pd.read_html(StringIO(str(table)))[0]
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [' '.join(str(c).split()[:2]) for c in df.columns]

                col_names = [str(c).lower() for c in df.columns]
                team_cols = [i for i, c in enumerate(col_names) if 'team' in c]
                score_cols = [i for i, c in enumerate(col_names) if 'score' in c or 'result' in c]

                for _, row in df.iterrows():
                    if len(team_cols) >= 2:
                        home_team = _clean_team_name(str(row.iloc[team_cols[0]]))
                        away_team = _clean_team_name(str(row.iloc[team_cols[1]]))
                    else:
                        continue

                    hs, aw = 0, 0
                    if score_cols:
                        hs, aw = _parse_score(str(row.iloc[score_cols[0]]))

                    if not home_team or not away_team:
                        continue

                    key = (home_team, away_team, hs, aw)
                    if key not in seen:
                        seen.add(key)
                        all_matches.append({
                            'Year': year, 'Date': '', 'Host_Country': host,
                            'Host_City': host, 'Stage': stage,
                            'Home_Team': home_team, 'Away_Team': away_team,
                            'Home_Score': hs, 'Away_Score': aw,
                            'Penalties': 0, 'Penalties_Home_Score': 0,
                            'Penalties_Away_Score': 0, 'Winner': '',
                            'Draw': 1 if hs == aw else 0,
                        })
            except Exception:
                continue

    count = len(all_matches)
    expected = EXPECTED_MATCHES.get(year, '?')
    status = 'OK' if count == expected else f'{count}/{expected}'
    print(f'{status}')

    return all_matches


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------
def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Apply final cleaning and standardisation to the DataFrame."""
    df = df[df['Home_Team'].notna() & (df['Home_Team'] != '')].copy()
    df = df[df['Away_Team'].notna() & (df['Away_Team'] != '')].copy()

    df['Home_Score'] = pd.to_numeric(df['Home_Score'], errors='coerce').fillna(0).astype(int)
    df['Away_Score'] = pd.to_numeric(df['Away_Score'], errors='coerce').fillna(0).astype(int)
    df['Penalties'] = pd.to_numeric(df['Penalties'], errors='coerce').fillna(0).astype(int)
    df['Penalties_Home_Score'] = pd.to_numeric(df['Penalties_Home_Score'], errors='coerce').fillna(0).astype(int)
    df['Penalties_Away_Score'] = pd.to_numeric(df['Penalties_Away_Score'], errors='coerce').fillna(0).astype(int)
    df['Draw'] = pd.to_numeric(df['Draw'], errors='coerce').fillna(0).astype(int)
    df['Winner'] = df['Winner'].fillna('').str.strip()

    df['Date'] = df['Date'].fillna('').str.strip()

    # Standardise stage names
    stage_map = {
        'Final round': 'Final round',
        'Quarter-final': 'Quarter-final',
        'Semi-final': 'Semi-final',
        'Third place play-off': 'Third place play-off',
        'Final': 'Final',
        'Round of 16': 'Round of 16',
        'Round of 32': 'Round of 32',
        'Second round': 'Second round',
        'First round': 'First round',
        'Group Stage': 'Group Stage',
        'Preliminary round': 'Preliminary round',
        'Knockout stage': 'Knockout stage',
        'Play-off': 'Play-off',
    }

    def clean_stage(s):
        s = str(s).strip()
        for k, v in stage_map.items():
            if k.lower() in s.lower():
                return v
        return s.title()

    df['Stage'] = df['Stage'].apply(clean_stage)

    for col in ['Host_Country', 'Host_City', 'Home_Team', 'Away_Team']:
        df[col] = df[col].str.strip()

    df = df.sort_values(['Year', 'Date', 'Home_Team']).reset_index(drop=True)
    df = df[['Year', 'Date', 'Host_Country', 'Host_City', 'Stage',
             'Home_Team', 'Away_Team', 'Home_Score', 'Away_Score',
             'Penalties', 'Penalties_Home_Score', 'Penalties_Away_Score', 'Winner', 'Draw']]
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print('=' * 60)
    print('FIFA World Cup Match Scraper (1930–2022)')
    print('Data source: Wikipedia')
    print('=' * 60)
    print()

    all_matches: list[dict] = []

    for year, host in WORLD_CUPS:
        matches = scrape_tournament(year, host)
        all_matches.extend(matches)
        time.sleep(2)

    print()
    print(f'Total matches scraped: {len(all_matches)}')

    if not all_matches:
        print('ERROR: No matches scraped.')
        sys.exit(1)

    df = pd.DataFrame(all_matches)
    df = clean_dataset(df)

    output_path = 'data/fifa_world_cup_matches_1930_2022.csv'
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f'Saved to: {output_path}')

    total_expected = sum(EXPECTED_MATCHES.values())

    print()
    print('─' * 60)
    print('VERIFICATION')
    print('─' * 60)
    print(f'  Total rows in CSV:  {len(df)}')
    print(f'  Expected total:     {total_expected}')
    print(f'  Tournaments:        {df["Year"].nunique()}')
    print(f'  Year range:         {df["Year"].min()} – {df["Year"].max()}')
    print(f'  Stages present:     {sorted(df["Stage"].unique())}')
    print(f'  Unique home teams:  {df["Home_Team"].nunique()}')
    print(f'  Unique away teams:  {df["Away_Team"].nunique()}')
    print()

    print('Per-tournament counts:')
    print(f'  {"Year":<6} {"Scraped":<8} {"Expected":<9} Status')
    print(f'  {"─"*5} {"─"*7} {"─"*8} {"─"*6}')
    for year, host in WORLD_CUPS:
        count = (df['Year'] == year).sum()
        exp = EXPECTED_MATCHES.get(year, '?')
        ok = 'OK' if count == exp else 'MISMATCH'
        print(f'  {year:<6} {count:<8} {str(exp):<9} {ok}')

    missing = total_expected - len(df)
    if missing > 0:
        print(f'\n  {missing} matches missing.')
    elif missing < 0:
        print(f'\n  {abs(missing)} extra rows (possible duplicates).')
    else:
        print(f'\n  All {total_expected} matches accounted for.')


if __name__ == '__main__':
    main()
