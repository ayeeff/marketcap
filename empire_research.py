"""
Empire Research Scraper - Selenium Version
Uses Selenium to handle JavaScript-rendered content
"""
import csv
import os
import re
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

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


def setup_selenium_driver():
    """Set up Selenium WebDriver with appropriate options."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def fetch_with_selenium():
    """Fetch Nature Index data using Selenium to handle JavaScript rendering."""
    driver = setup_selenium_driver()
    
    urls = [
        "https://www.nature.com/nature-index/institution-outputs",
        "https://www.nature-index.com/institution-outputs",
        "https://www.nature.com/nature-index/annual-tables/2024/institution/all/all",
    ]
    
    for url in urls:
        print(f"🌐 Loading: {url}")
        try:
            driver.get(url)
            
            # Wait for the page to load and for institution data to appear
            wait = WebDriverWait(driver, 20)
            
            # Try different selectors for the data table
            selectors = [
                "table",
                "[data-test='institution-table']",
                ".institution-table",
                ".ranking-table",
                "tbody tr",
            ]
            
            for selector in selectors:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    print(f"✅ Found elements with selector: {selector}")
                    
                    # Check if we have actual data rows
                    rows = driver.find_elements(By.CSS_SELECTOR, f"{selector} tr")
                    if len(rows) > 5:  # If we have more than 5 rows, likely real data
                        print(f"✅ Found {len(rows)} rows with data")
                        return driver.page_source
                except:
                    continue
            
            # If no table found, wait a bit and check page content
            time.sleep(5)
            page_source = driver.page_source
            
            # Check if page contains institution names we'd expect
            if any(inst in page_source for inst in ['Harvard', 'Stanford', 'MIT', 'Cambridge', 'Oxford', 'Chinese Academy']):
                print("✅ Page contains expected institution names")
                return page_source
                
        except Exception as e:
            print(f"❌ Error loading {url}: {e}")
            continue
    
    driver.quit()
    return None


def parse_selenium_content(html_content):
    """Parse the rendered HTML content from Selenium."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    institutions = []
    
    print("🔍 Parsing rendered page content...")
    
    # Save the rendered HTML for inspection
    with open('rendered_page.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("💾 Saved rendered_page.html for inspection")
    
    # Method 1: Look for tables with institution data
    tables = soup.find_all('table')
    print(f"📊 Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        print(f"  Table {i+1}: {len(rows)} rows")
        
        for row in rows:
            # Skip header rows
            if row.find('th'):
                continue
                
            cells = row.find_all(['td', 'div'])
            cell_texts = [cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True)]
            
            if len(cell_texts) >= 2:
                # Try to extract rank from first cell
                rank_text = cell_texts[0]
                rank_match = re.search(r'(\d+)', rank_text)
                if rank_match:
                    rank = int(rank_match.group(1))
                    
                    # The institution name and country are likely in the next cells
                    # Look for pattern: "Institution Name, Country"
                    for text in cell_texts[1:]:
                        name_country_match = re.search(r'(.+?),\s*(.+)', text)
                        if name_country_match:
                            name = name_country_match.group(1).strip()
                            country = name_country_match.group(2).strip()
                            
                            institutions.append({
                                'rank': rank,
                                'name': name,
                                'country': country
                            })
                            break
    
    if institutions:
        print(f"✅ Found {len(institutions)} institutions from tables")
        return institutions
    
    # Method 2: Look for institution elements with specific classes
    institution_elements = soup.find_all(lambda tag: 
        tag.get('class') and 
        any(cls in str(tag.get('class')).lower() for cls in ['institution', 'ranking', 'row']) and
        tag.get_text(strip=True)
    )
    
    if institution_elements:
        print(f"🔍 Found {len(institution_elements)} potential institution elements")
        
        for element in institution_elements[:20]:  # Check first 20
            text = element.get_text(strip=True)
            # Look for pattern: "1. Harvard University, United States"
            pattern = r'(\d+)\.?\s+(.+?),\s*(.+)'
            match = re.search(pattern, text)
            if match:
                institutions.append({
                    'rank': int(match.group(1)),
                    'name': match.group(2).strip(),
                    'country': match.group(3).strip()
                })
    
    if institutions:
        print(f"✅ Found {len(institutions)} institutions from elements")
        return institutions
    
    # Method 3: Extract from any visible text on page
    body_text = soup.get_text()
    institutions = extract_institutions_from_text(body_text)
    
    if institutions:
        print(f"✅ Found {len(institutions)} institutions from text")
        return institutions
    
    return []


def extract_institutions_from_text(text):
    """Extract institutions from page text using regex patterns."""
    institutions = []
    
    # Common patterns in rankings
    patterns = [
        r'(\d+)\.?\s*([^,\n]+?),\s*([^\n\(\)]+?)(?:\s+\([^\)]*\))?\s*\n',
        r'^(\d+)\s+([^,\n]+?),\s*([^\n\(\)]+?)(?:\s+\([^\)]*\))?$',
        r'rank["\']?\s*:\s*["\']?(\d+)["\']?[^}]*?name["\']?\s*:\s*["\']?(.+?)["\']?[^}]*?country["\']?\s*:\s*["\']?(.+?)["\']?',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            if len(match) == 3:
                try:
                    institutions.append({
                        'rank': int(match[0]),
                        'name': match[1].strip(),
                        'country': match[2].strip()
                    })
                except:
                    continue
    
    return institutions


def try_alternative_approach():
    """
    Alternative approach: Use requests to mimic API calls or try different endpoints.
    This is a simplified version that might work if we can find the right endpoint.
    """
    import requests
    
    # Try the Nature Index API directly
    api_urls = [
        "https://www.nature.com/nature-index/api/index/2024/institution/all/all/global",
        "https://www.nature-index.com/api/index/2024/institution/all/all/global",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    
    for url in api_urls:
        print(f"🔧 Trying API endpoint: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API returned data with keys: {list(data.keys())}")
                return data
        except Exception as e:
            print(f"❌ API error: {e}")
    
    return None


def parse_api_data(api_data):
    """Parse institution data from API response."""
    institutions = []
    
    # Navigate through common API structures
    if 'data' in api_data and 'institutions' in api_data['data']:
        institutions_data = api_data['data']['institutions']
    elif 'institutions' in api_data:
        institutions_data = api_data['institutions']
    elif 'results' in api_data:
        institutions_data = api_data['results']
    else:
        print("❌ Could not find institution data in API response")
        return []
    
    print(f"📊 Processing {len(institutions_data)} institutions from API")
    
    for inst_data in institutions_data:
        try:
            # Extract information based on common field names
            rank = inst_data.get('rank') or inst_data.get('position') or inst_data.get('ranking')
            name = inst_data.get('name') or inst_data.get('institutionName') or inst_data.get('institution')
            country = inst_data.get('country') or inst_data.get('countryName') or inst_data.get('location')
            
            if rank and name and country:
                # Handle case where name might be a dictionary
                if isinstance(name, dict):
                    name = name.get('name', 'Unknown')
                
                institutions.append({
                    'rank': int(rank),
                    'name': str(name),
                    'country': str(country)
                })
        except Exception as e:
            print(f"⚠️  Error parsing institution: {e}")
            continue
    
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
    if any(us in country for us in ['United States', 'USA', 'U.S.']):
        return 'United States of America'
    elif any(uk in country for uk in ['United Kingdom', 'UK', 'U.K.']):
        return 'United Kingdom'
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


def main():
    """Main scraper function."""
    print("=" * 60)
    print("Nature Index Empire Research Scraper - Selenium Version")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    institutions = []
    
    # First try the API approach (simpler and faster)
    print("🔧 Attempting API approach...")
    api_data = try_alternative_approach()
    if api_data:
        institutions = parse_api_data(api_data)
    
    # If API approach failed, use Selenium
    if not institutions:
        print("\n🚀 API approach failed, trying Selenium...")
        print("📡 Loading page with Selenium (this may take a moment)...")
        html_content = fetch_with_selenium()
        
        if html_content:
            print("\n📊 Parsing rendered content...")
            institutions = parse_selenium_content(html_content)
        else:
            print("❌ Failed to load page with Selenium")
            return
    
    if not institutions:
        print("❌ No institutions found with any method.")
        print("💡 Check rendered_page.html to see what was actually loaded.")
        return
    
    print(f"✅ Successfully found {len(institutions)} institutions")
    
    # Show sample of found institutions
    print("\n📋 Sample of found institutions:")
    for inst in institutions[:10]:
        print(f"  #{inst['rank']}: {inst['name']} - {inst['country']}")
    
    # Categorize by empire
    print("\n🌍 Categorizing by empire...")
    empire_data = categorize_by_empire(institutions)
    
    print(f"  • Empire 1 (Commonwealth): {len(empire_data['empire_1'])} institutions")
    print(f"  • Empire 2 (USA): {len(empire_data['empire_2'])} institutions")
    print(f"  • Empire 3 (China): {len(empire_data['empire_3'])} institutions")
    
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
    
    # Save to CSV
    if any(empire_data.values()):
        print("\n💾 Saving to CSV...")
        save_to_csv(empire_data)
        print("✅ Success! Data has been saved.")
    else:
        print("\n❌ No data to save - no institutions matched empire categories")
    
    print("\n" + "=" * 60)
    print("Scraping complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
