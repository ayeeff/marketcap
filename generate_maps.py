import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import requests
import os
from io import StringIO, BytesIO
from PIL import Image
import numpy as np
import warnings
from urllib.parse import quote

# Suppress tight layout warning
warnings.filterwarnings("ignore", message="Tight layout")

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
global_df = global_df[global_df['perc'] > 0].sort_values('perc', ascending=False).head(20)  # Reduced to 20 for memory and clarity

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
        return Image.open(BytesIO(resp.content)).convert('RGBA')
    except:
        # Fallback: create a colored square based on index
        colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange']
        return Image.new('RGBA', (100, 100), color=colors[hash(url) % len(colors)])

# Simple treemap layout (slice-and-dice)
def simple_treemap_layout(values, width=1, height=1):
    total = sum(values)
    rects = []
    x, y = 0, 0
    for val in values:
        area = (val / total) * width * height
        if width > height:
            # Horizontal slice
            h = area / width
            rects.append({'x': x, 'y': y, 'dx': width, 'dy': h})
            y += h
            height -= h
        else:
            # Vertical slice
            w = area / height
            rects.append({'x': x, 'y': y, 'dx': w, 'dy': height})
            x += w
            width -= w
    return rects

# Function to generate treemap PNG with overlays
def generate_treemap(df, title, filename, is_empire=False):
    values = df['perc'].tolist()
    labels = df['Country or region'].tolist() if not is_empire else df['Empire'].tolist()
    
    # Get rect positions
    rects = simple_treemap_layout(values)
    
    # Create final figure
    fig, ax = plt.subplots(1, 1, figsize=(10, 7))  # Smaller size for memory
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    # Draw rectangles and overlay images
    for i, rect in enumerate(rects):
        rx, ry, rw, rh = rect['x'], rect['y'], rect['dx'], rect['dy']
        
        # Draw border rect
        rect_patch = patches.Rectangle((rx, ry), rw, rh, linewidth=1, edgecolor='black', facecolor='none')
        ax.add_patch(rect_patch)
        
        # Fetch and overlay image
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
        
        # No resize; let imshow scale
        img_array = np.array(pil_img)
        ax.imshow(img_array, extent=[rx, rx + rw, ry, ry + rh], aspect='auto', zorder=1)
        
        # Add label if space
        if rw > 0.05 or rh > 0.05:
            label_text = str(labels[i])[:6]
            ax.text(rx + 0.005, ry + rh - 0.005, label_text, fontsize=6, color='white', va='top', ha='left', zorder=2, weight='bold')
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
    plt.savefig(f'img/{filename}', dpi=100, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Generated img/{filename} with overlays")

# Generate maps
generate_treemap(global_df, 'Global Market Cap Treemap (% of Global)', 'map1.png', False)
generate_treemap(empire_df, 'Empire Market Cap Treemap (% of Empire Total)', 'map2.png', True)

print("Maps with flag overlays generated and saved to img/!")
