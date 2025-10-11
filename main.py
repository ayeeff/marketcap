import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from github import Github
from webdriver_manager.core.os_manager import ChromeType
import time
import shutil

# Configuration
URL = "https://www.marketcapwatch.com/all-countries/"
REPO_NAME = "ayeeff/marketcap"
FILE_PATH = "data/countries_marketcap.csv"  # Name the CSV file
GITHUB_TOKEN = os.getenv("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")  # Set your GitHub Personal Access Token as environment variable

# Set up Selenium with webdriver-manager
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode (no visible browser)
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")  # Extra for Replit/cloud environments
chrome_options.add_argument("--window-size=1920,1080")  # Set window size to avoid issues

# Find chromium binary path
chromium_path = shutil.which("chromium") or shutil.which("chromium-browser")
if chromium_path:
    chrome_options.binary_location = chromium_path

# Use system chromedriver if available
chromedriver_path = shutil.which("chromedriver")
if chromedriver_path:
    service = Service(chromedriver_path)
else:
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # Load the page
    driver.get(URL)
    
    # Wait for the page to fully load
    print("Waiting for page to load...")
    time.sleep(5)
    
    # Try different selectors
    data = []
    
    # Try to find table by various methods
    try:
        wait = WebDriverWait(driver, 20)
        # Wait for tbody rows to be present (more specific)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
        table = driver.find_element(By.TAG_NAME, "table")
        print("Table found")
    except:
        print("Could not find table with tbody rows, trying simple table...")
        try:
            table = driver.find_element(By.TAG_NAME, "table")
        except:
            print("No table found at all. Saving debug HTML...")
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("Debug HTML saved to debug_page.html")
            raise ValueError("No table element found on page")
    
    # Wait for table rows to be populated (JavaScript rendering)
    print("Extracting table data...")
    max_retries = 15
    for attempt in range(max_retries):
        time.sleep(2)
        rows = table.find_elements(By.TAG_NAME, "tr")
        temp_data = []
        for row in rows:
            # Try both th and td elements
            ths = row.find_elements(By.TAG_NAME, "th")
            tds = row.find_elements(By.TAG_NAME, "td")
            cells = []
            
            # Get text from th elements
            for th in ths:
                text = th.text.strip() or th.get_attribute('textContent').strip()
                cells.append(text)
            
            # Get text from td elements  
            for td in tds:
                text = td.text.strip() or td.get_attribute('textContent').strip()
                cells.append(text)
            
            if cells and any(c for c in cells):  # Skip empty rows
                temp_data.append(cells)
        
        if temp_data and len(temp_data) > 1:  # Has data beyond just headers
            data = temp_data
            print(f"Table data loaded successfully after {attempt + 1} attempts with {len(data)} rows")
            break
        print(f"Attempt {attempt + 1}: Rows found: {len(rows)}, Data rows: {len(temp_data)}")
    
    if not data or len(data) <= 1:
        print("No data found in table. Saving debug HTML...")
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Debug HTML saved to debug_page.html")
        raise ValueError("No table data found. The table selector might need adjustment.")
    
    # Create DataFrame
    columns = data[0]
    df = pd.DataFrame(data[1:], columns=columns)
    
    # Save to local CSV in data directory
    local_csv = "data/countries_marketcap.csv"
    df.to_csv(local_csv, index=False)
    print(f"Data saved to {local_csv}")
    
    # Upload to GitHub (optional - only if token is set)
    if GITHUB_TOKEN:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        # Read the CSV content
        with open(local_csv, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check if file exists and update or create
        try:
            file = repo.get_contents(FILE_PATH)
            repo.update_file(FILE_PATH, "Update countries market cap data", content, file.sha)
            print(f"Updated {FILE_PATH} in GitHub repo.")
        except Exception as e:
            if "not found" in str(e).lower():
                repo.create_file(FILE_PATH, "Add countries market cap data", content)
                print(f"Created {FILE_PATH} in GitHub repo.")
            else:
                raise e
        
        # Clean up local file
        os.remove(local_csv)
        print("Script completed successfully!")
    else:
        print("GITHUB_TOKEN not set. CSV saved locally but not uploaded to GitHub.")
        print(f"CSV file saved at: {local_csv}")
        print("Script completed successfully (without GitHub upload)!")

finally:
    driver.quit()
