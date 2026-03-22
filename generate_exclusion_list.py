import os
import pandas as pd
from pathlib import Path
import re

def parse_cha_header(file_path):
    """Parses the @ID header from a .cha file to get age, gender, and MMSE."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('@ID:'):
                    # Format: @ID: lang|corpus|role|age|gender|group|SES|subtype|MMSE|
                    parts = line.split('|')
                    if len(parts) >= 10:
                        age = parts[3].replace(';', '').strip()
                        gender = parts[4].strip().lower()
                        mmse = parts[8].strip()
                        return age, gender, mmse
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
    return None, None, None

def get_adress_metadata(base_dir):
    data = []
    # Train CC
    cc_train = pd.read_csv(os.path.join(base_dir, "train/cc_meta_data.txt"), sep=';', skipinitialspace=True)
    cc_train['label'] = 'Control'
    data.append(cc_train)
    
    # Train CD
    cd_train = pd.read_csv(os.path.join(base_dir, "train/cd_meta_data.txt"), sep=';', skipinitialspace=True)
    cd_train['label'] = 'Dementia'
    data.append(cd_train)
    
    # Test
    test = pd.read_csv(os.path.join(base_dir, "test/meta_data.txt"), sep=';', names=['ID', 'age', 'gender'], skipinitialspace=True)
    # Test labels are in testgroundtruth.csv usually, but we only need IDs for exclusion
    test['label'] = 'Test' 
    data.append(test)
    
    df = pd.concat(data, ignore_index=True)
    df['gender'] = df['gender'].str.strip().str.lower()
    return df

def generate_exclusion():
    pitt_base = Path("/Users/shyam/Downloads/Pitt")
    adress_base = Path("/Users/shyam/Desktop/cognitive_project/adress2020/ADReSS-IS2020-data")
    output_path = Path("/Users/shyam/Desktop/cognitive_project/pitt_adress_exclusion.csv")
    
    if not adress_base.exists():
        print(f"ADReSS data not found at {adress_base}")
        return

    adress_meta = get_adress_metadata(adress_base)
    print(f"Loaded {len(adress_meta)} ADReSS records.")

    exclusion_list = []

    # Iterate through Pitt files and match against ADReSS metadata
    for group in ["Control/cookie", "Dementia/cookie"]:
        pitt_dir = pitt_base / group
        if not pitt_dir.exists():
            continue
            
        for cha_file in pitt_dir.glob("*.cha"):
            age, gender, mmse = parse_cha_header(cha_file)
            if age and gender:
                # Match by Age and Gender (MMSE might vary slightly or be NA in ADReSS)
                # Note: Age in Pitt might be different from ADReSS (usually Pitt age <= ADReSS age)
                # But for ADReSS 2020, they are often identical in the underlying data.
                matches = adress_meta[
                    (adress_meta['age'].astype(str) == age) & 
                    (adress_meta['gender'] == gender)
                ]
                
                if not matches.empty:
                    # Found a potential match
                    pitt_id = cha_file.stem # e.g., 001-0
                    for _, row in matches.iterrows():
                        exclusion_list.append({
                            "pitt_id": pitt_id,
                            "adress_id": row['ID'],
                            "age": age,
                            "gender": gender,
                            "mmse_pitt": mmse,
                            "mmse_adress": row.get('mmse', 'NA')
                        })

    df_exclusion = pd.DataFrame(exclusion_list).drop_duplicates(subset=['pitt_id'])
    df_exclusion.to_csv(output_path, index=False)
    print(f"Generated exclusion list with {len(df_exclusion)} matches at {output_path}")

if __name__ == "__main__":
    generate_exclusion()
