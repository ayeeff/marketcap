"""
Empire Nature Share Scraper
Scrapes Nature Index country rankings and aggregates by empire
"""
import requests
import csv
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup

EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa',
    'Nigeria', 'Ghana', 'Kenya', 'Uganda', 'Tanzania', 'Zambia', 'Malawi',
    'Botswana', 'Namibia', 'Lesotho', 'Eswatini', 'Jamaica',
    'Trinidad and Tobago', 'Barbados', 'Bahamas', 'Belize', 'Guyana',
    'Saint Lucia', 'Grenada', 'Saint Vincent and the Grenadines',
    'Antigua and Barbuda', 'Dominica', 'Saint Kitts and Nevis',
    'Cyprus', 'Malta', 'Singapore', 'Malaysia', 'Brunei', 'Bangladesh',
    'Sri Lanka', 'Maldives'
}

EMPIRE_2_COUNTRIES = {'United States of America'}

EMPIRE_3_COUNTRIES = {'China', 'Hong Kong (China)', 'Taiwan'}


def fetch_nature_index_countries():
    """Fetch data from the Nature Index country rankings URL."""
    url = "https://www.nature.com/nature-index/research-leaders/2025/country/all/global"
    
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


def parse_share_value(share_text):
    """Parse Share 2024 value from text, handling various formats."""
    if not share_text:
        return 0.0
    
    # Remove any whitespace and commas
    share_text = share_text.strip().replace(',', '')
    
    # Try to extract number
    match = re.search(r'([\d.]+)', share_text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
    
    return 0.0


def parse_country_rankings_page(html_content):
    """Parse the country rankings page to extract Share 2024 data."""
    soup = BeautifulSoup(html_content, 'html.parser')
    countries = []
    
    print("🔍 Parsing page structure...")
    
    # Save HTML for debugging
    with open('country_rankings_page.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("💾 Saved country_rankings_page.html")
    
    # Look for tables
    tables = soup.find_all('table')
    print(f"📊 Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        print(f"  Analyzing table {i+1}...")
        countries_from_table = parse_rankings_table(table)
        if countries_from_table:
            print(f"✅ Table {i+1}: Found {len(countries_from_table)} countries")
            return countries_from_table
    
    # Alternative: Look for structured elements
    row_selectors = [
        'tr',
        '[data-test="country-row"]',
        '.country-row',
        '.ranking-item',
    ]
    
    for selector in row_selectors:
        elements = soup.select(selector)
        if len(elements) > 10:
            print(f"🔍 Found {len(elements)} elements with selector: {selector}")
            countries_from_elements = parse_country_elements(elements)
            if countries_from_elements:
                print(f"✅ Found {len(countries_from_elements)} countries from elements")
                return countries_from_elements
    
    return []


def parse_rankings_table(table):
    """Parse a rankings table to extract country and Share 2024 data."""
    countries = []
    
    # First, find the header to identify Share 2024 column
    header_row = table.find('tr')
    headers = []
    share_col_idx = -1
    country_col_idx = -1
    
    if header_row:
        header_cells = header_row.find_all(['th', 'td'])
        headers = [cell.get_text(strip=True) for cell in header_cells]
        
        # Find Share 2024 column and Country column
        for idx, header in enumerate(headers):
            if 'share' in header.lower() and '2024' in header:
                share_col_idx = idx
                print(f"  Found 'Share 2024' column at index {idx}")
            if 'country' in header.lower() or 'region' in header.lower():
                country_col_idx = idx
                print(f"  Found 'Country/Region' column at index {idx}")
    
    # Parse data rows
    rows = table.find_all('tr')
    
    for row in rows:
        # Skip header rows
        if row.find('th'):
            continue
            
        cells = row.find_all(['td'])
        if len(cells) < 3:
            continue
        
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        
        country_name = None
        share_value = 0.0
        
        # Extract country and share based on column indices
        if country_col_idx >= 0 and country_col_idx < len(cell_texts):
            country_name = cell_texts[country_col_idx]
        
        if share_col_idx >= 0 and share_col_idx < len(cell_texts):
            share_value = parse_share_value(cell_texts[share_col_idx])
        
        # Fallback: if we didn't find via column index, try pattern matching
        if not country_name or share_value == 0:
            # Look for country name (not a pure number, not a rank)
            for idx, text in enumerate(cell_texts):
                # Skip rank column (first column, pure number)
                if idx == 0 and re.match(r'^\d+


def parse_country_elements(elements):
    """Parse country data from various HTML elements."""
    countries = []
    
    for element in elements:
        text = element.get_text(strip=True)
        
        # Look for patterns like "United States 12345.67"
        # Country names can have spaces, numbers are the share value
        parts = text.split()
        
        if len(parts) >= 2:
            # Last part should be the number
            potential_share = parts[-1]
            share_value = parse_share_value(potential_share)
            
            if share_value > 0:
                # Everything before the last part is the country name
                country_name = ' '.join(parts[:-1])
                # Remove rank if present at the start
                country_name = re.sub(r'^\d+\.?\s*', '', country_name)
                
                if country_name:
                    countries.append({
                        'country': country_name,
                        'share_2024': share_value
                    })
    
    return countries


def normalize_country(country):
    """Normalize country names for empire categorization."""
    country = str(country).strip()
    
    # Exact matches
    country_map = {
        'United States of America': 'United States of America',
        'United States': 'United States of America',
        'USA': 'United States of America',
        'US': 'United States of America',
        'Hong Kong': 'Hong Kong (China)',
        'Hong Kong (China)': 'Hong Kong (China)',
        'Taiwan': 'Taiwan',
        'China': 'China',
    }
    
    if country in country_map:
        return country_map[country]
    
    return country


def categorize_by_empire(countries):
    """Categorize countries by empire and sum their Share 2024 values."""
    empire_1_total = 0.0
    empire_2_total = 0.0
    empire_3_total = 0.0
    
    empire_1_countries = []
    empire_2_countries = []
    empire_3_countries = []
    
    for country_data in countries:
        country = normalize_country(country_data['country'])
        share = country_data['share_2024']
        
        # Empire 3: China, Hong Kong, Taiwan
        if country in EMPIRE_3_COUNTRIES:
            empire_3_total += share
            empire_3_countries.append((country, share))
        # Empire 2: USA
        elif country in EMPIRE_2_COUNTRIES:
            empire_2_total += share
            empire_2_countries.append((country, share))
        # Empire 1: Commonwealth countries
        elif country in EMPIRE_1_COUNTRIES:
            empire_1_total += share
            empire_1_countries.append((country, share))
    
    total_all_empires = empire_1_total + empire_2_total + empire_3_total
    
    return {
        'empire_1': {
            'total': empire_1_total,
            'percent': (empire_1_total / total_all_empires * 100) if total_all_empires > 0 else 0,
            'countries': empire_1_countries
        },
        'empire_2': {
            'total': empire_2_total,
            'percent': (empire_2_total / total_all_empires * 100) if total_all_empires > 0 else 0,
            'countries': empire_2_countries
        },
        'empire_3': {
            'total': empire_3_total,
            'percent': (empire_3_total / total_all_empires * 100) if total_all_empires > 0 else 0,
            'countries': empire_3_countries
        },
        'total': total_all_empires
    }


def save_to_csv(empire_data, output_dir='data'):
    """Save empire nature share data to CSV file."""
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.join(output_dir, 'empire_nature_share.csv')
    
    # Remove existing file if it exists
    if os.path.exists(filename):
        os.remove(filename)
        print(f"♻️  Removed existing file: {filename}")
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['empire', 'share_2024', 'percent', 'date'])
        
        # Empire 1
        writer.writerow([
            '1',
            f"{empire_data['empire_1']['total']:.2f}",
            f"{empire_data['empire_1']['percent']:.1f}",
            current_date
        ])
        
        # Empire 2
        writer.writerow([
            '2',
            f"{empire_data['empire_2']['total']:.2f}",
            f"{empire_data['empire_2']['percent']:.1f}",
            current_date
        ])
        
        # Empire 3
        writer.writerow([
            '3',
            f"{empire_data['empire_3']['total']:.2f}",
            f"{empire_data['empire_3']['percent']:.1f}",
            current_date
        ])
    
    print(f"✓ Data saved to {filename}")
    return filename


def main():
    """Main scraper function."""
    print("=" * 60)
    print("Nature Index Empire Share Scraper")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fetch data
    print("📡 Fetching country rankings data...")
    html_content = fetch_nature_index_countries()
    
    if not html_content:
        print("❌ Failed to fetch data.")
        return
    
    print(f"✓ Fetched {len(html_content)} characters")
    
    # Parse the page
    print("\n📊 Parsing country data...")
    countries = parse_country_rankings_page(html_content)
    
    if not countries:
        print("❌ No countries found.")
        print("💡 Check country_rankings_page.html to see the page structure.")
        return
    
    print(f"✓ Found {len(countries)} countries")
    
    # Show sample
    print("\n📋 Sample countries:")
    for country in countries[:5]:
        print(f"  {country['country']}: {country['share_2024']}")
    
    # Categorize by empire
    print("\n🌍 Categorizing by empire...")
    empire_data = categorize_by_empire(countries)
    
    print(f"\n📊 Empire Totals (Share 2024):")
    print(f"  • Empire 1 (Commonwealth): {empire_data['empire_1']['total']:.2f} ({empire_data['empire_1']['percent']:.1f}%)")
    print(f"  • Empire 2 (USA): {empire_data['empire_2']['total']:.2f} ({empire_data['empire_2']['percent']:.1f}%)")
    print(f"  • Empire 3 (China): {empire_data['empire_3']['total']:.2f} ({empire_data['empire_3']['percent']:.1f}%)")
    print(f"  • Total: {empire_data['total']:.2f}")
    
    # Show contributing countries
    print("\n🏅 Contributing countries:")
    
    if empire_data['empire_1']['countries']:
        print("\n  Empire 1 (Commonwealth):")
        for country, share in sorted(empire_data['empire_1']['countries'], key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {country}: {share:.2f}")
    
    if empire_data['empire_2']['countries']:
        print("\n  Empire 2 (USA):")
        for country, share in empire_data['empire_2']['countries']:
            print(f"    {country}: {share:.2f}")
    
    if empire_data['empire_3']['countries']:
        print("\n  Empire 3 (China):")
        for country, share in empire_data['empire_3']['countries']:
            print(f"    {country}: {share:.2f}")
    
    # Save to CSV
    if empire_data['total'] > 0:
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
, text):
                    continue
                
                # Country name should contain letters
                if not country_name and re.search(r'[A-Za-z]', text) and not re.match(r'^[\d.,%-]+


def parse_country_elements(elements):
    """Parse country data from various HTML elements."""
    countries = []
    
    for element in elements:
        text = element.get_text(strip=True)
        
        # Look for patterns like "United States 12345.67"
        # Country names can have spaces, numbers are the share value
        parts = text.split()
        
        if len(parts) >= 2:
            # Last part should be the number
            potential_share = parts[-1]
            share_value = parse_share_value(potential_share)
            
            if share_value > 0:
                # Everything before the last part is the country name
                country_name = ' '.join(parts[:-1])
                # Remove rank if present at the start
                country_name = re.sub(r'^\d+\.?\s*', '', country_name)
                
                if country_name:
                    countries.append({
                        'country': country_name,
                        'share_2024': share_value
                    })
    
    return countries


def normalize_country(country):
    """Normalize country names for empire categorization."""
    country = str(country).strip()
    
    # Exact matches
    country_map = {
        'United States of America': 'United States of America',
        'United States': 'United States of America',
        'USA': 'United States of America',
        'US': 'United States of America',
        'Hong Kong': 'Hong Kong (China)',
        'Hong Kong (China)': 'Hong Kong (China)',
        'Taiwan': 'Taiwan',
        'China': 'China',
    }
    
    if country in country_map:
        return country_map[country]
    
    return country


def categorize_by_empire(countries):
    """Categorize countries by empire and sum their Share 2024 values."""
    empire_1_total = 0.0
    empire_2_total = 0.0
    empire_3_total = 0.0
    
    empire_1_countries = []
    empire_2_countries = []
    empire_3_countries = []
    
    for country_data in countries:
        country = normalize_country(country_data['country'])
        share = country_data['share_2024']
        
        # Empire 3: China, Hong Kong, Taiwan
        if country in EMPIRE_3_COUNTRIES:
            empire_3_total += share
            empire_3_countries.append((country, share))
        # Empire 2: USA
        elif country in EMPIRE_2_COUNTRIES:
            empire_2_total += share
            empire_2_countries.append((country, share))
        # Empire 1: Commonwealth countries
        elif country in EMPIRE_1_COUNTRIES:
            empire_1_total += share
            empire_1_countries.append((country, share))
    
    total_all_empires = empire_1_total + empire_2_total + empire_3_total
    
    return {
        'empire_1': {
            'total': empire_1_total,
            'percent': (empire_1_total / total_all_empires * 100) if total_all_empires > 0 else 0,
            'countries': empire_1_countries
        },
        'empire_2': {
            'total': empire_2_total,
            'percent': (empire_2_total / total_all_empires * 100) if total_all_empires > 0 else 0,
            'countries': empire_2_countries
        },
        'empire_3': {
            'total': empire_3_total,
            'percent': (empire_3_total / total_all_empires * 100) if total_all_empires > 0 else 0,
            'countries': empire_3_countries
        },
        'total': total_all_empires
    }


def save_to_csv(empire_data, output_dir='data'):
    """Save empire nature share data to CSV file."""
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.join(output_dir, 'empire_nature_share.csv')
    
    # Remove existing file if it exists
    if os.path.exists(filename):
        os.remove(filename)
        print(f"♻️  Removed existing file: {filename}")
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['empire', 'share_2024', 'percent', 'date'])
        
        # Empire 1
        writer.writerow([
            '1',
            f"{empire_data['empire_1']['total']:.2f}",
            f"{empire_data['empire_1']['percent']:.1f}",
            current_date
        ])
        
        # Empire 2
        writer.writerow([
            '2',
            f"{empire_data['empire_2']['total']:.2f}",
            f"{empire_data['empire_2']['percent']:.1f}",
            current_date
        ])
        
        # Empire 3
        writer.writerow([
            '3',
            f"{empire_data['empire_3']['total']:.2f}",
            f"{empire_data['empire_3']['percent']:.1f}",
            current_date
        ])
    
    print(f"✓ Data saved to {filename}")
    return filename


def main():
    """Main scraper function."""
    print("=" * 60)
    print("Nature Index Empire Share Scraper")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fetch data
    print("📡 Fetching country rankings data...")
    html_content = fetch_nature_index_countries()
    
    if not html_content:
        print("❌ Failed to fetch data.")
        return
    
    print(f"✓ Fetched {len(html_content)} characters")
    
    # Parse the page
    print("\n📊 Parsing country data...")
    countries = parse_country_rankings_page(html_content)
    
    if not countries:
        print("❌ No countries found.")
        print("💡 Check country_rankings_page.html to see the page structure.")
        return
    
    print(f"✓ Found {len(countries)} countries")
    
    # Show sample
    print("\n📋 Sample countries:")
    for country in countries[:5]:
        print(f"  {country['country']}: {country['share_2024']}")
    
    # Categorize by empire
    print("\n🌍 Categorizing by empire...")
    empire_data = categorize_by_empire(countries)
    
    print(f"\n📊 Empire Totals (Share 2024):")
    print(f"  • Empire 1 (Commonwealth): {empire_data['empire_1']['total']:.2f} ({empire_data['empire_1']['percent']:.1f}%)")
    print(f"  • Empire 2 (USA): {empire_data['empire_2']['total']:.2f} ({empire_data['empire_2']['percent']:.1f}%)")
    print(f"  • Empire 3 (China): {empire_data['empire_3']['total']:.2f} ({empire_data['empire_3']['percent']:.1f}%)")
    print(f"  • Total: {empire_data['total']:.2f}")
    
    # Show contributing countries
    print("\n🏅 Contributing countries:")
    
    if empire_data['empire_1']['countries']:
        print("\n  Empire 1 (Commonwealth):")
        for country, share in sorted(empire_data['empire_1']['countries'], key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {country}: {share:.2f}")
    
    if empire_data['empire_2']['countries']:
        print("\n  Empire 2 (USA):")
        for country, share in empire_data['empire_2']['countries']:
            print(f"    {country}: {share:.2f}")
    
    if empire_data['empire_3']['countries']:
        print("\n  Empire 3 (China):")
        for country, share in empire_data['empire_3']['countries']:
            print(f"    {country}: {share:.2f}")
    
    # Save to CSV
    if empire_data['total'] > 0:
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
, text):
                    country_name = text
                    continue
                
                # Share value should be a number (after we found country)
                if country_name and share_value == 0 and re.match(r'^[\d.,]+


def parse_country_elements(elements):
    """Parse country data from various HTML elements."""
    countries = []
    
    for element in elements:
        text = element.get_text(strip=True)
        
        # Look for patterns like "United States 12345.67"
        # Country names can have spaces, numbers are the share value
        parts = text.split()
        
        if len(parts) >= 2:
            # Last part should be the number
            potential_share = parts[-1]
            share_value = parse_share_value(potential_share)
            
            if share_value > 0:
                # Everything before the last part is the country name
                country_name = ' '.join(parts[:-1])
                # Remove rank if present at the start
                country_name = re.sub(r'^\d+\.?\s*', '', country_name)
                
                if country_name:
                    countries.append({
                        'country': country_name,
                        'share_2024': share_value
                    })
    
    return countries


def normalize_country(country):
    """Normalize country names for empire categorization."""
    country = str(country).strip()
    
    # Exact matches
    country_map = {
        'United States of America': 'United States of America',
        'United States': 'United States of America',
        'USA': 'United States of America',
        'US': 'United States of America',
        'Hong Kong': 'Hong Kong (China)',
        'Hong Kong (China)': 'Hong Kong (China)',
        'Taiwan': 'Taiwan',
        'China': 'China',
    }
    
    if country in country_map:
        return country_map[country]
    
    return country


def categorize_by_empire(countries):
    """Categorize countries by empire and sum their Share 2024 values."""
    empire_1_total = 0.0
    empire_2_total = 0.0
    empire_3_total = 0.0
    
    empire_1_countries = []
    empire_2_countries = []
    empire_3_countries = []
    
    for country_data in countries:
        country = normalize_country(country_data['country'])
        share = country_data['share_2024']
        
        # Empire 3: China, Hong Kong, Taiwan
        if country in EMPIRE_3_COUNTRIES:
            empire_3_total += share
            empire_3_countries.append((country, share))
        # Empire 2: USA
        elif country in EMPIRE_2_COUNTRIES:
            empire_2_total += share
            empire_2_countries.append((country, share))
        # Empire 1: Commonwealth countries
        elif country in EMPIRE_1_COUNTRIES:
            empire_1_total += share
            empire_1_countries.append((country, share))
    
    total_all_empires = empire_1_total + empire_2_total + empire_3_total
    
    return {
        'empire_1': {
            'total': empire_1_total,
            'percent': (empire_1_total / total_all_empires * 100) if total_all_empires > 0 else 0,
            'countries': empire_1_countries
        },
        'empire_2': {
            'total': empire_2_total,
            'percent': (empire_2_total / total_all_empires * 100) if total_all_empires > 0 else 0,
            'countries': empire_2_countries
        },
        'empire_3': {
            'total': empire_3_total,
            'percent': (empire_3_total / total_all_empires * 100) if total_all_empires > 0 else 0,
            'countries': empire_3_countries
        },
        'total': total_all_empires
    }


def save_to_csv(empire_data, output_dir='data'):
    """Save empire nature share data to CSV file."""
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.join(output_dir, 'empire_nature_share.csv')
    
    # Remove existing file if it exists
    if os.path.exists(filename):
        os.remove(filename)
        print(f"♻️  Removed existing file: {filename}")
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['empire', 'share_2024', 'percent', 'date'])
        
        # Empire 1
        writer.writerow([
            '1',
            f"{empire_data['empire_1']['total']:.2f}",
            f"{empire_data['empire_1']['percent']:.1f}",
            current_date
        ])
        
        # Empire 2
        writer.writerow([
            '2',
            f"{empire_data['empire_2']['total']:.2f}",
            f"{empire_data['empire_2']['percent']:.1f}",
            current_date
        ])
        
        # Empire 3
        writer.writerow([
            '3',
            f"{empire_data['empire_3']['total']:.2f}",
            f"{empire_data['empire_3']['percent']:.1f}",
            current_date
        ])
    
    print(f"✓ Data saved to {filename}")
    return filename


def main():
    """Main scraper function."""
    print("=" * 60)
    print("Nature Index Empire Share Scraper")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fetch data
    print("📡 Fetching country rankings data...")
    html_content = fetch_nature_index_countries()
    
    if not html_content:
        print("❌ Failed to fetch data.")
        return
    
    print(f"✓ Fetched {len(html_content)} characters")
    
    # Parse the page
    print("\n📊 Parsing country data...")
    countries = parse_country_rankings_page(html_content)
    
    if not countries:
        print("❌ No countries found.")
        print("💡 Check country_rankings_page.html to see the page structure.")
        return
    
    print(f"✓ Found {len(countries)} countries")
    
    # Show sample
    print("\n📋 Sample countries:")
    for country in countries[:5]:
        print(f"  {country['country']}: {country['share_2024']}")
    
    # Categorize by empire
    print("\n🌍 Categorizing by empire...")
    empire_data = categorize_by_empire(countries)
    
    print(f"\n📊 Empire Totals (Share 2024):")
    print(f"  • Empire 1 (Commonwealth): {empire_data['empire_1']['total']:.2f} ({empire_data['empire_1']['percent']:.1f}%)")
    print(f"  • Empire 2 (USA): {empire_data['empire_2']['total']:.2f} ({empire_data['empire_2']['percent']:.1f}%)")
    print(f"  • Empire 3 (China): {empire_data['empire_3']['total']:.2f} ({empire_data['empire_3']['percent']:.1f}%)")
    print(f"  • Total: {empire_data['total']:.2f}")
    
    # Show contributing countries
    print("\n🏅 Contributing countries:")
    
    if empire_data['empire_1']['countries']:
        print("\n  Empire 1 (Commonwealth):")
        for country, share in sorted(empire_data['empire_1']['countries'], key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {country}: {share:.2f}")
    
    if empire_data['empire_2']['countries']:
        print("\n  Empire 2 (USA):")
        for country, share in empire_data['empire_2']['countries']:
            print(f"    {country}: {share:.2f}")
    
    if empire_data['empire_3']['countries']:
        print("\n  Empire 3 (China):")
        for country, share in empire_data['empire_3']['countries']:
            print(f"    {country}: {share:.2f}")
    
    # Save to CSV
    if empire_data['total'] > 0:
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
, text):
                    share_value = parse_share_value(text)
                    break
        
        if country_name and share_value > 0:
            countries.append({
                'country': country_name,
                'share_2024': share_value
            })
    
    return countries


def parse_country_elements(elements):
    """Parse country data from various HTML elements."""
    countries = []
    
    for element in elements:
        text = element.get_text(strip=True)
        
        # Look for patterns like "United States 12345.67"
        # Country names can have spaces, numbers are the share value
        parts = text.split()
        
        if len(parts) >= 2:
            # Last part should be the number
            potential_share = parts[-1]
            share_value = parse_share_value(potential_share)
            
            if share_value > 0:
                # Everything before the last part is the country name
                country_name = ' '.join(parts[:-1])
                # Remove rank if present at the start
                country_name = re.sub(r'^\d+\.?\s*', '', country_name)
                
                if country_name:
                    countries.append({
                        'country': country_name,
                        'share_2024': share_value
                    })
    
    return countries


def normalize_country(country):
    """Normalize country names for empire categorization."""
    country = str(country).strip()
    
    # Exact matches
    country_map = {
        'United States of America': 'United States of America',
        'United States': 'United States of America',
        'USA': 'United States of America',
        'US': 'United States of America',
        'Hong Kong': 'Hong Kong (China)',
        'Hong Kong (China)': 'Hong Kong (China)',
        'Taiwan': 'Taiwan',
        'China': 'China',
    }
    
    if country in country_map:
        return country_map[country]
    
    return country


def categorize_by_empire(countries):
    """Categorize countries by empire and sum their Share 2024 values."""
    empire_1_total = 0.0
    empire_2_total = 0.0
    empire_3_total = 0.0
    
    empire_1_countries = []
    empire_2_countries = []
    empire_3_countries = []
    
    for country_data in countries:
        country = normalize_country(country_data['country'])
        share = country_data['share_2024']
        
        # Empire 3: China, Hong Kong, Taiwan
        if country in EMPIRE_3_COUNTRIES:
            empire_3_total += share
            empire_3_countries.append((country, share))
        # Empire 2: USA
        elif country in EMPIRE_2_COUNTRIES:
            empire_2_total += share
            empire_2_countries.append((country, share))
        # Empire 1: Commonwealth countries
        elif country in EMPIRE_1_COUNTRIES:
            empire_1_total += share
            empire_1_countries.append((country, share))
    
    total_all_empires = empire_1_total + empire_2_total + empire_3_total
    
    return {
        'empire_1': {
            'total': empire_1_total,
            'percent': (empire_1_total / total_all_empires * 100) if total_all_empires > 0 else 0,
            'countries': empire_1_countries
        },
        'empire_2': {
            'total': empire_2_total,
            'percent': (empire_2_total / total_all_empires * 100) if total_all_empires > 0 else 0,
            'countries': empire_2_countries
        },
        'empire_3': {
            'total': empire_3_total,
            'percent': (empire_3_total / total_all_empires * 100) if total_all_empires > 0 else 0,
            'countries': empire_3_countries
        },
        'total': total_all_empires
    }


def save_to_csv(empire_data, output_dir='data'):
    """Save empire nature share data to CSV file."""
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.join(output_dir, 'empire_nature_share.csv')
    
    # Remove existing file if it exists
    if os.path.exists(filename):
        os.remove(filename)
        print(f"♻️  Removed existing file: {filename}")
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['empire', 'share_2024', 'percent', 'date'])
        
        # Empire 1
        writer.writerow([
            '1',
            f"{empire_data['empire_1']['total']:.2f}",
            f"{empire_data['empire_1']['percent']:.1f}",
            current_date
        ])
        
        # Empire 2
        writer.writerow([
            '2',
            f"{empire_data['empire_2']['total']:.2f}",
            f"{empire_data['empire_2']['percent']:.1f}",
            current_date
        ])
        
        # Empire 3
        writer.writerow([
            '3',
            f"{empire_data['empire_3']['total']:.2f}",
            f"{empire_data['empire_3']['percent']:.1f}",
            current_date
        ])
    
    print(f"✓ Data saved to {filename}")
    return filename


def main():
    """Main scraper function."""
    print("=" * 60)
    print("Nature Index Empire Share Scraper")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Fetch data
    print("📡 Fetching country rankings data...")
    html_content = fetch_nature_index_countries()
    
    if not html_content:
        print("❌ Failed to fetch data.")
        return
    
    print(f"✓ Fetched {len(html_content)} characters")
    
    # Parse the page
    print("\n📊 Parsing country data...")
    countries = parse_country_rankings_page(html_content)
    
    if not countries:
        print("❌ No countries found.")
        print("💡 Check country_rankings_page.html to see the page structure.")
        return
    
    print(f"✓ Found {len(countries)} countries")
    
    # Show sample
    print("\n📋 Sample countries:")
    for country in countries[:5]:
        print(f"  {country['country']}: {country['share_2024']}")
    
    # Categorize by empire
    print("\n🌍 Categorizing by empire...")
    empire_data = categorize_by_empire(countries)
    
    print(f"\n📊 Empire Totals (Share 2024):")
    print(f"  • Empire 1 (Commonwealth): {empire_data['empire_1']['total']:.2f} ({empire_data['empire_1']['percent']:.1f}%)")
    print(f"  • Empire 2 (USA): {empire_data['empire_2']['total']:.2f} ({empire_data['empire_2']['percent']:.1f}%)")
    print(f"  • Empire 3 (China): {empire_data['empire_3']['total']:.2f} ({empire_data['empire_3']['percent']:.1f}%)")
    print(f"  • Total: {empire_data['total']:.2f}")
    
    # Show contributing countries
    print("\n🏅 Contributing countries:")
    
    if empire_data['empire_1']['countries']:
        print("\n  Empire 1 (Commonwealth):")
        for country, share in sorted(empire_data['empire_1']['countries'], key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {country}: {share:.2f}")
    
    if empire_data['empire_2']['countries']:
        print("\n  Empire 2 (USA):")
        for country, share in empire_data['empire_2']['countries']:
            print(f"    {country}: {share:.2f}")
    
    if empire_data['empire_3']['countries']:
        print("\n  Empire 3 (China):")
        for country, share in empire_data['empire_3']['countries']:
            print(f"    {country}: {share:.2f}")
    
    # Save to CSV
    if empire_data['total'] > 0:
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
