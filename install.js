module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: "uv pip install -r requirements.txt"
      }
    },
    {
      method: "script.run",
      params: {
        uri: "torch.js",
        args: {
          venv: "env",
          path: "app",
          flashattention: true
        }
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "if [ ! -d sglang-omni/.git ]; then git clone https://github.com/sgl-project/sglang-omni.git sglang-omni; else git -C sglang-omni pull; fi",
          "uv pip install nixl || echo '[warn] nixl not on PyPI, continuing without it'",
          "uv pip install sglang==0.5.8 --find-links https://flashinfer.ai/whl/cu128/torch2.9/ || uv pip install sglang==0.5.8",
          "uv pip install -v ./sglang-omni --no-deps",
          "uv pip install pyzmq msgpack pydantic PyYAML accelerate transformers safetensors pillow huggingface-hub datasets fastapi uvicorn httpx xxhash av numba librosa pandas tabulate typer openai soundfile websockets scipy s3prl tiktoken hydra-core omegaconf torchaudio silero-vad onnxruntime gradio diffusers",
          "hf download bosonai/higgs-audio-v3-tts-4b --local-dir models/higgs-audio-v3-tts-4b"
        ]
      }
    },
    {
      method: "input",
      params: {
        title: "Install Complete",
        description: "Higgs Audio v3 TTS is installed with the Gradio UI, SGLang-Omni backend, and local Higgs Audio v3 model files. Use Start Backend, then Start UI."
      }
    }
  ]
}
