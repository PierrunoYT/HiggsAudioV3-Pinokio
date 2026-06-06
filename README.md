# Higgs Audio v3 TTS Pinokio Launcher

This is a Pinokio launcher scaffold for `bosonai/higgs-audio-v3-tts-4b`.

The current `app/app.py` is a placeholder Gradio app. It lets you build Higgs Audio v3 prompt text with emotion, style, prosody, and reference-audio fields, but it does not run real model inference yet.

## Usage

1. Click **Install** in Pinokio.
2. Click **Start**.
3. Open the Web UI.
4. Enter text and optional control settings.
5. Click **Build placeholder request**.

## Model

- Hugging Face: https://huggingface.co/bosonai/higgs-audio-v3-tts-4b
- License: Boson Higgs Audio v3 Research and Non-Commercial License

## API documentation

The placeholder app exposes a Gradio UI only. The intended final backend should provide an OpenAI-compatible speech endpoint through SGLang-Omni.

### Curl

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input":"Hello, how are you?"}' \
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
