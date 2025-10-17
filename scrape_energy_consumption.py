import os
import pandas as pd

DATA_URL = "https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/monthly_full_release_long_format.csv"

def load_data(local_path: str | None = None) -> pd.DataFrame:
    """
    Load the CSV from a local path if available, otherwise download it from the public URL.
    """
    if local_path and os.path.exists(local_path):
        print(f"📂 Loading local CSV: {local_path}")
        df = pd.read_csv(local_path)
    else:
        print(f"🌐 Downloading CSV from: {DATA_URL}")
        df = pd.read_csv(DATA_URL)
    return df


def normalize_empire_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert the Empire column to numeric codes (1, 2, 3).
    """
    if "Empire" in df.columns:
        empire_map = {
            "First Empire": 1,
            "Second Empire": 2,
            "Third Empire": 3,
            "I": 1,
            "II": 2,
            "III": 3
        }
        df["Empire"] = df["Empire"].replace(empire_map)
    else:
        print("⚠️  'Empire' column not found in data.")
    return df


def main(local_path: str | None = None):
    # Load data (local or from URL)
    df = load_data(local_path)

    # Normalize Empire column
    df = normalize_empire_column(df)

    # Print quick sanity checks
    print("✅ Data loaded successfully!")
    print(f"Rows: {len(df):,}, Columns: {len(df.columns)}")
    print("\nSample:")
    print(df.head(10))

    # Save cleaned version (optional)
    out_path = "cleaned_monthly_full_release.csv"
    df.to_csv(out_path, index=False)
    print(f"\n💾 Cleaned data saved to: {out_path}")


if __name__ == "__main__":
    # Run with local CSV if present; fallback to remote if not
    main("monthly_full_release_long_format.csv")
