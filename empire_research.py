"""
Empire Research Scraper - Correct Share 2024 Data Extraction
Fixed to specifically extract Share 2024 from the correct table column
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
    
    # Method 1: Look for the main rankings table with specific column structure
    tables = soup.find_all('table')
    print(f"📊 Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        print(f"  Analyzing table {i+1} for Share 2024 data...")
        institutions_from_table = parse_rankings_table_correct_2024(table)
        if institutions_from_table:
            print(f"✅ Table {i+1}: Found {len(institutions_from_table)} institutions with Share 2024")
            return institutions_from_table
    
    return []


def parse_rankings_table_correct_2024(table):
    """Parse the rankings table with correct column mapping for Share 2024."""
    institutions = []
    rows = table.find_all('tr')
    
    # First, identify the exact column indices
    header_row = table.find('tr')
    if not header_row:
        return institutions
        
    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
    print(f"📋 Table headers: {headers}")
    
    # Find column indices
    position_col = None
    institution_col = None
    share_2023_col = None
    share_2024_col = None
    
    for i, header in enumerate(headers):
        if 'position' in header.lower() or header == '':
            position_col = i
        elif 'institution' in header.lower():
            institution_col = i
        elif 'share 2023' in header.lower():
            share_2023_col = i
        elif 'share 2024' in header.lower():
            share_2024_col = i
    
    print(f"🔍 Column mapping: Position={position_col}, Institution={institution_col}, Share 2023={share_2023_col}, Share 2024={share_2024_col}")
    
    if share_2024_col is None:
        print("❌ Could not find Share 2024 column!")
        return institutions
    
    # Parse data rows
    for row in rows:
        # Skip header rows
        if row.find('th'):
            continue
            
        cells = row.find_all(['td', 'div'])
        if len(cells) > max(filter(None, [position_col, institution_col, share_2024_col])):
            try:
                # Extract rank from position column
                rank_text = cells[position_col].get_text(strip=True) if position_col is not None else cells[0].get_text(strip=True)
                rank_match = re.search(r'(\d+)', rank_text)
                if not rank_match:
                    continue
                rank = int(rank_match.group(1))
                
                # Extract institution name and country from institution column
                institution_cell = cells[institution_col] if institution_col is not None else cells[1]
                institution_text = institution_cell.get_text(strip=True)
                
                if 'University of California' in institution_text:
                    name, country = parse_uc_institution(institution_text)
                else:
                    name_country_match = re.search(r'^(.+?),\s*(.+)$', institution_text)
                    if name_country_match:
                        name = name_country_match.group(1).strip()
                        country_raw = name_country_match.group(2).strip()
                        country = extract_country_name(country_raw)
                    else:
                        name = institution_text
                        country = 'Unknown'
                
                # Extract Share 2024 from the correct column
                share_2024_cell = cells[share_2024_col]
                share_2024_text = share_2024_cell.get_text(strip=True)
                research_share = float(share_2024_text) if share_2024_text.replace('.', '').isdigit() else None
                
                if name:
                    institutions.append({
                        'rank': rank,
                        'name': name,
                        'country': country,
                        'research_share': research_share
                    })
                    print(f"  ✅ #{rank}: {name} - Share 2024: {research_share}")
                    
            except Exception as e:
                print(f"⚠️ Error parsing row: {e}")
                continue
    
    return institutions


def parse_uc_institution(text):
    """Parse University of California institution names specifically."""
    # Handle UC institutions - they have campus names after the comma
    if 'University of California' in text:
        # Split by last comma to separate institution from country
        parts = text.rsplit(',', 1)
        if len(parts) == 2:
            name = parts[0].strip()
            country_raw = parts[1].strip()
            country = extract_country_name(country_raw)
            return name, country
    
    # Fallback for other institutions
    parts = text.rsplit(',', 1)
    if len(parts) == 2:
        name = parts[0].strip()
        country_raw = parts[1].strip()
        country = extract_country_name(country_raw)
        return name, country
    else:
        return text, 'Unknown'


def extract_country_name(country_raw):
    """Extract clean country name from raw country string."""
    country = re.sub(r'\s*\([^)]*\)$', '', country_raw).strip()
    
    # Handle specific cases
    if any(us in country for us in ['United States of America', 'USA', 'United States']):
        return 'United States of America'
    elif 'United Kingdom' in country or 'UK' in country:
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
    print("Nature Index Empire Research Scraper - Correct Share 2024 Extraction")
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
        print(f"  #{inst['rank']}: {inst['name']} - {inst['country']} - Share 2024: {research_share}")
    
    # Verify Chinese Academy of Sciences data
    cas_institutions = [inst for inst in institutions if 'Chinese Academy of Sciences' in inst['name']]
    if cas_institutions:
        print("\n🔍 Verifying Chinese Academy of Sciences data:")
        for inst in cas_institutions:
            research_share = inst.get('research_share', 'N/A')
            print(f"  #{inst['rank']}: {inst['name']} - Share 2024: {research_share}")
            if research_share == 2776.90:
                print("  ✅ CORRECT: Share 2024 matches expected value (2776.90)")
    
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
        
        # Show first few lines of CSV
        print("\n📄 First few lines of CSV:")
        with open(filename, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i < 5:  # Show first 5 lines
                    print(f"  {line.strip()}")
    else:
        print("\n❌ No data to save")
    
    print("\n" + "=" * 60)
    print("Scraping complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
