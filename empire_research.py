"""
Empire Research Scraper - Final Version
Fixed empire numbering and country parsing
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
    """Parse the research leaders page to extract institution rankings."""
    soup = BeautifulSoup(html_content, 'html.parser')
    institutions = []
    
    print("🔍 Parsing page structure...")
    
    # Save HTML for debugging
    with open('research_leaders_page.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("💾 Saved research_leaders_page.html")
    
    # Method 1: Look for the main rankings table
    tables = soup.find_all('table')
    print(f"📊 Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        print(f"  Analyzing table {i+1}...")
        institutions_from_table = parse_rankings_table(table)
        if institutions_from_table:
            print(f"✅ Table {i+1}: Found {len(institutions_from_table)} institutions")
            return institutions_from_table
    
    # Method 2: Look for institution cards or list items
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
    
    # Method 3: Extract from page text using regex patterns
    page_text = soup.get_text()
    institutions_from_text = extract_institutions_from_text(page_text)
    if institutions_from_text:
        print(f"✅ Found {len(institutions_from_text)} institutions from text")
        return institutions_from_text
    
    return []


def parse_rankings_table(table):
    """Parse a rankings table to extract institution data."""
    institutions = []
    rows = table.find_all('tr')
    
    for row in rows:
        # Skip header rows
        if row.find('th'):
            continue
            
        cells = row.find_all(['td', 'div'])
        cell_texts = [cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True)]
        
        if len(cell_texts) >= 2:
            # First cell should contain rank
            rank_text = cell_texts[0]
            rank_match = re.search(r'(\d+)', rank_text)
            if rank_match:
                rank = int(rank_match.group(1))
                
                # Look for institution name and country pattern
                for text in cell_texts[1:]:
                    # Pattern: "Institution Name, Country"
                    name_country_match = re.search(r'^(.+?),\s*(.+)$', text)
                    if name_country_match:
                        name = name_country_match.group(1).strip()
                        country = name_country_match.group(2).strip()
                        
                        # Clean up country - remove extra parenthetical info
                        country = clean_country_name(country)
                        
                        institutions.append({
                            'rank': rank,
                            'name': name,
                            'country': country
                        })
                        break
                    else:
                        # Try without comma - might be just name
                        institutions.append({
                            'rank': rank,
                            'name': text,
                            'country': 'Unknown'
                        })
                        break
    
    return institutions


def clean_country_name(country):
    """Clean and normalize country names."""
    # Remove extra parenthetical information after country
    country = re.sub(r'\s*\([^)]*\)$', '', country).strip()
    
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
        
        # Look for ranking patterns
        patterns = [
            r'^(\d+)\.?\s+(.+?),\s*(.+)$',  # "1. Harvard University, United States"
            r'rank\s*[:\-]?\s*(\d+).*?name\s*[:\-]?\s*(.+?),\s*(.+)',  # "rank: 1 name: Harvard University, United States"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                if len(match) == 3:
                    try:
                        country = clean_country_name(match[2].strip())
                        institutions.append({
                            'rank': int(match[0]),
                            'name': match[1].strip(),
                            'country': country
                        })
                    except:
                        continue
    
    return institutions


def extract_institutions_from_text(text):
    """Extract institutions from page text using regex."""
    institutions = []
    
    # Common ranking patterns
    patterns = [
        r'(\d+)\.?\s*([^,\n]+?),\s*([^\n\(\)]+?)(?:\s+\([^\)]*\))?\s*\n',
        r'^(\d+)\s+([^,\n]+?),\s*([^\n\(\)]+?)(?:\s+\([^\)]*\))?$',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            if len(match) == 3:
                try:
                    country = clean_country_name(match[2].strip())
                    institutions.append({
                        'rank': int(match[0]),
                        'name': match[1].strip(),
                        'country': country
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
    """Save empire rankings to CSV file."""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y-%m')
    filename = os.path.join(output_dir, f'empire_research_{timestamp}.csv')
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['Empire', 'Empire_Rank', 'Institution', 'Country', 'Global_Rank'])
        
        # Empire 1: Commonwealth
        for idx, inst in enumerate(empire_data['empire_1'], 1):
            writer.writerow([
                '1',  # Changed from 'Empire_1_Commonwealth' to '1'
                idx,
                inst['name'],
                inst['country'],
                inst['rank']
            ])
        
        # Empire 2: USA
        for idx, inst in enumerate(empire_data['empire_2'], 1):
            writer.writerow([
                '2',  # Changed from 'Empire_2_USA' to '2'
                idx,
                inst['name'],
                inst['country'],
                inst['rank']
            ])
        
        # Empire 3: China
        for idx, inst in enumerate(empire_data['empire_3'], 1):
            writer.writerow([
                '3',  # Changed from 'Empire_3_China' to '3'
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
    print("Nature Index Empire Research Scraper - Final Version")
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
    
    # Show sample
    print("\n📋 Sample institutions:")
    for inst in institutions[:10]:
        print(f"  #{inst['rank']}: {inst['name']} - {inst['country']}")
    
    # Categorize by empire
    print("\n🌍 Categorizing by empire...")
    empire_data = categorize_by_empire(institutions)
    
    print(f"  • Empire 1 (Commonwealth): {len(empire_data['empire_1'])}")
    print(f"  • Empire 2 (USA): {len(empire_data['empire_2'])}")
    print(f"  • Empire 3 (China): {len(empire_data['empire_3'])}")
    
    # Show top institutions from each empire
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
    
    # Save to CSV
    if any(empire_data.values()):
        print("\n💾 Saving to CSV...")
        save_to_csv(empire_data)
        print("✅ Success! Data saved.")
    else:
        print("\n❌ No data to save")
    
    print("\n" + "=" * 60)
    print("Scraping complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
