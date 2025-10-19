"""
Empire Research Scraper - With Research Share Data
Enhanced version that includes Research Share (2024) for each institution
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
    """Parse the research leaders page to extract institution rankings and research share."""
    soup = BeautifulSoup(html_content, 'html.parser')
    institutions = []
    
    print("🔍 Parsing page structure...")
    
    # Save HTML for debugging
    with open('research_leaders_page.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("💾 Saved research_leaders_page.html")
    
    # Method 1: Look for script tags containing JSON data (common in modern web apps)
    script_tags = soup.find_all('script')
    for script in script_tags:
        script_content = script.string
        if script_content and '__NEXT_DATA__' in script_content:
            print("✅ Found Next.js data payload")
            institutions = parse_nextjs_data(script_content)
            if institutions:
                return institutions
    
    # Method 2: Look for the main rankings table
    tables = soup.find_all('table')
    print(f"📊 Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        print(f"  Analyzing table {i+1}...")
        institutions_from_table = parse_rankings_table(table)
        if institutions_from_table:
            print(f"✅ Table {i+1}: Found {len(institutions_from_table)} institutions")
            return institutions_from_table
    
    # Method 3: Look for institution cards or list items
    institution_selectors = [
        '[data-test="institution-card"]',
        '.institution-card',
        '.ranking-item',
        '.institution-row',
        'tr',
        'li',
    ]
    
    for selector in institution_selectors:
        elements = soup.select(selector)
        if len(elements) > 10:  # Likely real data if we have many elements
            print(f"🔍 Found {len(elements)} elements with selector: {selector}")
            institutions_from_elements = parse_institution_elements(elements)
            if institutions_from_elements:
                print(f"✅ Found {len(institutions_from_elements)} institutions from elements")
                return institutions_from_elements
    
    # Method 4: Extract from page text using regex patterns
    page_text = soup.get_text()
    institutions_from_text = extract_institutions_from_text(page_text)
    if institutions_from_text:
        print(f"✅ Found {len(institutions_from_text)} institutions from text")
        return institutions_from_text
    
    return []


def parse_nextjs_data(script_content):
    """Parse Next.js JSON data to extract institution information."""
    try:
        # Extract JSON data from script tag
        json_match = re.search(r'__NEXT_DATA__\s*=\s*({.*?})', script_content)
        if json_match:
            json_data = json.loads(json_match.group(1))
            
            # Navigate through the JSON structure to find institution data
            # This structure may vary - we need to explore the actual JSON
            institutions = extract_from_json_structure(json_data)
            if institutions:
                return institutions
            
            # Alternative: Look for research share data in props
            props = json_data.get('props', {})
            page_props = props.get('pageProps', {})
            
            # Try different possible keys for institution data
            possible_keys = ['institutions', 'rankings', 'data', 'results', 'items']
            for key in possible_keys:
                if key in page_props:
                    print(f"🔍 Found data in key: {key}")
                    data = page_props[key]
                    if isinstance(data, list) and len(data) > 0:
                        return parse_institution_list(data)
    
    except Exception as e:
        print(f"❌ Error parsing Next.js data: {e}")
    
    return []


def extract_from_json_structure(json_data, path=[]):
    """Recursively search JSON structure for institution data."""
    institutions = []
    
    if isinstance(json_data, dict):
        # Check if this looks like institution data
        if all(key in json_data for key in ['rank', 'name', 'country']):
            institutions.append(parse_institution_from_json(json_data))
        
        # Recursively search deeper
        for key, value in json_data.items():
            institutions.extend(extract_from_json_structure(value, path + [key]))
    
    elif isinstance(json_data, list):
        for item in json_data:
            institutions.extend(extract_from_json_structure(item, path))
    
    return institutions


def parse_institution_from_json(inst_data):
    """Parse institution data from JSON object."""
    return {
        'rank': inst_data.get('rank'),
        'name': inst_data.get('name', ''),
        'country': inst_data.get('country', ''),
        'research_share': inst_data.get('share', inst_data.get('research_share', 0))
    }


def parse_institution_list(data_list):
    """Parse a list of institution data."""
    institutions = []
    for item in data_list:
        if isinstance(item, dict):
            institution = parse_institution_from_json(item)
            if institution['name']:  # Only add if we have a name
                institutions.append(institution)
    return institutions


def parse_rankings_table(table):
    """Parse a rankings table to extract institution data including research share."""
    institutions = []
    rows = table.find_all('tr')
    
    for row in rows:
        # Skip header rows
        if row.find('th'):
            continue
            
        cells = row.find_all(['td', 'div'])
        cell_texts = [cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True)]
        
        if len(cell_texts) >= 3:
            try:
                # First cell should contain rank
                rank_text = cell_texts[0]
                rank_match = re.search(r'(\d+)', rank_text)
                if rank_match:
                    rank = int(rank_match.group(1))
                    
                    # Look for research share (usually a decimal number)
                    research_share = 0
                    for text in cell_texts:
                        share_match = re.search(r'(\d+\.\d+)', text)
                        if share_match:
                            research_share = float(share_match.group(1))
                            break
                    
                    # Look for institution name and country pattern
                    for text in cell_texts[1:]:
                        # Skip numeric-only cells (likely research share)
                        if re.match(r'^\d+\.?\d*$', text):
                            continue
                            
                        # Pattern: "Institution Name, Country"
                        if 'University of California' in text:
                            name, country = parse_uc_institution(text)
                        else:
                            name_country_match = re.search(r'^(.+?),\s*(.+)$', text)
                            if name_country_match:
                                name = name_country_match.group(1).strip()
                                country_raw = name_country_match.group(2).strip()
                                country = extract_country_name(country_raw)
                            else:
                                # Try without comma
                                name = text
                                country = 'Unknown'
                        
                        institutions.append({
                            'rank': rank,
                            'name': name,
                            'country': country,
                            'research_share': research_share
                        })
                        break
            except Exception as e:
                print(f"⚠️ Error parsing row: {e}")
                continue
    
    return institutions


def parse_uc_institution(text):
    """Parse University of California institution names specifically."""
    # Example: "University of California, Los Angeles (UCLA), United States of America (USA)"
    # We want to keep: "University of California, Los Angeles (UCLA)" as name
    # And extract: "United States of America" as country
    
    # Split by the last comma to separate institution from country
    parts = text.rsplit(',', 1)
    if len(parts) == 2:
        name = parts[0].strip()
        country_raw = parts[1].strip()
        country = extract_country_name(country_raw)
        return name, country
    else:
        # Fallback if parsing fails
        return text, 'United States of America'


def extract_country_name(country_raw):
    """Extract clean country name from raw country string."""
    # Remove extra parenthetical information after country
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


def parse_institution_elements(elements):
    """Parse institution data from various HTML elements."""
    institutions = []
    
    for element in elements:
        text = element.get_text(strip=True)
        
        # Look for ranking patterns with research share
        patterns = [
            r'^(\d+)\.?\s+(.+?),\s*(.+?)\s+(\d+\.\d+)$',  # "1. Harvard University, United States 123.45"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if len(match) == 4:
                    try:
                        if 'University of California' in match[1]:
                            name, country = parse_uc_institution(f"{match[1]}, {match[2]}")
                        else:
                            name = match[1].strip()
                            country = extract_country_name(match[2].strip())
                        
                        institutions.append({
                            'rank': int(match[0]),
                            'name': name,
                            'country': country,
                            'research_share': float(match[3])
                        })
                    except:
                        continue
    
    return institutions


def extract_institutions_from_text(text):
    """Extract institutions from page text using regex."""
    institutions = []
    
    # Common ranking patterns with research share
    patterns = [
        r'(\d+)\.?\s*([^,\n]+?),\s*([^\n\(\)]+?)\s+(\d+\.\d+)(?:\s+\([^\)]*\))?\s*\n',
        r'^(\d+)\s+([^,\n]+?),\s*([^\n\(\)]+?)\s+(\d+\.\d+)(?:\s+\([^\)]*\))?$',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            if len(match) == 4:
                try:
                    if 'University of California' in match[1]:
                        name, country = parse_uc_institution(f"{match[1]}, {match[2]}")
                    else:
                        name = match[1].strip()
                        country = extract_country_name(match[2].strip())
                    
                    institutions.append({
                        'rank': int(match[0]),
                        'name': name,
                        'country': country,
                        'research_share': float(match[3])
                    })
                except:
                    continue
    
    # Remove duplicates by rank
    seen_ranks = set()
    unique_institutions = []
    for inst in institutions:
        if inst['rank'] not in seen_ranks:
            seen_ranks.add(inst['rank'])
            unique_institutions.append(inst)
    
    return unique_institutions


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
    """Save empire rankings to CSV file with Research Share column."""
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.join(output_dir, 'empire_research.csv')  
    
    # Remove existing file if it exists to ensure clean overwrite
    if os.path.exists(filename):
        os.remove(filename)
        print(f"♻️  Removed existing file: {filename}")
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header with Research Share column
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
    return filename


def main():
    """Main scraper function."""
    print("=" * 60)
    print("Nature Index Empire Research Scraper - With Research Share")
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
    
    # Parse the page
    print("\n📊 Parsing institution data...")
    institutions = parse_research_leaders_page(html_content)
    
    if not institutions:
        print("❌ No institutions found.")
        print("💡 Check research_leaders_page.html to see the page structure.")
        return
    
    print(f"✓ Found {len(institutions)} institutions")
    
    # Show sample with research share data
    print("\n📋 Sample institutions with Research Share:")
    for inst in institutions[:5]:
        research_share = inst.get('research_share', 'N/A')
        print(f"  #{inst['rank']}: {inst['name']} - {inst['country']} - Share: {research_share}")
    
    # Check for UC institutions specifically
    uc_institutions = [inst for inst in institutions if 'University of California' in inst['name']]
    if uc_institutions:
        print("\n📋 UC Institutions found:")
        for inst in uc_institutions[:3]:
            research_share = inst.get('research_share', 'N/A')
            print(f"  #{inst['rank']}: {inst['name']} - Share: {research_share}")
    
    # Categorize by empire
    print("\n🌍 Categorizing by empire...")
    empire_data = categorize_by_empire(institutions)
    
    print(f"  • Empire 1 (Commonwealth): {len(empire_data['empire_1'])}")
    print(f"  • Empire 2 (USA): {len(empire_data['empire_2'])}")
    print(f"  • Empire 3 (China): {len(empire_data['empire_3'])}")
    
    # Show top institutions from each empire with research share
    print("\n🏅 Top institutions from each empire:")
    
    if empire_data['empire_1']:
        print("\n  Empire 1 (Commonwealth):")
        for i, inst in enumerate(empire_data['empire_1'][:3], 1):
            research_share = inst.get('research_share', 'N/A')
            print(f"    {i}. {inst['name']} - Share: {research_share} (#{inst['rank']})")
    
    if empire_data['empire_2']:
        print("\n  Empire 2 (USA):")
        for i, inst in enumerate(empire_data['empire_2'][:3], 1):
            research_share = inst.get('research_share', 'N/A')
            print(f"    {i}. {inst['name']} - Share: {research_share} (#{inst['rank']})")
    
    if empire_data['empire_3']:
        print("\n  Empire 3 (China):")
        for i, inst in enumerate(empire_data['empire_3'][:3], 1):
            research_share = inst.get('research_share', 'N/A')
            print(f"    {i}. {inst['name']} - Share: {research_share} (#{inst['rank']})")
    
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
