module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "uv pip install -r requirements.txt",
          "if [ ! -d sglang-omni/.git ]; then git clone https://github.com/sgl-project/sglang-omni.git sglang-omni; else git -C sglang-omni pull; fi",
          "uv pip install -v ./sglang-omni",
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
