import pandas as pd
import os
from github import Github, Auth

# Configuration
CSV_INPUT = "countries_marketcap.csv"
CSV_OUTPUT = "empire_marketcap.csv"
REPO_NAME = "ayeeff/marketcap"
FILE_PATH = "data/empire_marketcap.csv"

# Load GitHub token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# British Commonwealth countries (Empire 1.0)
# Including all current and former British territories with significant markets
# NOTE: Hong Kong is excluded - it's now part of China (Empire 3.0)
COMMONWEALTH_COUNTRIES = [
    # Major economies
    'United Kingdom', 'UK', 'Great Britain',
    'Canada',
    'Australia',
    'India',
    'Singapore',
    
    # Other Commonwealth nations
    'New Zealand',
    'South Africa',
    'Malaysia',
    'Pakistan',
    'Bangladesh',
    'Sri Lanka',
    'Nigeria',
    'Kenya',
    'Ghana',
    'Jamaica',
    'Uganda',
    'Tanzania',
    'Zambia',
    'Malawi',
    'Cyprus',
    'Malta',
    'Mauritius',
    'Botswana',
    'Namibia',
    'Zimbabwe',
    
    # Caribbean
    'Barbados',
    'Trinidad and Tobago',
    
    # Pacific
    'Fiji',
    'Papua New Guinea'
]

def parse_market_cap(value):
    """Convert market cap string to numeric value"""
    if pd.isna(value) or value == '' or value == '-':
        return 0
    
    value = str(value).replace('$', '').replace(',', '').replace(' ', '').strip()
    multiplier = 1
    
    if 'T' in value.upper():
        multiplier = 1_000_000_000_000
        value = value.upper().replace('T', '').strip()
    elif 'B' in value.upper():
        multiplier = 1_000_000_000
        value = value.upper().replace('B', '').strip()
    elif 'M' in value.upper():
        multiplier = 1_000_000
        value = value.upper().replace('M', '').strip()
    
    try:
        return float(value) * multiplier
    except (ValueError, AttributeError):
        return 0

def format_market_cap(value):
    """Format numeric value as market cap string"""
    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f} T"
    elif value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f} B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f} M"
    return f"${value:.2f}"

print("Loading country market cap data...")
df = pd.read_csv(CSV_INPUT)

print(f"\nFirst 5 rows of raw data:")
print(df.head())
print(f"\nColumn dtypes:")
print(df.dtypes)

# Find the market cap column more specifically
market_cap_col = next((col for col in df.columns if 'total marketcap' in col.lower()), None)
country_col = next((col for col in df.columns if 'country' in col.lower()), None)

if not market_cap_col or not country_col:
    raise ValueError(f"Could not find required columns. Available: {list(df.columns)}")

print(f"\nUsing columns: {country_col}, {market_cap_col}")

# Show some sample values before parsing
print(f"\nSample market cap values (raw):")
for idx, row in df.head(5).iterrows():
    print(f"  {row[country_col]}: '{row[market_cap_col]}'")

# Convert market cap to numeric
df['MarketCapNumeric'] = df[market_cap_col].apply(parse_market_cap)

# Show parsed values
print(f"\nSample market cap values (parsed to numeric):")
for idx, row in df.head(5).iterrows():
    print(f"  {row[country_col]}: {row['MarketCapNumeric']:,.0f} -> {format_market_cap(row['MarketCapNumeric'])}")

# Normalize country names for matching (strip and lower)
df['CountryNormalized'] = df[country_col].str.strip().str.lower()
commonwealth_normalized = [c.strip().lower() for c in COMMONWEALTH_COUNTRIES]

# Calculate Empire totals
print(f"\nSearching for Commonwealth countries in dataset...")
print(f"Available countries in CSV: {sorted(df[country_col].unique())}\n")

empire_1_countries = df[df['CountryNormalized'].isin(commonwealth_normalized)].copy()
empire_1_total = empire_1_countries['MarketCapNumeric'].sum()
empire_1_count = len(empire_1_countries)

# Check for missing matches
found_countries = set(empire_1_countries[country_col].unique())
expected_countries = set(COMMONWEALTH_COUNTRIES)
missing_countries = expected_countries - found_countries
present_countries = expected_countries & found_countries

print(f"✓ Found {len(found_countries)} Commonwealth countries:")
for country in sorted(found_countries):
    mc = empire_1_countries[empire_1_countries[country_col] == country]['MarketCapNumeric'].sum()
    print(f"  - {country}: {format_market_cap(mc)}")

