import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from github import Github, Auth
import time

# Configuration
URL = "https://www.aei.org/china-global-investment-tracker/"
REPO_NAME = "ayeeff/marketcap"  # Adjust if needed for your repo
FILE_PATH = "data/china_investments.csv"

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

def setup_driver():
    """Setup Chrome driver with options."""
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
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins-discovery')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--allow-running-insecure-content')

    print("Setting up ChromeDriver...")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def handle_cookies(driver, wait):
    """Handle cookie consent if present."""
    try:
        # XPATH selectors
        xpath_selectors = [
            "//button[contains(text(), 'Accept')]",
            "//button[contains(text(), 'Agree')]"
        ]
        # CSS selectors
        css_selectors = [
            "[data-testid='cookie-accept']",
            ".cookie-accept",
            "#cookie-accept"
        ]
        
        # Try XPATH first
        for selector in xpath_selectors:
            try:
                accept_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                accept_btn.click()
                print("✓ Cookie consent accepted (XPath).")
                time.sleep(2)
                return
            except TimeoutException:
                continue
        
        # Try CSS
        for selector in css_selectors:
            try:
                accept_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                accept_btn.click()
                print("✓ Cookie consent accepted (CSS).")
                time.sleep(2)
                return
            except TimeoutException:
                continue
    except Exception as e:
        print(f"⚠️ No cookie banner found or error: {e}")

def wait_for_table(driver, wait, max_attempts=3):
    """Robust wait for the DataTable to load."""
    for attempt in range(max_attempts):
        try:
            print(f"Attempt {attempt + 1}/{max_attempts} waiting for table...")
            # Try multiple selectors for the table
            table_selectors = [
                "table.dataTable",
                "table.table",
                ".dataTable",
                "table"
            ]
            table = None
            for sel in table_selectors:
                try:
                    table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                    print(f"✓ Table found with selector: {sel}")
                    break
                except TimeoutException:
                    continue
            
            if table is None:
                raise TimeoutException("No table found with any selector.")
            
            # Additional wait for rows to populate
            wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, f"{sel} tbody tr")) > 0)
            print("✓ Table loaded with data.")
            return table
        except TimeoutException:
            print(f"⚠️ Attempt {attempt + 1} timed out, retrying...")
            time.sleep(15)
            # Refresh page on retry
            if attempt > 0:
                driver.refresh()
                time.sleep(5)
                # Scroll to bottom to load dynamic content
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(5)
    raise TimeoutException("Table failed to load after multiple attempts.")

def scrape_table(driver, wait, table):
    """Scrape the current page's table."""
    # Verify headers
    headers = [th.text.strip() for th in table.find_elements(By.TAG_NAME, "th")]
    print(f"Found table headers: {headers}")
    
    if len(headers) < 7 or not any(word in h.lower() for h in headers for word in ['year', 'month', 'investor', 'sector', 'country', 'amount', 'type']):
        print("Warning: Unexpected table headers. Attempting to scrape anyway.")
    
    rows = table.find_elements(By.TAG_NAME, "tr")
    data = []
    
    for
