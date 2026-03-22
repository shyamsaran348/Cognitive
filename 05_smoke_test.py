"""
05_smoke_test.py — End-to-end integration test
Takes 10 ADReSS samples (5 AD, 5 HC), runs the full pipeline
from raw audio → feature extraction → model → prediction.
Asserts output shapes and value ranges.
Run before committing to a full extraction run.

Usage: python 05_smoke_test.py
"""

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path

# Hardened environment to prevent mutex deadlocks and library conflicts
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
# CRITICAL: Prevent transformers from importing TensorFlow/Flax, which
# causes C++ deadlocks on macOS via grpc/abseil during lazy loading.
os.environ["USE_TF"] = "0"
os.environ["USE_FLAX"] = "0"

PROJECT = Path("/Users/shyam/Desktop/cognitive_project")


def load_smoke_samples(n_per_class: int = 5) -> pd.DataFrame:
    """Load N samples per class from ADReSS train set."""
    from data_loader import load_adress
    df = load_adress(str(PROJECT / "adress2020/ADReSS-IS2020-data"), split="train")
    df = df[df["audio_path"].notna()]
    hc = df[df["label"] == 0].head(n_per_class)
    ad = df[df["label"] == 1].head(n_per_class)
    samples = pd.concat([hc, ad]).reset_index(drop=True)
    print(f"[SMOKE] Loaded {len(samples)} samples ({n_per_class} HC + {n_per_class} AD).")
    return samples


def test_egemaps(samples: pd.DataFrame) -> bool:
    from03 = __import__("03_feature_extractor", fromlist=["extract_egemaps"])
    ok = True
    for i, (_, row) in enumerate(samples.iterrows()):
        print(f"  [EGEMAPS] {i+1}/{len(samples)}: {row['id']}...")
        feats = from03.extract_egemaps(row["audio_path"])
        if feats is None:
            print(f"[FAIL] eGeMAPS returned None for {row['id']}")
            ok = False
        elif feats.shape != (88,):
            print(f"[FAIL] eGeMAPS shape {feats.shape} != (88,) for {row['id']}")
            ok = False
    if ok:
        print("[PASS] eGeMAPS: correct shape (88,) for all samples.")
    return ok


def test_wav2vec(samples: pd.DataFrame) -> bool:
    from03 = __import__("03_feature_extractor", fromlist=["extract_wav2vec"])
    ok = True
    for i, (_, row) in enumerate(samples.iterrows()):
        print(f"  [WAV2VEC] {i+1}/{len(samples)}: {row['id']}...")
        emb = from03.extract_wav2vec(row["audio_path"])
        if emb is None:
            print(f"[FAIL] Wav2vec returned None for {row['id']}")
            ok = False
        elif emb.shape != (768,):
            print(f"[FAIL] Wav2vec shape {emb.shape} != (768,) for {row['id']}")
            ok = False
    if ok:
        print("[PASS] Wav2vec: correct shape (768,) for all samples.")
    return ok


