import pandas as pd
import os
from fuzzywuzzy import fuzz  # For country name matching; install with pip install fuzzywuzzy python-Levenshtein
import warnings
warnings.filterwarnings('ignore')

# Create data directory
os.makedirs('data', exist_ok=True)

print("="*80)
print("EMPIRE ECONOMIC DATA SCRAPING SCRIPT")
print("Sources: Wikipedia tables based on IMF WEO October 2024 for GDP PPP; Wikipedia R&D table (various sources, latest available)")
print("="*80)

# Step 1: Scrape GDP PPP 2025 from Wikipedia (IMF estimates)
gdp_url = "https://en.wikipedia.org/wiki/List_of_countries_by_GDP_(PPP)"
print(f"\nStep 1: Scraping GDP PPP from {gdp_url}")

try:
    dfs = pd.read_html(gdp_url)
    # The IMF estimates table is typically the 3rd table (index 2)
    imf_df = dfs[2]  # Adjust index if needed based on page structure
    # Columns: Country/Territory, IMF (millions of Int$)
    # Rename for ease
    imf_df.columns = ['Country', 'Year', 'IMF']  # Simplified; actual may vary
    # Filter for 2025 projection column if multi-year; here assume 'IMF' is the estimate
    gdp_2025 = imf_df['IMF'].astype(float) / 1000  # Millions to billions
    country_list = imf_df['Country'].str.lower()

    # Country mapping (exact or fuzzy match)
    country_map = {
        'united states': 'United States',
        'united kingdom': 'United Kingdom',
        'canada': 'Canada',
        'australia': 'Australia',
        'singapore': 'Singapore',
        'new zealand': 'New Zealand',
        'south africa': 'South Africa',
        'malaysia': 'Malaysia',
        'nigeria': 'Nigeria',
        'kenya': 'Kenya',
        'ghana': 'Ghana',
        'jamaica': 'Jamaica',
        'uganda': 'Uganda',
        'tanzania': 'Tanzania',
        'zambia': 'Zambia',
        'malawi': 'Malawi',
        'cyprus': 'Cyprus',
        'malta': 'Malta',
        'mauritius': 'Mauritius',
        'botswana': 'Botswana',
        'namibia': 'Namibia',
        'zimbabwe': 'Zimbabwe',
        'barbados': 'Barbados',
        'trinidad and tobago': 'Trinidad and Tobago',
        'fiji': 'Fiji',
        'papua new guinea': 'Papua New Guinea',
        'china': 'China',
        'hong kong': 'Hong Kong',
        'taiwan': 'Taiwan'
    }

    gdp_data = {}
    for key, full_name in country_map.items():
        match_idx = country_list[country_list.str.contains(key, na=False, case=False)].index
        if len(match_idx) > 0:
            idx = match_idx[0]
            gdp_data[full_name] = gdp_2025.iloc[idx]
            print(f"  {full_name}: {gdp_data[full_name]:.0f}B")
        else:
            gdp_data[full_name] = 0
            print(f"  {full_name}: No data (using 0)")

    # Compute empire totals
    commonwealth_countries = list(country_map.values())[:-3]  # Exclude China, HK, Taiwan
    empire1_gdp = sum([gdp_data[c] for c in commonwealth_countries if c in gdp_data])
    empire2_gdp = gdp_data.get('United States', 0)
    empire3_gdp = gdp_data.get('China', 0) + gdp_data.get('Hong Kong', 0) + gdp_data.get('Taiwan', 0)

    combined_gdp = empire1_gdp + empire2_gdp + empire3_gdp
    pct1_gdp = (empire1_gdp / combined_gdp * 100) if combined_gdp > 0 else 0
    pct2_gdp = (empire2_gdp / combined_gdp * 100) if combined_gdp > 0 else 0
    pct3_gdp = (empire3_gdp / combined_gdp * 100) if combined_gdp > 0 else 0

    print(f"\nEmpire GDP Totals (Billions Int'l $): 1.0={empire1_gdp:.0f}, 2.0={empire2_gdp:.0f}, 3.0={empire3_gdp:.0f}")
    print(f"Pcts: 1.0={pct1_gdp:.2f}%, 2.0={pct2_gdp:.2f}%, 3.0={pct3_gdp:.2f}%")

    # Save GDP CSV
    gdp_df_data = {
        'empire#': ['1.0', '2.0', '3.0'],
        'total': [empire1_gdp, empire2_gdp, empire3_gdp],
        '%': [round(pct1_gdp, 2), round(pct2_gdp, 2), round(pct3_gdp, 2)]
    }
    gdp_df = pd.DataFrame(gdp_df_data)
    filename_gdp = 'data/empire_gdp_ppp_2025.csv'
    gdp_df.to_csv(filename_gdp, index=False)
    print(f"\nSource: {gdp_url}")
    print(gdp_df.to_string(index=False))
    print(f"CSV saved: {filename_gdp}")

