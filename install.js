module.exports = {
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "uv pip install -r requirements.txt"
        ]
      }
    },
    {
      method: "input",
      params: {
        title: "Install Complete",
        description: "Higgs Audio v3 TTS client UI is installed. Start a SGLang-Omni-compatible backend separately for speech generation."
      }
    }
  ]
}
