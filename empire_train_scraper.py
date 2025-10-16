import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import os
from io import StringIO

# Define countries for each empire (matched to Wikipedia naming conventions)
EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa', 'Nigeria', 'Ghana', 'Kenya', 'Uganda', 'Tanzania',
    'Zambia', 'Malawi', 'Botswana', 'Namibia', 'Lesotho', 'Eswatini', 'Jamaica', 'Trinidad and Tobago', 'Barbados', 'Bahamas',
    'Belize', 'Guyana', 'Saint Lucia', 'Grenada', 'Saint Vincent and the Grenadines', 'Antigua and Barbuda', 'Dominica',
    'Saint Kitts and Nevis', 'Cyprus', 'Malta', 'Singapore', 'Malaysia', 'Brunei', 'Bangladesh', 'Sri Lanka', 'Maldives',
    'Pakistan'  # Excluding India
    # Add more as needed; small islands may not have data
}

EMPIRE_2_COUNTRIES = {'United States'}

EMPIRE_3_COUNTRIES = {'China', 'Hong Kong', 'Taiwan'}

EMPIRES = {
    'Empire 1.0: Steam & Colonies British Commonwealth excluding India': EMPIRE_1_COUNTRIES,
    'Empire 2.0: Oil & Silicon United States': EMPIRE_2_COUNTRIES,
    'Empire 3.0: Rare Earths, Renewables & Robotics China + Hong Kong + taiwan': EMPIRE_3_COUNTRIES
}

def get_empire(country):
    if pd.isna(country) or str(country).lower() == 'nan':
        return None
    country = str(country).strip().lower()
    for empire_name, countries in EMPIRES.items():
        lowered_countries_list = [c.lower() for c in countries]
        if country in lowered_countries_list or any(alias in country for alias in lowered_countries_list):
            return empire_name
    return None

def parse_length(text):
    if pd.isna(text):
        return 0.0
    text = str(text).replace(',', '')
    # Match number before 'km'
    match = re.search(r'(\d+(?:\.\d+)?)\s*km', text)
    if match:
        return float(match.group(1))
    # For plain numbers in suburban
    match = re.search(r'(\d+(?:\.\d+)?)', text)
    if match:
        return float(match.group(1))
    return 0.0

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Scrape Metro
print("Scraping metro data...")
url_metro = 'https://en.wikipedia.org/wiki/List_of_metro_systems'
response_metro = requests.get(url_metro, headers=headers)
soup_metro = BeautifulSoup(response_metro.text, 'html.parser')
# Find wikitable class tables
wikitable = soup_metro.find('table', {'class': 'wikitable'})
if wikitable:
    tables_metro = pd.read_html(StringIO(str(wikitable)), flavor='lxml')
    df_metro = tables_metro[0]
    df_metro.columns = ['City', 'Country', 'Name', 'Service opened', 'Last expanded', 'Stations', 'Lines', 'System length', 'Annual ridership (millions)']
    df_metro['Country'] = df_metro['Country'].astype(str).str.extract(r'>([^<]+)<')[0].str.strip()
    df_metro['Length_km'] = df_metro['System length'].apply(parse_length)
    df_metro['Empire'] = df_metro['Country'].apply(get_empire)
    df_metro = df_metro[df_metro['Empire'].notna()][['Empire', 'Country', 'City', 'Name', 'Length_km']]
    df_metro.to_csv('data/empire_metro.csv', index=False)
    print(f"Metro data saved: {len(df_metro)} rows")
else:
    print("No metro table found")

# Scrape HSR
print("Scraping HSR data...")
url_hsr = 'https://en.wikipedia.org/wiki/List_of_high-speed_railway_lines'
response_hsr = requests.get(url_hsr, headers=headers)
soup = BeautifulSoup(response_hsr.text, 'html.parser')
hsr_data = []
# Find country sections (h3 with mw-headline)
for h3 in soup.find_all('h3'):
    headline = h3.find('span', class_='mw-headline')
    if not headline:
        continue
    country = headline.get_text(strip=True)
    # Only process relevant countries
    if get_empire(country) is not None:
        # Look for the next table after this heading
        table = h3.find_next('table', {'class': 'wikitable'})
        if table:
            try:
                tables = pd.read_html(StringIO(str(table)), flavor='lxml')
                if tables:
                    df = tables[0]
                    # Find length column
                    length_cols = [col for col in df.columns if 'length' in str(col).lower()]
                    if length_cols:
                        length_col = length_cols[0]
                        df['Length_km'] = df[length_col].apply(parse_length)
                    else:
                        continue
                    # Filter operational
                    status_cols = [col for col in df.columns if 'status' in str(col).lower()]
                    if status_cols:
                        status_col = status_cols[0]
                        df = df[df[status_col].str.contains('Operational', na=False, case=False)]
                    df['Country'] = country
                    df['Empire'] = get_empire(country)
                    # Find route/line column
                    route_cols = [col for col in df.columns if 'route' in str(col).lower() or 'line' in str(col).lower()]
                    if route_cols:
                        route_col = route_cols[0]
                    else:
                        route_col = df.columns[0]  # Fallback
                    for _, row in df.iterrows():
                        if pd.notna(row.get('Length_km')) and row['Length_km'] > 0:
                            hsr_data.append({
                                'Empire': row['Empire'],
                                'Country': country,
                                'Line': str(row.get(route_col, '')),
                                'Length_km': row['Length_km']
                            })
            except Exception as e:
                print(f"Error processing HSR table for {country}: {e}")
                continue

df_hsr = pd.DataFrame(hsr_data)
df_hsr.to_csv('data/empire_hsr.csv', index=False)
print(f"HSR data saved: {len(df_hsr)} rows")

# Scrape Suburban Rail
print("Scraping suburban rail data...")
url_rail = 'https://en.wikipedia.org/wiki/List_of_suburban_and_commuter_rail_systems'
response_rail = requests.get(url_rail, headers=headers)
soup_rail = BeautifulSoup(response_rail.text, 'html.parser')
wikitable_rail = soup_rail.find('table', {'class': 'wikitable'})
if wikitable_rail:
    tables_rail = pd.read_html(StringIO(str(wikitable_rail)), flavor='lxml')
    df_rail = tables_rail[0]
    # Columns may vary; assume standard
    df_rail.columns = ['City or area', 'Country', 'Continent', 'Name', 'External link', 'Lines', 'Stations', 'Length (km)', 'Daily ridership']
    df_rail['Country'] = df_rail['Country'].astype(str).str.extract(r'>([^<]+)<')[0].str.strip()
    df_rail['Length_km'] = df_rail['Length (km)'].apply(parse_length)
    df_rail['Empire'] = df_rail['Country'].apply(get_empire)
    df_rail = df_rail[df_rail['Empire'].notna()][['Empire', 'Country', 'City or area', 'Name', 'Length_km']]
    df_rail.to_csv('data/empire_rail.csv', index=False)
    print(f"Rail data saved: {len(df_rail)} rows")
else:
    print("No rail table found")

print("Scraping complete!")
