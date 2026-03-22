import os
import re
import csv
from pathlib import Path
import pandas as pd
import numpy as np
# pylangacq is imported lazily only if needed; raw parser is preferred
# (pylangacq rejects old-style &uh/&um CHAT notation found in ADReSS/Pitt)


# ---------------------------------------------------------------------------
# Scale normalisation
# ---------------------------------------------------------------------------

def moca_to_mmse_equiv(moca_score: float) -> float:
    """
    Convert MoCA score to an MMSE-equivalent score using the standard
    dementia-literature mapping:  MMSE_equiv = MoCA × 1.22 + 1.28
    Reference: Bergeron et al. (2017) J Geriatr Psychiatry Neurol.
    Valid range: MoCA 0-30  →  MMSE_equiv ≈ 1.28-37.88 (clipped to 30).
    """
    return float(np.clip(moca_score * 1.22 + 1.28, 0, 30))


def normalise_score(score, source: str, convert_moca: bool = True) -> float:
    """
    Normalise a cognitive score to MMSE scale.
    Args:
        score:        Raw score (float or int)
        source:       'mmse' | 'moca'
        convert_moca: If False, returns raw MoCA score unchanged
    """
    if source == "moca" and convert_moca:
        return moca_to_mmse_equiv(float(score))
    return float(score)


# ---------------------------------------------------------------------------
# .cha file parsing — direct regex parser (no pylangacq dependency)
# Handles both modern CHAT (&-uh) and old-style (&uh) filled-pause notation.
# ---------------------------------------------------------------------------

# CHAT annotation patterns to strip from utterance text
_CHAT_STRIP = re.compile(
    r"<[^>]*>"           # <overlap text>
    r"|\[[^\]]*\]"       # [codes like /]
    r"|&[=-][^\s]+"      # &-uh &=laughs (modern)
    r"|&[a-zA-Z]+"       # &uh &um (old-style — causes pylangacq to fail)
    r"|\x15\d+_\d+\x15"  # timestamp bullets
    r"|[+/][\S]*"        # continuation markers
    r"|[<>\[\]@*]"       # remaining CHAT symbols
)
_WHITESPACE = re.compile(r"\s+")

# Both modern (&-uh, &-um) and old-style (&uh, &um) filled pauses
_PAUSE_RE = re.compile(r"&-?u[hm]", re.IGNORECASE)


def parse_cha_file(filepath: str) -> dict:
    """
    Parse a CHAT format .cha file using direct regex (no pylangacq).
    Handles all CHAT variants including old-style &uh / &um notation.

    Returns dict with keys:
        text, mmse, age, gender, dx,
        pause_count, word_count, n_utterances
    """
    meta = {
        "text": "", "mmse": None, "age": None,
        "gender": None, "dx": None,
        "pause_count": 0, "word_count": 0, "n_utterances": 0,
    }

    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        print(f"[WARN] Cannot open {filepath}: {e}")
        return meta

    words = []
    pause_count = 0
    n_utterances = 0

    for line in lines:
        # --- Header: extract participant metadata from @ID ---
        if line.startswith("@ID:") and "|PAR|" in line:
            parts = line.split("|")
            if len(parts) >= 10:
                age_str = parts[3].replace(";", "").strip()
                try:
                    meta["age"] = float(age_str) if age_str else None
                except ValueError:
                    pass
                meta["gender"] = parts[4].strip().lower()[:1]
                group = parts[5].strip().lower()
                if "control" in group:
                    meta["dx"] = "Control"
                elif any(k in group for k in ("dementia", "ad", "probable", "mci")):
                    meta["dx"] = "Dementia"
                mmse_str = parts[8].strip()
                try:
                    meta["mmse"] = float(mmse_str) if mmse_str else None
                except ValueError:
                    pass
            continue

        # --- PAR utterance lines ---
        if not line.startswith("*PAR:"):
            continue

        n_utterances += 1
        raw = line[5:].strip()  # strip "*PAR:"

        # Count filled pauses BEFORE cleaning (both &uh and &-uh)
        pause_count += len(_PAUSE_RE.findall(raw))

        # Strip CHAT annotations, normalise whitespace
        cleaned = _CHAT_STRIP.sub(" ", raw)
        cleaned = _WHITESPACE.sub(" ", cleaned).strip()
        # Remove trailing sentence-final punctuation
        cleaned = cleaned.rstrip(". ?!,;:")
        token_list = [t for t in cleaned.split() if t]
        words.extend(token_list)

    meta["text"] = " ".join(words)
    meta["word_count"] = len(words)
    meta["pause_count"] = pause_count
    meta["n_utterances"] = n_utterances
    return meta


