import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from github import Github
import time

# Configuration
URL = "https://www.marketcapwatch.com/all-countries/"
REPO_NAME = "ayeeff/marketcap"
FILE_PATH = "data/countries_marketcap.csv"

# SECURE: Load token from environment variable
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Validate token
if not GITHUB_TOKEN:
    raise ValueError(
        "GITHUB_TOKEN environment variable not set.\n"
        "Run: export GITHUB_TOKEN=your_token_here\n"
        "Or in Codespaces: Add to repository secrets"
    )

print("✓ GitHub token loaded successfully.")

# Selenium setup with Chrome
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

print("Setting up ChromeDriver...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print(f"Loading page: {URL}")
    driver.get(URL)
    
    # Wait longer for JavaScript to execute
    print("Waiting for page to fully load...")
    time.sleep(5)
    
    # Try multiple table selectors
    wait = WebDriverWait(driver, 20)
    
    # Debug: Print page title and URL
    print(f"Page title: {driver.title}")
    print(f"Current URL: {driver.current_url}")
    
    # Debug: Check if there are any tables
    tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"\nFound {len(tables)} table(s) on page")
    
    if not tables:
        # Try finding by common class names
        print("\nNo <table> tags found. Checking for common data containers...")
        divs = driver.find_elements(By.CSS_SELECTOR, "div[class*='table'], div[id*='table']")
        print(f"Found {len(divs)} div elements with 'table' in class/id")
        
        # Save page source for debugging
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Saved page source to page_source.html for inspection")
        raise ValueError("No tables found on page")
    
    # Use the first table
    table = tables[0]
    print("✓ Using first table found")
    
    # Debug: Print table HTML structure (first 500 chars)
    print(f"\nTable HTML preview:\n{table.get_attribute('outerHTML')[:500]}...")
    
    # Extract table data - try different methods
    rows = table.find_elements(By.TAG_NAME, "tr")
    print(f"\nFound {len(rows)} rows in table")
    
    if len(rows) == 0:
        raise ValueError("Table found but contains 0 rows")
    
    data = []
    for i, row in enumerate(rows[:5]):  # Debug: show first 5 rows
        # Try both th and td
        cells_th = row.find_elements(By.TAG_NAME, "th")
        cells_td = row.find_elements(By.TAG_NAME, "td")
        
        print(f"\nRow {i}: {len(cells_th)} <th> cells, {len(cells_td)} <td> cells")
        
        # Combine both
        all_cells = cells_th + cells_td
        cells = [cell.text.strip() for cell in all_cells]
        
        if cells:
            print(f"  Content: {cells}")
            data.append(cells)
    
    # Now extract all rows
    data = []
    for row in rows:
        cells_th = row.find_elements(By.TAG_NAME, "th")
        cells_td = row.find_elements(By.TAG_NAME, "td")
        all_cells = cells_th + cells_td
        cells = [cell.text.strip() for cell in all_cells]
        if cells and any(cell for cell in cells):  # Skip completely empty rows
            data.append(cells)
    
    print(f"\nTotal rows with data: {len(data)}")
    
    if not data:
        # Save screenshot for debugging
        driver.save_screenshot("screenshot.png")
        print("Saved screenshot to screenshot.png")
        raise ValueError("No table data found. Check the table selector.")
    
    # Create DataFrame
    columns = data[0]
    df = pd.DataFrame(data[1:], columns=columns)
    print(f"✓ Extracted {len(df)} rows of data.")
    print(f"\nColumn names: {list(df.columns)}")
    print(f"\nFirst few rows:\n{df.head()}")
    
    # Save locally (temporary)
    local_csv = "countries_marketcap.csv"
    df.to_csv(local_csv, index=False)
    print(f"\n✓ Data saved to {local_csv}")
    
    # Push to GitHub
    print("\nConnecting to GitHub...")
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    with open(local_csv, "r", encoding="utf-8") as f:
        content = f.read()
    
    try:
        # Try to update existing file
        file = repo.get_contents(FILE_PATH)
        repo.update_file(
            FILE_PATH, 
            f"Update countries market cap data - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}", 
            content, 
            file.sha
        )
        print(f"✓ Updated {FILE_PATH} in GitHub repo.")
    except Exception as e:
        if "not found" in str(e).lower():
            # Create new file if it doesn't exist
            repo.create_file(
                FILE_PATH, 
                "Add countries market cap data", 
                content
            )
            print(f"✓ Created {FILE_PATH} in GitHub repo.")
        else:
            print(f"GitHub error: {e}")
            raise e
    
    # Cleanup
    os.remove(local_csv)
    print("\n✅ Script completed successfully!")

except Exception as e:
    print(f"\n❌ Error occurred: {e}")
    import traceback
    traceback.print_exc()
    
    # Save debug files
    try:
        driver.save_screenshot("error_screenshot.png")
        print("Saved error screenshot to error_screenshot.png")
    except:
        pass
    
    try:
        with open("error_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Saved page source to error_page_source.html")
    except:
        pass
    
    raise e

finally:
    driver.quit()
    print("✓ Driver closed.")
