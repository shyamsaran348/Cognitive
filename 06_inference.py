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

    # 0. Automatic Transcription (ASR) if transcript is missing
    target_transcript = transcript
    if not target_transcript or target_transcript.strip() == "":
        print("[INFO] No transcript provided. Running Whisper ASR for automatic extraction...")
        import whisper
        # Use simple base/small for fast ASR, or large if preferred.
        # We use the existing extractor's logic if possible.
        asr_model = whisper.load_model("base", device="cpu")
        asr_res = asr_model.transcribe(audio_path)
        target_transcript = asr_res["text"].strip()
        print(f"[INFO] Auto-ASR Result: \"{target_transcript}\"")

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
    enc = tokenizer(target_transcript, max_length=256, padding="max_length", truncation=True, return_tensors="pt")
    
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

    import librosa
    import numpy as np
    
    # Fast lightweight loading for amplitude waveform UI
    y, sr_ = librosa.load(audio_path, sr=16000)
    chunk_size = max(1, len(y) // 100)
    waveform = [float(np.max(np.abs(y[i*chunk_size:(i+1)*chunk_size]))) for i in range(100) if i*chunk_size < len(y)]
    if len(waveform) < 100: waveform += [0.0] * (100 - len(waveform))
    
    # 5. Forward Pass
    print("[INFO] Running Trimodal PoE Fusion...")
    with torch.no_grad():
        egemaps_t = torch.tensor(egemaps, dtype=torch.float32).unsqueeze(0).to(device)
        wav2vec_t = torch.tensor(wav2vec, dtype=torch.float32).unsqueeze(0).to(device)
        whisper_t = torch.tensor(whisper_emb, dtype=torch.float32).unsqueeze(0).to(device)
        input_ids_t = enc["input_ids"].to(device)
        attention_mask_t = enc["attention_mask"].to(device)
        clinical_t = clinical.to(device)

        # Trimodal Component Probing (Pre-Fusion Logits)
        acoustic_feat = model.acoustic(egemaps_t, wav2vec_t, whisper_t)
        text_feat = model.text(input_ids_t, attention_mask_t)
        clinical_feat = model.clinical(clinical_t)

        acoustic_mu = model.fusion.acoustic_mu(acoustic_feat)
        text_mu = model.fusion.text_mu(text_feat)
        clinical_mu = model.fusion.clinical_mu(clinical_feat)

        p_ac = torch.softmax(model.clf_head(acoustic_mu), dim=-1)[0][1].item()
        p_text = torch.softmax(model.clf_head(text_mu), dim=-1)[0][1].item()
        p_clin = torch.softmax(model.clf_head(clinical_mu), dim=-1)[0][1].item()

        clf_out, reg_out = model(
            egemaps=egemaps_t,
            wav2vec=wav2vec_t,
            whisper=whisper_t,
            input_ids=input_ids_t,
            attention_mask=attention_mask_t,
            clinical=clinical_t,
        )
    
    # 6. Interpret Results
    probs = torch.softmax(clf_out, dim=-1)[0]
    is_dementia = probs[1].item() > 0.5
    mmse_pred = reg_out[0].item()

    print("\n" + "="*60)
    print("🧠 Trimodal Cognitive Assessment Report")
    print("="*60)
    print(f"Transcript         : \"{target_transcript}\"")
    print(f"Patient Dimensions : Age {age} | Edu {education}ys | CDR {cdr}")
    print("-" * 60)
    print(f"Classification     : {'Dementia (AD)' if is_dementia else 'Healthy Control (HC)'}")
    print(f"AD Probability     : {probs[1].item() * 100:.2f}%")
    print(f"Predicted MMSE     : {mmse_pred:.2f} / 30.0")
    print("="*60 + "\n")

    return {
        "classification": "Dementia (AD)" if is_dementia else "Healthy Control (HC)",
        "ad_probability": probs[1].item(),
        "mmse_score": mmse_pred,
        "modality_probs": {
            "acoustic": p_ac,
            "text": p_text,
            "clinical": p_clin
        },
        "waveform": waveform,
        "transcript": target_transcript,
        "age": age,
        "education": education,
        "cdr": cdr
    }

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
