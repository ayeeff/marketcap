import requests
import pandas as pd
from datetime import datetime
import os
import time

# Commonwealth countries (ISO3 codes)
COMMONWEALTH_ISO3 = [
    'GBR',  # United Kingdom
    'CAN',  # Canada
    'AUS',  # Australia
    'SGP',  # Singapore
    'NZL',  # New Zealand
    'ZAF',  # South Africa
    'MYS',  # Malaysia
    'NGA',  # Nigeria
    'KEN',  # Kenya
    'GHA',  # Ghana
    'JAM',  # Jamaica
    'UGA',  # Uganda
    'TZA',  # Tanzania
    'ZMB',  # Zambia
    'MWI',  # Malawi
    'CYP',  # Cyprus
    'MLT',  # Malta
    'MUS',  # Mauritius
    'BWA',  # Botswana
    'NAM',  # Namibia
    'ZWE',  # Zimbabwe
    'BRB',  # Barbados
    'TTO',  # Trinidad and Tobago
    'FJI',  # Fiji
    'PNG',  # Papua New Guinea
]

# Empire definitions
EMPIRES = {
    'Empire 1.0': COMMONWEALTH_ISO3,
    'Empire 2.0': ['USA'],
    'Empire 3.0': ['CHN', 'HKG', 'TWN']  # China, Hong Kong, Taiwan
}

# World Bank indicators
GDP_PPP_INDICATOR = 'NY.GDP.MKTP.PP.CD'  # GDP, PPP (current international $)
RD_PCT_INDICATOR = 'GB.XPD.RSDV.GD.ZS'    # R&D expenditure (% of GDP)
GDP_CURRENT_INDICATOR = 'NY.GDP.MKTP.CD'  # GDP (current US$)

def fetch_country_data(country_code, indicator, year):
    """Fetch data for a single country from World Bank API."""
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}"
    params = {
        'date': str(year),
        'format': 'json',
        'per_page': 1000
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # World Bank API returns [metadata, data_array]
            if len(data) > 1 and data[1]:
                for entry in data[1]:
                    if entry['value'] is not None:
                        return entry['value']
        
        return None
        
    except Exception as e:
        print(f"  Error fetching {country_code}: {e}")
        return None

def fetch_empire_data(empire_countries, indicator, year):
    """Fetch data for all countries in an empire."""
    empire_total = 0
    countries_with_data = 0
    
    for country in empire_countries:
        value = fetch_country_data(country, indicator, year)
        
        if value is not None:
            empire_total += value
            countries_with_data += 1
            print(f"    {country}: ${value:,.0f}")
        else:
            print(f"    {country}: No data")
        
        # Be nice to the API
        time.sleep(0.1)
    
    print(f"  Total countries with data: {countries_with_data}/{len(empire_countries)}")
    return empire_total

def calculate_empire_totals(year, data_type, indicator):
    """Calculate empire totals for a given indicator."""
    print(f"\n{'='*60}")
    print(f"Processing {data_type.upper()} - Year {year}")
    print(f"{'='*60}")
    
    results = []
    empire_totals = {}
    
    # Fetch data for each empire
    for empire_name, countries in EMPIRES.items():
        print(f"\n{empire_name}:")
        total = fetch_empire_data(countries, indicator, year)
        empire_totals[empire_name] = total
        print(f"  TOTAL: ${total:,.0f}")
    
    # Calculate global total and percentages
    global_total = sum(empire_totals.values())
    print(f"\nGlobal Total: ${global_total:,.0f}")
    
    for empire, total in empire_totals.items():
        percentage = (total / global_total * 100) if global_total > 0 else 0
        results.append({
            'empire': empire,
            'total': total,
            'percentage': percentage
        })
    
    # Save to CSV
    os.makedirs('data', exist_ok=True)
    df = pd.DataFrame(results)
    filename = f'data/empire_{data_type}_{year}.csv'
    df.to_csv(filename, index=False)
    
    print(f"\n✓ Saved {filename}")
    print(f"\n{df.to_string(index=False)}")
    
    return df

def calculate_rd_expenditure(year):
    """Calculate R&D expenditure by combining R&D % and GDP."""
    print(f"\n{'='*60}")
    print(f"Processing R&D EXPENDITURE - Year {year}")
    print(f"{'='*60}")
    
    results = []
    empire_totals = {}
    
    for empire_name, countries in EMPIRES.items():
        print(f"\n{empire_name}:")
        empire_rd_total = 0
        countries_with_data = 0
        
        for country in countries:
            # Fetch both R&D percentage and GDP
            rd_pct = fetch_country_data(country, RD_PCT_INDICATOR, year)
            gdp = fetch_country_data(country, GDP_CURRENT_INDICATOR, year)
            
            if rd_pct is not None and gdp is not None:
                rd_absolute = (rd_pct / 100) * gdp
                empire_rd_total += rd_absolute
                countries_with_data += 1
                print(f"    {country}: {rd_pct:.2f}% of ${gdp:,.0f} = ${rd_absolute:,.0f}")
            else:
                print(f"    {country}: No data")
            
            # Be nice to the API
            time.sleep(0.1)
        
        empire_totals[empire_name] = empire_rd_total
        print(f"  Total countries with data: {countries_with_data}/{len(countries)}")
        print(f"  TOTAL: ${empire_rd_total:,.0f}")
    
    # Calculate global total and percentages
    global_total = sum(empire_totals.values())
    print(f"\nGlobal Total: ${global_total:,.0f}")
    
    for empire, total in empire_totals.items():
        percentage = (total / global_total * 100) if global_total > 0 else 0
        results.append({
            'empire': empire,
            'total': total,
            'percentage': percentage
        })
    
    # Save to CSV
    os.makedirs('data', exist_ok=True)
    df = pd.DataFrame(results)
    filename = f'data/empire_rd_expenditure_{year}.csv'
    df.to_csv(filename, index=False)
    
    print(f"\n✓ Saved {filename}")
    print(f"\n{df.to_string(index=False)}")
    
    return df

def main():
    """Main function to run annually."""
    # Use previous year for most complete data
    current_year = datetime.now().year - 1
    
    print("="*60)
    print(f"EMPIRE ECONOMIC DATA COLLECTION")
    print(f"Year: {current_year}")
    print("="*60)
    
    try:
        # Fetch and process GDP PPP data
        calculate_empire_totals(current_year, 'gdp_ppp', GDP_PPP_INDICATOR)
        
        # Fetch and process R&D expenditure data
        calculate_rd_expenditure(current_year)
        
        print("\n" + "="*60)
        print("✓ DATA COLLECTION COMPLETE!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Error in main execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
