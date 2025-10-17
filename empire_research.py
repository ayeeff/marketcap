"""
Empire Research Scraper - Direct Scraping Version
Scrapes the actual Nature Index rankings page directly
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
    'Brunei', 'Bangladesh', 'Sri Lanka', 'Maldives', 'India', 'Pakistan'
}

EMPIRE_2_COUNTRIES = {'United States of America', 'USA', 'United States'}

EMPIRE_3_COUNTRIES = {'China', 'Hong Kong', 'Taiwan', 'Macau'}


def fetch_nature_index_direct():
    """Fetch the actual Nature Index rankings page directly."""
    # Try the main rankings page
    urls = [
        "https://www.nature.com/nature-index/institution-outputs",
        "https://www.nature-index.com/institution-outputs",
        "https://www.nature.com/nature-index/annual-tables/2024/institution/all/all",
        "https://www.nature-index.com/annual-tables/2024/institution/all/all",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
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


def parse_nature_index_html(html_content):
    """Parse the Nature Index HTML content to extract rankings."""
    soup = BeautifulSoup(html_content, 'html.parser')
    institutions = []
    
    print("🔍 Analyzing page structure...")
    
    # Save the HTML for debugging
    with open('nature_index_page.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("💾 Saved nature_index_page.html for inspection")
    
    # Method 1: Look for table with rankings
    tables = soup.find_all('table')
    print(f"📊 Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        institutions_from_table = parse_table(table)
        if institutions_from_table:
            print(f"✅ Table {i+1}: Found {len(institutions_from_table)} institutions")
            institutions.extend(institutions_from_table)
    
    if institutions:
        return institutions
    
    # Method 2: Look for script tags with JSON data
    script_tags = soup.find_all('script')
    print(f"📜 Found {len(script_tags)} script tags")
    
    for script in script_tags:
        if script.string:
            script_content = script.string
            # Look for common data patterns
            if any(keyword in script_content for keyword in ['institution', 'rank', 'ranking', 'data']):
                json_data = extract_json_from_script(script_content)
                if json_data:
                    print("✅ Found JSON data in script")
                    institutions_from_json = parse_json_data(json_data)
                    if institutions_from_json:
                        return institutions_from_json
    
    # Method 3: Look for institution elements in the page
    institution_selectors = [
        '[data-test="institution-row"]',
        '.institution-row',
        '.ranking-row',
        '.institution-item',
        'tr[data-rank]',
    ]
    
    for selector in institution_selectors:
        elements = soup.select(selector)
        if elements:
            print(f"✅ Found {len(elements)} elements with selector: {selector}")
            institutions_from_elements = parse_institution_elements(elements)
            if institutions_from_elements:
                return institutions_from_elements
    
    # Method 4: Look for any elements containing rank and institution info
    return find_institutions_in_text(str(soup))


def parse_table(table):
    """Parse institution data from HTML table."""
    institutions = []
    rows = table.find_all('tr')
    
    for row in rows:
        # Skip header rows
        if row.find('th'):
            continue
            
        cells = row.find_all(['td', 'div'])
        if len(cells) >= 2:
            try:
                # Try to find rank in first cell
                rank_cell = cells[0].get_text(strip=True)
                rank_match = re.search(r'(\d+)', rank_cell)
                rank = int(rank_match.group(1)) if rank_match else None
                
                # Look for institution name and country
                institution_text = ' '.join(cell.get_text(strip=True) for cell in cells[1:3] if cell.get_text(strip=True))
                
                if rank and institution_text:
                    # Try to split institution name and country
                    name_country_match = re.search(r'(.+?),\s*(.+)$', institution_text)
                    if name_country_match:
                        name = name_country_match.group(1).strip()
                        country = name_country_match.group(2).strip()
                    else:
                        # If no comma, try other patterns
                        name = institution_text
                        country = "Unknown"
                    
                    institutions.append({
                        'rank': rank,
                        'name': name,
                        'country': country
                    })
            except Exception as e:
                continue
    
    return institutions


def extract_json_from_script(script_content):
    """Extract JSON data from script content."""
    try:
        # Look for window.__INITIAL_STATE__ or similar
        patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.__NUXT__\s*=\s*({.*?});',
            r'var\s+data\s*=\s*({.*?});',
            r'JSON\.parse\(\'({.*?})\'\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, script_content, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        
        # Look for standalone JSON objects
        json_pattern = r'{\s*"[\w\s]*"\s*:\s*\[.*?\]\s*}'
        matches = re.findall(json_pattern, script_content, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except:
                continue
                
    except Exception as e:
        print(f"❌ Error extracting JSON: {e}")
    
    return None


def parse_json_data(json_data):
    """Parse institution data from JSON structure."""
    institutions = []
    
    def extract_from_obj(obj, path=""):
        if isinstance(obj, list):
            for item in obj:
                result = extract_from_obj(item, path + "[]")
                if result:
                    institutions.extend(result)
        elif isinstance(obj, dict):
            # Check if this object looks like an institution
            if 'name' in obj and 'rank' in obj:
                institution = {
                    'rank': int(obj['rank']),
                    'name': obj['name'],
                    'country': obj.get('country', obj.get('countryName', 'Unknown'))
                }
                return [institution]
            
            # Recursively search
            for key, value in obj.items():
                result = extract_from_obj(value, path + "." + key)
                if result:
                    institutions.extend(result)
        return None
    
    extract_from_obj(json_data)
    return institutions


def parse_institution_elements(elements):
    """Parse institution data from HTML elements."""
    institutions = []
    
    for element in elements:
        try:
            text = element.get_text(strip=True)
            
            # Look for rank pattern: "1. Harvard University, United States"
            patterns = [
                r'(\d+)\.?\s+(.+?),\s*(.+)',
                r'^(\d+)\s+(.+?),\s*(.+)$',
                r'rank["\']?\s*:\s*["\']?(\d+)["\']?.*?name["\']?\s*:\s*["\']?(.+?)["\']?.*?country["\']?\s*:\s*["\']?(.+?)["\']?',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    institutions.append({
                        'rank': int(match.group(1)),
                        'name': match.group(2).strip(),
                        'country': match.group(3).strip()
                    })
                    break
        except:
            continue
    
    return institutions


def find_institutions_in_text(text):
    """Fallback: Find institutions in plain text."""
    institutions = []
    
    # Common pattern in rankings
    pattern = r'(\d+)\.?\s*([^,\n]+?),\s*([^\n\(\)]+?)(?:\s+\([^\)]*\))?\s*\n'
    matches = re.findall(pattern, text)
    
    for match in matches:
        institutions.append({
            'rank': int(match[0]),
            'name': match[1].strip(),
            'country': match[2].strip()
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
    
    for normalized, variants in country_map.items():
        if country == normalized or country in variants.split(', '):
            return normalized
    
    # Check for partial matches
    if 'United States' in country:
        return 'United States of America'
    elif 'China' in country:
        return 'China'
    elif 'Hong Kong' in country:
        return 'Hong Kong'
    elif 'Taiwan' in country:
        return 'Taiwan'
    
    return country


def categorize_by_empire(institutions):
    """Categorize institutions by empire and get top 10 for each."""
    empire_1 = []
    empire_2 = []
    empire_3 = []
    other = []
    
    for inst in institutions:
        country = normalize_country(inst['country'])
        
        # Check Empire 3 (China, Hong Kong, Taiwan, Macau)
        if country in EMPIRE_3_COUNTRIES:
            empire_3.append(inst)
        # Check Empire 2 (USA)
        elif country in EMPIRE_2_COUNTRIES:
            empire_2.append(inst)
        # Check Empire 1 (Commonwealth)
        elif country in EMPIRE_1_COUNTRIES:
            empire_1.append(inst)
        else:
            other.append(inst)
    
    # Sort by rank and get top 10 for each empire
    empire_1.sort(key=lambda x: x['rank'])
    empire_2.sort(key=lambda x: x['rank'])
    empire_3.sort(key=lambda x: x['rank'])
    
    print(f"  • Empire 1 count: {len(empire_1)}")
    print(f"  • Empire 2 count: {len(empire_2)}")
    print(f"  • Empire 3 count: {len(empire_3)}")
    print(f"  • Other countries: {len(other)}")
    
    if other:
        print(f"  • Sample other countries: {list(set([inst['country'] for inst in other[:10]]))}")
    
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


def main():
    """Main scraper function."""
    print("=" * 60)
    print("Nature Index Empire Research Scraper - Direct Scraping")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fetch the actual rankings page
    print("📡 Fetching Nature Index rankings page...")
    html_content = fetch_nature_index_direct()
    
    if not html_content:
        print("❌ Failed to fetch the rankings page.")
        return
    
    print(f"✓ Fetched {len(html_content)} characters")
    
    # Parse the HTML content
    print("\n📊 Parsing page content...")
    institutions = parse_nature_index_html(html_content)
    
    if not institutions:
        print("❌ No institutions found in the page.")
        print("💡 Check nature_index_page.html to see the actual page structure.")
        return
    
    print(f"✓ Found {len(institutions)} institutions total")
    
    # Show sample of found institutions
    print("\n📋 Sample of found institutions:")
    for inst in institutions[:10]:
        print(f"  #{inst['rank']}: {inst['name']} - {inst['country']}")
    
    # Categorize by empire
    print("\n🌍 Categorizing by empire...")
    empire_data = categorize_by_empire(institutions)
    
    print(f"\n🏆 Final counts for top 10:")
    print(f"  • Empire 1 (Commonwealth): {len(empire_data['empire_1'])}")
    print(f"  • Empire 2 (USA): {len(empire_data['empire_2'])}")
    print(f"  • Empire 3 (China): {len(empire_data['empire_3'])}")
    
    # Print top institutions from each empire
    print("\n🏅 Top institutions from each empire:")
    
    if empire_data['empire_1']:
        print("\n  Empire 1 (Commonwealth):")
        for i, inst in enumerate(empire_data['empire_1'][:5], 1):
            print(f"    {i}. {inst['name']} (#{inst['rank']}) - {inst['country']}")
    
    if empire_data['empire_2']:
        print("\n  Empire 2 (USA):")
        for i, inst in enumerate(empire_data['empire_2'][:5], 1):
            print(f"    {i}. {inst['name']} (#{inst['rank']}) - {inst['country']}")
    
    if empire_data['empire_3']:
        print("\n  Empire 3 (China):")
        for i, inst in enumerate(empire_data['empire_3'][:5], 1):
            print(f"    {i}. {inst['name']} (#{inst['rank']}) - {inst['country']}")
    
    # Save to CSV only if we have data
    if any(empire_data.values()):
        print("\n💾 Saving to CSV...")
        save_to_csv(empire_data)
        print("✅ Success! Data has been saved.")
    else:
        print("\n❌ No data to save - no institutions matched empire categories")
        print("💡 Check the country names in the sample output above")
    
    print("\n" + "=" * 60)
    print("Scraping complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
