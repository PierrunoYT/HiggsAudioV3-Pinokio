module.exports = {
  daemon: true,
  run: [
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
      },
      next: "frontend"
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
      id: "frontend",
      method: "shell.run",
      params: {
        venv: "env",
        env: {
          SGLANG_OMNI_API_BASE: "http://127.0.0.1:8000"
        },
        path: "app",
        message: [
          "python app.py",
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
        url: "{{input.event[1]}}"
      }
    }
  ]
}
