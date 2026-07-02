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
          // flashattention: true  // do NOT enable: the prebuilt Windows wheel in torch.js targets torch 2.7 / Python 3.10 and is ABI-incompatible with the torch 2.9.1 installed here
        }
      }
    },
    // ---- Linux: official SGLang-Omni backend ----
    {
      when: "{{platform === 'linux' && !exists('app/sglang-omni/.git')}}",
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: "git clone https://github.com/sgl-project/sglang-omni.git sglang-omni"
      }
    },
    {
      when: "{{platform === 'linux' && exists('app/sglang-omni/.git')}}",
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: "git -C sglang-omni pull"
      }
    },
    {
      when: "{{platform === 'linux'}}",
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "uv pip install -v -e ./sglang-omni --override ../uv-overrides.txt",
          "hf download bosonai/higgs-audio-v3-tts-4b --local-dir models/higgs-audio-v3-tts-4b"
        ]
      }
    },
    // ---- Windows / macOS: native transformers backend (SGLang-Omni needs Linux-only packages) ----
    {
      when: "{{platform !== 'linux'}}",
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          // sympy + networkx are torch runtime deps that torch.js skips via --no-deps
          "uv pip install \"transformers>=5.5\" accelerate soundfile numpy fastapi uvicorn pydantic sympy networkx",
          "hf download multimodalart/higgs-audio-v3-tts-4b-transformers --local-dir models/higgs-audio-v3-tts-4b-transformers",
          "hf download bosonai/higgs-audio-v2-tokenizer"
        ]
      }
    },
    {
      method: "input",
      params: {
        title: "Install Complete",
        description: "Higgs Audio v3 TTS is installed. On Linux the backend uses the official SGLang-Omni server; on Windows and macOS it uses a native transformers server. Click Start to launch the backend and the web UI together."
      }
    }
  ]
}
