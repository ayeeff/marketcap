# Adapted squarify pure Python code (no dependencies)
import numpy as np
import pandas as pd
import requests
from io import StringIO

def normalize_sizes(sizes, dx, dy):
    total = sum(sizes)
    return [float(size) / total * dx * dy for size in sizes]

def ishoriz(row):
    if len(row) == 1:
        return True
    if row[0] == 0:
        return True
    if row[-1] == 0:
        return False
    return row[0] > row[-1]

def get_rect_positions(sizes, width=1, height=1):
    dx = width
    dy = height
    sizes = normalize_sizes(sizes, dx, dy)
    
    row = []
    sumrow = 0
    x = 0
    y = 0
    rects = []
    
    def add_row(row, x, y, dx, dy):
        total_row = sum(row)
        if ishoriz(row):
            h = dy * row[0] / total_row if total_row > 0 else 0
            cx = x
            for size in row:
                w = dx * size / total_row if total_row > 0 else 0
                rects.append({'x': cx, 'y': y, 'dx': w, 'dy': h})
                cx += w
            return cx, y + h
        else:
            w = dx * row[0] / total_row if total_row > 0 else 0
            cy = y
            for size in row:
                h = dy * size / total_row if total_row > 0 else 0
                rects.append({'x': x, 'y': cy, 'dx': w, 'dy': h})
                cy += h
            return x + w, cy
    
    for size in sizes:
        row.append(size)
        sumrow += size
        if len(row) > 1 and sumrow > dx * dy / 2:
            new_x, new_y = add_row(row, x, y, dx, dy)
            if ishoriz(row):
                y = new_y
                x = 0
            else:
                x = new_x
                y = 0
            row = []
            sumrow = 0
    
    if row:
        add_row(row, x, y, dx, dy)
    
    return rects

# URLs for latest CSVs
GLOBAL_CSV_URL = "https://raw.githubusercontent.com/ayeeff/marketcap/main/data/countries_marketcap.csv"
EMPIRE_CSV_URL = "https://raw.githubusercontent.com/ayeeff/marketcap/main/data/empire_marketcap.csv"

# Tooltip texts for empires, indexed by rank-1
empire_tooltips = [
    '1,Empire 1.0: Steam & Colonies,British Commonwealth,$12.26 T,21,8.28%,11.65%',
    '2,Empire 2.0: Oil & Silicon,United States,$68.89 T,1,46.50%,65.42%',
    '3,"Empire 3.0: Rare Earths, Renewables & Robotics",China + Hong Kong + Taiwan,$24.15 T,3,16.30%,22.93%'
]

# Fetch and load global data
response = requests.get(GLOBAL_CSV_URL)
global_df = pd.read_csv(StringIO(response.text))
global_df['perc'] = pd.to_numeric(global_df['% of Global Market Cap'], errors='coerce')
global_df = global_df[global_df['perc'] > 0].sort_values('perc', ascending=False).head(15)

# Fetch and load empire data
response = requests.get(EMPIRE_CSV_URL)
empire_df = pd.read_csv(StringIO(response.text))
empire_df['perc'] = pd.to_numeric(empire_df['% of Empire Total'].str.replace('%', ''), errors='coerce')
empire_df = empire_df[empire_df['Rank'] <= 3].sort_values('Rank')  # Sort by Rank ascending

# Common params
figsize = (12, 8)
dpi = 150
img_width = int(figsize[0] * dpi)
img_height = int(figsize[1] * dpi - 30)  # Approximate subtract for title padding

# For global
global_values = global_df['perc'].tolist()
global_positions = get_rect_positions(global_values, 1, 1)
global_html = '<figure><img src="https://raw.githubusercontent.com/ayeeff/marketcap/main/img/map1.png" usemap="#globalmap" alt="Global Market Cap Treemap" style="max-width:100%;height:auto;"><map name="globalmap">\n'
for i, rect in enumerate(global_positions):
    row = global_df.iloc[i]
    left = int(rect['x'] * img_width)
    top = int((1 - (rect['y'] + rect['dy'])) * img_height)
    right = int((rect['x'] + rect['dx']) * img_width)
    bottom = int((1 - rect['y']) * img_height)
    coords = f"{left},{top},{right},{bottom}"
    tooltip = f"{row['Country or region']}\\n{row['Total MarketCap']}\\n{row['perc']:.2f}%"
    alt = row['Country or region'][:50].replace('"', '&quot;')
    tooltip = tooltip.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    global_html += f'  <area shape="rect" coords="{coords}" href="#" alt="{alt}" title="{tooltip}">\n'
global_html += '</map></figure>\n<p><em>Hover over rectangles for details.</em></p>\n'

# For empire
empire_values = empire_df['perc'].tolist()
empire_positions = get_rect_positions(empire_values, 1, 1)
empire_html = '<figure><img src="https://raw.githubusercontent.com/ayeeff/marketcap/main/img/map2.png" usemap="#empiremap" alt="Empire Market Cap Treemap" style="max-width:100%;height:auto;"><map name="empiremap">\n'
for i, rect in enumerate(empire_positions):
    row = empire_df.iloc[i]
    rank = int(row['Rank'])
    left = int(rect['x'] * img_width)
    top = int((1 - (rect['y'] + rect['dy'])) * img_height)
    right = int((rect['x'] + rect['dx']) * img_width)
    bottom = int((1 - rect['y']) * img_height)
    coords = f"{left},{top},{right},{bottom}"
    tooltip = empire_tooltips[rank - 1].replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
    alt = row['Empire'][:50].replace('"', '&quot;')
    empire_html += f'  <area shape="rect" coords="{coords}" href="#" alt="{alt}" title="{tooltip}">\n'
empire_html += '</map></figure>\n<p><em>Hover over rectangles for details.</em></p>\n'

print("GLOBAL HTML SNIPPET (paste into WordPress Custom HTML block):\n" + global_html)
print("\nEMPIRE HTML SNIPPET (paste into WordPress Custom HTML block):\n" + empire_html)
print(f"\nAssumed image size: {img_width} x {img_height} pixels (adjust if title affects bbox)")
