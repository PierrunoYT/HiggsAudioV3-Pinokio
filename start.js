module.exports = {
  daemon: true,
  run: [
    {
      // Reserve the next free port once so the backend and the UI agree on it
      method: "local.set",
      params: {
        backend_port: "{{port}}"
      }
    },
    {
      when: "{{platform === 'linux'}}",
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          // --allowed-local-media-path lets the server read reference-audio files
          // the UI writes to the system temp dir (voice cloning, self-clone chunks)
          "sgl-omni serve --model-path models/higgs-audio-v3-tts-4b --allowed-local-media-path /tmp --port {{local.backend_port}}"
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
        env: {
          PORT: "{{local.backend_port}}"
        },
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
          SGLANG_OMNI_API_BASE: "http://127.0.0.1:{{local.backend_port}}"
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
