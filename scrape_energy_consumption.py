import requests
import pandas as pd
from datetime import datetime
import os
from pathlib import Path

# Empire country definitions
EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa', 
    'Nigeria', 'Ghana', 'Kenya', 'Uganda', 'Tanzania', 'Zambia', 'Malawi', 
    'Botswana', 'Namibia', 'Jamaica', 'Singapore', 'Malaysia', 'Bangladesh', 
    'Sri Lanka', 'Pakistan', 'India'
}

EMPIRE_2_COUNTRIES = {'United States'}

EMPIRE_3_COUNTRIES = {'China', 'Hong Kong', 'Taiwan'}

# EIA API endpoint for total energy consumption
EIA_API_URL = "https://api.eia.gov/v2/international/data/"

def get_eia_data(api_key=None):
    """
    Fetch energy consumption data from EIA API
    """
    if not api_key:
        raise ValueError("EIA_API_KEY is required. Set it as an environment variable or pass it as a parameter.")
    
    print("Fetching energy consumption data from EIA API...")
    
    # All countries we need data for
    all_countries = EMPIRE_1_COUNTRIES | EMPIRE_2_COUNTRIES | EMPIRE_3_COUNTRIES
    
    energy_data = {}
    
    # EIA API v2 endpoint
    base_url = "https://api.eia.gov/v2/international/data/"
    
    params = {
        'api_key': api_key,
        'frequency': 'annual',
        'data[]': 'value',
        'facets[activityId][]': '1',  # Total Primary Energy Consumption
        'facets[productId][]': '44',   # Total Energy
        'facets[unit][]': 'QBTU',      # Quadrillion Btu
        'sort[0][column]': 'period',
        'sort[0][direction]': 'desc',
        'offset': 0,
        'length': 5000
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'response' not in data or 'data' not in data['response']:
            print(f"Unexpected API response structure: {data}")
            raise ValueError("Invalid API response format")
        
        # Process the data
        records = data['response']['data']
        print(f"Retrieved {len(records)} records from EIA API")
        
        # Get the most recent year's data for each country
        country_latest = {}
        for record in records:
            country = record.get('countryName')
            year = record.get('period')
            value = record.get('value')
            
            if country and year and value is not None:
                # Keep only the most recent year for each country
                if country not in country_latest or year > country_latest[country]['year']:
                    country_latest[country] = {
                        'year': year,
                        'value': float(value)
                    }
        
        # Map to our country names and filter
        for country, data_point in country_latest.items():
            if country in all_countries:
                energy_data[country] = data_point['value']
                print(f"  {country}: {data_point['value']} QBTU ({data_point['year']})")
        
        # Check for missing countries
        missing = all_countries - set(energy_data.keys())
        if missing:
            print(f"\nWarning: Missing data for countries: {missing}")
        
        if not energy_data:
            raise ValueError("No energy data retrieved from API")
        
        return energy_data
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from EIA API: {e}")
        raise
    except Exception as e:
        print(f"Error processing EIA data: {e}")
        raise

def calculate_empire_totals(energy_data):
    """Calculate total energy consumption for each empire"""
    
    empire_totals = {
        1: 0,
        2: 0,
        3: 0
    }
    
    for country, consumption in energy_data.items():
        if country in EMPIRE_1_COUNTRIES:
            empire_totals[1] += consumption
        elif country in EMPIRE_2_COUNTRIES:
            empire_totals[2] += consumption
        elif country in EMPIRE_3_COUNTRIES:
            empire_totals[3] += consumption
    
    return empire_totals

def create_empire_csv(empire_totals, output_dir='data'):
    """Create CSV file with empire energy consumption data"""
    
    # Create data directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Get current date for filename
    date_str = datetime.now().strftime('%d-%B-%Y')
    
    # Calculate total and percentages
    total_consumption = sum(empire_totals.values())
    
    data = []
    for empire_num in sorted(empire_totals.keys()):
        consumption = empire_totals[empire_num]
        percentage = (consumption / total_consumption * 100) if total_consumption > 0 else 0
        
        data.append({
            'empire#': f'{empire_num}.0',
            'total': round(consumption, 2),
            '%': round(percentage, 2)
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Save to CSV
    output_file = f'{output_dir}/{date_str}/empire_energy_consumption.csv'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False)
    
    print(f"Created: {output_file}")
    print(df)
    
    return output_file

def main():
    """Main function to run the scraper"""
    print("Starting Energy Consumption Scraper...")
    
    # Get EIA API key from environment variable (required)
    api_key = os.environ.get('EIA_API_KEY')
    
    if not api_key:
        print("ERROR: EIA_API_KEY environment variable is not set!")
        print("Please set it in GitHub Secrets or export it locally:")
        print("  export EIA_API_KEY='your_api_key_here'")
        exit(1)
    
    # Fetch energy data
    energy_data = get_eia_data(api_key)
    
    # Calculate empire totals
    empire_totals = calculate_empire_totals(energy_data)
    
    print("\nEmpire Energy Consumption Totals (Quadrillion Btu):")
    for empire, total in empire_totals.items():
        print(f"  Empire {empire}: {total:.2f}")
    
    # Create CSV file
    output_file = create_empire_csv(empire_totals)
    
    print(f"\nScraper completed successfully!")
    return output_file

if __name__ == "__main__":
    main()
