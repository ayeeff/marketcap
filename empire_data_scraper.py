import wbgapi as wb
import pandas as pd
from datetime import datetime
import os

# Commonwealth countries (ISO3 codes for API)
COMMONWEALTH_ISO3 = {
    'GBR': 'United Kingdom',
    'CAN': 'Canada', 
    'AUS': 'Australia',
    'SGP': 'Singapore',
    'NZL': 'New Zealand',
    'ZAF': 'South Africa',
    'MYS': 'Malaysia',
    'NGA': 'Nigeria',
    'KEN': 'Kenya',
    'GHA': 'Ghana',
    'JAM': 'Jamaica',
    'UGA': 'Uganda',
    'TZA': 'Tanzania',
    'ZMB': 'Zambia',
    'MWI': 'Malawi',
    'CYP': 'Cyprus',
    'MLT': 'Malta',
    'MUS': 'Mauritius',
    'BWA': 'Botswana',
    'NAM': 'Namibia',
    'ZWE': 'Zimbabwe',
    'BRB': 'Barbados',
    'TTO': 'Trinidad and Tobago',
    'FJI': 'Fiji',
    'PNG': 'Papua New Guinea'
}

# Empire definitions (using ISO3 codes)
EMPIRES = {
    'Empire 1.0': list(COMMONWEALTH_ISO3.keys()),
    'Empire 2.0': ['USA'],
    'Empire 3.0': ['CHN', 'HKG', 'TWN']  # China, Hong Kong, Taiwan
}

# World Bank indicators
GDP_PPP_INDICATOR = 'NY.GDP.MKTP.PP.CD'  # GDP, PPP (current international $)
RD_PCT_INDICATOR = 'GB.XPD.RSDV.GD.ZS'    # R&D expenditure (% of GDP)
GDP_CURRENT_INDICATOR = 'NY.GDP.MKTP.CD'  # GDP (current US$)

def fetch_indicator_data(indicator, countries, year):
    """Fetch data for specific countries and indicator."""
    try:
        # Get data for all specified countries
        data = wb.data.DataFrame(indicator, countries, time=year, skipBlanks=True, numericTimeKeys=True)
        return data
    except Exception as e:
        print(f"Error fetching {indicator}: {e}")
        return None

def calculate_empire_totals(year, data_type, indicator):
    """Calculate empire totals for a given indicator."""
    print(f"\nProcessing {data_type}...")
    
    results = []
    empire_totals = {}
    
    # Fetch data for each empire
    for empire_name, countries in EMPIRES.items():
        try:
            data = fetch_indicator_data(indicator, countries, year)
            
            if data is not None and not data.empty:
                # Sum up all countries in the empire
                if year in data.columns:
                    total = data[year].sum()
                else:
                    # Try year as string
                    total = data[str(year)].sum()
                    
                empire_totals[empire_name] = total
                print(f"  {empire_name}: ${total:,.0f}")
            else:
                empire_totals[empire_name] = 0
                print(f"  {empire_name}: No data available")
                
        except Exception as e:
            print(f"  {empire_name}: Error - {e}")
            empire_totals[empire_name] = 0
    
    # Calculate global total and percentages
    global_total = sum(empire_totals.values())
    
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
    print(df.to_string(index=False))
    
    return df

def calculate_rd_expenditure(year):
    """Calculate R&D expenditure by combining R&D % and GDP."""
    print(f"\nProcessing R&D expenditure...")
    
    results = []
    empire_totals = {}
    
    for empire_name, countries in EMPIRES.items():
        try:
            # Fetch both R&D percentage and GDP
            rd_pct_data = fetch_indicator_data(RD_PCT_INDICATOR, countries, year)
            gdp_data = fetch_indicator_data(GDP_CURRENT_INDICATOR, countries, year)
            
            if rd_pct_data is not None and gdp_data is not None:
                # Calculate absolute R&D for each country
                rd_absolute = 0
                
                for country in countries:
                    try:
                        year_col = year if year in rd_pct_data.columns else str(year)
                        
                        if country in rd_pct_data.index and country in gdp_data.index:
                            rd_pct = rd_pct_data.loc[country, year_col]
                            gdp = gdp_data.loc[country, year_col]
                            
                            if pd.notna(rd_pct) and pd.notna(gdp):
                                rd_absolute += (rd_pct / 100) * gdp
                    except:
                        continue
                
                empire_totals[empire_name] = rd_absolute
                print(f"  {empire_name}: ${rd_absolute:,.0f}")
            else:
                empire_totals[empire_name] = 0
                print(f"  {empire_name}: No data available")
                
        except Exception as e:
            print(f"  {empire_name}: Error - {e}")
            empire_totals[empire_name] = 0
    
    # Calculate global total and percentages
    global_total = sum(empire_totals.values())
    
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
    print(df.to_string(index=False))
    
    return df

def main():
    """Main function to run annually."""
    # Use previous year for most complete data
    current_year = datetime.now().year - 1
    
    print("=" * 60)
    print(f"Empire Economic Data Collection - Year {current_year}")
    print("=" * 60)
    
    try:
        # Fetch and process GDP PPP data
        calculate_empire_totals(current_year, 'gdp_ppp', GDP_PPP_INDICATOR)
        
        # Fetch and process R&D expenditure data
        calculate_rd_expenditure(current_year)
        
        print("\n" + "=" * 60)
        print("✓ Data collection complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error in main execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
