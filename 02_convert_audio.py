import os
from pathlib import Path
from pydub import AudioSegment
import argparse

def convert_audio(input_dir, output_dir, target_sr=16000):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Converting audio from {input_path} to {output_path}...")
    
    # Supported extensions
    extensions = ("*.mp3", "*.wav", "*.m4a")
    files = []
    for ext in extensions:
        files.extend(list(input_path.rglob(ext)))
        
    for file in files:
        # Create output subdirectory structure
        relative_path = file.relative_to(input_path)
        target_file = output_path / relative_path.with_suffix(".wav")
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        if target_file.exists():
            continue
            
        try:
            audio = AudioSegment.from_file(file)
            audio = audio.set_frame_rate(target_sr).set_channels(1)
            audio.export(target_file, format="wav")
            # print(f"Converted: {file.name} -> {target_file}")
        except Exception as e:
            print(f"Error converting {file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert audio to 16kHz mono wav.")
    parser.add_argument("--input", required=True, help="Input directory")
    parser.add_argument("--output", required=True, help="Output directory")
    args = parser.parse_args()
    
    convert_audio(args.input, args.output)
