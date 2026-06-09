"""Native (non-SGLang) Higgs Audio v3 TTS backend.

Serves the same /health and /v1/audio/speech endpoints the Gradio UI expects,
using the plain-transformers port of the model so it runs on Windows and macOS
where SGLang-Omni is unavailable.
"""

import io
import os

import soundfile as sf
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_MODEL_DIR = os.path.join(APP_DIR, "models", "higgs-audio-v3-tts-4b-transformers")
MODEL_ID = LOCAL_MODEL_DIR if os.path.isdir(LOCAL_MODEL_DIR) else "multimodalart/higgs-audio-v3-tts-4b-transformers"

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

if torch.cuda.is_available():
    DEVICE, DTYPE = "cuda", torch.bfloat16
elif torch.backends.mps.is_available():
    DEVICE, DTYPE = "mps", torch.float32
else:
    DEVICE, DTYPE = "cpu", torch.float32

print(f"Loading {MODEL_ID} on {DEVICE} ({DTYPE}) ...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = (
    AutoModelForCausalLM.from_pretrained(MODEL_ID, trust_remote_code=True, dtype=DTYPE)
    .to(DEVICE)
    .eval()
)
model.get_audio_codec()  # preload the 24 kHz codec so the first request isn't slow
SAMPLE_RATE = model.config.sample_rate
print("Model loaded.")

app = FastAPI(title="Higgs Audio v3 TTS (transformers backend)")


class Reference(BaseModel):
    audio_path: str
    text: str | None = ""


class SpeechRequest(BaseModel):
    input: str
    response_format: str | None = "wav"
    temperature: float | None = 0.7
    top_p: float | None = None
    top_k: int | None = None
    max_new_tokens: int | None = 2048
    seed: int | None = None
    references: list[Reference] | None = None


@app.get("/health")
def health():
    return {"status": "ok", "backend": "transformers", "device": DEVICE, "model": MODEL_ID}


@app.post("/v1/audio/speech")
def speech(req: SpeechRequest):
    text = (req.input or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="'input' must be a non-empty string.")

    if req.seed is not None and req.seed >= 0:
        torch.manual_seed(req.seed)

    kwargs = dict(
        max_new_tokens=int(req.max_new_tokens or 2048),
        temperature=float(req.temperature if req.temperature is not None else 0.7),
        top_p=float(req.top_p) if req.top_p is not None and req.top_p < 1.0 else None,
        top_k=int(req.top_k) if req.top_k is not None and req.top_k > 0 else None,
    )

    if req.references:
        ref = req.references[0]
        if not os.path.isfile(ref.audio_path):
            raise HTTPException(status_code=400, detail=f"Reference audio not found: {ref.audio_path}")
        data, sr = sf.read(ref.audio_path, dtype="float32", always_2d=True)  # [L, C]
        kwargs["reference_audio"] = torch.from_numpy(data).mean(dim=1)  # mono [L]
        kwargs["reference_sample_rate"] = sr
        if ref.text and ref.text.strip():
            kwargs["reference_text"] = ref.text.strip()

    audio = model.generate_speech(text, tokenizer, **kwargs)
    if audio.numel() == 0:
        raise HTTPException(status_code=500, detail="Generation produced no audio. Try again or adjust the text.")

    buf = io.BytesIO()
    sf.write(buf, audio.numpy(), SAMPLE_RATE, format="WAV")
    return Response(content=buf.getvalue(), media_type="audio/wav")


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
