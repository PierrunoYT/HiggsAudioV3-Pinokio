# Higgs Audio v3 TTS Pinokio Launcher

This is a Pinokio launcher for a lightweight Gradio UI that talks to a local Higgs Audio v3 TTS speech API.

The installer sets up the Gradio UI and a local speech backend, and downloads the Higgs Audio v3 model files locally. The UI sends requests to the local backend at `/v1/audio/speech`, defaulting to `http://127.0.0.1:8000`.

- **Linux**: official [SGLang-Omni](https://github.com/sgl-project/sglang-omni) server (high throughput, continuous batching, streaming).
- **Windows / macOS**: native transformers server (`app/server.py`) using the [plain-transformers port](https://huggingface.co/multimodalart/higgs-audio-v3-tts-4b-transformers) of the model — same API, no SGLang required.

## Usage

1. Click **Install** in Pinokio.
2. Click **Start Backend** in Pinokio.
3. Click **Start UI** in Pinokio.
4. Open the Web UI.
5. Enter text, optional reference audio, and generation settings.
6. Click **Generate speech**.

The install step downloads the backend source and the model (~10 GB), so the first install can take a while.

## Backend

On **Linux**, the launcher runs the official SGLang-Omni server:

```bash
sgl-omni serve \
  --model-path models/higgs-audio-v3-tts-4b \
  --port 8000
```

On **Windows and macOS**, SGLang-Omni cannot be installed natively (it depends on Linux-only packages like `sgl-kernel`, `nixl`, and `mooncake-transfer-engine`), so the launcher runs a native transformers server instead:

```bash
python server.py
```

It exposes the same `/health` and `/v1/audio/speech` endpoints (zero-shot synthesis, voice cloning, control tokens). Streaming (`"stream": true`) is only available with the SGLang-Omni backend on Linux. An NVIDIA GPU with roughly 12 GB+ of VRAM is recommended; the model loads in bf16 (~10 GB).

## Model

- Hugging Face: https://huggingface.co/bosonai/higgs-audio-v3-tts-4b
- License: Boson Higgs Audio v3 Research and Non-Commercial License (non-commercial only)

## Control Tokens

Embed control tokens directly in the `input` text using `<|category:value|>` syntax.

**Rule 1 — Delivery tokens first.** Emotion, style, and prosody speed/pitch/expressive tokens shape the whole utterance — put them at the very start of `input`.

**Rule 2 — Pair every `<|sfx:…|>` with its onomatopoeia immediately after.** e.g. `<|sfx:laughter|>Haha`, `<|sfx:sigh|>Uh`, `<|sfx:sneeze|>Achoo`.

### Emotion

| Token | Effect |
|---|---|
| `<\|emotion:elation\|>` | Elation / joy |
| `<\|emotion:amusement\|>` | Amusement / playful laughter |
| `<\|emotion:enthusiasm\|>` | Enthusiasm / excitement |
| `<\|emotion:determination\|>` | Determination / firmness |
| `<\|emotion:pride\|>` | Pride / confidence |
| `<\|emotion:contentment\|>` | Calm satisfaction |
| `<\|emotion:affection\|>` | Warmth / affection |
| `<\|emotion:relief\|>` | Relief |
| `<\|emotion:contemplation\|>` | Thoughtful / reflective |
| `<\|emotion:confusion\|>` | Confused |
| `<\|emotion:surprise\|>` | Surprised |
| `<\|emotion:awe\|>` | Awe / wonder |
| `<\|emotion:longing\|>` | Longing / yearning |
| `<\|emotion:anger\|>` | Anger |
| `<\|emotion:fear\|>` | Fear |
| `<\|emotion:disgust\|>` | Disgust |
| `<\|emotion:sadness\|>` | Sadness |

### Style

| Token | Effect |
|---|---|
| `<\|style:singing\|>` | Singing |
| `<\|style:shouting\|>` | Shouting / projected voice |
| `<\|style:whispering\|>` | Whisper |

### Sound Effects

Pair each token with the matching onomatopoeia immediately after it.

| Token | Effect | Suggested onomatopoeia |
|---|---|---|
| `<\|sfx:cough\|>` | Cough | Ahem |
| `<\|sfx:laughter\|>` | Laughter | Haha / Hehe |
| `<\|sfx:crying\|>` | Crying | Boohoo / Sob |
| `<\|sfx:screaming\|>` | Screaming | Ahh / Aaah |
| `<\|sfx:burping\|>` | Burping | Burp |
| `<\|sfx:humming\|>` | Humming | Hmm / Mmm |
| `<\|sfx:sigh\|>` | Sigh | Uh / Ahh |
| `<\|sfx:sniff\|>` | Sniff | Sff |
| `<\|sfx:sneeze\|>` | Sneeze | Achoo |

### Prosody

| Token | Effect |
|---|---|
| `<\|prosody:speed_very_slow\|>` | ≈0.65× speed |
| `<\|prosody:speed_slow\|>` | ≈0.85× speed |
| `<\|prosody:speed_fast\|>` | ≈1.2× speed |
| `<\|prosody:speed_very_fast\|>` | ≈1.4× speed |
| `<\|prosody:pitch_low\|>` | ≈−3 semitones |
| `<\|prosody:pitch_high\|>` | ≈+2.5 semitones |
| `<\|prosody:pause\|>` | ≈400–700 ms pause (inline) |
| `<\|prosody:long_pause\|>` | ≈700–1500 ms pause (inline) |
| `<\|prosody:expressive_high\|>` | More expressive delivery |
| `<\|prosody:expressive_low\|>` | Flatter delivery |

## API Documentation

### Curl — zero-shot synthesis

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, how are you?"}' \
  --output output.wav
```

### Curl — inline control tokens

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "<|emotion:amusement|><|prosody:expressive_high|>Wait, wait, that was kind of hilarious. <|sfx:laughter|>Hehe, no, seriously, I was not ready for that."}' \
  --output output.wav
```

### Python — voice cloning

Supplying the reference transcript (`text`) materially improves cloning fidelity.

```python
import requests

resp = requests.post(
    "http://localhost:8000/v1/audio/speech",
    json={
        "input": "Have a nice day and enjoy south california sunshine.",
        "references": [{
            "audio_path": "ref.wav",
            "text": "Hey, Adam here. Let's create something that feels real, sounds human, and connects every time.",
        }],
        "temperature": 0.8, "top_k": 50, "max_new_tokens": 1024,
    },
)
with open("output.wav", "wb") as f:
    f.write(resp.content)
```

### Python — streaming (Server-Sent Events)

Set `"stream": true` to receive base64-encoded WAV chunks as the vocoder emits them — sub-second time-to-first-audio.

```python
import requests, base64, json

with requests.post(
    "http://localhost:8000/v1/audio/speech",
    json={"input": "Get the trust fund to the bank early.", "stream": True},
    stream=True,
) as resp, open("output.wav", "wb") as f:
    for line in resp.iter_lines():
        if not line or not line.startswith(b"data: ") or line == b"data: [DONE]":
            continue
        event = json.loads(line[6:])
        if event.get("finish_reason") == "stop":
            break
        audio = event.get("audio") or {}
        if audio.get("data"):
            f.write(base64.b64decode(audio["data"]))
```

### JavaScript

```javascript
const response = await fetch("http://localhost:8000/v1/audio/speech", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ input: "Hello, how are you?" })
})
const audio = await response.arrayBuffer()
```
