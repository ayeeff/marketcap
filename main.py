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

# Configuration
URL = "https://www.marketcapwatch.com/all-countries/"
REPO_NAME = "ayeeff/marketcap"
FILE_PATH = "data/countries_marketcap.csv"  # Name the CSV file
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Set your GitHub Personal Access Token as environment variable

# Set up Selenium with webdriver-manager
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode (no visible browser)
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")  # Extra for Replit/cloud environments
chrome_options.add_argument("--window-size=1920,1080")  # Set window size to avoid issues

service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # Load the page
    driver.get(URL)
    
    # Wait for the table to load (adjust timeout if needed)
    wait = WebDriverWait(driver, 20)
    table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    
    # Extract table data
    rows = table.find_elements(By.TAG_NAME, "tr")
    data = []
    for row in rows:
        cells = [cell.text.strip() for cell in row.find_elements(By.TAG_NAME, "th, td")]
        if cells:  # Skip empty rows
            data.append(cells)
    
    if not data:
        raise ValueError("No table data found. The table selector might need adjustment.")
    
    # Create DataFrame
    columns = data[0]
    df = pd.DataFrame(data[1:], columns=columns)
    
    # Save to local CSV
    local_csv = "countries_marketcap.csv"
    df.to_csv(local_csv, index=False)
    print(f"Data saved to {local_csv}")
    
    # Upload to GitHub
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable not set. Please set your GitHub token.")
    
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

finally:
    driver.quit()
