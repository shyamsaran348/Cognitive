#!/bin/bash

# setup.sh - Environment setup for Cognitive Loss Detection Project

echo "Setting up Python environment..."

# Install core packages
pip install torch torchvision torchaudio
pip install transformers peft openai-whisper
pip install librosa opensmile pylangacq
pip install spacy nltk pydub
pip install pandas numpy scipy matplotlib scikit-learn

# Note: ffmpeg is required for pydub to handle .mp3 files.
# Install it via brew if not already present: brew install ffmpeg


# Download NLP models
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

echo "Environment setup complete."
