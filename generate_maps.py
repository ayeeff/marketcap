import pandas as pd
import squarify
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import requests
import os
from io import StringIO
from PIL import Image
import numpy as np
from urllib.parse import quote

# URLs for latest CSVs
GLOBAL_CSV_URL = "https://raw.githubusercontent.com/ayeeff/marketcap/main/data/countries_marketcap.csv"
EMPIRE_CSV_URL = "https://raw.githubusercontent.com/ayeeff/marketcap/main/data/empire_marketcap.csv"

# Create img dir
os.makedirs('img', exist_ok=True)

# Simple country to ISO mapping (subset for top countries; extend as needed)
country_to_iso = {
    'United States': 'us', 'China': 'cn', 'Japan': 'jp', 'India': 'in', 'United Kingdom': 'gb',
    'Canada': 'ca', 'France': 'fr', 'Taiwan': 'tw', 'Germany': 'de', 'Switzerland': 'ch',
    'Saudi Arabia': 'sa', 'South Korea': 'kr', 'Australia': 'au', 'Netherlands': 'nl',
    'Sweden': 'se', 'Spain': 'es', 'Italy': 'it', 'United Arab Emirates': 'ae', 'Ireland': 'ie',
    'Hong Kong': 'hk', 'Brazil': 'br', 'Indonesia': 'id', 'Singapore': 'sg', 'Denmark': 'dk',
    # Add more as needed
}

# Empire images URLs (raw GitHub)
empire_images = {
    1: 'https://raw.githubusercontent.com/ayeeff/marketcap/main/img/emp1.png',
    2: 'https://raw.githubusercontent.com/ayeeff/marketcap/main/img/emp2.png',
    3: 'https://raw.githubusercontent.com/ayeeff/marketcap/main/img/emp3.png'
}

# Fetch and load global data
response = requests.get(GLOBAL_CSV_URL)
global_df = pd.read_csv(StringIO(response.text))
global_df['perc'] = pd.to_numeric(global_df['% of Global Market Cap'], errors='coerce')
global_df = global_df[global_df['perc'] > 0].sort_values('perc', ascending=False).head(50)  # Top 50 for readability

# Fetch and load empire data
response = requests.get(EMPIRE_CSV_URL)
empire_df = pd.read_csv(StringIO(response.text))
empire_df['perc'] = pd.to_numeric(empire_df['% of Empire Total'].str.replace('%', ''), errors='coerce')
empire_df = empire_df[empire_df['Rank'] <= 3]

# Function to fetch image as PIL
def fetch_image(url):
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return Image.open(StringIO(resp.content)).convert('RGBA')
    except:
        # Fallback: create a gray square
        return Image.new('RGBA', (100, 100), color='gray')

# Function to generate treemap PNG with overlays
def generate_treemap(df, title, filename, is_empire=False):
    values = df['perc'].tolist()
    labels = df['Country or region'].tolist() if not is_empire else [f"Emp {r}" for r in df['Rank']]
    
    # Temporary plot to get positions
    fig_temp, ax_temp = plt.subplots(1, 1, figsize=(12, 8))
    squarify.plot(sizes=values, label=labels, color=['white'] * len(values), alpha=0, ax=ax_temp)
    ax_temp.axis('off')
    plt.close(fig_temp)
    
    # Extract positions from patches (normalized 0-1)
    rect_positions = []
    for patch in ax_temp.patches:
        bbox = patch.get_bbox().bounds
        rect_positions.append((bbox[0], bbox[1], bbox[2], bbox[3]))
    
    # Create final figure
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.set_xlim(0, 1)
    ax.set_ylim(1, 0)  # Invert y for top-left origin in imshow
    ax.axis('off')
    
    # Draw rectangles and overlay images
    for i, (rx, ry, rw, rh) in enumerate(rect_positions):
        # Draw border rect (note y inverted)
        rect_patch = patches.Rectangle((rx, 1 - (ry + rh)), rw, rh, linewidth=1, edgecolor='black', facecolor='none')
        ax.add_patch(rect_patch)
        
        # Fetch and overlay image (scale to rect size)
        if is_empire:
            rank = df.iloc[i]['Rank']
            img_url = empire_images.get(rank, '')
            if img_url:
                pil_img = fetch_image(img_url)
            else:
                pil_img = Image.new('RGBA', (100, 100), color='gray')
        else:
            country = labels[i]
            iso = country_to_iso.get(country, 'xx')
            if iso != 'xx':
                img_url = f"https://flagcdn.com/w320/{iso}.png"
                pil_img = fetch_image(img_url)
            else:
                pil_img = Image.new('RGBA', (100, 100), color='gray')
        
        # Convert PIL to numpy and add to axes (y inverted)
        img_array = np.array(pil_img)
        ax.imshow(img_array, extent=[rx, rx + rw, 1 - (ry + rh), 1 - ry], aspect='auto', zorder=1)
        
        # Add label if space
        if rw > 0.1 or rh > 0.1:  # Threshold for label
            ax.text(rx + 0.01, 1 - (ry + 0.01), str(labels[i])[:8], fontsize=8, color='white', va='top', ha='left', zorder=2)
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(f'img/{filename}', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Generated img/{filename} with overlays")

# Generate maps
generate_treemap(global_df, 'Global Market Cap Treemap (% of Global)', 'map1.png', False)
generate_treemap(empire_df, 'Empire Market Cap Treemap (% of Empire Total)', 'map2.png', True)

print("Maps with flag overlays generated and saved to img/!")
