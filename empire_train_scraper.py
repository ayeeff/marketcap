import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import os

# Define countries for each empire
EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa', 
    'Nigeria', 'Ghana', 'Kenya', 'Uganda', 'Tanzania', 'Zambia', 'Malawi', 
    'Botswana', 'Namibia', 'Lesotho', 'Eswatini', 'Jamaica', 'Trinidad and Tobago', 
    'Barbados', 'Bahamas', 'Belize', 'Guyana', 'Saint Lucia', 'Grenada', 
    'Saint Vincent and the Grenadines', 'Antigua and Barbuda', 'Dominica',
    'Saint Kitts and Nevis', 'Cyprus', 'Malta', 'Singapore', 'Malaysia', 
    'Brunei', 'Bangladesh', 'Sri Lanka', 'Maldives', 'Pakistan'
}

EMPIRE_2_COUNTRIES = {'United States'}

EMPIRE_3_COUNTRIES = {'China', 'Hong Kong', 'Taiwan'}

EMPIRES = {
    'Empire 1.0: Steam & Colonies British Commonwealth excluding India': EMPIRE_1_COUNTRIES,
    'Empire 2.0: Oil & Silicon United States': EMPIRE_2_COUNTRIES,
    'Empire 3.0: Rare Earths, Renewables & Robotics China + Hong Kong + taiwan': EMPIRE_3_COUNTRIES
}

def get_empire(country):
    """Match country to empire"""
    if pd.isna(country) or not country:
        return None
    country_str = str(country).strip()
    for empire_name, countries in EMPIRES.items():
        for emp_country in countries:
            if emp_country.lower() in country_str.lower():
                return empire_name
    return None