def type_token_ratio(text: str) -> float:
    """Compute TTR — type diversity metric."""
    tokens = text.lower().split()
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)




# ---------------------------------------------------------------------------
# ADReSS 2020 loader
# ---------------------------------------------------------------------------

def load_adress(base_dir: str, split: str = "train",
                include_clinical: bool = True) -> pd.DataFrame:
    """
    Load ADReSS 2020 dataset.
    Args:
        base_dir: path to ADReSS-IS2020-data/
        split:    'train' | 'test'
        include_clinical: whether to load age/gender covariates
    Returns: DataFrame with columns [id, audio_path, transcript_path,
                                     label, mmse, age, gender, text, ...]
    """
    base = Path(base_dir) / split
    rows = []

    for group, label in [("cc", 0), ("cd", 1)]:
        # Audio
        audio_dir = base / "Full_wave_enhanced_audio" / group
        # Transcripts
        trans_dir = base / "transcription" / group
        if not trans_dir.exists():
            trans_dir = base / "transcription"  # test set has flat structure

        # Metadata
        if split == "train":
            meta_file = base / (f"{group}_meta_data.txt")
            meta_df = pd.read_csv(meta_file, sep=";", skipinitialspace=True)
            meta_df.columns = meta_df.columns.str.strip()
            meta_df["ID"] = meta_df["ID"].str.strip()
        else:
            meta_df = None

        cha_files = sorted(trans_dir.glob("*.cha")) if trans_dir.exists() else []

        for cha_file in cha_files:
            sid = cha_file.stem  # e.g. "S001"
            audio_path = audio_dir / f"{sid}.wav" if audio_dir.exists() else None

            row = {
                "id": sid,
                "dataset": "adress",
                "split": split,
                "audio_path": str(audio_path) if audio_path and audio_path.exists() else None,
                "transcript_path": str(cha_file),
                "label": label,  # 0=HC, 1=AD
                "mmse": None,
                "mmse_source": "mmse",
                "age": None,
                "gender": None,
                "education": None,  # Not provided in ADReSS
                "cdr": None,
                "language": "en",
            }

            if meta_df is not None:
                m = meta_df[meta_df["ID"] == sid]
                if not m.empty:
                    row["mmse"] = float(m.iloc[0]["mmse"]) if str(m.iloc[0]["mmse"]).strip() != "NA" else None
                    row["age"] = float(m.iloc[0]["age"])
                    row["gender"] = m.iloc[0]["gender"].strip().lower()[:1]

            # Parse .cha
            cha_data = parse_cha_file(str(cha_file))
            row.update({
                "text": cha_data.get("text", ""),
                "word_count": cha_data.get("word_count", 0),
                "pause_count": cha_data.get("pause_count", 0),
                "n_utterances": cha_data.get("n_utterances", 0),
                "ttr": type_token_ratio(cha_data.get("text", "")),
            })
            rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pitt Corpus loader
# ---------------------------------------------------------------------------

