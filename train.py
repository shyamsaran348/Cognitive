"""
train.py — Stratified K-Fold Training for Cognitive Loss Detection
Features:
  - Weighted cross-entropy (for Pitt class imbalance 242:309)
  - Early stopping (patience=5 on validation loss)
  - ReduceLROnPlateau scheduler
  - Language-stratified K-Fold for TAUKADIAL
  - Joint classification (AD/HC) + regression (MMSE) loss
  - Saves best checkpoint per fold

Usage:
  python train.py --dataset adress  --folds 5
  python train.py --dataset taukadial --folds 5
"""

import os
# --- Core macOS Threading/Deadlock Fixes ---
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

# Crucial to prevent grpc/tensorflow from deadlocking C++ mutex on Mac
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
os.environ["USE_TF"] = "0"
os.environ["USE_FLAX"] = "0"
# -------------------------------------------

import argparse
import numpy as np

import pandas as pd
from pathlib import Path
from typing import Optional

import torch
torch.set_num_threads(1)  # Core macOS thread fix
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score, f1_score
from sklearn.preprocessing import StandardScaler
from transformers import RobertaTokenizer

from model import CognitiveLossModel
from data_loader import get_taukadial_stratified_folds

PROJECT = Path("/Users/shyam/Desktop/cognitive_project")
FEATURE_CACHE = PROJECT / "feature_cache"
CHECKPOINT_SAVE = PROJECT / "model_checkpoints"
CHECKPOINT_SAVE.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class CognitiveDataset(Dataset):
    def __init__(self, df: pd.DataFrame, tokenizer, max_len: int = 256):
        self.df = df.reset_index(drop=True)
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]

        # -- Text --
        text = str(row.get("text", "") or "")
        enc = self.tokenizer(
            text, max_length=self.max_len,
            padding="max_length", truncation=True,
            return_tensors="pt"
        )

        # -- Acoustic features (from precomputed cache) --
        egemaps = torch.tensor(
            row.get("egemaps", np.zeros(88)), dtype=torch.float32
        )
        wav2vec = torch.tensor(
            row.get("wav2vec_emb", np.zeros(768)), dtype=torch.float32
        )
        whisper = torch.tensor(
            row.get("whisper_emb", np.zeros(1280)), dtype=torch.float32
        )

        # -- Clinical covariates: age (normalised), education, CDR --
        age_v = row.get("age")
        age = 65.0 if pd.isna(age_v) else float(age_v)
        
        edu_v = row.get("education")
        edu = 12.0 if pd.isna(edu_v) else float(edu_v)
        
        cdr_v = row.get("cdr")
        cdr = 0.5 if pd.isna(cdr_v) else float(cdr_v)
        
        clinical = torch.tensor([age / 100.0, edu / 20.0, cdr], dtype=torch.float32)

        # -- Labels --
        label = int(row.get("label", 0))
        mmse_v = row.get("mmse_regression_target")
        mmse = 20.0 if pd.isna(mmse_v) else float(mmse_v)

        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "egemaps": egemaps,
            "wav2vec": wav2vec,
            "whisper": whisper,
            "clinical": clinical,
            "label": torch.tensor(label, dtype=torch.long),
            "mmse": torch.tensor(mmse, dtype=torch.float32),
        }


# ---------------------------------------------------------------------------
# Early Stopping
# ---------------------------------------------------------------------------

class EarlyStopping:
    """
    Stop training if validation loss doesn't improve for `patience` epochs.
    Saves the best model weights in memory.
    """
    def __init__(self, patience: int = 5, min_delta: float = 1e-4):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = float("inf")
        self.best_state = None
        self.stop = False

    def __call__(self, val_loss: float, model: nn.Module) -> bool:
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.best_state = {k: v.clone() for k, v in model.state_dict().items()}
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.stop = True
        return self.stop

    def restore_best(self, model: nn.Module):
        if self.best_state:
            model.load_state_dict(self.best_state)


# ---------------------------------------------------------------------------
# Loss computation
# ---------------------------------------------------------------------------