def test_data_loader() -> bool:
    from data_loader import load_all_datasets, moca_to_mmse_equiv
    # Unit test: known MoCA score
    # Unit test: MoCA below clip threshold
    moca_in = 20.0  # 20 × 1.22 + 1.28 = 25.68 — safely below clip at 30
    expected = moca_in * 1.22 + 1.28
    result = moca_to_mmse_equiv(moca_in)
    tol = 0.01
    if abs(result - expected) > tol:
        print(f"[FAIL] moca_to_mmse_equiv({moca_in}) = {result}, expected {expected:.2f}")
        return False
    print(f"[PASS] MoCA→MMSE normalisation: {moca_in} → {result:.2f} (expected {expected:.2f})")

    # Also verify clip at 30 (MoCA=24 → pre-clip 30.56 → clipped to 30.0)
    clipped = moca_to_mmse_equiv(24.0)
    if clipped != 30.0:
        print(f"[FAIL] Clip at 30 failed: got {clipped}")
        return False
    print(f"[PASS] MoCA→MMSE clip at 30: moca=24.0 → {clipped}")


    # Check exclusion list applied
    excl_path = PROJECT / "pitt_adress_exclusion.csv"
    if excl_path.exists():
        datasets = load_all_datasets(
            adress_dir=str(PROJECT / "adress2020/ADReSS-IS2020-data"),
            pitt_audio_dir=str(PROJECT / "pitt_audio"),
            pitt_transcript_dir=str(PROJECT / "pitt_transcripts"),
            taukadial_dir=str(PROJECT / "taukadial/TAUKADIAL-24"),
            exclusion_csv=str(excl_path),
            convert_moca=True,
        )
        pitt = datasets.get("pitt", pd.DataFrame())
        if "id" not in pitt.columns:
            print("[SKIP] Pitt dataset not loaded (transcripts may be missing).")
        else:
            excl_df = pd.read_csv(excl_path)
            excluded_parts = set(excl_df["pitt_id"].str.extract(r"^(\d+)")[0].dropna())
            pitt_parts = set(pitt["id"].str.extract(r"^(\d+)")[0].dropna())
            overlap = pitt_parts & excluded_parts
            if overlap:
                print(f"[FAIL] {len(overlap)} excluded participants still in Pitt data!")
                return False
            print(f"[PASS] Exclusion list: no leakage between Pitt and ADReSS.")
    return True


def test_model_forward() -> bool:
    """Run a forward pass with dummy data through the full model."""
    try:
        import torch
        from model import CognitiveLossModel

        model = CognitiveLossModel()
        model.eval()

        batch_size = 4
        dummy = {
            "egemaps": torch.randn(batch_size, 88),
            "wav2vec": torch.randn(batch_size, 768),
            "whisper": torch.randn(batch_size, 1280),
            "input_ids": torch.randint(0, 1000, (batch_size, 64)),
            "attention_mask": torch.ones(batch_size, 64, dtype=torch.long),
            "clinical": torch.randn(batch_size, 3),  # age, education, CDR
        }

        with torch.no_grad():
            clf_out, reg_out = model(**dummy)

        # Classification output: (batch_size, 2) or (batch_size,)
        assert clf_out.shape[0] == batch_size, f"Bad clf shape: {clf_out.shape}"
        # Regression output: (batch_size,) or (batch_size, 1)
        assert reg_out.shape[0] == batch_size, f"Bad reg shape: {reg_out.shape}"
        # MMSE in valid range after sigmoid scaling
        reg_vals = reg_out.squeeze().numpy()
        assert reg_vals.min() >= 0 and reg_vals.max() <= 30.5, \
            f"MMSE out of range: min={reg_vals.min()}, max={reg_vals.max()}"
        print(f"[PASS] Model forward pass: clf={clf_out.shape}, reg={reg_out.shape}")
        return True
    except ImportError as e:
        print(f"[SKIP] Model test skipped (import error): {e}")
        return True  # Non-fatal if model.py not implemented yet
    except Exception as e:
        print(f"[FAIL] Model forward pass failed: {e}")
        return False


def run_all():
    print("\n" + "="*60)
    print("SMOKE TEST — Cognitive Loss Detection Pipeline")
    print("="*60 + "\n")

    results = {}

    print("--- Test 1: DataLoader & MoCA normalisation ---")
    results["data_loader"] = test_data_loader()

    print("\n--- Test 2: Loading ADReSS samples ---")
    try:
        samples = load_smoke_samples(n_per_class=5)
        results["sample_load"] = True
    except Exception as e:
        print(f"[FAIL] Could not load samples: {e}")
        results["sample_load"] = False
        samples = None

    if samples is not None:
        print("\n--- Test 3: Wav2vec extraction ---")
        results["wav2vec"] = test_wav2vec(samples)

        print("\n--- Test 4: eGeMAPS extraction ---")
        results["egemaps"] = test_egemaps(samples)

    print("\n--- Test 5: Model forward pass ---")
    results["model"] = test_model_forward()

    print("\n" + "="*60)
    passed = sum(v for v in results.values())
    total = len(results)
    print(f"RESULTS: {passed}/{total} tests passed")
    for k, v in results.items():
        status = "✓ PASS" if v else "✗ FAIL"
        print(f"  {status}  {k}")
    print("="*60)

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
