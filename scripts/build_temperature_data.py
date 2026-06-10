"""Build host city temperature dataset using Open-Meteo Historical API.

Geocodes each unique host city, then fetches daily mean temperatures
during each tournament's date range from the ERA5 reanalysis (1940+).

For pre-1940 tournaments, uses the earliest available data as climate proxy.
"""

import time
import requests
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

HEADERS = {'User-Agent': 'world-cup-heat-impact/1.0'}

GEO_URL = 'https://geocoding-api.open-meteo.com/v1/search'
ARCHIVE_URL = 'https://archive-api.open-meteo.com/v1/archive'

# Manual coordinates for cities that geocoding might struggle with
MANUAL_COORDS = {
    'Guadalajara [ a ]': (20.66, -103.35),
    'D.C': (38.9072, -77.0369),
    'East Rutherford': (40.8137, -74.0743),
    'Foxborough': (42.0654, -71.2479),
    'Stanford': (37.4275, -122.1697),
    'Pasadena': (34.1478, -118.1445),
    'Pontiac': (42.6389, -83.2910),
    'San Nicolás de los Garza': (25.7417, -100.3014),
    'Zapopan': (20.7203, -103.3919),
    'Nezahualcóyotl': (19.4029, -99.0061),
    'Rifu': (38.3306, 140.9756),
    'Fukuroi': (34.7520, 137.9265),
    'Seogwipo': (33.2536, 126.5608),
    'Ibaraki': (34.8164, 135.5686),
    'Miyagi': (38.2682, 140.8694),
    'Saitama': (35.8617, 139.6453),
    'Shizuoka': (34.9756, 138.3828),
    'Al Rayyan': (25.2916, 51.4247),
    'Al Khor': (25.6804, 51.4969),
    'Al Wakrah': (25.1753, 51.6035),
    'Lusail': (25.4232, 51.5054),
    'Solna': (59.3600, 18.0008),
    'Sandviken': (60.6167, 16.7667),
    'Borås': (57.7210, 12.9401),
    'Örebro': (59.2753, 15.2134),
    'Västerås': (59.6099, 16.5448),
    'Malmö': (55.6050, 13.0038),
    'Helsingborg': (56.0465, 12.6945),
    'Norrköping': (58.5942, 16.1826),
    'Uddevalla': (58.3498, 11.9356),
    'Halmstad': (56.6744, 12.8578),
    'Eskilstuna': (59.3703, 16.5102),
    'Gothenburg': (57.7089, 11.9746),
    'Colombes': (48.9227, 2.2545),
    'Antibes': (43.5804, 7.1251),
    'Reims': (49.2583, 4.0317),
    'Le Havre': (49.4944, 0.1079),
    'Lille': (50.6292, 3.0573),
    'Strasbourg': (48.5734, 7.7521),
    'Lens': (50.4290, 2.8319),
    'Saint-Denis': (48.9362, 2.3574),
    'Saint-Étienne': (45.4397, 4.3872),
    'Arica': (-18.4786, -70.3208),
    'Rancagua': (-34.1701, -70.7406),
    'Viña del Mar': (-33.0245, -71.5518),
    'A Coruña': (43.3623, -8.4115),
    'Gijón': (43.5322, -5.6611),
    'Málaga': (36.7213, -4.4214),
    'León': (21.1251, -101.6860),
    'Irapuato': (20.6770, -101.3554),
    'Nezahualcóyotl': (19.4029, -99.0061),
    'Querétaro': (20.5888, -100.3899),
    'Monterrey': (25.6866, -100.3161),
    'Toluca': (19.2826, -99.6557),
    'Puebla': (19.0414, -98.2063),
    'Guadalajara': (20.6597, -103.3496),
    'Bloemfontein': (-29.0852, 26.1596),
    'Nelspruit': (-25.4753, 30.9694),
    'Polokwane': (-23.8962, 29.4483),
    'Rustenburg': (-25.6676, 27.2421),
    'Durban': (-29.8587, 31.0218),
    'Pretoria': (-25.7479, 28.2293),
    'Port Elizabeth': (-33.9608, 25.6022),
    'Cape Town': (-33.9249, 18.4241),
    'Johannesburg': (-26.2041, 28.0473),
    'Cuiabá': (-15.6010, -56.0974),
    'Manaus': (-3.1190, -60.0217),
    'Natal': (-5.7793, -35.2009),
    'Fortaleza': (-3.7319, -38.5267),
    'Recife': (-8.0476, -34.8770),
    'Salvador': (-12.9777, -38.5016),
    'Brasília': (-15.8267, -47.9218),
    'Belo Horizonte': (-19.9167, -43.9345),
    'Curitiba': (-25.4290, -49.2671),
    'Porto Alegre': (-30.0346, -51.2177),
    'Rio de Janeiro': (-22.9068, -43.1729),
    'São Paulo': (-23.5505, -46.6333),
    'Buenos Aires': (-34.6037, -58.3816),
    'Córdoba': (-31.4201, -64.1888),
    'Mar del Plata': (-38.0055, -57.5426),
    'Mendoza': (-32.8895, -68.8458),
    'Rosario': (-32.9468, -60.6393),
    'Kaliningrad': (54.7104, 20.4522),
    'Kazan': (55.7961, 49.1064),
    'Moscow': (55.7558, 37.6173),
    'Nizhny Novgorod': (56.2965, 43.9361),
    'Rostov-on-Don': (47.2357, 39.7015),
    'Saint Petersburg': (59.9343, 30.3351),
    'Samara': (53.1959, 50.1002),
    'Saransk': (54.1874, 45.1839),
    'Sochi': (43.5855, 39.7231),
    'Volgograd': (48.7080, 44.5133),
    'Yekaterinburg': (56.8389, 60.6057),
    'Trieste': (45.6495, 13.7768),
    'Turin': (45.0703, 7.6869),
    'Genoa': (44.4056, 8.9463),
    'Bologna': (44.4949, 11.3426),
    'Florence': (43.7696, 11.2558),
    'Rome': (41.9028, 12.4964),
    'Naples': (40.8518, 14.2681),
    'Milan': (45.4642, 9.1900),
    'Palermo': (38.1157, 13.3615),
    'Cagliari': (39.2238, 9.1217),
    'Bari': (41.1171, 16.8719),
    'Udine': (46.0711, 13.2346),
    'Verona': (45.4384, 10.9916),
    'Dortmund': (51.5136, 7.4653),
    'Düsseldorf': (51.2277, 6.7735),
    'Gelsenkirchen': (51.5177, 7.0857),
    'Hanover': (52.3759, 9.7320),
    'Kaiserslautern': (49.4401, 7.7491),
    'Leipzig': (51.3397, 12.3731),
    'Nuremberg': (49.4521, 11.0767),
    'Stuttgart': (48.7758, 9.1829),
    'Munich': (48.1351, 11.5820),
    'Frankfurt': (50.1109, 8.6821),
    'Hamburg': (53.5511, 9.9937),
    'Cologne': (50.9375, 6.9603),
    'Berlin': (52.5200, 13.4050),
    'West Berlin': (52.5200, 13.4050),
    'Busan': (35.1796, 129.0756),
    'Daegu': (35.8714, 128.6014),
    'Daejeon': (36.3504, 127.3845),
    'Gwangju': (35.1595, 126.8526),
    'Incheon': (37.4563, 126.7052),
    'Jeonju': (35.8242, 127.1480),
    'Seoul': (37.5665, 126.9780),
    'Suwon': (37.2636, 127.0286),
    'Ulsan': (35.5384, 129.3114),
    'Sapporo': (43.0618, 141.3545),
    'Yokohama': (35.4437, 139.6380),
    'Kobe': (34.6901, 135.1955),
    'Osaka': (34.6937, 135.5023),
    'Niigata': (37.9162, 139.0364),
    'Chicago': (41.8781, -87.6298),
    'Dallas': (32.7767, -96.7970),
    'Orlando': (28.5383, -81.3792),
    'London': (51.5074, -0.1278),
    'Birmingham': (52.4862, -1.8904),
    'Liverpool': (53.4084, -2.9916),
    'Manchester': (53.4808, -2.2426),
    'Middlesbrough': (54.5742, -1.2350),
    'Sheffield': (53.3811, -1.4701),
    'Sunderland': (54.9069, -1.3838),
    'Basel': (47.5596, 7.5886),
    'Bern': (46.9480, 7.4474),
    'Geneva': (46.2044, 6.1432),
    'Lausanne': (46.5197, 6.6323),
    'Lugano': (46.0037, 8.9511),
    'Zürich': (47.3769, 8.5417),
    'Montevideo': (-34.9011, -56.1645),
    'Mexico City': (19.4326, -99.1332),
    'Ibaraki, Osaka': (34.8164, 135.5686),
    'Ōita': (33.2396, 131.6093),
}