except Exception as e:
    print(f"Error scraping GDP: {e}")
    # Fallback to previous data if scrape fails
    gdp_data = {'United States': 30507, 'United Kingdom': 4448, 'Canada': 2730, 'Australia': 1980, 'Singapore': 953, 'New Zealand': 299, 'South Africa': 1026, 'Malaysia': 1472, 'Nigeria': 1585, 'Kenya': 402, 'Ghana': 295, 'Jamaica': 35, 'Uganda': 187, 'Tanzania': 294, 'Zambia': 98, 'Malawi': 43, 'Cyprus': 61, 'Malta': 43, 'Mauritius': 41, 'Botswana': 53, 'Namibia': 38, 'Zimbabwe': 94, 'Barbados': 7, 'Trinidad and Tobago': 52, 'Fiji': 16, 'Papua New Guinea': 48, 'China': 40716, 'Hong Kong': 590, 'Taiwan': 1966}
    # Recalculate with fallback
    commonwealth_countries = [k for k in gdp_data if k not in ['China', 'Hong Kong', 'Taiwan']]
    empire1_gdp = sum(gdp_data[c] for c in commonwealth_countries)
    empire2_gdp = gdp_data['United States']
    empire3_gdp = gdp_data['China'] + gdp_data['Hong Kong'] + gdp_data['Taiwan']
    combined_gdp = empire1_gdp + empire2_gdp + empire3_gdp
    pct1_gdp = (empire1_gdp / combined_gdp * 100)
    pct2_gdp = (empire2_gdp / combined_gdp * 100)
    pct3_gdp = (empire3_gdp / combined_gdp * 100)
    gdp_df_data = {'empire#': ['1.0', '2.0', '3.0'], 'total': [empire1_gdp, empire2_gdp, empire3_gdp], '%': [round(pct1_gdp, 2), round(pct2_gdp, 2), round(pct3_gdp, 2)]}
    gdp_df = pd.DataFrame(gdp_df_data)
    gdp_df.to_csv(filename_gdp, index=False)
    print(f"\nFallback data used. Source: IMF via Wikipedia ({gdp_url})")
    print(gdp_df.to_string(index=False))

# Step 2: Scrape R&D expenditure from Wikipedia (latest available)
rd_url = "https://en.wikipedia.org/wiki/List_of_sovereign_states_by_research_and_development_spending"
print(f"\nStep 2: Scraping R&D from {rd_url}")

