import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import time

# Empire country mappings
EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa', 
    'Nigeria', 'Ghana', 'Kenya', 'Uganda', 'Tanzania', 'Zambia', 'Malawi', 
    'Botswana', 'Namibia', 'Jamaica', 'Singapore', 'Malaysia', 
    'Bangladesh', 'Sri Lanka'
}
EMPIRE_2_COUNTRIES = {'United States'}
EMPIRE_3_COUNTRIES = {'China', 'Hong Kong', 'Taiwan'}

def get_empire_number(country):
    """Determine which empire a country belongs to"""
    if country in EMPIRE_1_COUNTRIES:
        return 1
    elif country in EMPIRE_2_COUNTRIES:
        return 2
    elif country in EMPIRE_3_COUNTRIES:
        return 3
    return None

def scrape_world_cities():
    """Scrape city population data from World Population Review"""
    url = "https://worldpopulationreview.com/cities"
    
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the main table
        table = soup.find('table')
        if not table:
            raise ValueError("No table found on the page")
        
        cities_data = []
        rows = table.find_all('tr')[1:]  # Skip header
        
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 7:  # Full row with 7 columns (flag, rank, city, country, 2025 pop, 2024 pop, change)
                try:
                    # cols[0]: flag, cols[1]: rank, cols[2]: city, cols[3]: country, cols[4]: 2025 pop
                    city = cols[2].get_text(strip=True)  # City in third column (index 2)
                    country = cols[3].get_text(strip=True)  # Country in fourth column (index 3)
                    pop_text = cols[4].get_text(strip=True)  # 2025 Pop in fifth column (index 4)
                    
                    # Clean population text (remove commas)
                    population = int(pop_text.replace(',', ''))
                    
                    empire = get_empire_number(country)
                    if empire:
                        cities_data.append({
                            'Empire': empire,
                            'City': city,
                            'Country': country,
                            'Population': population
                        })
                except (ValueError, IndexError):
                    continue
        
        return cities_data
    
    except Exception as e:
        print(f"Error scraping data: {e}")
        return []

def get_top_cities_per_empire(cities_data, n=10):
    """Get top N cities for each empire"""
    df = pd.DataFrame(cities_data)
    
    result = []
    for empire in [1, 2, 3]:
        empire_cities = df[df['Empire'] == empire].nlargest(n, 'Population')
        empire_cities['Rank'] = range(1, len(empire_cities) + 1)
        result.append(empire_cities)
    
    return pd.concat(result, ignore_index=True)

def save_to_csv(df, output_dir='data'):
    """Save data to CSV file"""
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.join(output_dir, 'empire_cities_population.csv')
    
    # Add scraped date for versioning
    df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Reorder columns
    df = df[['Empire', 'Rank', 'City', 'Country', 'Population', 'Scraped_Date']]
    df.to_csv(filename, index=False)
    
    print(f"Data saved to {filename}")
    return filename

def main():
    print("Starting city population scraper (World Population Review)...")
    
    # Scrape primary source
    cities_data = scrape_world_cities()
    
    if not cities_data:
        print("Failed to scrape data")
        return
    
    print(f"Scraped data for {len(cities_data)} cities")
    
    # Get top 10 per empire
    top_cities_df = get_top_cities_per_empire(cities_data, n=10)
    
    # Display summary
    print("\nSummary by Empire:")
    print(top_cities_df.groupby('Empire').size())
    
    print("\nTop cities preview:")
    print(top_cities_df.head())
    
    # Save to CSV
    save_to_csv(top_cities_df)
    
    print("\nScraping completed successfully!")

if __name__ == "__main__":
    main()
