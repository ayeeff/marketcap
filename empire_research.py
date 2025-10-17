"""
Empire Research Scraper
Fetches Nature Index research leader data and categorizes by empires
"""
import requests
from bs4 import BeautifulSoup
import csv
import os
from datetime import datetime
import time

EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa',
    'Nigeria', 'Ghana', 'Kenya', 'Uganda', 'Tanzania', 'Zambia', 'Malawi',
    'Botswana', 'Namibia', 'Lesotho', 'Eswatini', 'Jamaica', 'Trinidad and Tobago',
    'Barbados', 'Bahamas', 'Belize', 'Guyana', 'Saint Lucia', 'Grenada',
    'Saint Vincent and the Grenadines', 'Antigua and Barbuda', 'Dominica',
    'Saint Kitts and Nevis', 'Cyprus', 'Malta', 'Singapore', 'Malaysia',
    'Brunei', 'Bangladesh', 'Sri Lanka', 'Maldives'
}

EMPIRE_2_COUNTRIES = {'United States'}

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


def parse_institutions(html_content):
    """Parse HTML content to extract institution rankings."""
    soup = BeautifulSoup(html_content, 'html.parser')
    institutions = []
    
    # This is a placeholder parser - you'll need to adjust selectors based on actual HTML structure
    # Nature Index pages often use JavaScript to load data, so you may need Selenium or API access
    
    # Try to find table or list elements containing institution data
    # Common selectors for Nature Index (adjust as needed):
    rows = soup.find_all(['tr', 'div'], class_=['institution-row', 'data-row'])
    
    for row in rows:
        try:
            # Extract institution name, country, and rank
            # These selectors are examples - adjust based on actual HTML
            name_elem = row.find(['td', 'div'], class_=['name', 'institution-name'])
            country_elem = row.find(['td', 'div'], class_=['country', 'location'])
            rank_elem = row.find(['td', 'div'], class_=['rank', 'ranking'])
            
            if name_elem and country_elem:
                institution = {
                    'rank': len(institutions) + 1,  # Fallback ranking
                    'name': name_elem.get_text(strip=True),
                    'country': country_elem.get_text(strip=True)
                }
                
                if rank_elem:
                    institution['rank'] = int(rank_elem.get_text(strip=True))
                
                institutions.append(institution)
        except Exception as e:
            print(f"Error parsing row: {e}")
            continue
    
    return institutions


def categorize_by_empire(institutions):
    """Categorize institutions by empire and get top 10 for each."""
    empire_1 = []
    empire_2 = []
    empire_3 = []
    
    for inst in institutions:
        country = inst['country']
        
        if country in EMPIRE_1_COUNTRIES:
            empire_1.append(inst)
        elif country in EMPIRE_2_COUNTRIES:
            empire_2.append(inst)
        elif country in EMPIRE_3_COUNTRIES:
            empire_3.append(inst)
    
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
    filename = os.path.join(output_dir, f'nature_index_empires_{timestamp}.csv')
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['Empire', 'Rank', 'Institution', 'Country', 'Global_Rank'])
        
        # Write Empire 1 (Commonwealth & former British territories)
        for inst in empire_data['empire_1']:
            writer.writerow([
                'Empire_1_Commonwealth',
                empire_data['empire_1'].index(inst) + 1,
                inst['name'],
                inst['country'],
                inst['rank']
            ])
        
        # Write Empire 2 (United States)
        for inst in empire_data['empire_2']:
            writer.writerow([
                'Empire_2_USA',
                empire_data['empire_2'].index(inst) + 1,
                inst['name'],
                inst['country'],
                inst['rank']
            ])
        
        # Write Empire 3 (China/Hong Kong/Taiwan)
        for inst in empire_data['empire_3']:
            writer.writerow([
                'Empire_3_China',
                empire_data['empire_3'].index(inst) + 1,
                inst['name'],
                inst['country'],
                inst['rank']
            ])
    
    print(f"Data saved to {filename}")
    return filename


def main():
    """Main scraper function."""
    print("Starting Nature Index scraper...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Fetch data
    html_content = fetch_nature_index_data()
    if not html_content:
        print("Failed to fetch data. Exiting.")
        return
    
    # Parse institutions
    print("Parsing institution data...")
    institutions = parse_institutions(html_content)
    
    if not institutions:
        print("No institutions found. The page structure may have changed.")
        print("Consider using Selenium for JavaScript-rendered content or Nature Index API.")
        return
    
    print(f"Found {len(institutions)} institutions")
    
    # Categorize by empire
    print("Categorizing by empire...")
    empire_data = categorize_by_empire(institutions)
    
    print(f"Empire 1 (Commonwealth): {len(empire_data['empire_1'])} institutions")
    print(f"Empire 2 (USA): {len(empire_data['empire_2'])} institutions")
    print(f"Empire 3 (China): {len(empire_data['empire_3'])} institutions")
    
    # Save to CSV
    save_to_csv(empire_data)
    
    print("Scraping complete!")


if __name__ == "__main__":
    main()
