"""Native (non-SGLang) Higgs Audio v3 TTS backend.

Serves the same /health and /v1/audio/speech endpoints the Gradio UI expects,
using the plain-transformers port of the model so it runs on Windows and macOS
where SGLang-Omni is unavailable.
"""

import io
import os
from threading import Lock
from typing import Literal

import soundfile as sf
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
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
generation_lock = Lock()


class Reference(BaseModel):
    audio_path: str
    text: str | None = ""


class SpeechRequest(BaseModel):
    input: str
    response_format: Literal["wav"] = "wav"
    stream: Literal[False] = False
    temperature: float | None = Field(default=0.7, ge=0, allow_inf_nan=False)
    top_p: float | None = Field(default=None, gt=0, le=1, allow_inf_nan=False)
    top_k: int | None = Field(default=None, ge=0)
    max_new_tokens: int | None = Field(default=2048, ge=1, le=4096)
    seed: int | None = Field(default=None, ge=-1, le=2**63 - 1)
    references: list[Reference] | None = Field(default=None, max_length=1)


@app.get("/health")
def health():
    return {"status": "ok", "backend": "transformers", "device": DEVICE, "model": MODEL_ID}


@app.post("/v1/audio/speech")
def speech(req: SpeechRequest):
    text = (req.input or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="'input' must be a non-empty string.")

    kwargs = dict(
        max_new_tokens=int(req.max_new_tokens or 2048),
        temperature=float(req.temperature if req.temperature is not None else 0.7),
        top_p=float(req.top_p) if req.top_p is not None and req.top_p < 1.0 else None,
        top_k=int(req.top_k) if req.top_k is not None and req.top_k > 0 else None,
    )
    # Omit unset sampling params instead of passing explicit None, which the
    # model's generate_speech may not treat as "use default".
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    if req.references:
        ref = req.references[0]
        if not os.path.isfile(ref.audio_path):
            raise HTTPException(status_code=400, detail=f"Reference audio not found: {ref.audio_path}")
        try:
            data, sr = sf.read(ref.audio_path, dtype="float32", always_2d=True)  # [L, C]
        except (OSError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail="Reference is not a readable audio file.") from exc
        if data.size == 0:
            raise HTTPException(status_code=400, detail="Reference audio is empty.")
        kwargs["reference_audio"] = torch.from_numpy(data).mean(dim=1)  # mono [L]
        kwargs["reference_sample_rate"] = sr
        if ref.text and ref.text.strip():
            kwargs["reference_text"] = ref.text.strip()

    # FastAPI runs synchronous routes in a thread pool. The shared model and
    # global torch RNG must be used by only one generation at a time.
    with generation_lock, torch.inference_mode():
        if req.seed is not None and req.seed >= 0:
            torch.manual_seed(req.seed)
        audio = model.generate_speech(text, tokenizer, **kwargs)
        audio = audio.detach().cpu().float()
    if audio.numel() == 0:
        raise HTTPException(status_code=500, detail="Generation produced no audio. Try again or adjust the text.")

    buf = io.BytesIO()
    sf.write(buf, audio.numpy(), SAMPLE_RATE, format="WAV")
    return Response(content=buf.getvalue(), media_type="audio/wav")


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
