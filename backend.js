module.exports = {
  daemon: true,
  run: [
    {
      method: "input",
      params: {
        title: "Start Speech Backend",
        description: [
          "This starts the Higgs Audio v3 speech server. The UI expects it at http://127.0.0.1:8000.",
          "",
          "Linux: official SGLang-Omni server (high throughput, continuous batching).",
          "Windows / macOS: native transformers server (same API, single-request).",
          "",
          "The first start loads ~10 GB of weights and can take a few minutes."
        ].join("\n")
      }
    },
    {
      when: "{{platform === 'linux'}}",
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
      when: "{{platform !== 'linux'}}",
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "python server.py"
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
