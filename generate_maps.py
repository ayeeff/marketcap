import pandas as pd
import squarify
import matplotlib.pyplot as plt
import requests
import os
from io import StringIO

# URLs for latest CSVs
GLOBAL_CSV_URL = "https://raw.githubusercontent.com/ayeeff/marketcap/main/data/countries_marketcap.csv"
EMPIRE_CSV_URL = "https://raw.githubusercontent.com/ayeeff/marketcap/main/data/empire_marketcap.csv"

# Create img dir
os.makedirs('img', exist_ok=True)

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

# Function to generate treemap PNG
def generate_treemap(df, title, filename, is_empire=False):
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    labels = [str(l)[:10] for l in (df['Country or region'] if not is_empire else df['Empire'])]  # Short labels
    values = df['perc'].tolist()
    
    # Colors: Simple palette
    if is_empire:
        colors = ['#8B0000', '#000080', '#006400']  # Empire-specific
    else:
        colors = plt.cm.Set3(range(len(values)))  # Diverse colors
    
    squarify.plot(sizes=values, label=labels, color=colors, alpha=0.8, ax=ax, text_kwargs={'fontsize': 8, 'color': 'white'})
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(f'img/{filename}', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Generated img/{filename}")

# Generate maps
generate_treemap(global_df, 'Global Market Cap Treemap (% of Global)', 'map1.png', False)
generate_treemap(empire_df, 'Empire Market Cap Treemap (% of Empire Total)', 'map2.png', True)

print("Maps generated and saved to img/!")