def compute_loss(clf_logits, mmse_pred, labels, mmse_targets,
                 cls_weight: Optional[torch.Tensor] = None,
                 clf_weight: float = 1.0,
                 reg_weight: float = 0.5) -> torch.Tensor:
    """
    Combined loss: weighted CE (classification) + MSE (regression).
    reg_weight=0.5 keeps regression from overpowering classification.
    """
    ce_loss = nn.CrossEntropyLoss(weight=cls_weight)(clf_logits, labels)
    # Only compute regression on labeled samples with valid MMSE
    valid_mask = mmse_targets > 0  # 0 = unknown/missing
    if valid_mask.any():
        mse_loss = nn.MSELoss()(mmse_pred[valid_mask], mmse_targets[valid_mask])
    else:
        mse_loss = torch.tensor(0.0)
    return clf_weight * ce_loss + reg_weight * mse_loss


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(model, loader, device, cls_weight=None):
    model.eval()
    total_loss = 0.0
    all_logits, all_labels, all_mmse_pred, all_mmse_gt = [], [], [], []

    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            clf_out, reg_out = model(
                egemaps=batch["egemaps"],
                wav2vec=batch["wav2vec"],
                whisper=batch["whisper"],
                input_ids=batch["input_ids"],
                attention_mask=batch["attention_mask"],
                clinical=batch["clinical"],
            )
            loss = compute_loss(clf_out, reg_out, batch["label"], batch["mmse"],
                                cls_weight=cls_weight)
            total_loss += loss.item()
            all_logits.append(clf_out.cpu())
            all_labels.append(batch["label"].cpu())
            all_mmse_pred.append(reg_out.cpu())
            all_mmse_gt.append(batch["mmse"].cpu())

    logits = torch.cat(all_logits)
    labels = torch.cat(all_labels).numpy()
    probs = torch.softmax(logits, dim=-1)[:, 1].numpy()
    preds = logits.argmax(dim=-1).numpy()
    mmse_pred = torch.cat(all_mmse_pred).numpy()
    mmse_gt = torch.cat(all_mmse_gt).numpy()

    auc = roc_auc_score(labels, probs) if len(np.unique(labels)) > 1 else 0.0
    f1 = f1_score(labels, preds, average="macro", zero_division=0)
    rmse = np.sqrt(np.mean((mmse_pred - mmse_gt) ** 2))
    avg_loss = total_loss / max(len(loader), 1)

    return {"loss": avg_loss, "auc": auc, "f1": f1, "rmse": rmse}


# ---------------------------------------------------------------------------
# K-Fold training loop
# ---------------------------------------------------------------------------