def load_pitt(pitt_audio_dir: str, pitt_transcript_dir: str,
              exclusion_csv: str = None) -> pd.DataFrame:
    """
    Load Pitt Corpus audio + transcripts.
    Applies exclusion list (ADReSS participants already covered) to
    prevent data leakage.

    Args:
        pitt_audio_dir:       path to pitt_audio/ (Control/ + Dementia/)
        pitt_transcript_dir:  path to pitt_transcripts/ (Control/cookie/ etc.)
        exclusion_csv:        path to pitt_adress_exclusion.csv
    """
    base_audio = Path(pitt_audio_dir)
    base_trans = Path(pitt_transcript_dir)

    # Load exclusion list
    excluded_pitt_ids = set()
    if exclusion_csv and Path(exclusion_csv).exists():
        excl_df = pd.read_csv(exclusion_csv)
        # pitt_id format: "001-0"  →  exclude ALL visits for that participant
        excluded_parts = set(excl_df["pitt_id"].str.extract(r"^(\d+)")[0].dropna())
        excluded_pitt_ids = excluded_parts
        print(f"[INFO] Excluding {len(excluded_parts)} Pitt participants (ADReSS overlap).")

    rows = []
    for group, label in [("Control", 0), ("Dementia", 1)]:
        audio_dir = base_audio / group
        trans_dir = base_trans / group / "cookie"

        if not audio_dir.exists():
            print(f"[WARN] Audio dir not found: {audio_dir}")
            continue
        if not trans_dir.exists():
            print(f"[WARN] Transcript dir not found: {trans_dir}")
            continue

        for mp3_file in sorted(audio_dir.glob("*.mp3")):
            stem = mp3_file.stem  # e.g. "002-0"
            part_id = stem.split("-")[0]  # "002"

            if part_id in excluded_pitt_ids:
                continue

            cha_file = trans_dir / f"{stem}.cha"
            row = {
                "id": stem,
                "dataset": "pitt",
                "split": "pretrain",
                "audio_path": str(mp3_file),
                "transcript_path": str(cha_file) if cha_file.exists() else None,
                "label": label,
                "mmse": None,
                "mmse_source": "mmse",
                "age": None,
                "gender": None,
                "education": None,
                "cdr": None,
                "language": "en",
                "text": "",
                "word_count": 0,
                "pause_count": 0,
                "n_utterances": 0,
                "ttr": 0.0,
            }

            if cha_file.exists():
                cha_data = parse_cha_file(str(cha_file))
                row.update({
                    "text": cha_data.get("text", ""),
                    "word_count": cha_data.get("word_count", 0),
                    "pause_count": cha_data.get("pause_count", 0),
                    "n_utterances": cha_data.get("n_utterances", 0),
                    "ttr": type_token_ratio(cha_data.get("text", "")),
                    "mmse": cha_data.get("mmse"),
                    "age": cha_data.get("age"),
                    "gender": cha_data.get("gender"),
                })
            rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# TAUKADIAL 2024 loader
# ---------------------------------------------------------------------------

def load_taukadial(taukadial_dir: str,
                   convert_moca: bool = True) -> pd.DataFrame:
    """
    Load TAUKADIAL 2024 dataset.
    Args:
        taukadial_dir:  path to TAUKADIAL-24/
        convert_moca:   if True, apply MoCA → MMSE equivalent conversion
    Returns: DataFrame; includes 'language' column ('en' or 'zh').
    """
    base = Path(taukadial_dir)

    # Language detection: participant IDs ≤ 169 are known English speakers
    # per the TAUKADIAL dataset paper conventions.
    # participant IDs for English: listed in supplementary — we infer from
    # the groundtruth which includes no explicit language tag.
    # Heuristic: IDs 1–83 are Chinese, 84–169 are English (per ADReSS24 paper).
    # NOTE: update this mapping if you have the official language metadata.
    ENGLISH_IDS = set(range(84, 170))

    rows = []
    for split_name in ["train", "test"]:
        split_dir = base / split_name
        if not split_dir.exists():
            continue

        # Labels
        if split_name == "train":
            gt_file = split_dir / "groundtruth.csv"
            gt_df = pd.read_csv(gt_file, sep=None, engine='python') if gt_file.exists() else None
        else:
            gt_file = base.parent / "testgroundtruth.csv"
            gt_df = pd.read_csv(gt_file, sep=None, engine='python') if gt_file.exists() else None

        for wav_file in sorted(split_dir.glob("taukdial-*.wav")):
            fname = wav_file.name  # "taukdial-002-1.wav"
            # Extract participant ID
            m = re.match(r"taukdial-(\d+)-\d+\.wav", fname)
            if not m:
                continue
            part_id = int(m.group(1))
            language = "en" if part_id in ENGLISH_IDS else "zh"

            row = {
                "id": fname.replace(".wav", ""),
                "dataset": "taukadial",
                "split": split_name,
                "audio_path": str(wav_file),
                "transcript_path": None,  # TAUKADIAL has no .cha files
                "label": None,
                "mmse": None,
                "mmse_source": "moca",  # TAUKADIAL uses MoCA
                "mmse_normalised": None,
                "age": None,
                "gender": None,
                "education": None,
                "cdr": None,
                "language": language,
                "text": "",
                "word_count": 0,
                "pause_count": 0,
                "n_utterances": 0,
                "ttr": 0.0,
            }

            if gt_df is not None:
                match = gt_df[gt_df["tkdname"] == fname]
                if not match.empty:
                    r = match.iloc[0]
                    raw_mmse = float(r["mmse"]) if "mmse" in r else None
                    dx = str(r.get("dx", "")).strip().upper()
                    row["label"] = 0 if dx == "NC" else 1  # NC=0, MCI=1
                    row["age"] = float(r["age"]) if "age" in r else None
                    row["gender"] = str(r.get("sex", "")).strip().lower()[:1]
                    row["mmse"] = raw_mmse
                    row["mmse_normalised"] = normalise_score(
                        raw_mmse, source="moca", convert_moca=convert_moca
                    ) if raw_mmse is not None else None

            rows.append(row)

    df = pd.DataFrame(rows)
    # For TAUKADIAL, use normalised MMSE for regression (if enabled)
    if convert_moca and "mmse_normalised" in df.columns:
        df["mmse_regression_target"] = df["mmse_normalised"]
    else:
        df["mmse_regression_target"] = df["mmse"]
    return df


