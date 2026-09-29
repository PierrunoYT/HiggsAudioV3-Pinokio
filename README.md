# Higgs Audio v3 TTS Pinokio Launcher

This is a Pinokio launcher for a lightweight Gradio UI that talks to a local Higgs Audio v3 TTS speech API.

The installer sets up the Gradio UI and a local speech backend, and downloads the Higgs Audio v3 model files locally. The UI sends requests to the local backend at `/v1/audio/speech`; the launcher picks the next free port automatically and passes it to the UI (standalone `server.py` defaults to `http://127.0.0.1:8000`).

- **Linux**: official [SGLang-Omni](https://github.com/sgl-project/sglang-omni) server (high throughput, continuous batching, streaming).
- **Windows / macOS**: native transformers server (`app/server.py`) using the [plain-transformers port](https://huggingface.co/multimodalart/higgs-audio-v3-tts-4b-transformers) of the model — same API, no SGLang required.

## Usage

1. Click **Install** in Pinokio.
2. Click **Start** in Pinokio (launches the speech backend and the web UI together).
3. Click **Open Web UI** once it appears.
4. Enter text, optional reference audio, and generation settings.
5. Click **Generate speech**.

After updating an older installation, run **Install** once to create the separate UI environment
and completion marker. Existing model downloads are reused. Fresh environments use Python 3.11.
The launcher shows **Start** only after installation finishes successfully.

The install step downloads the backend source and the model (~10 GB), so the first install can take a while.

The UI uses `app/ui-env`; the backend uses `app/env`. Linux lets SGLang-Omni resolve
its own Torch dependencies. Windows and Apple Silicon use Torch 2.9.1 with its runtime
dependencies. Intel macOS is unsupported by that Torch release; installation reports this
explicitly. Windows AMD and CPU-only systems use CPU inference and may be very slow.

On Linux, the installer passes `uv-overrides.txt` to uv when installing SGLang-Omni. This mirrors SGLang-Omni's upstream protobuf override and avoids a resolver conflict between `grpcio-tools` and `descript-audiotools`.

## Backend

On **Linux**, the launcher runs the official SGLang-Omni server:

```bash
sgl-omni serve \
  --model-path models/higgs-audio-v3-tts-4b \
  --allowed-local-media-path /tmp \
  --host 127.0.0.1 \
  --port <free port picked by the launcher>
```

`--allowed-local-media-path /tmp` lets the server read the reference-audio files the UI writes to the system temp directory (voice cloning and cross-chunk voice consistency). Because references are passed as file paths, cloning only works when the backend runs on the same machine as the UI. `--host 127.0.0.1` keeps the unauthenticated API off the local network (SGLang-Omni binds `0.0.0.0` by default).

On **Windows and macOS**, SGLang-Omni cannot be installed natively (it depends on Linux-only packages like `sgl-kernel`, `nixl`, and `mooncake-transfer-engine`), so the launcher runs a native transformers server instead:

```bash
python server.py
```

It exposes the same `/health` and `/v1/audio/speech` endpoints (zero-shot synthesis, voice cloning, control tokens). Streaming (`"stream": true`) is only available with the SGLang-Omni backend on Linux. An NVIDIA GPU with roughly 12 GB+ of VRAM is recommended; the model loads in bf16 (~10 GB) on CUDA and in float32 (roughly twice the memory) on Apple Silicon and CPU.

## Model

- Hugging Face: https://huggingface.co/bosonai/higgs-audio-v3-tts-4b
- License: Boson Higgs Audio v3 Research and Non-Commercial License (non-commercial only)

## Long Text

A single `/v1/audio/speech` request can only produce about 40 ms of audio per generated token (8 codebooks at 25 fps), so `max_new_tokens` caps the output at roughly `max_new_tokens / 25` seconds — about 80 s at the default 2048. Text whose spoken duration exceeds that budget gets truncated mid-sentence or degrades (looping, premature stop). Syllable-dense languages such as Indonesian hit the cap at fewer characters than English.

The Web UI handles this automatically: inputs longer than the **Long-text chunk size** setting (default 400 characters, under Advanced settings; 0 disables it) are split at sentence boundaries, synthesized one chunk at a time, and joined into a single WAV.

- The text is always split at every run of delivery tokens (emotion, style, prosody speed/pitch/expressive), even with chunking set to 0, because the model applies them to the whole request. Each run applies until the next one and is re-applied to every chunk after it; inline tokens (`<|sfx:…|>`, pauses) stay where they appear.
- With a reference voice, every chunk uses it, so the cloned voice stays consistent.
- Without a reference voice, the first chunk's audio is reused as the reference for the remaining chunks, keeping the zero-shot voice consistent across chunks.

API users sending long text directly to the backend should chunk the same way — the backend itself does not split text.

## Control Tokens

Embed control tokens directly in the `input` text using `<|category:value|>` syntax.

**Rule 1 — Delivery tokens first.** Emotion, style, and prosody speed/pitch/expressive tokens shape the whole request — when calling the API directly, put them at the very start of `input`. The Web UI also accepts them mid-text: it splits the text there and synthesizes each part separately (see [Long Text](#long-text)).

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
| `<\|emotion:arousal\|>` | Arousal |
| `<\|emotion:anger\|>` | Anger |
| `<\|emotion:fear\|>` | Fear |
| `<\|emotion:disgust\|>` | Disgust |
| `<\|emotion:bitterness\|>` | Bitterness / resentment |
| `<\|emotion:sadness\|>` | Sadness |
| `<\|emotion:shame\|>` | Shame |
| `<\|emotion:helplessness\|>` | Helplessness |

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
resp.raise_for_status()
with open("output.wav", "wb") as f:
    f.write(resp.content)
```

### Python — streaming (Server-Sent Events)

Set `"stream": true` to receive base64-encoded WAV chunks as the vocoder emits them — sub-second time-to-first-audio.

```python
import requests, base64, json
from app.audio_utils import concat_wavs  # run from this repository

chunks = []

with requests.post(
    "http://localhost:8000/v1/audio/speech",
    json={"input": "Get the trust fund to the bank early.", "stream": True},
    stream=True,
) as resp:
    resp.raise_for_status()
    for line in resp.iter_lines():
        if not line or not line.startswith(b"data: ") or line == b"data: [DONE]":
            continue
        event = json.loads(line[6:])
        audio = event.get("audio") or {}
        if audio.get("data"):
            chunks.append(base64.b64decode(audio["data"]))
        if event.get("finish_reason") == "stop":
            break

# Each chunk has its own WAV header: join decoded frames, not raw files.
with open("output.wav", "wb") as f:
    f.write(concat_wavs(chunks))
```

### JavaScript

```javascript
const response = await fetch("http://localhost:8000/v1/audio/speech", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ input: "Hello, how are you?" })
})
if (!response.ok) throw new Error(await response.text())
const audio = await response.arrayBuffer()
```


## Validation and tests

The native backend accepts WAV output, one reference clip, and non-streaming requests.
Invalid sampling values and unsupported formats return HTTP 422. `max_new_tokens` must
be between 1 and 4096. Invalid or empty reference files return HTTP 400. Generation is
serialized to keep concurrent calls from sharing model execution or changing each other's seed.

Run the lightweight regression suite without downloading model weights:

```bash
python -m pip install -r tests/requirements.txt
python -m unittest discover -s tests -v
node --test tests/launcher.test.js
```

The tests cover text splitting, WAV integrity, request validation, concurrent generation,
and launcher menu/installation states. Model inference is mocked; real speech quality,
GPU memory usage, and complete Pinokio installs require hardware integration testing.
