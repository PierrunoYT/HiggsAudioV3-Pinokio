# Higgs Audio v3 TTS Pinokio Launcher

This is a Pinokio launcher for a lightweight Gradio UI that talks to the official Higgs Audio v3 TTS SGLang-Omni speech API.

The UI does not load the model directly. It sends requests to a SGLang-Omni-compatible backend at `/v1/audio/speech`, defaulting to `http://127.0.0.1:8000`.

## Usage

1. Click **Install** in Pinokio.
2. Start a compatible SGLang-Omni backend for `bosonai/higgs-audio-v3-tts-4b`.
3. Click **Start UI** in Pinokio.
4. Open the Web UI.
5. Enter text, optional reference audio, and generation settings.
6. Click **Generate speech**.

Use **Backend Setup** in the Pinokio menu for a quick reminder of the official server command and platform notes.

## Backend

The official SGLang-Omni command is:

```bash
sgl-omni serve \
  --model-path bosonai/higgs-audio-v3-tts-4b \
  --port 8000
```

SGLang-Omni is documented primarily for Linux/Windows systems with NVIDIA GPUs and Docker. On macOS, use the Pinokio UI as a client for a compatible local or remote SGLang-Omni/Boson API server. If you have an experimental SGLang/MLX backend running locally, enter its API base URL in the UI.

## Model

- Hugging Face: https://huggingface.co/bosonai/higgs-audio-v3-tts-4b
- License: Boson Higgs Audio v3 Research and Non-Commercial License

## API documentation

The backend should provide an OpenAI-compatible speech endpoint through SGLang-Omni.

### Curl

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input":"Hello, how are you?"}' \
  --output output.wav
```

With voice cloning:

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Have a nice day and enjoy the sunshine.",
    "references": [{
      "audio_path": "ref.wav",
      "text": "Reference transcript for the voice clip."
    }],
    "temperature": 0.8,
    "top_k": 50,
    "max_new_tokens": 1024
  }' \
  --output output.wav
```

### Python

```python
import requests

resp = requests.post(
    "http://localhost:8000/v1/audio/speech",
    json={"input": "Hello, how are you?"},
)
with open("output.wav", "wb") as f:
    f.write(resp.content)
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
