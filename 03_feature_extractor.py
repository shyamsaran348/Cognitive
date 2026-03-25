"""
03_feature_extractor.py — Multimodal Feature Extraction Pipeline
Extracts: eGeMAPS (openSMILE), Wav2vec 2.0, Whisper encoder, hand-crafted.

Checkpoint/resume: saves every CHECKPOINT_EVERY samples to a .npz file.
If interrupted, re-running will skip already-processed samples.

Usage:
  python 03_feature_extractor.py --dataset adress --split train
  python 03_feature_extractor.py --dataset pitt
  python 03_feature_extractor.py --dataset taukadial
"""

import os
import argparse
import numpy as np

# Disable tokenizers parallelism and limit threading to prevent deadlocks/mutex issues
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
# Fix for abseil/grpc mutex issues: use pure python protobuf implementation
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
# CRITICAL: Prevent transformers from importing TensorFlow/Flax, which
# causes C++ deadlocks on macOS via grpc/abseil during lazy loading.
os.environ["USE_TF"] = "0"
os.environ["USE_FLAX"] = "0"
from pathlib import Path
from typing import Optional

import pandas as pd
import librosa

# Lazy imports — loaded only when needed
_opensmile = None
_wav2vec_processor = None
_wav2vec_model = None
_whisper_model = None

CHECKPOINT_EVERY = 50
CHECKPOINT_DIR = Path("/Users/shyam/Desktop/cognitive_project/feature_cache")


# ---------------------------------------------------------------------------
# Checkpoint utilities
# ---------------------------------------------------------------------------

def load_checkpoint(name: str) -> dict:
    """Load an existing feature checkpoint, or return empty dict."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = CHECKPOINT_DIR / f"{name}.npz"
    if ckpt_path.exists():
        data = np.load(ckpt_path, allow_pickle=True)
        result = {k: data[k] for k in data.files}
        print(f"[CKPT] Loaded checkpoint '{name}' with {len(result.get('ids', []))} samples.")
        return result
    return {}


def save_checkpoint(name: str, accumulator: dict) -> None:
    """Save current accumulator state to a .npz checkpoint."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = CHECKPOINT_DIR / f"{name}.npz"
    np.savez_compressed(str(ckpt_path), **{
        k: np.array(v, dtype=object) for k, v in accumulator.items()
    })
    n = len(accumulator.get("ids", []))
    print(f"[CKPT] Saved checkpoint '{name}' with {n} samples → {ckpt_path}")


# ---------------------------------------------------------------------------
# Audio loading utility
# ---------------------------------------------------------------------------

def load_audio(path: str, target_sr: int = 16000) -> Optional[np.ndarray]:
    """Load audio from .wav or .mp3, resample to target_sr, mono."""
    try:
        audio, sr = librosa.load(path, sr=target_sr, mono=True)
        return audio
    except Exception as e:
        print(f"[WARN] Cannot load {path}: {e}")
        return None


# ---------------------------------------------------------------------------
# eGeMAPS (openSMILE)
# ---------------------------------------------------------------------------

def extract_egemaps(audio_path: str) -> Optional[np.ndarray]:
    """Extract 88-dim eGeMAPS feature vector via openSMILE."""
    global _opensmile
    if _opensmile is None:
        try:
            import opensmile
            _opensmile = opensmile.Smile(
                feature_set=opensmile.FeatureSet.eGeMAPSv02,
                feature_level=opensmile.FeatureLevel.Functionals,
            )
        except ImportError:
            print("[ERROR] opensmile not installed. Run: pip install opensmile")
            return None

    try:
        features = _opensmile.process_file(audio_path)
        return features.values.flatten().astype(np.float32)
    except Exception as e:
        print(f"[WARN] eGeMAPS failed for {audio_path}: {e}")
        return None


# ---------------------------------------------------------------------------
# Wav2vec 2.0
# ---------------------------------------------------------------------------

