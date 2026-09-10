module.exports = {
  run: [
    {
      when: "{{exists('app/.installed')}}",
      method: "fs.rm",
      params: { path: "app/.installed" }
    },
    {
      method: "shell.run",
      params: {
        venv: "ui-env",
        venv_python: "3.11",
        path: "app",
        message: "uv pip install -r requirements.txt"
      }
    },
    {
      when: "{{platform !== 'linux'}}",
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "env",
          path: "app",
        }
      }
    },
    // ---- Linux: official SGLang-Omni backend ----
    {
      when: "{{platform === 'linux' && !exists('app/sglang-omni/.git')}}",
      method: "shell.run",
      params: {
        venv: "env",
        venv_python: "3.11",
        path: "app",
        message: "git clone https://github.com/sgl-project/sglang-omni.git sglang-omni"
      }
    },
    {
      when: "{{platform === 'linux' && exists('app/sglang-omni/.git')}}",
      method: "shell.run",
      params: {
        venv: "env",
        venv_python: "3.11",
        path: "app",
        message: "git -C sglang-omni pull --ff-only"
      }
    },
    {
      when: "{{platform === 'linux'}}",
      method: "shell.run",
      params: {
        venv: "env",
        venv_python: "3.11",
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
        venv_python: "3.11",
        path: "app",
        message: [
          "uv pip install -r requirements-native.txt",
          "hf download multimodalart/higgs-audio-v3-tts-4b-transformers --local-dir models/higgs-audio-v3-tts-4b-transformers",
          "hf download bosonai/higgs-audio-v2-tokenizer"
        ]
      }
    },
    {
      when: "{{platform !== 'linux'}}",
      method: "shell.run",
      params: {
        venv: "env",
        venv_python: "3.11",
        path: "app",
        message: "uv pip check"
      }
    },
    {
      when: "{{platform === 'linux'}}",
      method: "shell.run",
      params: {
        venv: "env",
        venv_python: "3.11",
        path: "app",
        // pip check cannot account for the intentional protobuf override.
        message: "python -c \"import torch; import sglang_omni\""
      }
    },
    {
      method: "fs.write",
      params: { path: "app/.installed", text: "complete" }
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