def geocode_city(city: str) -> tuple[float, float] | None:
    """Get lat/lon for a city."""
    if city in MANUAL_COORDS:
        return MANUAL_COORDS[city]

    params = {'name': city, 'count': 1, 'language': 'en', 'format': 'json'}
    try:
        resp = requests.get(GEO_URL, params=params, headers=HEADERS, timeout=10)
        data = resp.json()
        if 'results' in data and data['results']:
            r = data['results'][0]
            return (round(r['latitude'], 4), round(r['longitude'], 4))
    except Exception:
        pass
    return None


def fetch_temperature(lat: float, lon: float, start: str, end: str) -> float | None:
    """Fetch mean daily temperature for a date range."""
    year = int(start[:4])
    if year < 1940:
        # Use 1940 as fallback for climate normal approximation
        start = f'1940{start[4:]}'
        end = f'1940{end[4:]}'

    params = {
        'latitude': lat,
        'longitude': lon,
        'start_date': start,
        'end_date': end,
        'daily': 'temperature_2m_mean',
        'timezone': 'UTC',
    }
    try:
        resp = requests.get(ARCHIVE_URL, params=params, headers=HEADERS, timeout=30)
        data = resp.json()
        temps = data.get('daily', {}).get('temperature_2m_mean', [])
        if temps:
            valid = [t for t in temps if t is not None]
            if valid:
                return round(sum(valid) / len(valid), 1)
    except Exception:
        pass
    return None


