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
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "env",
          path: "app",
          // flashattention: true  // uncomment if flash-attn prebuilt wheels become available for your torch/cuda version
        }
      }
    },
    {
      when: "{{!exists('app/sglang-omni/.git')}}",
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: "git clone https://github.com/sgl-project/sglang-omni.git sglang-omni"
      }
    },
    {
      when: "{{exists('app/sglang-omni/.git')}}",
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: "git -C sglang-omni pull"
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "uv pip install -v -e ./sglang-omni",
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
