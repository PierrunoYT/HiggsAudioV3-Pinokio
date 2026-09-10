# Remaining limitations and integration checks

The September 2026 audit fixed verified local defects in text chunking, WAV validation,
native API validation/concurrency, installation state, dependency isolation, and platform
Torch commands. These remaining items need deployment-specific validation or additional features.

## Upstream Linux dependencies

SGLang-Omni is installed from its moving default branch and owns its Torch dependencies.
The launcher no longer installs a competing Torch build first. Upstream changes can still
break resolution or require newer GPU drivers; complete Linux installation and inference
have not been validated in this Windows checkout. The intentional protobuf override remains.
Linux uses an import smoke check because `uv pip check` does not account for that override.

## Remote backend reference audio

Reference audio is sent as a local file path. Voice cloning and automatic first-chunk
self-cloning require the backend to share the UI's filesystem. A remote backend can handle
single-chunk zero-shot synthesis; long-text synthesis automatically uses self-cloning and
therefore also requires a shared filesystem. Remote uploads are not implemented.

## Shared Hugging Face cache survives reset

Reset removes both virtual environments, the installation marker, the cloned backend,
and local model downloads. Codec/tokenizer files in the shared Hugging Face cache survive
reset intentionally because other applications may use them.

## Native platform and model validation

The community model uses `trust_remote_code=True`; updates to its Python implementation
can change compatibility. Tests mock that model rather than downloading its weights.
GPU inference, voice-cloning quality, and Apple Silicon execution still require real-device
checks. Intel macOS is explicitly unsupported; Windows AMD and CPU-only inference may be slow.
The incompatible optional Windows flash-attention wheel has been removed.

## Existing Python environments

New environments request Python 3.11. Existing environments are reused by Pinokio; if a
legacy interpreter causes dependency resolution to fail, reset and reinstall. Reset deletes
local model downloads, so retain a backup if downloading them again would be inconvenient.
