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

def test_eia_api(api_key):
    """
    Test the EIA API and print raw response to understand data structure
    """
    print("Testing EIA API connection...")
    
    base_url = "https://api.eia.gov/v2/international/data/"
    
    params = {
        'api_key': api_key,
        'frequency': 'annual',
        'data[]': 'value',
        'facets[activityId][]': '1',
        'facets[productId][]': '44',
        'facets[unit][]': 'QBTU',
        'sort[0][column]': 'period',
        'sort[0][direction]': 'desc',
        'offset': 0,
        'length': 10  # Just get 10 records for testing
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        print(f"API Response Status: {response.status_code}")
        
        response.raise_for_status()
        
        data = response.json()
        
        print(f"\nAPI Response Keys: {data.keys()}")
        
        if 'response' in data:
            print(f"Response Keys: {data['response'].keys()}")
            
            if 'data' in data['response']:
                records = data['response']['data']
                print(f"\nNumber of records: {len(records)}")
                
                if records:
                    print(f"\nFirst record:")
                    import json
                    print(json.dumps(records[0], indent=2))
                    
                    print(f"\nAll keys in first record: {records[0].keys()}")
        
        return data
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_eia_data(api_key=None):
    """
    Fetch energy consumption data from EIA API
    """
    if not api_key:
        raise ValueError("EIA_API_KEY is required. Set it as an environment variable or pass it as a parameter.")
    
    print("Fetching energy consumption data from EIA API...")
    
    # All countries we need data for
    all_countries = EMPIRE_1_COUNTRIES | EMPIRE_2_COUNTRIES | EMPIRE_3_COUNTRIES
    
    # Map EIA country names to our standardized names
    eia_country_mapping = {
        'China, People\'s Republic of': 'China',
        'Hong Kong Special Administrative Region': 'Hong Kong',
        'Taiwan': 'Taiwan',
        'United States': 'United States',
        'United Kingdom': 'United Kingdom',
        'Canada': 'Canada',
        'Australia': 'Australia',
        'New Zealand': 'New Zealand',
        'South Africa': 'South Africa',
        'Nigeria': 'Nigeria',
        'Ghana': 'Ghana',
        'Kenya': 'Kenya',
        'Uganda': 'Uganda',
        'Tanzania': 'Tanzania',
        'Zambia': 'Zambia',
        'Malawi': 'Malawi',
        'Botswana': 'Botswana',
        'Namibia': 'Namibia',
        'Jamaica': 'Jamaica',
        'Singapore': 'Singapore',
        'Malaysia': 'Malaysia',
        'Bangladesh': 'Bangladesh',
        'Sri Lanka': 'Sri Lanka',
        'Pakistan': 'Pakistan',
        'India': 'India',
    }
    
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
        
        # Debug: Print ALL unique country names to see the format
        unique_countries = set()
        for record in records:
            country = record.get('countryName')
            if country:
                unique_countries.add(country)
        
        print(f"\nTotal unique countries in API: {len(unique_countries)}")
        print(f"All country names from API:\n{sorted(list(unique_countries))}")
        
        # Also print a sample record to see the structure
        if records:
            print(f"\nSample record structure: {records[0]}")
        
        # Get the most recent year's data for each country
        country_latest = {}
        for record in records:
            eia_country = record.get('countryName')
            year = record.get('period')
            value = record.get('value')
            
            if eia_country and year and value is not None:
                # Map EIA country name to our standard name
                standard_country = eia_country_mapping.get(eia_country, eia_country)
                
                # Keep only the most recent year for each country
                if standard_country not in country_latest or year > country_latest[standard_country]['year']:
                    country_latest[standard_country] = {
                        'year': year,
                        'value': float(value),
                        'eia_name': eia_country
                    }
        
        # Filter for countries we need
        for country, data_point in country_latest.items():
            if country in all_countries:
                energy_data[country] = data_point['value']
                print(f"  {country}: {data_point['value']} QBTU ({data_point['year']}) [EIA: {data_point['eia_name']}]")
        
        # Check for missing countries
        missing = all_countries - set(energy_data.keys())
        if missing:
            print(f"\nWarning: Missing data for countries: {sorted(missing)}")
            print("\nTo fix this, add the correct EIA country names to the mapping in the script.")
        
        if not energy_data:
            raise ValueError("No energy data retrieved from API. Check country name mappings.")
        
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
    
    # HARDCODED API KEY FOR TESTING
    api_key = "vnZZ23GixkRlGThX93MlwOMdSzgF20FuO5f5bCS6"
    
    # Also try to get from environment variable
    env_api_key = os.environ.get('EIA_API_KEY')
    if env_api_key:
        print("Using API key from environment variable")
        api_key = env_api_key
    else:
        print("Using hardcoded API key for testing")
    
    # First, test the API to see what we're getting
    print("\n" + "="*60)
    print("STEP 1: Testing API Connection")
    print("="*60)
    test_eia_api(api_key)
    
    print("\n" + "="*60)
    print("STEP 2: Fetching Full Data")
    print("="*60)
    
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
