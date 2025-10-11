import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from github import Github, Auth
import time

# Configuration
URL = "https://www.marketcapwatch.com/all-countries/"
REPO_NAME = "ayeeff/marketcap"
FILE_PATH = "data/countries_marketcap.csv"

# Load token from environment variable (provided by GitHub Actions)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Only validate if running locally (not in CI)
if not GITHUB_TOKEN and not os.getenv("CI"):
    raise ValueError(
        "GITHUB_TOKEN environment variable not set.\n"
        "Run: export GITHUB_TOKEN=your_token_here"
    )

if GITHUB_TOKEN:
    print("✓ GitHub token loaded successfully.")

# Selenium setup
chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-software-rasterizer')
chrome_options.add_argument('--remote-debugging-port=9222')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

print("Setting up ChromeDriver...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print(f"Loading page: {URL}")
    driver.get(URL)
    
    # Wait for JavaScript to load
    time.sleep(5)
    
    # Find table
    wait = WebDriverWait(driver, 20)
    tables = driver.find_elements(By.TAG_NAME, "table")
    
    if not tables:
        raise ValueError("No tables found on page")
    
    table = tables[0]
    print("✓ Table found!")
    
    # Extract table data
    rows = table.find_elements(By.TAG_NAME, "tr")
    data = []
    
    for row in rows:
        # Get both th and td elements
        cells_th = row.find_elements(By.TAG_NAME, "th")
        cells_td = row.find_elements(By.TAG_NAME, "td")
        all_cells = cells_th + cells_td
        
        # Extract text from cells
        cells = [cell.text.strip() for cell in all_cells]
        
        # Only add rows that have content
        if cells and any(cell for cell in cells):
            data.append(cells)
    
    if not data:
        raise ValueError("No data extracted from table")
    
    # Create DataFrame
    columns = data[0]
    df = pd.DataFrame(data[1:], columns=columns)
    
    # Clean up commas from numeric columns (like Total Companies: 6,784 -> 6784)
    for col in df.columns:
        if df[col].dtype == 'object':
            # Remove commas from values that contain digits
            df[col] = df[col].apply(lambda x: str(x).replace(',', '') if isinstance(x, str) and any(c.isdigit() for c in str(x)) else x)
    
    print(f"✓ Extracted {len(df)} rows of data.")
    print(f"\nPreview:\n{df.head()}")
    
    # Find the market cap column for percentage calculation
    market_cap_col = None
    for col in df.columns:
        if 'market' in col.lower() and 'cap' in col.lower():
            market_cap_col = col
            break
    
    # Add percentage of global market cap column
    def parse_market_cap(value):
        """Convert market cap string (e.g., '$68.89 T', '$1.5 B') to numeric value"""
        if pd.isna(value) or value == '' or value == '-':
            return 0
        
        # Remove dollar sign and spaces (commas already removed above)
        value = str(value).replace('$', '').replace(' ', '').strip()
        
        # Extract multiplier (T, B, M)
        multiplier = 1
        if 'T' in value.upper():
            multiplier = 1_000_000_000_000  # Trillion
            value = value.upper().replace('T', '').strip()
        elif 'B' in value.upper():
            multiplier = 1_000_000_000  # Billion
            value = value.upper().replace('B', '').strip()
        elif 'M' in value.upper():
            multiplier = 1_000_000  # Million
            value = value.upper().replace('M', '').strip()
        
        try:
            return float(value) * multiplier
        except (ValueError, AttributeError):
            return 0
    
    if market_cap_col:
        print(f"\nFound market cap column: '{market_cap_col}'")
        
        # Convert to numeric values for ALL countries
        df['Market Cap Numeric'] = df[market_cap_col].apply(parse_market_cap)
        
        # Calculate global total
        global_total = df['Market Cap Numeric'].sum()
        print(f"Global total market cap: ${global_total / 1_000_000_000_000:.2f}T")
        
        # Calculate percentage for EVERY country
        df['% of Global Market Cap'] = (df['Market Cap Numeric'] / global_total * 100).round(2)
        
        # Debug: Print first few percentages to verify
        print(f"\nSample percentages:")
        if 'Country or region' in df.columns:
            print(df[['Country or region', market_cap_col, '% of Global Market Cap']].head(10))
        else:
            print(df[[market_cap_col, '% of Global Market Cap']].head(10))
        
        # Remove the temporary numeric column
        df = df.drop(columns=['Market Cap Numeric'])
        
        print(f"\n✓ Added '% of Global Market Cap' column for all {len(df)} countries")
    else:
        print("\n⚠️ Warning: Could not find market cap column. Skipping percentage calculation.")
        print(f"Available columns: {list(df.columns)}")
    
    # Save locally
    local_csv = "countries_marketcap.csv"
    df.to_csv(local_csv, index=False)
    print(f"\n✓ Data saved to {local_csv}")
    
    # Generate treemap HTML with embedded data
    print("\nGenerating treemap visualization...")
    
    # Read the treemap template and embed data
    treemap_html_path = "treemap.html"
    if os.path.exists(treemap_html_path):
        # Treemap already exists with auto-load functionality
        print("✓ Treemap.html already exists")
    else:
        print("⚠️ treemap.html not found in repo, will be served from GitHub Pages")
    
    # Push to GitHub with proper authentication
    print("\nConnecting to GitHub...")
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)
    
    with open(local_csv, "r", encoding="utf-8") as f:
        content = f.read()
    
    timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M UTC')
    commit_message = f"Update countries market cap data - {timestamp}"
    
    # Upload CSV
    try:
        # Update existing file
        file = repo.get_contents(FILE_PATH)
        repo.update_file(FILE_PATH, commit_message, content, file.sha)
        print(f"✓ Updated {FILE_PATH} in GitHub repo.")
    except Exception as e:
        if "not found" in str(e).lower() or "404" in str(e):
            # Create new file
            repo.create_file(FILE_PATH, commit_message, content)
            print(f"✓ Created {FILE_PATH} in GitHub repo.")
        else:
            raise e
    
    # Upload treemap HTML if it exists
    treemap_path = "treemap.html"
    if os.path.exists(treemap_path):
        print("✓ Treemap will be accessible at: https://ayeeff.github.io/marketcap/treemap.html")
    
    # Cleanup
    os.remove(local_csv)
    print("\n✅ Script completed successfully!")

except Exception as e:
    print(f"\n❌ Error occurred: {e}")
    import traceback
    traceback.print_exc()
    raise e

finally:
    driver.quit()
    print("✓ Driver closed.")
