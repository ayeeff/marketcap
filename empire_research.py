"""
Empire Research Scraper - Updated Version
Fetches Nature Index research leader data and categorizes by empires
"""
import requests
import csv
import os
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup

EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa',
    'Nigeria', 'Ghana', 'Kenya', 'Uganda', 'Tanzania', 'Zambia', 'Malawi',
    'Botswana', 'Namibia', 'Lesotho', 'Eswatini', 'Jamaica', 'Trinidad and Tobago',
    'Barbados', 'Bahamas', 'Belize', 'Guyana', 'Saint Lucia', 'Grenada',
    'Saint Vincent and the Grenadines', 'Antigua and Barbuda', 'Dominica',
    'Saint Kitts and Nevis', 'Cyprus', 'Malta', 'Singapore', 'Malaysia',
    'Brunei', 'Bangladesh', 'Sri Lanka', 'Maldives', 'India', 'Pakistan'
}

EMPIRE_2_COUNTRIES = {'United States of America', 'USA', 'United States'}

EMPIRE_3_COUNTRIES = {'China', 'Hong Kong', 'Taiwan', 'Macau'}


def fetch_nature_index_data():
    """Fetch data from Nature Index with proper headers and session."""
    # Try multiple possible URLs
    urls = [
        "https://www.nature.com/nature-index/institution-outputs/generate/All/global/All/score",
        "https://www.nature.com/nature-index/institution-outputs",
        "https://www.nature-index.com/institution-outputs"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    for url in urls:
        print(f"🌐 Trying URL: {url}")
        try:
            response = session.get(url, timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.text
                
        except Exception as e:
            print(f"   Error: {e}")
    
    return None


def parse_with_bs4(html_content):
    """Parse HTML content using BeautifulSoup to find institution data."""
    soup = BeautifulSoup(html_content, 'html.parser')
    institutions = []
    
    print("🔍 Searching for data patterns...")
    
    # Method 1: Look for JSON data in script tags
    script_tags = soup.find_all('script')
    for script in script_tags:
        if script.string:
            script_content = script.string
            
            # Look for common JSON patterns
            if 'window.__INITIAL_STATE__' in script_content:
                print("✅ Found window.__INITIAL_STATE__")
                data = extract_from_initial_state(script_content)
                if data:
                    return data
            
            # Look for other JSON structures
            if 'institutions' in script_content.lower() or 'rankings' in script_content.lower():
                print("✅ Found potential data in script")
                json_data = extract_json_from_script(script_content)
                if json_data:
                    return json_data
    
    # Method 2: Look for table structures
    tables = soup.find_all('table')
    if tables:
        print(f"✅ Found {len(tables)} tables")
        institutions = parse_tables(tables)
        if institutions:
            return institutions
    
    # Method 3: Look for list items or cards with institution data
    institution_elements = soup.find_all(['tr', 'div'], class_=re.compile(r'institution|ranking|row', re.I))
    if institution_elements:
        print(f"✅ Found {len(institution_elements)} institution elements")
        institutions = parse_institution_elements(institution_elements)
        if institutions:
            return institutions
    
    # Method 4: Look for any elements containing institution names and ranks
    return find_institutions_in_text(soup.get_text())


def extract_from_initial_state(script_content):
    """Extract data from window.__INITIAL_STATE__ pattern."""
    try:
        json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', script_content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
            print("✅ Successfully parsed INITIAL_STATE")
            
            # Navigate through common data structures
            if 'institutions' in data:
                return format_institution_data(data['institutions'])
            elif 'rankings' in data:
                return format_institution_data(data['rankings'])
            else:
                # Try to find institutions in nested structures
                return find_institutions_in_json(data)
                
    except Exception as e:
        print(f"❌ Error parsing INITIAL_STATE: {e}")
    
    return None


def extract_json_from_script(script_content):
    """Extract JSON data from script content."""
    try:
        # Look for JSON objects or arrays
        json_patterns = [
            r'{\s*"institutions"\s*:\s*\[.*?\]}',
            r'{\s*"rankings"\s*:\s*\[.*?\]}',
            r'\[\s*{.*?}\s*\]',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, script_content, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list) and len(data) > 0:
                        print(f"✅ Found JSON array with {len(data)} items")
                        return format_institution_data(data)
                    elif isinstance(data, dict) and ('institutions' in data or 'rankings' in data):
                        key = 'institutions' if 'institutions' in data else 'rankings'
                        print(f"✅ Found JSON object with {len(data[key])} {key}")
                        return format_institution_data(data[key])
                except:
                    continue
    except Exception as e:
        print(f"❌ Error extracting JSON: {e}")
    
    return None


def find_institutions_in_json(data):
    """Recursively search for institution data in JSON structure."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key.lower() in ['institutions', 'rankings', 'items', 'results'] and isinstance(value, list):
                if value and isinstance(value[0], dict) and any(field in value[0] for field in ['name', 'institution', 'rank']):
                    print(f"✅ Found institutions in {key}")
                    return format_institution_data(value)
            
            # Recursively search nested structures
            result = find_institutions_in_json(value)
            if result:
                return result
    
    elif isinstance(data, list) and data:
        if isinstance(data[0], dict) and any(field in data[0] for field in ['name', 'institution', 'rank']):
            return format_institution_data(data)
    
    return None


def format_institution_data(data):
    """Format institution data from various JSON structures."""
    institutions = []
    
    for item in data:
        institution = {}
        
        # Extract rank
        if 'rank' in item:
            institution['rank'] = int(item['rank'])
        elif 'position' in item:
            institution['rank'] = int(item['position'])
        
        # Extract name
        if 'name' in item:
            institution['name'] = item['name']
        elif 'institution' in item:
            if isinstance(item['institution'], dict) and 'name' in item['institution']:
                institution['name'] = item['institution']['name']
            else:
                institution['name'] = str(item['institution'])
        
        # Extract country
        if 'country' in item:
            institution['country'] = item['country']
        elif 'institution' in item and isinstance(item['institution'], dict) and 'country' in item['institution']:
            institution['country'] = item['institution']['country']
        elif 'location' in item:
            institution['country'] = item['location']
        
        # Only add if we have the essential fields
        if all(key in institution for key in ['rank', 'name', 'country']):
            institutions.append(institution)
    
    return institutions if institutions else None


def parse_tables(tables):
    """Parse data from HTML tables."""
    institutions = []
    
    for table in tables:
        rows = table.find_all('tr')
        for row in rows[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                try:
                    # Try to extract rank, name, country from cells
                    rank_text = cells[0].get_text(strip=True)
                    name_text = cells[1].get_text(strip=True)
                    country_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    
                    if rank_text.isdigit():
                        institutions.append({
                            'rank': int(rank_text),
                            'name': name_text,
                            'country': country_text
                        })
                except:
                    continue
    
    return institutions if institutions else None


def parse_institution_elements(elements):
    """Parse data from institution elements."""
    institutions = []
    
    for element in elements:
        text = element.get_text(strip=True)
        
        # Look for pattern: number followed by institution name
        match = re.search(r'^(\d+)\s+(.+?),\s*(.+)$', text)
        if match:
            institutions.append({
                'rank': int(match.group(1)),
                'name': match.group(2),
                'country': match.group(3)
            })
    
    return institutions if institutions else None


def find_institutions_in_text(text):
    """Fallback: Find institutions in plain text using regex."""
    institutions = []
    
    # Pattern for: "1. Harvard University, United States"
    patterns = [
        r'(\d+)\.?\s+([^,\n]+?),\s*([^\n\(\)]+?)(?:\s+\([^\)]*\))?\s*\n',
        r'^(\d+)\s+([^,\n]+?),\s*([^\n\(\)]+?)(?:\s+\([^\)]*\))?$',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.MULTILINE)
        for match in matches:
            institutions.append({
                'rank': int(match.group(1)),
                'name': match.group(2).strip(),
                'country': match.group(3).strip()
            })
    
    return institutions if institutions else None


def normalize_country(country):
    """Normalize country names for matching."""
    country = country.strip()
    
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
    }
    
    return country_map.get(country, country)


def categorize_by_empire(institutions):
    """Categorize institutions by empire and get top 10 for each."""
    empire_1 = []
    empire_2 = []
    empire_3 = []
    
    for inst in institutions:
        country = normalize_country(inst['country'])
        
        # Check Empire 3 (China, Hong Kong, Taiwan)
        if country in EMPIRE_3_COUNTRIES or any(c.lower() in country.lower() for c in ['China', 'Hong Kong', 'Taiwan', 'Macau']):
            empire_3.append(inst)
        # Check Empire 2 (USA)
        elif country in EMPIRE_2_COUNTRIES or any(c.lower() in country.lower() for c in ['United States', 'USA', 'US']):
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


def debug_page_content(html_content):
    """Debug function to analyze page content."""
    print("\n🔍 Debugging page content...")
    print(f"Content length: {len(html_content)}")
    
    # Save sample for inspection
    with open('debug_sample.html', 'w', encoding='utf-8') as f:
        f.write(html_content[:10000])  # First 10k chars
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Check for common elements
    print(f"Title: {soup.title.string if soup.title else 'No title'}")
    
    script_tags = soup.find_all('script')
    print(f"Script tags: {len(script_tags)}")
    
    tables = soup.find_all('table')
    print(f"Tables: {len(tables)}")
    
    # Look for any text containing "Harvard" or "China" as markers
    if "Harvard" in html_content:
        print("✅ Found 'Harvard' in content")
    if "China" in html_content:
        print("✅ Found 'China' in content")
    
    print("💾 Saved debug_sample.html for manual inspection")


def main():
    """Main scraper function."""
    print("=" * 60)
    print("Nature Index Empire Research Scraper - Updated")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fetch data
    print("📡 Fetching data from Nature Index...")
    html_content = fetch_nature_index_data()
    
    if not html_content:
        print("❌ Failed to fetch data. Exiting.")
        return
    
    print(f"✓ Fetched {len(html_content)} characters")
    
    # Debug: analyze content
    debug_page_content(html_content)
    
    # Parse institutions
    print("\n📊 Parsing institution data...")
    institutions = parse_with_bs4(html_content)
    
    if not institutions:
        print("❌ No institutions found with BeautifulSoup.")
        print("💡 The page structure may have significantly changed.")
        print("💡 Check debug_sample.html manually to see the current structure.")
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
    
    # Print top 3 from each empire for preview
    print("\n🏆 Top institutions from each empire:")
    
    if empire_data['empire_1']:
        print("\n  Empire 1 (Commonwealth):")
        for i, inst in enumerate(empire_data['empire_1'][:3], 1):
            print(f"    {i}. {inst['name']} (#{inst['rank']}) - {inst['country']}")
    
    if empire_data['empire_2']:
        print("\n  Empire 2 (USA):")
        for i, inst in enumerate(empire_data['empire_2'][:3], 1):
            print(f"    {i}. {inst['name']} (#{inst['rank']}) - {inst['country']}")
    
    if empire_data['empire_3']:
        print("\n  Empire 3 (China):")
        for i, inst in enumerate(empire_data['empire_3'][:3], 1):
            print(f"    {i}. {inst['name']} (#{inst['rank']}) - {inst['country']}")
    
    # Save to CSV
    print("\n💾 Saving to CSV...")
    save_to_csv(empire_data)
    
    print("\n" + "=" * 60)
    print("✅ Scraping complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
