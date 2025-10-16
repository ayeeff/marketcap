import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import os

# Define countries for each empire - SIMPLIFIED TO 1, 2, 3
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
    '1': EMPIRE_1_COUNTRIES,
    '2': EMPIRE_2_COUNTRIES,
    '3': EMPIRE_3_COUNTRIES
}

def get_empire(country):
    """Match country to empire (returns 1, 2, or 3)"""
    if pd.isna(country) or not country:
        return None
    country_str = str(country).strip()
    for empire_num, countries in EMPIRES.items():
        for emp_country in countries:
            if emp_country.lower() in country_str.lower():
                return empire_num
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
    
    # Strategy: Find h3 headings that contain country names
    # These are marked with <span class="mw-headline">
    for heading in soup.find_all('h3'):
        span = heading.find('span', class_='mw-headline')
        if not span:
            continue
            
        country_name = span.get_text(strip=True)
        empire = get_empire(country_name)
        
        if empire:
            print(f"  Found {country_name} -> Empire {empire}")
            
            # Find the next table after this heading
            current_element = heading.find_next_sibling()
            while current_element:
                if current_element.name == 'table' and 'wikitable' in current_element.get('class', []):
                    try:
                        # Parse this table
                        df = pd.read_html(str(current_element))[0]
                        
                        # Find length column
                        length_col = None
                        for col in df.columns:
                            if 'length' in str(col).lower():
                                length_col = col
                                break
                        
                        if length_col:
                            # Get line/route name (usually first column)
                            line_col = df.columns[0]
                            
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
                    except Exception as e:
                        print(f"  Error parsing table for {country_name}: {e}")
                    break
                elif current_element.name in ['h2', 'h3', 'h4']:
                    # Hit next section, stop looking
                    break
                current_element = current_element.find_next_sibling()
    
    if hsr_data:
        df_hsr = pd.DataFrame(hsr_data)
        df_hsr.to_csv('data/empire_hsr.csv', index=False)
        print(f"HSR data saved: {len(df_hsr)} rows")
    else:
        print("No HSR data found")
        pd.DataFrame(columns=['Empire', 'Country', 'Line', 'Length_km']).to_csv('data/empire_hsr.csv', index=False)
        
except Exception as e:
    print(f"Error scraping HSR data: {e}")
    import traceback
    traceback.print_exc()
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

print("\n" + "="*60)
print("SCRAPING COMPLETE!")
print("="*60)
print("\nSummary:")
for file in ['empire_metro.csv', 'empire_hsr.csv', 'empire_rail.csv']:
    filepath = f'data/{file}'
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        print(f"\n{file}: {len(df)} rows")
        if len(df) > 0:
            print(f"  Empires present: {sorted(df['Empire'].unique())}")
            print(f"  Countries: {df['Country'].nunique()}")
            for empire in sorted(df['Empire'].unique()):
                empire_df = df[df['Empire'] == empire]
                total_km = empire_df['Length_km'].sum()
                print(f"  Empire {empire}: {len(empire_df)} entries, {total_km:,.1f} km total")
