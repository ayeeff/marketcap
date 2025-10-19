"""
Empire Research Scraper - With Research Share 2024 Data
Enhanced version that specifically extracts Share 2024 data
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


def fetch_nature_index_direct():
    """Fetch data from the Wikipedia-referenced Nature Index URL."""
    url = "https://www.nature.com/nature-index/research-leaders/2025/institution/all/all/global"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.nature.com/',
    }
    
    try:
        print(f"🌐 Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"✅ Status: {response.status_code}")
        return response.text
    except Exception as e:
        print(f"❌ Error fetching: {e}")
        return None


def parse_research_leaders_page(html_content):
    """Parse the research leaders page to extract institution rankings and research share 2024."""
    soup = BeautifulSoup(html_content, 'html.parser')
    institutions = []
    
    print("🔍 Parsing page structure for Share 2024 data...")
    
    # Save HTML for debugging
    with open('research_leaders_page.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("💾 Saved research_leaders_page.html")
    
    # Method 1: Look for script tags containing JSON data
    script_tags = soup.find_all('script')
    for script in script_tags:
        script_content = script.string
        if script_content and '__NEXT_DATA__' in script_content:
            print("✅ Found Next.js data payload")
            institutions = parse_nextjs_data_2024(script_content)
            if institutions:
                print(f"✅ Extracted {len(institutions)} institutions with Share 2024 data")
                return institutions
    
    # Method 2: Look for tables and specifically target Share 2024 columns
    tables = soup.find_all('table')
    print(f"📊 Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        print(f"  Analyzing table {i+1} for Share 2024 data...")
        institutions_from_table = parse_rankings_table_2024(table)
        if institutions_from_table:
            print(f"✅ Table {i+1}: Found {len(institutions_from_table)} institutions with Share 2024")
            return institutions_from_table
    
    # Method 3: Look for elements containing 2024 share data
    print("🔍 Searching for Share 2024 data in page elements...")
    share_2024_elements = soup.find_all(string=re.compile(r'2024', re.IGNORECASE))
    if share_2024_elements:
        print(f"✅ Found {len(share_2024_elements)} elements mentioning 2024")
        institutions_from_elements = parse_share_2024_elements(soup)
        if institutions_from_elements:
            return institutions_from_elements
    
    return []


def parse_nextjs_data_2024(script_content):
    """Parse Next.js JSON data to extract institution information with Share 2024."""
    try:
        json_match = re.search(r'__NEXT_DATA__\s*=\s*({.*?})', script_content)
        if json_match:
            json_data = json.loads(json_match.group(1))
            print("🔍 Searching for Share 2024 data in JSON structure...")
            
            # Look for Share 2024 data in the JSON structure
            institutions = extract_share_2024_from_json(json_data)
            if institutions:
                return institutions
            
            # Alternative approach: look for specific 2024 share keys
            props = json_data.get('props', {})
            page_props = props.get('pageProps', {})
            
            # Try to find institution data with share_2024 or similar keys
            institutions = find_2024_share_data(page_props)
            if institutions:
                return institutions
                
    except Exception as e:
        print(f"❌ Error parsing Next.js data: {e}")
    
    return []


def extract_share_2024_from_json(json_data, path=[]):
    """Recursively search JSON structure for institution data with Share 2024."""
    institutions = []
    
    if isinstance(json_data, dict):
        # Check if this looks like institution data with 2024 share
        if all(key in json_data for key in ['rank', 'name', 'country']):
            share_2024 = extract_2024_share_value(json_data)
            if share_2024 is not None:
                institutions.append({
                    'rank': json_data.get('rank'),
                    'name': json_data.get('name', ''),
                    'country': json_data.get('country', ''),
                    'research_share': share_2024
                })
        
        # Recursively search deeper
        for key, value in json_data.items():
            institutions.extend(extract_share_2024_from_json(value, path + [key]))
    
    elif isinstance(json_data, list):
        for item in json_data:
            institutions.extend(extract_share_2024_from_json(item, path))
    
    return institutions


def extract_2024_share_value(inst_data):
    """Extract Share 2024 value from institution data using various possible key names."""
    # Try different possible keys for Share 2024
    possible_keys = [
        'share_2024', 'share2024', '2024_share', '2024share',
        'current_share', 'latest_share', 'share',
        'research_share_2024', 'research_share'
    ]
    
    for key in possible_keys:
        if key in inst_data and inst_data[key] is not None:
            return float(inst_data[key])
    
    # If no direct key, look in nested structures
    if 'shares' in inst_data and isinstance(inst_data['shares'], dict):
        for year_key, share_value in inst_data['shares'].items():
            if '2024' in str(year_key):
                return float(share_value)
    
    return None


def find_2024_share_data(data):
    """Find Share 2024 data in various data structures."""
    institutions = []
    
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                share_2024 = extract_2024_share_value(item)
                if share_2024 is not None and item.get('name'):
                    institutions.append({
                        'rank': item.get('rank'),
                        'name': item.get('name', ''),
                        'country': item.get('country', ''),
                        'research_share': share_2024
                    })
    
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list) and key in ['institutions', 'rankings', 'data']:
                institutions.extend(find_2024_share_data(value))
    
    return institutions


def parse_rankings_table_2024(table):
    """Parse a rankings table to extract institution data with Share 2024."""
    institutions = []
    rows = table.find_all('tr')
    
    # First, identify which column contains Share 2024
    header_row = table.find('tr')
    if header_row:
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        share_2024_col_index = None
        
        for i, header in enumerate(headers):
            if '2024' in header and ('share' in header.lower() or 'count' in header.lower()):
                share_2024_col_index = i
                print(f"✅ Found Share 2024 column at index {i}: '{header}'")
                break
        
        if share_2024_col_index is None:
            # If no 2024 header found, try to infer column (often the first numeric column after name)
            print("⚠️ No explicit Share 2024 column found, trying to infer...")
    
    for row in rows:
        # Skip header rows
        if row.find('th'):
            continue
            
        cells = row.find_all(['td', 'div'])
        if len(cells) >= 3:
            try:
                # Extract rank from first cell
                rank_text = cells[0].get_text(strip=True)
                rank_match = re.search(r'(\d+)', rank_text)
                if not rank_match:
                    continue
                    
                rank = int(rank_match.group(1))
                
                # Extract institution name and country
                name = ''
                country = 'Unknown'
                
                for i, cell in enumerate(cells[1:], 1):
                    cell_text = cell.get_text(strip=True)
                    if not cell_text or cell_text.isdigit() or re.match(r'^\d+\.\d+$', cell_text):
                        continue
                    
                    if 'University of California' in cell_text:
                        name, country = parse_uc_institution(cell_text)
                        break
                    else:
                        name_country_match = re.search(r'^(.+?),\s*(.+)$', cell_text)
                        if name_country_match:
                            name = name_country_match.group(1).strip()
                            country_raw = name_country_match.group(2).strip()
                            country = extract_country_name(country_raw)
                            break
                        else:
                            name = cell_text
                
                # Extract Share 2024 - look for decimal numbers in cells
                research_share = None
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    # Look for decimal numbers that could be share values
                    share_match = re.search(r'^(\d+\.\d+)$', cell_text)
                    if share_match:
                        research_share = float(share_match.group(1))
                        break
                
                if name:  # Only add if we found a name
                    institutions.append({
                        'rank': rank,
                        'name': name,
                        'country': country,
                        'research_share': research_share
                    })
                    
            except Exception as e:
                print(f"⚠️ Error parsing row: {e}")
                continue
    
    return institutions


def parse_share_2024_elements(soup):
    """Parse page elements to find Share 2024 data."""
    institutions = []
    
    # Look for elements that might contain ranking data with 2024 share
    possible_selectors = [
        '[data-test*="institution"]',
        '.institution-row',
        '.ranking-item',
        'tr',
    ]
    
    for selector in possible_selectors:
        elements = soup.select(selector)
        if len(elements) > 10:
            print(f"🔍 Found {len(elements)} elements with selector: {selector}")
            # Try to parse these elements for 2024 share data
            for element in elements[:5]:  # Check first 5
                text = element.get_text()
                if '2024' in text:
                    print(f"  Found 2024 mention: {text[:100]}...")
    
    return institutions


def parse_uc_institution(text):
    """Parse University of California institution names specifically."""
    parts = text.rsplit(',', 1)
    if len(parts) == 2:
        name = parts[0].strip()
        country_raw = parts[1].strip()
        country = extract_country_name(country_raw)
        return name, country
    else:
        return text, 'United States of America'


def extract_country_name(country_raw):
    """Extract clean country name from raw country string."""
    country = re.sub(r'\s*\([^)]*\)$', '', country_raw).strip()
    
    # Handle specific cases
    if 'United States of America' in country:
        return 'United States of America'
    elif 'United Kingdom' in country:
        return 'United Kingdom'
    elif 'China' in country:
        return 'China'
    elif 'Canada' in country:
        return 'Canada'
    elif 'Australia' in country:
        return 'Australia'
    elif 'Singapore' in country:
        return 'Singapore'
    
    return country


def normalize_country(country):
    """Normalize country names for empire categorization."""
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
    
    # Exact match
    if country in country_map:
        return country_map[country]
    
    # Partial match
    for normalized, variants in country_map.items():
        if any(variant.lower() in country.lower() for variant in variants.split(', ')):
            return normalized
    
    return country


def categorize_by_empire(institutions):
    """Categorize institutions by empire and get top 10 for each."""
    empire_1 = []
    empire_2 = []
    empire_3 = []
    
    for inst in institutions:
        country = normalize_country(inst['country'])
        
        # Empire 3: China, Hong Kong, Taiwan, Macau
        if country in EMPIRE_3_COUNTRIES:
            empire_3.append(inst)
        # Empire 2: USA
        elif country in EMPIRE_2_COUNTRIES:
            empire_2.append(inst)
        # Empire 1: Commonwealth countries
        elif country in EMPIRE_1_COUNTRIES:
            empire_1.append(inst)
    
    # Sort by global rank and take top 10
    empire_1.sort(key=lambda x: x['rank'])
    empire_2.sort(key=lambda x: x['rank'])
    empire_3.sort(key=lambda x: x['rank'])
    
    return {
        'empire_1': empire_1[:10],
        'empire_2': empire_2[:10],
        'empire_3': empire_3[:10]
    }


def save_to_csv(empire_data, output_dir='data'):
    """Save empire rankings to CSV file with Research Share 2024 column."""
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.join(output_dir, 'empire_research.csv')  
    
    # Remove existing file if it exists to ensure clean overwrite
    if os.path.exists(filename):
        os.remove(filename)
        print(f"♻️  Removed existing file: {filename}")
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header with Research Share 2024 column
        writer.writerow(['Empire', 'Empire_Rank', 'Institution', 'Country', 'Research Share', 'Global_Rank'])
        
        # Empire 1: Commonwealth
        for idx, inst in enumerate(empire_data['empire_1'], 1):
            writer.writerow([
                '1',
                idx,
                inst['name'],
                inst['country'],
                inst.get('research_share', 'N/A'),
                inst['rank']
            ])
        
        # Empire 2: USA
        for idx, inst in enumerate(empire_data['empire_2'], 1):
            writer.writerow([
                '2',
                idx,
                inst['name'],
                inst['country'],
                inst.get('research_share', 'N/A'),
                inst['rank']
            ])
        
        # Empire 3: China
        for idx, inst in enumerate(empire_data['empire_3'], 1):
            writer.writerow([
                '3',
                idx,
                inst['name'],
                inst['country'],
                inst.get('research_share', 'N/A'),
                inst['rank']
            ])
    
    print(f"✓ Data saved to {filename}")
    
    # Count institutions with actual share data
    institutions_with_share = sum(1 for empire in empire_data.values() for inst in empire if inst.get('research_share') is not None)
    print(f"📊 {institutions_with_share} institutions have Share 2024 data")
    
    return filename


def main():
    """Main scraper function."""
    print("=" * 60)
    print("Nature Index Empire Research Scraper - Share 2024 Focus")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fetch data from the direct URL
    print("📡 Fetching research leaders data...")
    html_content = fetch_nature_index_direct()
    
    if not html_content:
        print("❌ Failed to fetch data.")
        return
    
    print(f"✓ Fetched {len(html_content)} characters")
    
    # Parse the page with focus on Share 2024 data
    print("\n📊 Parsing institution data for Share 2024...")
    institutions = parse_research_leaders_page(html_content)
    
    if not institutions:
        print("❌ No institutions found.")
        print("💡 Check research_leaders_page.html to see the page structure.")
        return
    
    print(f"✓ Found {len(institutions)} institutions")
    
    # Show sample with research share 2024 data
    print("\n📋 Sample institutions with Share 2024 data:")
    institutions_with_share = [inst for inst in institutions if inst.get('research_share') is not None]
    print(f"📊 {len(institutions_with_share)} institutions have Share 2024 data")
    
    for inst in institutions_with_share[:5]:
        research_share = inst.get('research_share', 'N/A')
        print(f"  #{inst['rank']}: {inst['name']} - Share 2024: {research_share}")
    
    # Categorize by empire
    print("\n🌍 Categorizing by empire...")
    empire_data = categorize_by_empire(institutions)
    
    print(f"  • Empire 1 (Commonwealth): {len(empire_data['empire_1'])}")
    print(f"  • Empire 2 (USA): {len(empire_data['empire_2'])}")
    print(f"  • Empire 3 (China): {len(empire_data['empire_3'])}")
    
    # Show top institutions from each empire with research share 2024
    print("\n🏅 Top institutions from each empire (with Share 2024):")
    
    for empire_name, empire_institutions in [('Empire 1 (Commonwealth)', empire_data['empire_1']),
                                           ('Empire 2 (USA)', empire_data['empire_2']),
                                           ('Empire 3 (China)', empire_data['empire_3'])]:
        if empire_institutions:
            print(f"\n  {empire_name}:")
            for i, inst in enumerate(empire_institutions[:3], 1):
                research_share = inst.get('research_share', 'N/A')
                share_indicator = "✓" if research_share != 'N/A' else "✗"
                print(f"    {i}. {inst['name']} - Share 2024: {research_share} {share_indicator} (#{inst['rank']})")
    
    # Save to CSV
    if any(empire_data.values()):
        print("\n💾 Saving to CSV...")
        filename = save_to_csv(empire_data)
        print("✅ Success! Data saved.")
        
        # Show file info
        file_size = os.path.getsize(filename)
        print(f"📁 File: {filename} ({file_size} bytes)")
    else:
        print("\n❌ No data to save")
    
    print("\n" + "=" * 60)
    print("Scraping complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