def extract_wav2vec(audio_path: str) -> Optional[np.ndarray]:
    """Extract Wav2vec 2.0 CLS embedding (768-dim from base model)."""
    global _wav2vec_processor, _wav2vec_model
    if _wav2vec_processor is None:
        try:
            from transformers import Wav2Vec2Processor, Wav2Vec2Model
            import torch
            torch.set_num_threads(1)
            print("[INFO] Loading Wav2vec 2.0 (first run = ~360MB download)...")
            _wav2vec_processor = Wav2Vec2Processor.from_pretrained(
                "facebook/wav2vec2-base-960h"
            )
            _wav2vec_model = Wav2Vec2Model.from_pretrained(
                "facebook/wav2vec2-base-960h"
            )
            _wav2vec_model.eval()
            print("[INFO] Wav2vec 2.0 loaded.")
        except Exception as e:
            print(f"[ERROR] Wav2vec load failed: {e}")
            return None

    try:
        import torch
        print(f"  [DEBUG] Loading audio for {audio_path}...")
        audio = load_audio(audio_path)
        if audio is None:
            return None
        print(f"  [DEBUG] Processing audio tensors...")
        inputs = _wav2vec_processor(
            audio, sampling_rate=16000, return_tensors="pt", padding=True
        )
        print(f"  [DEBUG] Model forward pass...")
        with torch.no_grad():
            outputs = _wav2vec_model(**inputs)
        print(f"  [DEBUG] Post-processing embeddings...")
        # Mean-pool hidden states over time  →  (768,)
        embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
        return embedding.astype(np.float32)
    except Exception as e:
        print(f"[WARN] Wav2vec failed for {audio_path}: {e}")
        return None


# ---------------------------------------------------------------------------
# Whisper large-v3 encoder
# ---------------------------------------------------------------------------

_whisper_models = {}  # Map of model_size -> model

def extract_whisper(audio_path: str, transcribe: bool = False, model_size: str = "large-v3") -> tuple[Optional[np.ndarray], Optional[str]]:
    """
    Run Whisper, return mean-pooled encoder embeddings (1280 or model-specific dim).
    If transcribe=True, also returns the ASR text.
    """
    global _whisper_models
    if model_size not in _whisper_models:
        try:
            import whisper
            print(f"[INFO] Loading Whisper {model_size} (on CPU)...")
            _whisper_models[model_size] = whisper.load_model(model_size, device="cpu")
        except Exception as e:
            print(f"[ERROR] Whisper {model_size} load failed: {e}")
            return None, None
    
    model = _whisper_models[model_size]

    try:
        import whisper
        import torch
        audio = whisper.load_audio(audio_path)
        audio = whisper.pad_or_trim(audio)
        
        # Whisper large-v3 requires 128 mel bins; others (base, small) use 80.
        n_mels = 128 if "large-v3" in model_size else 80
        mel = whisper.log_mel_spectrogram(audio, n_mels=n_mels).to(model.device)
        
        with torch.no_grad():
            encoder_out = model.encoder(mel.unsqueeze(0))
            
            text = None
            if transcribe:
                # Use greedy decoding for clinical speed
                options = whisper.DecodingOptions(fp16=False, language="en")
                result = whisper.decode(model, mel, options)
                text = result.text

        # Mean-pool across time  →  (1280,)
        embedding = encoder_out.mean(dim=1).squeeze().cpu().numpy()
        return embedding.astype(np.float32), text
    except Exception as e:
        print(f"[WARN] Whisper failed for {audio_path}: {e}")
        return None, None


# ---------------------------------------------------------------------------
# Hand-crafted linguistic features
# ---------------------------------------------------------------------------

def compute_handcrafted(text: str, pause_count: int = 0,
                        n_utterances: int = 1) -> dict:
    """
    Compute hand-crafted linguistic features.
    Returns dict with keys: ttr, filler_rate, avg_utt_len, pause_rate
    """
    tokens = text.lower().split()
    n_tokens = len(tokens) if tokens else 1
    fillers = {"uh", "um", "er", "erm", "hmm", "ah", "like", "you know"}
    filler_count = sum(1 for t in tokens if t in fillers)

    return {
        "ttr": len(set(tokens)) / n_tokens,
        "filler_rate": filler_count / n_tokens,
        "avg_utt_len": n_tokens / max(n_utterances, 1),
        "pause_rate": pause_count / max(n_tokens, 1),
    }


# ---------------------------------------------------------------------------
# Main extraction loop
# ---------------------------------------------------------------------------

