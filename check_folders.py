import os
from pathlib import Path

def check_structure():
    base_dir = Path("/Users/shyam/Desktop/cognitive_project")
    required_dirs = [
        "pitt_audio/Control",
        "pitt_audio/Dementia",
        "taukadial/TAUKADIAL-24",
        "adress2020/ADReSS-IS2020-data",
    ]
    
    print(f"Checking project structure at {base_dir}...")
    for rd in required_dirs:
        path = base_dir / rd
        if path.exists():
            print(f"[OK] Found: {rd}")
        else:
            print(f"[MISSING] {rd}")

    # Check for Pitt transcripts (should be moved from Downloads)
    pitt_transcripts = base_dir / "pitt_transcripts"
    if pitt_transcripts.exists():
        print(f"[OK] Found: pitt_transcripts")
    else:
        print(f"[WARNING] pitt_transcripts not found at {pitt_transcripts}")
        print("Note: Pitt transcripts were found in ~/Downloads/Pitt. They should be moved.")

if __name__ == "__main__":
    check_structure()
