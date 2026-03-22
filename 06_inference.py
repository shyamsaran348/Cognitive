import os
# macOS mutithreading protections
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
os.environ["USE_TF"] = "0"
os.environ["USE_FLAX"] = "0"

import torch
torch.set_num_threads(1)
import argparse
import numpy as np
from transformers import RobertaTokenizer
from model import CognitiveLossModel
import importlib.util

# Lazily import the trusted feature extraction methods from step 3
spec = importlib.util.spec_from_file_location("extractor", "03_feature_extractor.py")
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)

def run_inference(audio_path, transcript, age, education, cdr, checkpoint_path):
    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    print(f"\n[INFO] Initializing Inference on {device}...")

    # 1. Acoustic Features
    print("[INFO] Extracting Acoustic Vectors (eGeMAPS, Wav2vec, Whisper)...")
    egemaps = extractor.extract_egemaps(audio_path)
    if egemaps is None: egemaps = np.zeros(88)

    wav2vec = extractor.extract_wav2vec(audio_path)
    if wav2vec is None: wav2vec = np.zeros(768)

    whisper_emb = extractor.extract_whisper(audio_path)
    if whisper_emb is None: whisper_emb = np.zeros(1280)

    # 2. Text Features
    print("[INFO] Tokenizing Transcript (RoBERTa)...")
    tokenizer = RobertaTokenizer.from_pretrained("roberta-large")
    enc = tokenizer(transcript, max_length=256, padding="max_length", truncation=True, return_tensors="pt")
    
    # 3. Clinical Features
    clinical = torch.tensor([[age / 100.0, education / 20.0, cdr]], dtype=torch.float32)

    # 4. Load Model
    print(f"[INFO] Injecting LoRA Weights from {checkpoint_path}...")
    model = CognitiveLossModel()
    
    # Load into CPU first to prevent RAM spikes, then send to device
    state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    # 5. Forward Pass
    print("[INFO] Running Trimodal PoE Fusion...")
    with torch.no_grad():
        clf_out, reg_out = model(
            egemaps=torch.tensor(egemaps, dtype=torch.float32).unsqueeze(0).to(device),
            wav2vec=torch.tensor(wav2vec, dtype=torch.float32).unsqueeze(0).to(device),
            whisper=torch.tensor(whisper_emb, dtype=torch.float32).unsqueeze(0).to(device),
            input_ids=enc["input_ids"].to(device),
            attention_mask=enc["attention_mask"].to(device),
            clinical=clinical.to(device),
        )
    
    # 6. Interpret Results
    probs = torch.softmax(clf_out, dim=-1)[0]
    is_dementia = probs[1].item() > 0.5
    mmse_pred = reg_out[0].item()

    print("\n" + "="*60)
    print("🧠 Trimodal Cognitive Assessment Report")
    print("="*60)
    print(f"Transcript         : \"{transcript}\"")
    print(f"Patient Dimensions : Age {age} | Edu {education}ys | CDR {cdr}")
    print("-" * 60)
    print(f"Classification     : {'Dementia (AD)' if is_dementia else 'Healthy Control (HC)'}")
    print(f"AD Probability     : {probs[1].item() * 100:.2f}%")
    print(f"Predicted MMSE     : {mmse_pred:.2f} / 30.0")
    print("="*60 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, help="Path to .wav/.mp3 audio file")
    parser.add_argument("--text", required=True, help="Transcript of the audio")
    parser.add_argument("--age", type=float, default=65.0, help="Patient age")
    parser.add_argument("--edu", type=float, default=12.0, help="Years of education")
    parser.add_argument("--cdr", type=float, default=0.5, help="Clinical Dementia Rating")
    parser.add_argument("--ckpt", default="model_checkpoints/taukadial_fold5_best.pt", help="Path to .pt checkpoint")
    args = parser.parse_args()

    run_inference(args.audio, args.text, args.age, args.edu, args.cdr, args.ckpt)
