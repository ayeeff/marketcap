import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import os

# Define countries for each empire (matched to Wikipedia naming conventions)
EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa', 'Nigeria', 'Ghana', 'Kenya', 'Uganda', 'Tanzania',
    'Zambia', 'Malawi', 'Botswana', 'Namibia', 'Lesotho', 'Eswatini', 'Jamaica', 'Trinidad and Tobago', 'Barbados', 'Bahamas',
    'Belize', 'Guyana', 'Saint Lucia', 'Grenada', 'Saint Vincent and the Grenadines', 'Antigua and Barbuda', 'Dominica',
    'Saint Kitts and Nevis', 'Cyprus', 'Malta', 'Singapore', 'Malaysia', 'Brunei', 'Bangladesh', 'Sri Lanka', 'Maldives'
    # Note: Excluding India as per request, but included here for matching; filter later if needed
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
    country = country.strip()
    for empire_name, countries in EMPIRES.items():
        if country in countries or any(alias in country for alias in countries):  # Simple fuzzy match
            return empire_name
    return None

def parse_length(text):
    if pd.isna(text):
        return 0.0
    text = str(text)
    # Match number before 'km'
    match = re.search(r'(\d+(?:\.\d+)?)\s*km', text)
    if match:
        return float(match.group(1))
    # For plain numbers in suburban
    match = re.search(r'(\d+(?:\.\d+)?)', text)
    if match:
        return float(match.group(1))
    return 0.0

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Scrape Metro
print("Scraping metro data...")
url_metro = 'https://en.wikipedia.org/wiki/List_of_metro_systems'
tables_metro = pd.read_html(url_metro)
df_metro = tables_metro[0]
df_metro.columns = ['City', 'Country', 'Name', 'Service opened', 'Last expanded', 'Stations', 'Lines', 'System length', 'Annual ridership (millions)']
df_metro['Country'] = df_metro['Country'].astype(str).str.extract(r'>([^<]+)<')[0].str.strip()
df_metro['Length_km'] = df_metro['System length'].apply(parse_length)
df_metro['Empire'] = df_metro['Country'].apply(get_empire)
df_metro = df_metro[df_metro['Empire'].notna()][['Empire', 'Country', 'City', 'Name', 'Length_km']]
df_metro.to_csv('data/empire_metro.csv', index=False)
print(f"Metro data saved: {len(df_metro)} rows")

# Scrape HSR
print("Scraping HSR data...")
url_hsr = 'https://en.wikipedia.org/wiki/List_of_high-speed_railway_lines'
response = requests.get(url_hsr)
soup = BeautifulSoup(response.text, 'html.parser')
hsr_data = []
# Find country sections (h3 with mw-headline)
for h3 in soup.find_all('h3', class_='mw-headline'):
    country = h3.get_text(strip=True)
    # Only process relevant countries
    if get_empire(country) is not None:
        table = h3.find_next_sibling('table')
        if table:
            tables = pd.read_html(str(table))
            if tables:
                df = tables[0]
                # Assume standard columns; adjust based on table
                if 'Length' in df.columns:
                    df['Length_km'] = df['Length'].apply(parse_length)
                    # Filter operational
                    if 'Status' in df.columns:
                        df = df[df['Status'].str.contains('Operational', na=False)]
                    df['Country'] = country
                    df['Empire'] = get_empire(country)
                    for _, row in df.iterrows():
                        if pd.notna(row.get('Length_km', 0)) and row['Length_km'] > 0:
                            hsr_data.append({
                                'Empire': row['Empire'],
                                'Country': country,
                                'Line': row.get('Line', row.get('Route', '')),
                                'Length_km': row['Length_km']
                            })
df_hsr = pd.DataFrame(hsr_data)
df_hsr.to_csv('data/empire_hsr.csv', index=False)
print(f"HSR data saved: {len(df_hsr)} rows")

# Scrape Suburban Rail
print("Scraping suburban rail data...")
url_rail = 'https://en.wikipedia.org/wiki/List_of_suburban_and_commuter_rail_systems'
tables_rail = pd.read_html(url_rail)
df_rail = tables_rail[0]
# Columns may vary; assume standard
df_rail.columns = ['City or area', 'Country', 'Continent', 'Name', 'External link', 'Lines', 'Stations', 'Length (km)', 'Daily ridership']
df_rail['Country'] = df_rail['Country'].astype(str).str.extract(r'>([^<]+)<')[0].str.strip()
df_rail['Length_km'] = pd.to_numeric(df_rail['Length (km)'], errors='coerce').fillna(0)
df_rail['Empire'] = df_rail['Country'].apply(get_empire)
df_rail = df_rail[df_rail['Empire'].notna()][['Empire', 'Country', 'City or area', 'Name', 'Length_km']]
df_rail.to_csv('data/empire_rail.csv', index=False)
print(f"Rail data saved: {len(df_rail)} rows")

print("Scraping complete!")