if missing_countries:
    print(f"\n⚠️ {len(missing_countries)} Commonwealth countries not found in dataset:")
    for country in sorted(missing_countries):
        print(f"  - {country}")

# Empire 2: United States (case insensitive)
us_mask = df['CountryNormalized'].str.contains('united states', na=False)
empire_2_countries = df[us_mask].copy()
empire_2_total = empire_2_countries['MarketCapNumeric'].sum()
empire_2_count = len(empire_2_countries)

# Empire 3: China + Hong Kong + Taiwan (case insensitive)
china_hk_tw_mask = df['CountryNormalized'].str.contains('china|hong kong|taiwan', na=False)
empire_3_countries = df[china_hk_tw_mask].copy()
empire_3_total = empire_3_countries['MarketCapNumeric'].sum()
empire_3_count = len(empire_3_countries)

print(f"\nEmpire 3.0 (China + Hong Kong + Taiwan):")
for country in empire_3_countries[country_col].unique():
    mc = empire_3_countries[empire_3_countries[country_col] == country]['MarketCapNumeric'].sum()
    print(f"  - {country}: {format_market_cap(mc)}")

# Calculate grand total
grand_total = empire_1_total + empire_2_total + empire_3_total
global_total = df['MarketCapNumeric'].sum()

# Calculate percentages
empire_1_percent = (empire_1_total / global_total * 100) if global_total > 0 else 0
empire_2_percent = (empire_2_total / global_total * 100) if global_total > 0 else 0
empire_3_percent = (empire_3_total / global_total * 100) if global_total > 0 else 0

# Calculate percentage of EMPIRE total (not global)
empire_1_empire_percent = (empire_1_total / grand_total * 100) if grand_total > 0 else 0
empire_2_empire_percent = (empire_2_total / grand_total * 100) if grand_total > 0 else 0
empire_3_empire_percent = (empire_3_total / grand_total * 100) if grand_total > 0 else 0

# Create empire dataframe (only top 3 empires, matching attached table)
empire_data = {
    'Rank': [1, 2, 3],
    'Empire': [
        'Empire 1.0: Steam & Colonies',
        'Empire 2.0: Oil & Silicon',
        'Empire 3.0: Rare Earths, Renewables & Robotics'
    ],
    'Description': [
        'British Commonwealth',
        'United States',
        'China + Hong Kong + Taiwan'
    ],
    'Total Market Cap': [
        format_market_cap(empire_1_total),
        format_market_cap(empire_2_total),
        format_market_cap(empire_3_total)
    ],
    'Countries': [
        empire_1_count,
        empire_2_count,
        empire_3_count
    ],
    '% of Global': [
        f"{empire_1_percent:.2f}%",
        f"{empire_2_percent:.2f}%",
        f"{empire_3_percent:.2f}%"
    ],
    '% of Empire Total': [
        f"{empire_1_empire_percent:.2f}%",
        f"{empire_2_empire_percent:.2f}%",
        f"{empire_3_empire_percent:.2f}%"
    ]
}

empire_df = pd.DataFrame(empire_data)

# Print summary
print("\n" + "="*80)
print("EMPIRE MARKET CAP ANALYSIS")
print("="*80)
print(empire_df.to_string(index=False))
print("\n" + "="*80)
print(f"\nEmpire 1.0 Countries ({empire_1_count}):")
print(empire_1_countries[[country_col, market_cap_col]].to_string(index=False))
print("="*80)

# Save to CSV
empire_df.to_csv(CSV_OUTPUT, index=False)
print(f"\n✓ Saved empire analysis to {CSV_OUTPUT}")

# Upload to GitHub if token available
if GITHUB_TOKEN:
    try:
        print("\nUploading to GitHub...")
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        repo = g.get_repo(REPO_NAME)
        
        with open(CSV_OUTPUT, "r", encoding="utf-8") as f:
            content = f.read()
        
        timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M UTC')
        commit_message = f"Update empire market cap analysis - {timestamp}"
        
        try:
            file = repo.get_contents(FILE_PATH)
            repo.update_file(FILE_PATH, commit_message, content, file.sha)
            print(f"✓ Updated {FILE_PATH} in GitHub repo.")
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                repo.create_file(FILE_PATH, commit_message, content)
                print(f"✓ Created {FILE_PATH} in GitHub repo.")
            else:
                raise e
        
        os.remove(CSV_OUTPUT)
        print("\n✅ Empire analysis uploaded successfully!")
        
    except Exception as e:
        print(f"\n⚠️ Could not upload to GitHub: {e}")
else:
    print("\n⚠️ No GitHub token found, skipping upload")
