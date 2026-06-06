module.exports = {
  run: [
    {
      method: "input",
      params: {
        title: "SGLang-Omni Backend",
        description: [
          "This launcher uses the official Higgs Audio v3 /v1/audio/speech API.",
          "",
          "Stable local serving is currently documented for Linux/Windows systems with NVIDIA GPUs and Docker:",
          "docker pull lmsysorg/sglang-omni:dev",
          "sgl-omni serve --model-path bosonai/higgs-audio-v3-tts-4b --port 8000",
          "",
          "On macOS, use this UI as a client for a compatible SGLang-Omni or Boson API server. If you have an experimental local SGLang/MLX backend, set the UI API base URL to that server."
        ].join("\n")
      }
    }
  ]
}
