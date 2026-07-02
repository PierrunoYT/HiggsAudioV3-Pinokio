# Known Issues / Deferred Items

Findings from the 2026-07-02 launcher audit that were **deliberately not fixed**, either because
they carry risk without testing on the affected platform or because they are architectural
changes beyond a minimal fix. Revisit if the matching symptom shows up.

## 1. Torch install order vs. SGLang-Omni (Linux only)

`install.js` installs torch 2.9.1/cu128 via `torch.js` **before** `uv pip install -e ./sglang-omni`.
If sglang-omni ever pins a different torch version, its editable install can replace the CUDA
build (possibly with a CPU wheel).

- **Symptom:** after install on Linux, `torch.cuda.is_available()` is false or torch version ≠ 2.9.1.
- **Fix if it happens:** run the sglang-omni install first and `torch.js` afterwards, or align the
  torch pin with sglang-omni's requirement.

## 2. Flash-attention wheel is stale (Windows)

The prebuilt wheel referenced in `torch.js` (`flash_attn-2.8.2+cu128torch2.7-cp310`) targets
torch 2.7 / Python 3.10 and is ABI-incompatible with the torch 2.9.1 installed by this launcher.
The `flashattention` option in `install.js` is commented out with a warning — leave it disabled
until a torch-2.9/cu128 Windows wheel exists, then update the URL in `torch.js`.

## 3. UI and backend share one venv (Linux)

On Linux, Gradio 6 (UI) and sglang-omni's tightly pinned server stack are resolved into the same
`app/env` in separate `uv pip install` runs, so a later install can silently downgrade an earlier
one's dependencies.

- **Symptom:** UI or backend breaks after `update.js` re-runs install.
- **Fix if it happens:** give the UI its own venv (e.g. `venv: "ui-env"` on the frontend step in
  `start.js` and the requirements step in `install.js`).

## 4. Voice cloning requires a same-machine backend

Reference audio (and the automatic first-chunk self-clone) is sent to the backend as a local
**file path**, so cloning cannot work against a remote API base URL. Supporting remote backends
would require uploading audio as base64/multipart. Documented in `README.md`.

## 5. Reset leaves files in the Hugging Face cache

`reset.js` removes `app/env`, `app/sglang-omni`, and `app/models`, but the
`bosonai/higgs-audio-v2-tokenizer` download (and codec files fetched at runtime via
`trust_remote_code`) live in the global Hugging Face cache (`~/.cache/huggingface`) and survive a
reset. They must stay hub-cached for the backend to find them by name, so this is cosmetic —
a few GB linger after reset. Delete them manually from the HF cache if needed.

## 6. Unverified third-party assumptions

- `transformers>=5.5` and the `multimodalart/higgs-audio-v3-tts-4b-transformers` repo (Windows/macOS
  backend) are community-maintained; if that repo's remote code changes its `generate_speech`
  signature, `app/server.py` will return HTTP 500s.
- CPU-only or AMD-on-Windows machines get CPU torch and will run the 4B model impractically
  slowly (~minutes per sentence, ~20 GB RAM). No guard warns about this at install time.
