"""
Empire Research Scraper
Fetches Nature Index research leader data and categorizes by empires
"""
import requests
import csv
import os
import re
from datetime import datetime

EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa',
    'Nigeria', 'Ghana', 'Kenya', 'Uganda', 'Tanzania', 'Zambia', 'Malawi',
    'Botswana', 'Namibia', 'Lesotho', 'Eswatini', 'Jamaica', 'Trinidad and Tobago',
    'Barbados', 'Bahamas', 'Belize', 'Guyana', 'Saint Lucia', 'Grenada',
    'Saint Vincent and the Grenadines', 'Antigua and Barbuda', 'Dominica',
    'Saint Kitts and Nevis', 'Cyprus', 'Malta', 'Singapore', 'Malaysia',
    'Brunei', 'Bangladesh', 'Sri Lanka', 'Maldives'
}

EMPIRE_2_COUNTRIES = {'United States of America', 'USA'}

EMPIRE_3_COUNTRIES = {'China', 'Hong Kong', 'Taiwan'}


def fetch_nature_index_data():
    """Fetch data from Nature Index research leaders page."""
    url = "https://www.nature.com/nature-index/research-leaders/2025/institution/all/all/global"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


def parse_institutions(text_content):
    """Parse text content to extract institution rankings using regex."""
    institutions = []
    
    # Pattern to match: number, newline, institution name with country
    # Example: "2\nHarvard University, United States of America (USA)"
    pattern = r'(\d+)\s*\n\s*([^,\n]+?),\s*([^\n]+?)(?:\s+\([\w\s]+\))?\s*\n'
    
    matches = re.finditer(pattern, text_content, re.MULTILINE)
    
    for match in matches:
        rank = int(match.group(1))
        name = match.group(2).strip()
        country_raw = match.group(3).strip()
        
        # Clean up country name - remove parenthetical codes
        country = re.sub(r'\s*\([^)]*\)$', '', country_raw).strip()
        
        institutions.append({
            'rank': rank,
            'name': name,
            'country': country
        })
    
    # If regex doesn't work, try line-by-line parsing as backup
    if len(institutions) < 50:
        print("  ⚠️  Regex parsing found few results, trying line-by-line...")
        institutions = parse_institutions_line_by_line(text_content)
    
    return institutions


def parse_institutions_line_by_line(text_content):
    """Fallback: Parse line by line."""
    institutions = []
    lines = [l.strip() for l in text_content.split('\n') if l.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if line is just a number (potential rank)
        if line.isdigit() and len(line) <= 4:
            rank = int(line)
            
            # Look ahead for institution line
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                
                # Institution line should have a comma
                if ',' in next_line:
                    # Split on last comma to separate name from country
                    parts = next_line.rsplit(',', 1)
                    if len(parts) == 2:
                        name = parts[0].strip()
                        country_raw = parts[1].strip()
                        
                        # Remove parenthetical country codes
                        country = re.sub(r'\s*\([^)]*\)$', '', country_raw).strip()
                        
                        institutions.append({
                            'rank': rank,
                            'name': name,
                            'country': country
                        })
                        
                        i += 2  # Skip the institution line
                        continue
        
        i += 1
    
    return institutions


def normalize_country(country):
    """Normalize country names for matching."""
    country_map = {
        'United States of America': 'United States of America',
        'USA': 'United States of America',
        'United Kingdom': 'United Kingdom',
        'UK': 'United Kingdom',
        'Singapore': 'Singapore',
        'Australia': 'Australia',
        'Canada': 'Canada',
        'New Zealand': 'New Zealand',
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
        if country in EMPIRE_3_COUNTRIES or any(c in inst['country'] for c in ['China', 'Hong Kong', 'Taiwan']):
            empire_3.append(inst)
        # Check Empire 2 (USA)
        elif country in EMPIRE_2_COUNTRIES or 'United States' in inst['country']:
            empire_2.append(inst)
        # Check Empire 1 (Commonwealth)
        elif country in EMPIRE_1_COUNTRIES:
            empire_1.append(inst)
    
    # Get top 10 for each empire
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
    
    print(f"\n✓ Data saved to {filename}")
    return filename


def main():
    """Main scraper function."""
    print("=" * 60)
    print("Nature Index Empire Research Scraper")
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
    
    # Parse institutions
    print("📊 Parsing institution data...")
    institutions = parse_institutions(html_content)
    
    if not institutions:
        print("❌ No institutions found. The page structure may have changed.")
        print("💡 Try checking the URL manually or enable debug mode.")
        return
    
    print(f"✓ Found {len(institutions)} institutions")
    
    # Categorize by empire
    print("\n🌍 Categorizing by empire...")
    empire_data = categorize_by_empire(institutions)
    
    print(f"  • Empire 1 (Commonwealth): {len(empire_data['empire_1'])} institutions in top 10")
    print(f"  • Empire 2 (USA): {len(empire_data['empire_2'])} institutions in top 10")
    print(f"  • Empire 3 (China): {len(empire_data['empire_3'])} institutions in top 10")
    
    # Print top 3 from each empire for preview
    print("\n📋 Preview - Top 3 from each empire:")
    
    if empire_data['empire_1']:
        print("\n  Empire 1 (Commonwealth):")
        for i, inst in enumerate(empire_data['empire_1'][:3], 1):
            print(f"    {i}. {inst['name']} (#{inst['rank']})")
    
    if empire_data['empire_2']:
        print("\n  Empire 2 (USA):")
        for i, inst in enumerate(empire_data['empire_2'][:3], 1):
            print(f"    {i}. {inst['name']} (#{inst['rank']})")
    
    if empire_data['empire_3']:
        print("\n  Empire 3 (China):")
        for i, inst in enumerate(empire_data['empire_3'][:3], 1):
            print(f"    {i}. {inst['name']} (#{inst['rank']})")
    
    # Save to CSV
    print("\n💾 Saving to CSV...")
    save_to_csv(empire_data)
    
    print("\n" + "=" * 60)
    print("✅ Scraping complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
