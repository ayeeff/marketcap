import pandas as pd
import squarify
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import requests
import os
import gc
from io import StringIO, BytesIO
from PIL import Image
import numpy as np
import warnings
from urllib.parse import quote
import xml.etree.ElementTree as ET

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

# Tooltip texts for empires
tooltip_texts = [
    '1,Empire 1.0: Steam & Colonies,British Commonwealth,$12.26 T,21,8.28%,11.65%',
    '2,Empire 2.0: Oil & Silicon,United States,$68.89 T,1,46.50%,65.42%',
    '3,"Empire 3.0: Rare Earths, Renewables & Robotics",China + Hong Kong + Taiwan,$24.15 T,3,16.30%,22.93%'
]

# Fetch and load global data
response = requests.get(GLOBAL_CSV_URL)
global_df = pd.read_csv(StringIO(response.text))
global_df['perc'] = pd.to_numeric(global_df['% of Global Market Cap'], errors='coerce')
global_df = global_df[global_df['perc'] > 0].sort_values('perc', ascending=False).head(15)  # Top 15 for global

# Fetch and load empire data
response = requests.get(EMPIRE_CSV_URL)
empire_df = pd.read_csv(StringIO(response.text))
empire_df['perc'] = pd.to_numeric(empire_df['% of Empire Total'].str.replace('%', ''), errors='coerce')
empire_df = empire_df[empire_df['Rank'] <= 3]  # All 3 empires

# Function to fetch image as PIL
def fetch_image(url):
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert('RGBA')
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        # Fallback: create a colored square
        colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange']
        return Image.new('RGBA', (100, 100), color=colors[hash(url) % len(colors)])

# Function to get rectangle positions without plotting
def get_rect_positions(sizes):
    normalized = squarify.normalize_sizes(sizes, 1, 1)
    rects = squarify.squarify(normalized, 0, 0, 1, 1)
    return [(r['x'], r['y'], r['dx'], r['dy']) for r in rects]

# Function to generate treemap PNG/SVG with overlays
def generate_treemap(df, title, filename, is_empire=False):
    values = df['perc'].tolist()
    labels = df['Country or region'].tolist() if not is_empire else df['Empire'].tolist()
    
    # Get positions without temp plot
    rect_positions = get_rect_positions(values)
    
    # Create final figure
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    # Calculate figure dimensions in pixels
    dpi = 150
    fig_width_px = 12 * dpi
    fig_height_px = 8 * dpi
    
    # Draw rectangles and overlay images
    for i, (rx, ry, rw, rh) in enumerate(rect_positions):
        # Draw border rect
        rect_patch = patches.Rectangle((rx, ry), rw, rh, linewidth=1, edgecolor='black', facecolor='none')
        ax.add_patch(rect_patch)
        
        # Fetch image
        if is_empire:
            rank = df.iloc[i]['Rank']
            img_url = empire_images.get(rank, '')
            pil_img = fetch_image(img_url)
        else:
            country = labels[i]
            iso = country_to_iso.get(country, 'xx')
            if iso != 'xx':
                img_url = f"https://flagcdn.com/w320/{iso}.png"
                pil_img = fetch_image(img_url)
            else:
                pil_img = Image.new('RGBA', (100, 100), color='gray')
        
        # Calculate target size and resize
        target_w = max(1, int(rw * fig_width_px))
        target_h = max(1, int(rh * fig_height_px))
        pil_resized = pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        img_array = np.array(pil_resized)
        
        # Use imshow to scale and stretch
        ax.imshow(img_array, extent=[rx, rx + rw, ry, ry + rh], aspect='auto', zorder=1)
        
        # Add label if space
        if rw > 0.08 or rh > 0.08:
            label_text = str(labels[i])[:10]
            ax.text(rx + 0.01, ry + rh - 0.01, label_text, fontsize=8, color='white', va='top', ha='left', zorder=2, weight='bold')
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    if is_empire:
        # Save to SVG buffer and add tooltips
        svg_buffer = BytesIO()
        plt.savefig(svg_buffer, format='svg', bbox_inches='tight', facecolor='white', dpi=dpi)
        svg_buffer.seek(0)
        svg_str = svg_buffer.read().decode('utf-8')
        
        root = ET.fromstring(svg_str)
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        images = root.findall('.//svg:image', ns)
        
        for j, img in enumerate(images[:len(tooltip_texts)]):
            title_elem = ET.SubElement(img, '{http://www.w3.org/2000/svg}title')
            title_elem.text = tooltip_texts[j]
        
        svg_output = ET.tostring(root, encoding='unicode', method='xml')
        filename_out = filename.replace('.png', '.svg')
        with open(f'img/{filename_out}', 'w', encoding='utf-8') as f:
            f.write(svg_output)
        print(f"Generated img/{filename_out} with overlays and tooltips")
    else:
        plt.savefig(f'img/{filename}', dpi=dpi, bbox_inches='tight', facecolor='white')
        print(f"Generated img/{filename} with overlays")
    
    plt.close(fig)
    gc.collect()

# Generate maps
generate_treemap(global_df, 'Global Market Cap Treemap (% of Global)', 'map1.png', False)
generate_treemap(empire_df, 'Empire Market Cap Treemap (% of Empire Total)', 'map2.png', True)

print("Maps with flag overlays generated and saved to img/!")