def parse_length(text):
    """Extract numeric length in km from text"""
    if pd.isna(text) or not text:
        return 0.0
    text = str(text).replace(',', '').replace(' ', '')
    # Match number before 'km'
    match = re.search(r'(\d+(?:\.\d+)?)\s*km', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    # Try plain number
    match = re.search(r'(\d+(?:\.\d+)?)', text)
    if match:
        return float(match.group(1))
    return 0.0

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# ===== SCRAPE METRO DATA =====
print("Scraping metro data...")
url_metro = 'https://en.wikipedia.org/wiki/List_of_metro_systems'
try:
    response = requests.get(url_metro, headers=headers, timeout=30)
    response.raise_for_status()
    
    # Parse all tables from the page
    tables = pd.read_html(response.text)
    
    # Find the main metro table (usually the largest one with City, Country, etc.)
    metro_df = None
    for df in tables:
        if 'City' in df.columns and 'Country' in df.columns and len(df) > 50:
            metro_df = df
            break
    
    if metro_df is not None:
        # Clean and process
        if 'System length' in metro_df.columns:
            metro_df['Length_km'] = metro_df['System length'].apply(parse_length)
        elif 'Length' in metro_df.columns:
            metro_df['Length_km'] = metro_df['Length'].apply(parse_length)
        else:
            print("Warning: Could not find length column in metro table")
            metro_df['Length_km'] = 0.0
        
        metro_df['Empire'] = metro_df['Country'].apply(get_empire)
        metro_df = metro_df[metro_df['Empire'].notna()]
        
        # Select relevant columns
        cols = ['Empire', 'Country', 'City']
        if 'Name' in metro_df.columns:
            cols.append('Name')
        cols.append('Length_km')
        
        metro_df = metro_df[cols]
        metro_df.to_csv('data/empire_metro.csv', index=False)
        print(f"Metro data saved: {len(metro_df)} rows")
    else:
        print("Could not find metro table")
        pd.DataFrame(columns=['Empire', 'Country', 'City', 'Name', 'Length_km']).to_csv('data/empire_metro.csv', index=False)
except Exception as e:
    print(f"Error scraping metro data: {e}")
    pd.DataFrame(columns=['Empire', 'Country', 'City', 'Name', 'Length_km']).to_csv('data/empire_metro.csv', index=False)

# ===== SCRAPE HSR DATA =====
print("\nScraping HSR data...")
url_hsr = 'https://en.wikipedia.org/wiki/List_of_high-speed_railway_lines'
hsr_data = []

try:
    response = requests.get(url_hsr, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all h3 headings (country sections)
    for heading in soup.find_all(['h2', 'h3']):
        # Look for country name in heading
        country_name = heading.get_text(strip=True)
        empire = get_empire(country_name)
        
        if empire:
            # Find next table after this heading
            current = heading.find_next_sibling()
            while current:
                if current.name == 'table' and 'wikitable' in current.get('class', []):
                    try:
                        df = pd.read_html(str(current))[0]
                        
                        # Try to find length column
                        length_col = None
                        for col in df.columns:
                            if 'length' in str(col).lower():
                                length_col = col
                                break
                        
                        if length_col:
                            # Extract route/line name
                            line_col = df.columns[0]  # Usually first column
                            
                            for idx, row in df.iterrows():
                                try:
                                    length = parse_length(row[length_col])
                                    if length > 0:
                                        hsr_data.append({
                                            'Empire': empire,
                                            'Country': country_name,
                                            'Line': str(row[line_col]),
                                            'Length_km': length
                                        })
                                except:
                                    continue
                    except:
                        pass
                    break
                elif current.name in ['h2', 'h3']:
                    break
                current = current.find_next_sibling()
    
    if hsr_data:
        df_hsr = pd.DataFrame(hsr_data)
        df_hsr.to_csv('data/empire_hsr.csv', index=False)
        print(f"HSR data saved: {len(df_hsr)} rows")
    else:
        print("No HSR data found")
        pd.DataFrame(columns=['Empire', 'Country', 'Line', 'Length_km']).to_csv('data/empire_hsr.csv', index=False)
        
except Exception as e:
    print(f"Error scraping HSR data: {e}")
    pd.DataFrame(columns=['Empire', 'Country', 'Line', 'Length_km']).to_csv('data/empire_hsr.csv', index=False)

# ===== SCRAPE SUBURBAN RAIL DATA =====
print("\nScraping suburban rail data...")
url_rail = 'https://en.wikipedia.org/wiki/List_of_suburban_and_commuter_rail_systems'
try:
    response = requests.get(url_rail, headers=headers, timeout=30)
    response.raise_for_status()
    
    # Parse all tables
    tables = pd.read_html(response.text)
    
    # Find the main table with City, Country, Length
    rail_df = None
    for df in tables:
        if 'Country' in df.columns and len(df) > 50:
            rail_df = df
            break
    
    if rail_df is not None:
        # Find length column
        length_col = None
        for col in rail_df.columns:
            if 'length' in str(col).lower() and 'km' in str(col).lower():
                length_col = col
                break
        
        if length_col:
            rail_df['Length_km'] = rail_df[length_col].apply(parse_length)
        else:
            print("Warning: Could not find length column in rail table")
            rail_df['Length_km'] = 0.0
        
        rail_df['Empire'] = rail_df['Country'].apply(get_empire)
        rail_df = rail_df[rail_df['Empire'].notna()]
        
        # Select relevant columns
        cols = ['Empire', 'Country']
        if 'City or area' in rail_df.columns:
            cols.append('City or area')
        elif 'City' in rail_df.columns:
            cols.append('City')
        if 'Name' in rail_df.columns:
            cols.append('Name')
        cols.append('Length_km')
        
        rail_df = rail_df[cols]
        rail_df.to_csv('data/empire_rail.csv', index=False)
        print(f"Rail data saved: {len(rail_df)} rows")
    else:
        print("Could not find rail table")
        pd.DataFrame(columns=['Empire', 'Country', 'City or area', 'Name', 'Length_km']).to_csv('data/empire_rail.csv', index=False)
        
except Exception as e:
    print(f"Error scraping rail data: {e}")
    pd.DataFrame(columns=['Empire', 'Country', 'City or area', 'Name', 'Length_km']).to_csv('data/empire_rail.csv', index=False)

print("\nScraping complete!")
print("\nSummary:")
for file in ['empire_metro.csv', 'empire_hsr.csv', 'empire_rail.csv']:
    filepath = f'data/{file}'
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        print(f"{file}: {len(df)} rows")
        if len(df) > 0:
            print(f"  Empires: {df['Empire'].nunique()}")