def train_kfold(df: pd.DataFrame, dataset_name: str,
                n_folds: int = 5, n_epochs: int = 50,
                batch_size: int = 8, lr: float = 2e-4,
                is_taukadial: bool = False):

    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
    print(f"[INFO] Training on {device}  |  Folds: {n_folds}  |  Dataset: {dataset_name}")

    tokenizer = RobertaTokenizer.from_pretrained("roberta-large")

    # Compute class weights (relevant for Pitt imbalance)
    label_counts = df["label"].value_counts().sort_index()
    total = label_counts.sum()
    weights = torch.tensor(
        [total / (2.0 * c) for c in label_counts.values], dtype=torch.float32
    ).to(device)

    # Get folds — language-stratified for TAUKADIAL
    if is_taukadial:
        folds = get_taukadial_stratified_folds(df, n_folds)
        fold_pairs = [(df.index.get_indexer(tr), df.index.get_indexer(val))
                      for tr, val in folds]
    else:
        skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
        fold_pairs = list(skf.split(df, df["label"]))

    all_metrics = []

    for fold_idx, (train_idx, val_idx) in enumerate(fold_pairs):
        print(f"\n{'='*50}\nFold {fold_idx+1}/{n_folds}\n{'='*50}")

        train_df = df.iloc[train_idx].reset_index(drop=True)
        val_df = df.iloc[val_idx].reset_index(drop=True)

        train_ds = CognitiveDataset(train_df, tokenizer)
        val_ds = CognitiveDataset(val_df, tokenizer)

        train_loader = DataLoader(train_ds, batch_size=batch_size,
                                  shuffle=True, num_workers=0)
        val_loader = DataLoader(val_ds, batch_size=batch_size,
                                shuffle=False, num_workers=0)

        model = CognitiveLossModel().to(device)
        optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)

        # ReduceLROnPlateau — prevents oscillation when regression head lags
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=3, min_lr=1e-6
        )

        early_stop = EarlyStopping(patience=5)

        best_fold_metrics = {}

        for epoch in range(n_epochs):
            model.train()
            epoch_loss = 0.0

            for batch in train_loader:
                batch = {k: v.to(device) for k, v in batch.items()}
                optimizer.zero_grad()
                clf_out, reg_out = model(
                    egemaps=batch["egemaps"],
                    wav2vec=batch["wav2vec"],
                    whisper=batch["whisper"],
                    input_ids=batch["input_ids"],
                    attention_mask=batch["attention_mask"],
                    clinical=batch["clinical"],
                )
                loss = compute_loss(clf_out, reg_out, batch["label"],
                                    batch["mmse"], cls_weight=weights)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                epoch_loss += loss.item()

            val_metrics = evaluate(model, val_loader, device, cls_weight=weights)
            scheduler.step(val_metrics["loss"])

            print(f"  Epoch {epoch+1:3d} | train_loss={epoch_loss/len(train_loader):.4f}"
                  f" | val_loss={val_metrics['loss']:.4f}"
                  f" | AUC={val_metrics['auc']:.3f}"
                  f" | F1={val_metrics['f1']:.3f}"
                  f" | RMSE={val_metrics['rmse']:.2f}")

            if early_stop(val_metrics["loss"], model):
                print(f"  [EarlyStopping] No improvement for {early_stop.patience} epochs. Stopping.")
                early_stop.restore_best(model)
                best_fold_metrics = val_metrics
                break

            if val_metrics["loss"] == early_stop.best_loss:
                best_fold_metrics = val_metrics

        # Save best fold checkpoint
        ckpt_path = CHECKPOINT_SAVE / f"{dataset_name}_fold{fold_idx+1}_best.pt"
        torch.save({
            "fold": fold_idx + 1,
            "model_state": model.state_dict(),
            "metrics": best_fold_metrics,
        }, ckpt_path)
        print(f"  [SAVE] Best model → {ckpt_path}")
        all_metrics.append(best_fold_metrics)

    # Aggregate across folds
    print(f"\n{'='*50}")
    print(f"Cross-Validation Results — {dataset_name}")
    print(f"{'='*50}")
    for metric in ["auc", "f1", "rmse"]:
        vals = [m[metric] for m in all_metrics if metric in m]
        print(f"  {metric.upper():<8}: {np.mean(vals):.4f} ± {np.std(vals):.4f}")

    return all_metrics


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["adress", "taukadial", "pitt"],
                        default="adress")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=2e-4)
    args = parser.parse_args()

    from data_loader import load_all_datasets

    datasets = load_all_datasets(
        adress_dir=str(PROJECT / "adress2020/ADReSS-IS2020-data"),
        pitt_audio_dir=str(PROJECT / "pitt_audio"),
        pitt_transcript_dir=str(PROJECT / "pitt_transcripts"),
        taukadial_dir=str(PROJECT / "taukadial/TAUKADIAL-24"),
        exclusion_csv=str(PROJECT / "pitt_adress_exclusion.csv"),
        convert_moca=True,
    )

    # Merge feature cache if available
    def merge_features(df, name):
        cache_path = FEATURE_CACHE / f"{name}_features.parquet"
        if cache_path.exists():
            feats = pd.read_parquet(cache_path)
            return df.merge(feats[["id", "egemaps", "wav2vec_emb", "whisper_emb"]],
                            on="id", how="left")
        print(f"[WARN] No feature cache for '{name}'. Using zero vectors.")
        return df

    if args.dataset == "adress":
        df = datasets["adress_train"].dropna(subset=["label"])
        df = merge_features(df, "adress_train")
        train_kfold(df, "adress", n_folds=args.folds,
                    n_epochs=args.epochs, batch_size=args.batch_size,
                    lr=args.lr, is_taukadial=False)

    elif args.dataset == "taukadial":
        df = datasets["taukadial"].dropna(subset=["label"])
        df = merge_features(df, "taukadial")
        train_kfold(df, "taukadial", n_folds=args.folds,
                    n_epochs=args.epochs, batch_size=args.batch_size,
                    lr=args.lr, is_taukadial=True)

    elif args.dataset == "pitt":
        df = datasets["pitt"].dropna(subset=["label"])
        df = merge_features(df, "pitt")
        train_kfold(df, "pitt", n_folds=args.folds,
                    n_epochs=args.epochs, batch_size=args.batch_size,
                    lr=args.lr, is_taukadial=False)
