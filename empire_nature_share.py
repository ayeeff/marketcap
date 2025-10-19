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


def fetch_data():
    """Fetch country rankings from Nature Index."""
    url = "https://www.nature.com/nature-index/research-leaders/2025/country/all/global"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        print(f"🌐 Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"✅ Status: {response.status_code}")
        return response.text
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def parse_html(html_content):
    """Parse HTML to extract country and Share 2024 data."""
    soup = BeautifulSoup(html_content, 'html.parser')
    countries = []
    
    # Save HTML for debugging
    with open('country_rankings_page.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("💾 Saved country_rankings_page.html for debugging")
    
    # Find all tables
    tables = soup.find_all('table')
    print(f"📊 Found {len(tables)} tables")
    
    for table in tables:
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
            
            # Extract text from cells
            texts = [cell.get_text(strip=True) for cell in cells]
            
            # Skip if first cell is not a number (header row)
            if not re.match(r'^\d+$', texts[0]):
                continue
            
            # Country should be in second cell, Share 2024 in third or fourth
            country = texts[1] if len(texts) > 1 else None
            share = 0.0
            
            # Try to find the Share 2024 value (should be a large number)
            for text in texts[2:]:
                # Remove commas and try to parse as float
                cleaned = text.replace(',', '')
                if re.match(r'^\d+\.?\d*$', cleaned):
                    try:
                        val = float(cleaned)
                        # Share 2024 values are typically > 10
                        if val > 10:
                            share = val
                            break
                    except ValueError:
                        continue
            
            if country and share > 0:
                countries.append({'country': country, 'share_2024': share})
    
    return countries


def normalize_country(country):
    """Normalize country name for empire matching."""
    # Remove parentheses content
    country = re.sub(r'\s*\([^)]*\)\s*', '', country).strip()
    
    # Map variations to standard names
    if 'United States' in country or 'USA' in country:
        return 'United States of America'
    if 'Hong Kong' in country:
        return 'Hong Kong (China)'
    if country in ['China', 'Taiwan']:
        return country
    
    return country


def categorize_by_empire(countries):
    """Sum Share 2024 values by empire."""
    empire_totals = {1: 0.0, 2: 0.0, 3: 0.0}
    empire_countries = {1: [], 2: [], 3: []}
    
    for data in countries:
        country = normalize_country(data['country'])
        share = data['share_2024']
        
        if country in EMPIRE_3_COUNTRIES:
            empire_totals[3] += share
            empire_countries[3].append((country, share))
        elif country in EMPIRE_2_COUNTRIES:
            empire_totals[2] += share
            empire_countries[2].append((country, share))
        elif country in EMPIRE_1_COUNTRIES:
            empire_totals[1] += share
            empire_countries[1].append((country, share))
    
    total = sum(empire_totals.values())
    
    return {
        'totals': empire_totals,
        'countries': empire_countries,
        'grand_total': total
    }


def save_to_csv(empire_data, output_dir='data'):
    """Save empire share data to CSV."""
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, 'empire_nature_share.csv')
    
    if os.path.exists(filename):
        os.remove(filename)
        print(f"♻️  Removed existing: {filename}")
    
    date = datetime.now().strftime('%Y-%m-%d')
    total = empire_data['grand_total']
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['empire', 'share_2024', 'percent', 'date'])
        
        for empire in [1, 2, 3]:
            share = empire_data['totals'][empire]
            percent = (share / total * 100) if total > 0 else 0
            writer.writerow([empire, f"{share:.2f}", f"{percent:.1f}", date])
    
    print(f"✓ Saved to {filename}")


def main():
    """Main function."""
    print("=" * 60)
    print("Nature Index Empire Share Scraper")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Fetch and parse
    html = fetch_data()
    if not html:
        print("❌ Failed to fetch data")
        return
    
    countries = parse_html(html)
    if not countries:
        print("❌ No countries found - check country_rankings_page.html")
        return
    
    print(f"✓ Found {len(countries)} countries\n")
    
    # Show sample
    print("📋 Sample data:")
    for c in countries[:3]:
        print(f"  {c['country']}: {c['share_2024']}")
    
    # Categorize
    empire_data = categorize_by_empire(countries)
    
    print(f"\n📊 Empire Totals:")
    for empire in [1, 2, 3]:
        total = empire_data['totals'][empire]
        percent = (total / empire_data['grand_total'] * 100) if empire_data['grand_total'] > 0 else 0
        print(f"  Empire {empire}: {total:.2f} ({percent:.1f}%)")
    
    # Show top contributors
    print(f"\n🏅 Top contributors per empire:")
    for empire in [1, 2, 3]:
        countries = sorted(empire_data['countries'][empire], key=lambda x: x[1], reverse=True)[:3]
        if countries:
            print(f"  Empire {empire}:")
            for country, share in countries:
                print(f"    {country}: {share:.2f}")
    
    # Save
    if empire_data['grand_total'] > 0:
        print(f"\n💾 Saving...")
        save_to_csv(empire_data)
        print("✅ Complete!")
    else:
        print("\n❌ No data to save")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
