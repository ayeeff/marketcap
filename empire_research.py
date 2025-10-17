"""
Empire Research Scraper - Corrected Version
Handles Nature Index form submission to get actual data
"""
import requests
import csv
import os
import re
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup

EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa',
    'Nigeria', 'Ghana', 'Kenya', 'Uganda', 'Tanzania', 'Zambia', 'Malawi',
    'Botswana', 'Namibia', 'Lesotho', 'Eswatini', 'Jamaica', 'Trinidad and Tobago',
    'Barbados', 'Bahamas', 'Belize', 'Guyana', 'Saint Lucia', 'Grenada',
    'Saint Vincent and the Grenadines', 'Antigua and Barbuda', 'Dominica',
    'Saint Kitts and Nevis', 'Cyprus', 'Malta', 'Singapore', 'Malaysia',
    'Brunei', 'Bangladesh', 'Sri Lanka', 'Maldives'
}

EMPIRE_2_COUNTRIES = {'United States of America', 'USA', 'United States'}

EMPIRE_3_COUNTRIES = {'China', 'Hong Kong', 'Taiwan', 'Macau'}


def fetch_nature_index_data():
    """Fetch data from Nature Index by submitting the form."""
    # This is the form submission URL
    url = "https://www.nature.com/nature-index/institution-outputs/generate/All/global/All/score"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/json',
        'Origin': 'https://www.nature.com',
        'Referer': 'https://www.nature.com/nature-index/institution-outputs',
    }
    
    # The JSON payload that the form expects
    payload = {
        "year": "2025",
        "region": "global",
        "subject": "All",
        "size": 100,  # Number of institutions to fetch
        "page": 1
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        print("📡 Submitting form to Nature Index...")
        response = session.post(url, json=payload, timeout=30)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()  # This should be JSON data
        else:
            print(f"   Response: {response.text[:200]}...")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return None


def parse_json_data(json_data):
    """Parse the JSON response from Nature Index."""
    institutions = []
    
    print("🔍 Parsing JSON response...")
    
    try:
        # Navigate through the JSON structure to find institutions
        if 'data' in json_data and 'institutions' in json_data['data']:
            institutions_data = json_data['data']['institutions']
        elif 'institutions' in json_data:
            institutions_data = json_data['institutions']
        elif 'results' in json_data:
            institutions_data = json_data['results']
        else:
            # Try to find any array that contains institution data
            institutions_data = find_institutions_in_json(json_data)
        
        if not institutions_data:
            print("❌ No institution data found in JSON response")
            print(f"   JSON keys: {list(json_data.keys())}")
            return []
        
        print(f"✅ Found {len(institutions_data)} institutions in JSON")
        
        for idx, inst_data in enumerate(institutions_data):
            try:
                institution = extract_institution_info(inst_data, idx + 1)
                if institution:
                    institutions.append(institution)
            except Exception as e:
                print(f"⚠️  Error parsing institution {idx}: {e}")
                continue
                
    except Exception as e:
        print(f"❌ Error parsing JSON structure: {e}")
        # Try alternative parsing method
        institutions = parse_json_alternative(json_data)
    
    return institutions


def find_institutions_in_json(data):
    """Recursively search for institution data in JSON."""
    if isinstance(data, list):
        # Check if first item looks like an institution
        if data and isinstance(data[0], dict):
            if any(key in data[0] for key in ['name', 'institutionName', 'rank', 'country']):
                return data
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                if any(k in value[0] for k in ['name', 'institutionName', 'rank', 'country']):
                    return value
            # Recursive search
            result = find_institutions_in_json(value)
            if result:
                return result
    return None


def extract_institution_info(inst_data, default_rank):
    """Extract institution information from JSON object."""
    institution = {}
    
    # Extract rank
    if 'rank' in inst_data:
        institution['rank'] = int(inst_data['rank'])
    elif 'position' in inst_data:
        institution['rank'] = int(inst_data['position'])
    else:
        institution['rank'] = default_rank
    
    # Extract name
    if 'name' in inst_data:
        institution['name'] = inst_data['name']
    elif 'institutionName' in inst_data:
        institution['name'] = inst_data['institutionName']
    elif 'institution' in inst_data:
        if isinstance(inst_data['institution'], dict):
            institution['name'] = inst_data['institution'].get('name', 'Unknown')
        else:
            institution['name'] = str(inst_data['institution'])
    else:
        return None  # Skip if no name
    
    # Extract country
    if 'country' in inst_data:
        institution['country'] = inst_data['country']
    elif 'countryName' in inst_data:
        institution['country'] = inst_data['countryName']
    elif 'institution' in inst_data and isinstance(inst_data['institution'], dict):
        institution['country'] = inst_data['institution'].get('country', 'Unknown')
    else:
        institution['country'] = 'Unknown'
    
    return institution


def parse_json_alternative(json_data):
    """Alternative method to parse JSON data."""
    institutions = []
    
    # Convert entire JSON to string and look for patterns
    json_str = json.dumps(json_data)
    
    # Look for institution patterns in the JSON string
    patterns = [
        r'"rank"\s*:\s*(\d+).*?"name"\s*:\s*"([^"]+)".*?"country"\s*:\s*"([^"]+)"',
        r'"name"\s*:\s*"([^"]+)".*?"country"\s*:\s*"([^"]+)".*?"rank"\s*:\s*(\d+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, json_str, re.DOTALL)
        for match in matches:
            if len(match) == 3:
                institutions.append({
                    'rank': int(match[0]),
                    'name': match[1],
                    'country': match[2]
                })
    
    return institutions


def normalize_country(country):
    """Normalize country names for matching."""
    country = str(country).strip()
    
    country_map = {
        'United States of America': 'United States of America',
        'USA': 'United States of America',
        'US': 'United States of America',
        'United States': 'United States of America',
        'United Kingdom': 'United Kingdom',
        'UK': 'United Kingdom',
        'China': 'China',
        'Hong Kong': 'Hong Kong',
        'Taiwan': 'Taiwan',
        'Macau': 'Macau',
    }
    
    # Check for partial matches
    for normalized, variants in country_map.items():
        if country in variants or any(variant.lower() in country.lower() for variant in variants.split('/')):
            return normalized
    
    return country


def categorize_by_empire(institutions):
    """Categorize institutions by empire and get top 10 for each."""
    empire_1 = []
    empire_2 = []
    empire_3 = []
    
    for inst in institutions:
        country = normalize_country(inst['country'])
        
        # Check Empire 3 (China, Hong Kong, Taiwan, Macau)
        if country in EMPIRE_3_COUNTRIES or any(c.lower() in country.lower() for c in ['china', 'hong kong', 'taiwan', 'macau']):
            empire_3.append(inst)
        # Check Empire 2 (USA)
        elif country in EMPIRE_2_COUNTRIES or any(c.lower() in country.lower() for c in ['united states', 'usa', 'us']):
            empire_2.append(inst)
        # Check Empire 1 (Commonwealth)
        elif country in EMPIRE_1_COUNTRIES or any(c.lower() in country.lower() for c in list(EMPIRE_1_COUNTRIES)):
            empire_1.append(inst)
    
    # Sort by rank and get top 10 for each empire
    empire_1.sort(key=lambda x: x['rank'])
    empire_2.sort(key=lambda x: x['rank'])
    empire_3.sort(key=lambda x: x['rank'])
    
    return {
        'empire_1': empire_1[:10],
        'empire_2': empire_2[:10],
        'empire_3': empire_3[:10]
    }


def save_to_csv(empire_data, output_dir='data'):
    """Save empire rankings to CSV file."""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y-%m')
    filename = os.path.join(output_dir, f'empire_research_{timestamp}.csv')
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['Empire', 'Empire_Rank', 'Institution', 'Country', 'Global_Rank'])
        
        # Write Empire 1 (Commonwealth & former British territories)
        for idx, inst in enumerate(empire_data['empire_1'], 1):
            writer.writerow([
                'Empire_1_Commonwealth',
                idx,
                inst['name'],
                inst['country'],
                inst['rank']
            ])
        
        # Write Empire 2 (United States)
        for idx, inst in enumerate(empire_data['empire_2'], 1):
            writer.writerow([
                'Empire_2_USA',
                idx,
                inst['name'],
                inst['country'],
                inst['rank']
            ])
        
        # Write Empire 3 (China/Hong Kong/Taiwan)
        for idx, inst in enumerate(empire_data['empire_3'], 1):
            writer.writerow([
                'Empire_3_China',
                idx,
                inst['name'],
                inst['country'],
                inst['rank']
            ])
    
    print(f"✓ Data saved to {filename}")
    return filename


def debug_response(response_data):
    """Debug the API response."""
    print("\n🔍 Debugging API response...")
    
    if isinstance(response_data, dict):
        print(f"JSON keys: {list(response_data.keys())}")
        
        # Save full response for inspection
        with open('debug_response.json', 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=2, ensure_ascii=False)
        print("💾 Saved debug_response.json for inspection")
        
        # Look for any arrays that might contain institutions
        def find_arrays(obj, path=""):
            arrays = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    arrays.extend(find_arrays(v, f"{path}.{k}" if path else k))
            elif isinstance(obj, list):
                if obj and isinstance(obj[0], dict):
                    arrays.append((path, len(obj)))
                    # Print first item structure
                    if len(obj) > 0:
                        print(f"   Array '{path}': first item keys: {list(obj[0].keys())}")
            return arrays
        
        arrays = find_arrays(response_data)
        if arrays:
            print("📊 Found arrays in response:")
            for path, length in arrays:
                print(f"   {path}: {length} items")
    
    elif isinstance(response_data, list):
        print(f"Response is a list with {len(response_data)} items")
        if response_data and isinstance(response_data[0], dict):
            print(f"First item keys: {list(response_data[0].keys())}")


def main():
    """Main scraper function."""
    print("=" * 60)
    print("Nature Index Empire Research Scraper - Form Handler")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fetch data via form submission
    print("📡 Fetching data from Nature Index API...")
    json_data = fetch_nature_index_data()
    
    if not json_data:
        print("❌ Failed to fetch data. The API may have changed.")
        return
    
    # Debug the response structure
    debug_response(json_data)
    
    # Parse institutions from JSON
    print("\n📊 Parsing institution data from JSON...")
    institutions = parse_json_data(json_data)
    
    if not institutions:
        print("❌ No institutions found in the API response.")
        print("💡 The API structure may have changed. Check debug_response.json")
        return
    
    print(f"✓ Found {len(institutions)} institutions")
    
    # Show sample of found institutions
    print("\n📋 Sample of found institutions:")
    for inst in institutions[:5]:
        print(f"  #{inst['rank']}: {inst['name']} - {inst['country']}")
    
    # Categorize by empire
    print("\n🌍 Categorizing by empire...")
    empire_data = categorize_by_empire(institutions)
    
    print(f"  • Empire 1 (Commonwealth): {len(empire_data['empire_1'])} institutions in top 10")
    print(f"  • Empire 2 (USA): {len(empire_data['empire_2'])} institutions in top 10")
    print(f"  • Empire 3 (China): {len(empire_data['empire_3'])} institutions in top 10")
    
    # Print top institutions from each empire for preview
    print("\n🏆 Top institutions from each empire:")
    
    if empire_data['empire_1']:
        print("\n  Empire 1 (Commonwealth):")
        for i, inst in enumerate(empire_data['empire_1'][:3], 1):
            print(f"    {i}. {inst['name']} (#{inst['rank']}) - {inst['country']}")
    else:
        print("\n  Empire 1 (Commonwealth): No institutions found")
    
    if empire_data['empire_2']:
        print("\n  Empire 2 (USA):")
        for i, inst in enumerate(empire_data['empire_2'][:3], 1):
            print(f"    {i}. {inst['name']} (#{inst['rank']}) - {inst['country']}")
    else:
        print("\n  Empire 2 (USA): No institutions found")
    
    if empire_data['empire_3']:
        print("\n  Empire 3 (China):")
        for i, inst in enumerate(empire_data['empire_3'][:3], 1):
            print(f"    {i}. {inst['name']} (#{inst['rank']}) - {inst['country']}")
    else:
        print("\n  Empire 3 (China): No institutions found")
    
    # Save to CSV only if we have data
    if any(empire_data.values()):
        print("\n💾 Saving to CSV...")
        save_to_csv(empire_data)
    else:
        print("\n❌ No data to save - all empires are empty")
    
    print("\n" + "=" * 60)
    print("✅ Scraping complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