def main():
    df = pd.read_csv(DATA_DIR / 'fifa_world_cup_matches_1930_2022.csv')
    df['Date'] = pd.to_datetime(df['Date'])

    # Get tournament date ranges per city per year
    city_years = df.groupby(['Host_City', 'Year'])['Date'].agg(['min', 'max']).reset_index()
    city_years.columns = ['City', 'Year', 'Start', 'End']

    # Cache geocoded coordinates
    coords = {}
    for city in df['Host_City'].unique():
        latlon = geocode_city(city)
        if latlon:
            coords[city] = latlon
        else:
            print(f'  WARNING: no coords for {city}')

    print(f'Geocoded {len(coords)}/{df["Host_City"].nunique()} cities')

    results = []
    failed = []

    for i, (_, row) in enumerate(city_years.iterrows()):
        city = row['City']
        year = row['Year']
        start = row['Start'].strftime('%Y-%m-%d')
        end = row['End'].strftime('%Y-%m-%d')

        if city not in coords:
            failed.append((city, year))
            continue

        lat, lon = coords[city]
        temp = fetch_temperature(lat, lon, start, end)

        if temp is not None:
            results.append({
                'City': city, 'Year': year,
                'Start_Date': start, 'End_Date': end,
                'Avg_Temp_C': temp,
            })
            if (i + 1) % 50 == 0:
                print(f'  [{i+1}/{len(city_years)}] done')

        time.sleep(0.15)  # polite to API

    if not results:
        print('No temperature data retrieved.')
        return

    df_out = pd.DataFrame(results)
    output = DATA_DIR / 'host_city_temperatures.csv'
    df_out.to_csv(output, index=False)
    print(f'\nSaved {len(df_out)} rows to {output}')
    print(f'Cities covered: {df_out["City"].nunique()}')
    print(f'Temperature range: {df_out["Avg_Temp_C"].min():.1f} to {df_out["Avg_Temp_C"].max():.1f}°C')

    if failed:
        print(f'\nFailed ({len(failed)}):')
        for c, y in failed[:10]:
            print(f'  {c} ({y})')


if __name__ == '__main__':
    main()
