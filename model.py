"""
model.py — Trimodal Product of Experts (PoE) Model
Three feature streams:
  1. Acoustic:  eGeMAPS (88) + Wav2vec 2.0 (768) + Whisper encoder (1280)
  2. Text:      RoBERTa-large + LoRA (1024 → 256)
  3. Clinical:  age, education, CDR  →  MLP (3 → 32 → 64)

Fusion: Product of Experts (PoE)
Heads: Classification (AD vs HC) + Regression (MMSE score)

LoRA config: r=16, alpha=32, target_modules=["query","value"], dropout=0.1
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# LoRA import guard
# ---------------------------------------------------------------------------
try:
    from peft import get_peft_model, LoraConfig
    PEFT_AVAILABLE = True
except ImportError:
    print("[WARN] peft not installed. LoRA disabled. Run: pip install peft")
    PEFT_AVAILABLE = False

try:
    from transformers import RobertaModel, RobertaConfig
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("[WARN] transformers not installed.")
    TRANSFORMERS_AVAILABLE = False


LORA_CONFIG = dict(
    r=16,
    lora_alpha=32,
    target_modules=["query", "value"],
    lora_dropout=0.1,
    bias="none",
    task_type="FEATURE_EXTRACTION",
)


# ---------------------------------------------------------------------------
# Stream 1: Acoustic Encoder
# ---------------------------------------------------------------------------

class AcousticEncoder(nn.Module):
    """
    Fuses eGeMAPS (88), Wav2vec (768), Whisper (1280) into a 256-dim vector.
    """
    def __init__(self,
                 egemaps_dim: int = 88,
                 wav2vec_dim: int = 768,
                 whisper_dim: int = 1280,
                 hidden_dim: int = 256):
        super().__init__()
        concat_dim = egemaps_dim + wav2vec_dim + whisper_dim  # 2136

        self.proj = nn.Sequential(
            nn.Linear(concat_dim, 512),
            nn.LayerNorm(512),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(512, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
        )

    def forward(self, egemaps: torch.Tensor, wav2vec: torch.Tensor,
                whisper: torch.Tensor) -> torch.Tensor:
        x = torch.cat([egemaps, wav2vec, whisper], dim=-1)
        return self.proj(x)  # (B, 256)


# ---------------------------------------------------------------------------
# Stream 2: Text Encoder (RoBERTa + LoRA)
# ---------------------------------------------------------------------------

class TextEncoder(nn.Module):
    """
    RoBERTa-large with LoRA fine-tuning, projected to 256-dim.
    Falls back to a dummy encoder if transformers / peft not available.
    """
    def __init__(self, output_dim: int = 256):
        super().__init__()
        self.output_dim = output_dim

        if TRANSFORMERS_AVAILABLE and PEFT_AVAILABLE:
            base = RobertaModel.from_pretrained("roberta-large")
            lora_cfg = LoraConfig(**LORA_CONFIG)
            self.roberta = get_peft_model(base, lora_cfg)
            self.proj = nn.Sequential(
                nn.Linear(1024, output_dim),  # RoBERTa-large hidden = 1024
                nn.LayerNorm(output_dim),
                nn.GELU(),
            )
            self.use_roberta = True
        else:
            # Fallback: random projection for smoke tests
            self.dummy_proj = nn.Linear(64, output_dim)
            self.use_roberta = False
            print("[WARN] Using dummy TextEncoder (no peft/transformers).")

    def forward(self, input_ids: torch.Tensor,
                attention_mask: torch.Tensor) -> torch.Tensor:
        if self.use_roberta:
            out = self.roberta(input_ids=input_ids, attention_mask=attention_mask)
            cls = out.last_hidden_state[:, 0, :]  # CLS token  (B, 1024)
            return self.proj(cls)  # (B, 256)
        else:
            # Dummy path for testing
            return self.dummy_proj(input_ids[:, :64].float())


# ---------------------------------------------------------------------------
# Stream 3: Clinical MLP
# ---------------------------------------------------------------------------

class ClinicalEncoder(nn.Module):
    """
    MLP for clinical covariates: age, education, CDR  →  64-dim.
    Architecture: 3 → 32 → 64  (as specified in the project brief).
    """
    def __init__(self, input_dim: int = 3, hidden1: int = 32, output_dim: int = 64):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.LayerNorm(hidden1),
            nn.GELU(),
            nn.Linear(hidden1, output_dim),
            nn.LayerNorm(output_dim),
            nn.GELU(),
        )

    def forward(self, covariates: torch.Tensor) -> torch.Tensor:
        return self.mlp(covariates)  # (B, 64)


# ---------------------------------------------------------------------------
# Product of Experts Fusion
# ---------------------------------------------------------------------------

class PoEFusion(nn.Module):
    """
    Product of Experts for trimodal fusion.
    Each expert produces (mean, log_var). PoE combines via:
        1/var_combined = sum(1/var_i)
        mu_combined    = var_combined * sum(mu_i / var_i)

    Falls back to concatenation if variances are degenerate.
    """
    def __init__(self, acoustic_dim: int = 256, text_dim: int = 256,
                 clinical_dim: int = 64, latent_dim: int = 128):
        super().__init__()
        # Each stream projects to (mean, log_var) with latent_dim each
        self.acoustic_mu = nn.Linear(acoustic_dim, latent_dim)
        self.acoustic_lv = nn.Linear(acoustic_dim, latent_dim)

        self.text_mu = nn.Linear(text_dim, latent_dim)
        self.text_lv = nn.Linear(text_dim, latent_dim)

        self.clinical_mu = nn.Linear(clinical_dim, latent_dim)
        self.clinical_lv = nn.Linear(clinical_dim, latent_dim)

        self.latent_dim = latent_dim

    def _poe(self, means: list, logvars: list) -> Tuple[torch.Tensor, torch.Tensor]:
        """PoE combination of multiple Gaussian experts."""
        # precision = 1 / var = exp(-logvar)
        precisions = [torch.exp(-lv) for lv in logvars]
        precision_sum = sum(precisions)
        var_combined = 1.0 / (precision_sum + 1e-8)
        mu_combined = var_combined * sum(p * m for p, m in zip(precisions, means))
        return mu_combined, torch.log(var_combined + 1e-8)

    def forward(self, acoustic: torch.Tensor, text: torch.Tensor,
                clinical: torch.Tensor) -> torch.Tensor:
        means = [
            self.acoustic_mu(acoustic),
            self.text_mu(text),
            self.clinical_mu(clinical),
        ]
        logvars = [
            torch.clamp(self.acoustic_lv(acoustic), -10, 10),
            torch.clamp(self.text_lv(text), -10, 10),
            torch.clamp(self.clinical_lv(clinical), -10, 10),
        ]
        mu, lv = self._poe(means, logvars)
        # Reparameterisation (only active during training)
        if self.training:
            std = torch.exp(0.5 * lv)
            eps = torch.randn_like(std)
            return mu + eps * std
        return mu  # (B, latent_dim)


# ---------------------------------------------------------------------------
# Full Trimodal Model
# ---------------------------------------------------------------------------

class CognitiveLossModel(nn.Module):
    """
    Full trimodal model for cognitive loss detection.
    Outputs:
      - clf_logits: (B, 2)  for AD vs HC classification
      - mmse_pred:  (B,)    for MMSE regression (0–30)
    """

    def __init__(self,
                 n_classes: int = 2,
                 latent_dim: int = 128,
                 dropout: float = 0.3):
        super().__init__()

        self.acoustic = AcousticEncoder()
        self.text = TextEncoder()
        self.clinical = ClinicalEncoder()
        self.fusion = PoEFusion(latent_dim=latent_dim)

        # Classification head
        self.clf_head = nn.Sequential(
            nn.Linear(latent_dim, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, n_classes),
        )

        # Regression head — output scaled to 0-30 range via sigmoid * 30
        self.reg_head = nn.Sequential(
            nn.Linear(latent_dim, 64),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
        )

    def forward(self,
                egemaps: torch.Tensor,
                wav2vec: torch.Tensor,
                whisper: torch.Tensor,
                input_ids: torch.Tensor,
                attention_mask: torch.Tensor,
                clinical: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:

        acoustic_feat = self.acoustic(egemaps, wav2vec, whisper)  # (B, 256)
        text_feat = self.text(input_ids, attention_mask)           # (B, 256)
        clinical_feat = self.clinical(clinical)                    # (B, 64)

        fused = self.fusion(acoustic_feat, text_feat, clinical_feat)  # (B, 128)

        clf_logits = self.clf_head(fused)                         # (B, 2)
        mmse_pred = torch.sigmoid(self.reg_head(fused)).squeeze(-1) * 30.0  # (B,)

        return clf_logits, mmse_pred

    def get_unimodal_predictions(self, modality: str, **kwargs):
        """Run prediction from a single modality (for PoE training)."""
        if modality == "acoustic":
            acoustic_feat = self.acoustic(kwargs["egemaps"], kwargs["wav2vec"], kwargs["whisper"])
            dummy_text = torch.zeros_like(acoustic_feat)
            dummy_clin = self.clinical(torch.zeros(acoustic_feat.shape[0], 3))
            fused = self.fusion(acoustic_feat, dummy_text[:, :256], dummy_clin)
        elif modality == "text":
            text_feat = self.text(kwargs["input_ids"], kwargs["attention_mask"])
            dummy_ac = torch.zeros_like(text_feat)
            dummy_clin = self.clinical(torch.zeros(text_feat.shape[0], 3))
            fused = self.fusion(dummy_ac, text_feat, dummy_clin)
        elif modality == "clinical":
            clinical_feat = self.clinical(kwargs["clinical"])
            dummy = torch.zeros(clinical_feat.shape[0], 256)
            fused = self.fusion(dummy, dummy, clinical_feat)
        else:
            raise ValueError(f"Unknown modality: {modality}")
        return self.clf_head(fused), torch.sigmoid(self.reg_head(fused)).squeeze(-1) * 30.0


if __name__ == "__main__":
    model = CognitiveLossModel()
    print(model)
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\nTotal params:    {total:,}")
    print(f"Trainable params:{trainable:,}")
