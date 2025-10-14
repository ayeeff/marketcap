import wbdata
import pandas as pd
from datetime import datetime

# Commonwealth countries
COMMONWEALTH_COUNTRIES = [
    # Major economies
    'United Kingdom', 'Canada', 'Australia', 'Singapore',
    
    # Other Commonwealth nations
    'New Zealand', 'South Africa', 'Malaysia', 'Nigeria',
    'Kenya', 'Ghana', 'Jamaica', 'Uganda', 'Tanzania',
    'Zambia', 'Malawi', 'Cyprus', 'Malta', 'Mauritius',
    'Botswana', 'Namibia', 'Zimbabwe',
    
    # Caribbean
    'Barbados', 'Trinidad and Tobago',
    
    # Pacific
    'Fiji', 'Papua New Guinea'
]

# Empire definitions
EMPIRES = {
    'Empire 1.0': COMMONWEALTH_COUNTRIES,
    'Empire 2.0': ['United States'],
    'Empire 3.0': ['China', 'Hong Kong SAR, China', 'Taiwan, China']
}

# World Bank indicators
GDP_PPP_INDICATOR = 'NY.GDP.MKTP.PP.CD'  # GDP, PPP (current international $)
RD_INDICATOR = 'GB.XPD.RSDV.GD.ZS'  # R&D expenditure (% of GDP)
GDP_CURRENT_INDICATOR = 'NY.GDP.MKTP.CD'  # GDP (current US$) for R&D calculation

def get_empire_data(indicator, year):
    """Fetch data for all countries for a specific indicator and year."""
    try:
        # Get data for the specific year
        data = wbdata.get_dataframe({indicator: 'value'}, convert_date=False)
        
        # Filter for the year we want
        data = data[data.index.get_level_values('date') == str(year)]
        
        return data
    except Exception as e:
        print(f"Error fetching data for {indicator}: {e}")
        return None

def calculate_empire_totals(data, year, data_type):
    """Calculate totals and percentages for each empire."""
    results = []
    
    # Get country data
    country_values = {}
    for country in data.index.get_level_values('country').unique():
        try:
            val = data.loc[(country, str(year)), 'value']
            if pd.notna(val):
                country_values[country] = val
        except:
            continue
    
    # Calculate empire totals
    empire_totals = {}
    for empire, countries in EMPIRES.items():
        total = 0
        for country in countries:
            # Try exact match first
            if country in country_values:
                total += country_values[country]
            # Try partial match for variations
            else:
                for c in country_values.keys():
                    if country.lower() in c.lower() or c.lower() in country.lower():
                        total += country_values[c]
                        break
        empire_totals[empire] = total
    
    # Calculate global total
    global_total = sum(country_values.values())
    
    # Create results
    for empire, total in empire_totals.items():
        percentage = (total / global_total * 100) if global_total > 0 else 0
        results.append({
            'empire': empire,
            'total': total,
            'percentage': percentage
        })
    
    # Save to CSV in data folder
    import os
    os.makedirs('data', exist_ok=True)
    
    df = pd.DataFrame(results)
    filename = f'data/empire_{data_type}_{year}.csv'
    df.to_csv(filename, index=False)
    print(f"Saved {filename}")
    print(df)
    print()

def main():
    """Main function to run annually."""
    current_year = datetime.now().year - 1  # Use previous year for complete data
    
    print(f"Fetching data for year {current_year}...\n")
    
    # Fetch and process GDP PPP data
    print("Processing GDP PPP data...")
    gdp_data = get_empire_data(GDP_PPP_INDICATOR, current_year)
    if gdp_data is not None:
        calculate_empire_totals(gdp_data, current_year, 'gdp_ppp')
    
    # Fetch and process R&D expenditure data
    print("Processing R&D expenditure data...")
    
    # R&D is stored as % of GDP, so we need to calculate absolute values
    rd_pct_data = get_empire_data(RD_INDICATOR, current_year)
    gdp_current_data = get_empire_data(GDP_CURRENT_INDICATOR, current_year)
    
    if rd_pct_data is not None and gdp_current_data is not None:
        # Calculate absolute R&D expenditure
        rd_absolute = pd.DataFrame(index=rd_pct_data.index)
        
        for idx in rd_pct_data.index:
            country, year = idx
            try:
                rd_pct = rd_pct_data.loc[idx, 'value']
                gdp = gdp_current_data.loc[idx, 'value']
                if pd.notna(rd_pct) and pd.notna(gdp):
                    rd_absolute.loc[idx, 'value'] = (rd_pct / 100) * gdp
            except:
                continue
        
        calculate_empire_totals(rd_absolute, current_year, 'rd_expenditure')
    
    print("Data collection complete!")

if __name__ == "__main__":
    main()
