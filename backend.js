module.exports = {
  daemon: true,
  run: [
    {
      method: "input",
      params: {
        title: "Start SGLang-Omni Backend",
        description: [
          "This will start the official Higgs Audio v3 SGLang-Omni speech server installed by the Pinokio installer.",
          "",
          "The UI expects the server at http://127.0.0.1:8000.",
          "",
          "Official stable local serving is documented mainly for Linux/Windows with NVIDIA GPUs. On macOS, use a compatible remote server or an experimental local SGLang/MLX setup."
        ].join("\n")
      }
    },
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "sgl-omni serve --model-path models/higgs-audio-v3-tts-4b --port 8000"
        ],
        on: [{
          event: "/(http:\\/\\/[0-9.:]+)/",
          done: true
        }]
      }
    },
    {
      method: "local.set",
      params: {
        url: "http://127.0.0.1:8000"
      }
    }
  ]
}