def extract_features(df: pd.DataFrame, checkpoint_name: str,
                     extract_acoustic: bool = True,
                     extract_whisper_feats: bool = True) -> pd.DataFrame:
    """
    Run full feature extraction with checkpoint/resume.
    Adds columns: egemaps, wav2vec_emb, whisper_emb, ttr, filler_rate, etc.
    """
    ckpt = load_checkpoint(checkpoint_name)
    already_done = set(ckpt.get("ids", []))

    accum = {k: list(v) for k, v in ckpt.items()}
    if not accum:
        accum = {
            "ids": [], "egemaps": [], "wav2vec_emb": [],
            "whisper_emb": [], "ttr": [], "filler_rate": [],
            "avg_utt_len": [], "pause_rate": [],
        }

    pending = df[~df["id"].isin(already_done)]
    total = len(pending)
    print(f"[INFO] Processing {total} samples (skipping {len(already_done)} already done).")

    for i, (_, row) in enumerate(pending.iterrows()):
        sid = row["id"]
        audio = row.get("audio_path")

        # Acoustic features
        # IMPORTANT: Wav2vec must be extracted BEFORE eGeMAPS to prevent a C++ mutex
        # deadlock on macOS when transformers interacts with opensmile's threading.
        w2v = extract_wav2vec(audio) if (audio and extract_acoustic) else None
        egemaps = extract_egemaps(audio) if (audio and extract_acoustic) else None
        whisper_emb, _ = extract_whisper(audio) if (audio and extract_whisper_feats) else (None, None)

        # Hand-crafted
        hc = compute_handcrafted(
            text=str(row.get("text", "")),
            pause_count=int(row.get("pause_count", 0)),
            n_utterances=int(row.get("n_utterances", 1)),
        )

        accum["ids"].append(sid)
        accum["egemaps"].append(egemaps if egemaps is not None else np.zeros(88, dtype=np.float32))
        accum["wav2vec_emb"].append(w2v if w2v is not None else np.zeros(768, dtype=np.float32))
        accum["whisper_emb"].append(whisper_emb if whisper_emb is not None else np.zeros(1280, dtype=np.float32))
        accum["ttr"].append(hc["ttr"])
        accum["filler_rate"].append(hc["filler_rate"])
        accum["avg_utt_len"].append(hc["avg_utt_len"])
        accum["pause_rate"].append(hc["pause_rate"])

        # Checkpoint every N samples
        if (i + 1) % CHECKPOINT_EVERY == 0:
            save_checkpoint(checkpoint_name, accum)
            print(f"  [{i+1}/{total}] Checkpoint saved.")

    # Final save
    save_checkpoint(checkpoint_name, accum)

    # Merge back into DataFrame
    feat_df = pd.DataFrame({
        "id": accum["ids"],
        "egemaps": accum["egemaps"],
        "wav2vec_emb": accum["wav2vec_emb"],
        "whisper_emb": accum["whisper_emb"],
        "ttr_feat": accum["ttr"],
        "filler_rate": accum["filler_rate"],
        "avg_utt_len": accum["avg_utt_len"],
        "pause_rate_feat": accum["pause_rate"],
    })
    return df.merge(feat_df, on="id", how="left")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract features for cognitive loss detection.")
    parser.add_argument("--dataset", choices=["adress", "pitt", "taukadial", "all"], default="adress")
    parser.add_argument("--split", default="train", help="train|test (for adress)")
    parser.add_argument("--no-whisper", action="store_true", help="Skip Whisper (faster)")
    parser.add_argument("--no-acoustic", action="store_true", help="Skip eGeMAPS + Wav2vec")
    args = parser.parse_args()

    PROJECT = Path("/Users/shyam/Desktop/cognitive_project")
    from data_loader import load_all_datasets

    datasets = load_all_datasets(
        adress_dir=str(PROJECT / "adress2020/ADReSS-IS2020-data"),
        pitt_audio_dir=str(PROJECT / "pitt_audio"),
        pitt_transcript_dir=str(PROJECT / "pitt_transcripts"),
        taukadial_dir=str(PROJECT / "taukadial/TAUKADIAL-24"),
        exclusion_csv=str(PROJECT / "pitt_adress_exclusion.csv"),
        convert_moca=True,
    )

    targets = {
        "adress": [("adress_train", f"adress_{args.split}")],
        "pitt": [("pitt", "pitt")],
        "taukadial": [("taukadial", "taukadial")],
        "all": [
            ("adress_train", "adress_train"), ("adress_test", "adress_test"),
            ("pitt", "pitt"), ("taukadial", "taukadial")
        ],
    }

    for key, ckpt_name in targets[args.dataset]:
        print(f"\n{'='*60}\nExtracting: {key}\n{'='*60}")
        df = datasets[key]
        df_out = extract_features(
            df, ckpt_name,
            extract_acoustic=not args.no_acoustic,
            extract_whisper_feats=not args.no_whisper,
        )
        out_path = PROJECT / "feature_cache" / f"{ckpt_name}_features.parquet"
        df_out.to_parquet(str(out_path), index=False)
        print(f"[DONE] Saved to {out_path}")
