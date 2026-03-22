import os
import sys

# MUST INJECT THREAD PROTECTIONS BEFORE FASTAPI OR TORCH LOAD
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
os.environ["USE_TF"] = "0"
os.environ["USE_FLAX"] = "0"

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import torch

torch.set_num_threads(1) # CRITICAL for macOS inference

# We wrap the existing inference logic directly into the API
from importlib import import_module
inference_module = import_module("06_inference")
run_inference = inference_module.run_inference

app = FastAPI(title="Trimodal Cognitive API")

# Essential for the React frontend to communicate natively with our Python backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/predict")
async def predict(
    audio: UploadFile = File(...),
    transcript: str = Form(...),
    age: float = Form(65.0),
    education: float = Form(12.0),
    cdr: float = Form(0.5)
):
    try:
        # Save the incoming React uploaded file temporarily to the Linux /tmp ramdisk
        temp_audio_path = f"/tmp/{audio.filename}"
        with open(temp_audio_path, 'wb') as out_file:
            out_file.write(await audio.read())

        # Bind to the best trained Kaggle model
        ckpt_path = "model_checkpoints/taukadial_fold5_best.pt"
        
        # Execute the heavy ML pipeline
        result = run_inference(
            audio_path=temp_audio_path,
            transcript=transcript,
            age=age,
            education=education,
            cdr=cdr,
            checkpoint_path=ckpt_path
        )
        
        # Cleanup the RAM cache
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            
        return {"status": "success", "data": result}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