# ---------------------------------------------------------------------------
# Unified loader
# ---------------------------------------------------------------------------

def load_all_datasets(
    adress_dir: str,
    pitt_audio_dir: str,
    pitt_transcript_dir: str,
    taukadial_dir: str,
    exclusion_csv: str = None,
    convert_moca: bool = True,
    include_pitt: bool = True,
) -> dict:
    """
    Load all datasets and return a dict of DataFrames.
    ADReSS is always the primary benchmark (no leakage).
    Pitt is used for pretraining only (with exclusion applied).
    TAUKADIAL is secondary benchmark (MCI detection).
    """
    print("Loading ADReSS 2020...")
    adress_train = load_adress(adress_dir, split="train")
    adress_test = load_adress(adress_dir, split="test")

    # ADReSS regression target
    adress_train["mmse_regression_target"] = adress_train["mmse"]
    adress_test["mmse_regression_target"] = adress_test["mmse"]

    result = {
        "adress_train": adress_train,
        "adress_test": adress_test,
    }

    if include_pitt:
        print("Loading Pitt Corpus (pretraining)...")
        pitt = load_pitt(pitt_audio_dir, pitt_transcript_dir, exclusion_csv)
        pitt["mmse_regression_target"] = pitt["mmse"]
        result["pitt"] = pitt

    print("Loading TAUKADIAL 2024...")
    taukadial = load_taukadial(taukadial_dir, convert_moca=convert_moca)
    result["taukadial"] = taukadial

    # Summary
    for k, v in result.items():
        n = len(v)
        n_labeled = v["label"].notna().sum() if "label" in v.columns else "?"
        print(f"  [{k}] {n} samples, {n_labeled} labeled")

    return result


# ---------------------------------------------------------------------------
# Language-stratified K-Fold for TAUKADIAL
# ---------------------------------------------------------------------------

def get_taukadial_stratified_folds(df: pd.DataFrame, n_folds: int = 5) -> list:
    """
    Build K-Fold splits that keep English and Chinese samples in separate
    groups — prevents cross-language acoustic leakage.
    Returns list of (train_idx, val_idx) tuples (by DataFrame index).
    """
    from sklearn.model_selection import StratifiedKFold

    en_df = df[df["language"] == "en"].copy()
    zh_df = df[df["language"] == "zh"].copy()

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    en_folds = list(skf.split(en_df, en_df["label"]))
    zh_folds = list(skf.split(zh_df, zh_df["label"]))

    folds = []
    for (en_tr, en_val), (zh_tr, zh_val) in zip(en_folds, zh_folds):
        train_idx = list(en_df.index[en_tr]) + list(zh_df.index[zh_tr])
        val_idx = list(en_df.index[en_val]) + list(zh_df.index[zh_val])
        folds.append((train_idx, val_idx))
    return folds


if __name__ == "__main__":
    PROJECT = Path("/Users/shyam/Desktop/cognitive_project")
    datasets = load_all_datasets(
        adress_dir=str(PROJECT / "adress2020/ADReSS-IS2020-data"),
        pitt_audio_dir=str(PROJECT / "pitt_audio"),
        pitt_transcript_dir=str(PROJECT / "pitt_transcripts"),
        taukadial_dir=str(PROJECT / "taukadial/TAUKADIAL-24"),
        exclusion_csv=str(PROJECT / "pitt_adress_exclusion.csv"),
        convert_moca=True,
        include_pitt=True,
    )
    for k, df in datasets.items():
        print(f"\n--- {k} ---")
        print(df.dtypes)
        print(df.head(2))