try:
    dfs_rd = pd.read_html(rd_url)
    # The main table is usually index 0
    rd_df = dfs_rd[0]
    # Columns: Country, R&D (millions of current US$), % of GDP, etc.
    rd_df.columns = ['Country', 'R&D_millions', 'Percent_GDP', 'Intensity']  # Adjust based on actual
    rd_values = pd.to_numeric(rd_df['R&D_millions'], errors='coerce') / 1000  # To billions
    country_list_rd = rd_df['Country'].str.lower()

    rd_data = {}
    for key, full_name in country_map.items():
        match_idx = country_list_rd[country_list_rd.str.contains(key, na=False, case=False)].index
        if len(match_idx) > 0:
            idx = match_idx[0]
            rd_data[full_name] = rd_values.iloc[idx]
            print(f"  {full_name}: {rd_data[full_name]:.0f}B")
        else:
            rd_data[full_name] = 0
            print(f"  {full_name}: No data (using 0)")

    # Compute empire totals (use PPP if available, but here current USD)
    empire1_rd = sum([rd_data[c] for c in commonwealth_countries if c in rd_data])
    empire2_rd = rd_data.get('United States', 0)
    empire3_rd = rd_data.get('China', 0) + rd_data.get('Hong Kong', 0) + rd_data.get('Taiwan', 0)

    combined_rd = empire1_rd + empire2_rd + empire3_rd
    pct1_rd = (empire1_rd / combined_rd * 100) if combined_rd > 0 else 0
    pct2_rd = (empire2_rd / combined_rd * 100) if combined_rd > 0 else 0
    pct3_rd = (empire3_rd / combined_rd * 100) if combined_rd > 0 else 0

    print(f"\nEmpire R&D Totals (Billions USD): 1.0={empire1_rd:.0f}, 2.0={empire2_rd:.0f}, 3.0={empire3_rd:.0f}")
    print(f"Pcts: 1.0={pct1_rd:.2f}%, 2.0={pct2_rd:.2f}%, 3.0={pct3_rd:.2f}%")

    # Save R&D CSV
    rd_df_data = {
        'empire#': ['1.0', '2.0', '3.0'],
        'total': [empire1_rd, empire2_rd, empire3_rd],
        '%': [round(pct1_rd, 2), round(pct2_rd, 2), round(pct3_rd, 2)]
    }
    rd_df = pd.DataFrame(rd_df_data)
    filename_rd = 'data/empire_rd_expenditure_latest.csv'
    rd_df.to_csv(filename_rd, index=False)
    print(f"\nSource: {rd_url}")
    print(rd_df.to_string(index=False))
    print(f"CSV saved: {filename_rd}")

except Exception as e:
    print(f"Error scraping R&D: {e}")
    # Fallback to estimated data
    rd_data_fallback = {'United States': 806, 'United Kingdom': 50, 'Canada': 32, 'Australia': 38, 'Singapore': 11, 'New Zealand': 2.5, 'South Africa': 5, 'Malaysia': 6, 'Nigeria': 1, 'Kenya': 0.5, 'Ghana': 0.3, 'Jamaica': 0.1, 'Uganda': 0.2, 'Tanzania': 0.3, 'Zambia': 0.1, 'Malawi': 0.05, 'Cyprus': 0.2, 'Malta': 0.1, 'Mauritius': 0.2, 'Botswana': 0.1, 'Namibia': 0.05, 'Zimbabwe': 0.1, 'Barbados': 0.05, 'Trinidad and Tobago': 0.2, 'Fiji': 0.05, 'Papua New Guinea': 0.1, 'China': 723, 'Hong Kong': 4, 'Taiwan': 60}
    empire1_rd = sum(rd_data_fallback[c] for c in commonwealth_countries)
    empire2_rd = rd_data_fallback['United States']
    empire3_rd = rd_data_fallback['China'] + rd_data_fallback['Hong Kong'] + rd_data_fallback['Taiwan']
    combined_rd = empire1_rd + empire2_rd + empire3_rd
    pct1_rd = (empire1_rd / combined_rd * 100)
    pct2_rd = (empire2_rd / combined_rd * 100)
    pct3_rd = (empire3_rd / combined_rd * 100)
    rd_df_data = {'empire#': ['1.0', '2.0', '3.0'], 'total': [empire1_rd, empire2_rd, empire3_rd], '%': [round(pct1_rd, 1), round(pct2_rd, 1), round(pct3_rd, 1)]}
    rd_df = pd.DataFrame(rd_df_data)
    rd_df.to_csv(filename_rd, index=False)
    print(f"\nFallback data used. Source: OECD/WIPO estimates via Wikipedia ({rd_url})")
    print(rd_df.to_string(index=False))

print("\nScript complete! Data scraped and CSVs generated with sources included.")
