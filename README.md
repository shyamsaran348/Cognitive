# Cognitive Inference Engine 🧠
**Trimodal Cognitive Loss Detection (Acoustic + Text + Demographics)**

This project provides a professional-grade dashboard for the early detection of Dementia and Alzheimer's Disease using a Product of Experts (PoE) fusion of audio, transcripts, and clinical covariates.

## 🚀 How to Run the Dashboard

To launch the full interactive experience, follow these two steps:

### 1. Launch the Backend (FastAPI)
This handles the heavy ML inference (Wav2vec, Whisper, opensmile).
```bash
# In the root directory:
uvicorn api:app --port 8000
```

### 2. Launch the Frontend (React + Vite)
This provides the professional Glassmorphic UI.
```bash
cd frontend
npm install  # (First time only)
npm run dev
```

### 3. Access the Dashboard
Open your browser and navigate to:
**[http://localhost:5173](http://localhost:5173)**

---

## ⚡ Presentation/Demo Mode (Simulation)
If you are in a presentation and don't want to wait for the ML models to load (which can take 40+ seconds), the dashboard includes a **Simulation Engine**.

- Simply open the dashboard at `http://localhost:5173`.
- Click the **'Healthy Patient'** or **'AD Patient'** demo buttons.
- The dashboard will instantly simulate a high-fidelity diagnostic walkthrough including MMSE gauge and modality confidence animations—**no backend required**.

---

## 🛠 Project Structure
- `api.py`: FastAPI server wrapping the 06_inference.py core.
- `06_inference.py`: The trimodal inference engine.
- `model.py`: Trimodal Product of Experts (PoE) model architecture.
- `frontend/`: React + Vite application.
