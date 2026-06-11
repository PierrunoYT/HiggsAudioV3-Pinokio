import io
import os
import re
import tempfile
import wave

import gradio as gr
import requests

DEFAULT_API_BASE = os.environ.get("SGLANG_OMNI_API_BASE", "http://127.0.0.1:8000")

# One generated token ≈ 40 ms of audio (8 codebooks @ 25 fps), so a single
# request can only ever produce ~max_new_tokens/25 seconds of speech. Long
# inputs must be split into sentence chunks that each fit the audio budget,
# otherwise generation truncates mid-sentence or degrades (looping, early
# stop) — sooner in syllable-dense languages such as Indonesian.
DEFAULT_CHUNK_CHARS = 400

# Control tokens from https://huggingface.co/bosonai/higgs-audio-v3-tts-4b#control-tokens
EMOTION_TOKENS = [
    ("Elation", "<|emotion:elation|>"),
    ("Amusement", "<|emotion:amusement|>"),
    ("Enthusiasm", "<|emotion:enthusiasm|>"),
    ("Determination", "<|emotion:determination|>"),
    ("Pride", "<|emotion:pride|>"),
    ("Contentment", "<|emotion:contentment|>"),
    ("Affection", "<|emotion:affection|>"),
    ("Relief", "<|emotion:relief|>"),
    ("Contemplation", "<|emotion:contemplation|>"),
    ("Confusion", "<|emotion:confusion|>"),
    ("Surprise", "<|emotion:surprise|>"),
    ("Awe", "<|emotion:awe|>"),
    ("Longing", "<|emotion:longing|>"),
    ("Arousal", "<|emotion:arousal|>"),
    ("Anger", "<|emotion:anger|>"),
    ("Fear", "<|emotion:fear|>"),
    ("Disgust", "<|emotion:disgust|>"),
    ("Bitterness", "<|emotion:bitterness|>"),
    ("Sadness", "<|emotion:sadness|>"),
    ("Shame", "<|emotion:shame|>"),
    ("Helplessness", "<|emotion:helplessness|>"),
]

STYLE_TOKENS = [
    ("Singing", "<|style:singing|>"),
    ("Shouting", "<|style:shouting|>"),
    ("Whispering", "<|style:whispering|>"),
]

# Sound effects must be paired with their onomatopoeia (per model card).
SFX_TOKENS = [
    ("Cough", "<|sfx:cough|>Ahem"),
    ("Laughter", "<|sfx:laughter|>Haha"),
    ("Crying", "<|sfx:crying|>Sob"),
    ("Screaming", "<|sfx:screaming|>Aaah"),
    ("Burping", "<|sfx:burping|>Burp"),
    ("Humming", "<|sfx:humming|>Hmm"),
    ("Sigh", "<|sfx:sigh|>Ahh"),
    ("Sniff", "<|sfx:sniff|>Sff"),
    ("Sneeze", "<|sfx:sneeze|>Achoo"),
]

PROSODY_TOKENS = [
    ("Very slow", "<|prosody:speed_very_slow|>"),
    ("Slow", "<|prosody:speed_slow|>"),
    ("Fast", "<|prosody:speed_fast|>"),
    ("Very fast", "<|prosody:speed_very_fast|>"),
    ("Pitch low", "<|prosody:pitch_low|>"),
    ("Pitch high", "<|prosody:pitch_high|>"),
    ("Pause", "<|prosody:pause|>"),
    ("Long pause", "<|prosody:long_pause|>"),
    ("Expressive", "<|prosody:expressive_high|>"),
    ("Flat", "<|prosody:expressive_low|>"),
]


# Sentence-level delivery tokens (emotion / style / prosody speed-pitch-expressive)
# color the whole utterance, so when the text is split into chunks the leading
# run of them is re-applied to every chunk. Inline tokens (sfx, pauses) stay
# wherever they appear.
_DELIVERY_PREFIX_RE = re.compile(
    r"^(?:\s*<\|(?:emotion:[a-z_]+|style:[a-z_]+|prosody:(?:speed|pitch|expressive)_[a-z_]+)\|>)+"
)
_CONTROL_TOKEN_RE = re.compile(r"<\|[a-z_]+:[a-z_]+\|>")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…。！？؟])[ \t]+|\n+")
_CLAUSE_SPLIT_RE = re.compile(r"(?<=[,;:，；：、])\s+")


def _split_oversized(sentence, max_chars):
    """Split a sentence longer than ``max_chars`` on clause boundaries,
    falling back to whitespace. Control tokens contain neither whitespace nor
    clause punctuation, so they are never split apart."""
    pieces = []
    for clause in _CLAUSE_SPLIT_RE.split(sentence):
        if len(clause) <= max_chars:
            pieces.append(clause)
            continue
        current = ""
        for word in clause.split():
            candidate = f"{current} {word}".strip()
            if current and len(candidate) > max_chars:
                pieces.append(current)
                current = word
            else:
                current = candidate
        if current:
            pieces.append(current)
    return pieces


def chunk_text(text, max_chars):
    """Split ``text`` into sentence-packed chunks of roughly ``max_chars``
    characters, re-applying any leading delivery tokens to every chunk.
    Returns ``[text]`` unchanged when chunking is off or unnecessary."""
    text = (text or "").strip()
    if max_chars <= 0 or len(text) <= max_chars:
        return [text] if text else []

    match = _DELIVERY_PREFIX_RE.match(text)
    prefix = "".join(match.group(0).split()) if match else ""
    body = text[match.end():].strip() if match else text

    pieces = []
    for sentence in _SENTENCE_SPLIT_RE.split(body):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= max_chars:
            pieces.append(sentence)
        else:
            pieces.extend(_split_oversized(sentence, max_chars))

    chunks = []
    current = ""
    for piece in pieces:
        candidate = f"{current} {piece}".strip() if current else piece
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = piece
        else:
            current = candidate
    if current:
        chunks.append(current)
    return [prefix + chunk for chunk in chunks] if prefix else chunks


def strip_control_tokens(text):
    return _CONTROL_TOKEN_RE.sub("", text or "").strip()


def concat_wavs(blobs):
    """Concatenate PCM WAV blobs into a single WAV (both backends emit PCM16)."""
    if len(blobs) == 1:
        return blobs[0]
    params = None
    frames = []
    for blob in blobs:
        with wave.open(io.BytesIO(blob), "rb") as wav:
            if params is None:
                params = wav.getparams()
            frames.append(wav.readframes(wav.getnframes()))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setparams(params)
        out.writeframes(b"".join(frames))
    return buf.getvalue()


def make_token_inserter(snippet):
    def insert(current_text):
        current_text = current_text or ""
        if current_text and not current_text.endswith((" ", "\n", ">")):
            current_text += " "
        return current_text + snippet

    return insert


def render_token_buttons(tokens, textbox, per_row=7):
    for start in range(0, len(tokens), per_row):
        with gr.Row():
            for label, snippet in tokens[start:start + per_row]:
                btn = gr.Button(label, size="sm", min_width=60)
                btn.click(
                    make_token_inserter(snippet),
                    inputs=textbox,
                    outputs=textbox,
                    show_progress="hidden",
                )


def backend_status(api_base):
    api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
    try:
        response = requests.get(f"{api_base}/health", timeout=5)
        if response.ok:
            return f"Backend is reachable at {api_base}."
        return f"Backend responded at {api_base}, but health returned HTTP {response.status_code}."
    except requests.RequestException:
        return (
            f"No backend is reachable at {api_base}. Start the SGLang-Omni backend first, "
            "or enter the URL of a compatible remote server."
        )


def synthesize(
    api_base,
    text,
    reference_audio,
    reference_text,
    temperature,
    top_p,
    top_k,
    max_new_tokens,
    seed,
    chunk_chars,
    progress=gr.Progress(),
):
    text = (text or "").strip()
    if not text:
        raise gr.Error("Please enter some text to synthesize.")

    api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
    payload = {
        "response_format": "wav",
        "temperature": float(temperature),
        "max_new_tokens": int(max_new_tokens),
    }

    if float(top_p) < 1.0:
        payload["top_p"] = float(top_p)
    if int(top_k) > 0:
        payload["top_k"] = int(top_k)
    if seed is not None and int(seed) >= 0:
        payload["seed"] = int(seed)
    if reference_audio:
        payload["references"] = [{
            "audio_path": reference_audio,
            "text": (reference_text or "").strip(),
        }]

    chunks = chunk_text(text, int(chunk_chars))
    if not chunks:
        raise gr.Error("Please enter some text to synthesize.")

    try:
        health = requests.get(f"{api_base}/health", timeout=5)
        health.raise_for_status()
    except requests.RequestException as exc:
        raise gr.Error(
            "No SGLang-Omni speech backend is running at this API base URL. "
            "Click Start Backend in Pinokio, start a compatible backend, or enter a remote backend URL. "
            f"Details: {exc}"
        ) from exc

    blobs = []
    self_clone_path = None
    try:
        for index, chunk in enumerate(progress.tqdm(chunks, desc="Synthesizing")):
            payload["input"] = chunk
            try:
                response = requests.post(
                    f"{api_base}/v1/audio/speech",
                    json=payload,
                    timeout=600,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                raise gr.Error(
                    f"Synthesis failed on chunk {index + 1}/{len(chunks)}. "
                    f"Details: {exc}"
                ) from exc

            if not response.content:
                raise gr.Error(
                    f"The speech server returned an empty response on chunk {index + 1}/{len(chunks)}."
                )
            blobs.append(response.content)

            # Zero-shot voice drifts between independent requests, so after the
            # first chunk reuse its audio as the reference for the rest.
            if index == 0 and len(chunks) > 1 and not reference_audio:
                clone = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                clone.write(response.content)
                clone.close()
                self_clone_path = clone.name
                payload["references"] = [{
                    "audio_path": self_clone_path,
                    "text": strip_control_tokens(chunk),
                }]
    finally:
        if self_clone_path:
            try:
                os.unlink(self_clone_path)
            except OSError:
                pass

    try:
        merged = concat_wavs(blobs)
    except wave.Error as exc:
        raise gr.Error(
            "Could not join the generated audio chunks (non-PCM WAV from backend). "
            "Set the long-text chunk size to 0 to disable chunking. "
            f"Details: {exc}"
        ) from exc

    output = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    output.write(merged)
    output.close()
    return output.name


with gr.Blocks(title="Higgs Audio v3 TTS") as demo:
    gr.Markdown(
        "# Higgs Audio v3 TTS\n"
        "Zero-shot text-to-speech & voice cloning with "
        "[`bosonai/higgs-audio-v3-tts-4b`](https://huggingface.co/bosonai/higgs-audio-v3-tts-4b) "
        "through a SGLang-Omni-compatible `/v1/audio/speech` server."
    )
    with gr.Row():
        with gr.Column():           
            reference_audio = gr.Audio(
                label="Reference voice (optional, for cloning)",
                type="filepath",
            )
            reference_text = gr.Textbox(
                label="Reference transcript (optional, improves cloning)",
                lines=2,
            )

            with gr.Row():
                text = gr.Textbox(
                    label="Text to synthesize",
                    placeholder="Type what you want the voice to say...",
                    lines=4,
                )

            with gr.Accordion("Advanced settings", open=False):
                temperature = gr.Slider(0.0, 1.5, value=0.7, step=0.05, label="Temperature")
                top_p = gr.Slider(0.1, 1.0, value=0.95, step=0.01, label="Top-p")
                top_k = gr.Slider(0, 1026, value=50, step=1, label="Top-k (0 = off)")
                max_new_tokens = gr.Slider(64, 4096, value=2048, step=64, label="Max new tokens")
                seed = gr.Number(value=-1, label="Seed (-1 = random)", precision=0)
                chunk_chars = gr.Slider(
                    0, 2000, value=DEFAULT_CHUNK_CHARS, step=50,
                    label="Long-text chunk size (characters, 0 = off)",
                    info="Long inputs are split at sentence boundaries into chunks of "
                         "roughly this size, synthesized one by one, and joined. Each "
                         "request can only produce ~40 ms of audio per generated token, "
                         "so unchunked long text gets truncated or degrades.",
                )
            run = gr.Button("Generate speech", variant="primary")

        with gr.Column():
            output_audio = gr.Audio(label="Generated speech", type="filepath")

            with gr.Accordion("Control tokens (click to insert)", open=False):
                gr.Markdown(
                    "Emotion, style, speed, pitch and expressiveness tokens shape the whole "
                    "utterance — insert them **before** your text. Pauses and sound effects fire "
                    "**inline**, exactly where they appear. Tokens are appended at the end of the "
                    "text box, so click first, then keep writing."
                )
                with gr.Tab("Emotion"):
                    render_token_buttons(EMOTION_TOKENS, text)
                with gr.Tab("Style"):
                    render_token_buttons(STYLE_TOKENS, text)
                with gr.Tab("Speed & Prosody"):
                    render_token_buttons(PROSODY_TOKENS, text, per_row=5)
                with gr.Tab("Sound effects"):
                    render_token_buttons(SFX_TOKENS, text, per_row=5)
                clear_text = gr.Button("Clear text", size="sm", variant="stop")
                clear_text.click(lambda: "", outputs=text, show_progress="hidden")

            api_base = gr.Textbox(
                value=DEFAULT_API_BASE,
                label="SGLang-Omni API base URL",
                info="Default local backend URL. Use a remote URL if the backend runs elsewhere.",
            )
            status = gr.Markdown()
            check_backend = gr.Button("Check backend")

    gr.Examples(
        examples=[
            [DEFAULT_API_BASE, "Higgs Audio version three, served through SGLang Omni.", None, ""],
            [DEFAULT_API_BASE, "<|emotion:amusement|><|prosody:expressive_high|>That was surprisingly fun.", None, ""],
        ],
        inputs=[api_base, text, reference_audio, reference_text],
    )

    demo.load(backend_status, inputs=api_base, outputs=status)
    check_backend.click(backend_status, inputs=api_base, outputs=status)

    run.click(
        synthesize,
        inputs=[api_base, text, reference_audio, reference_text, temperature, top_p, top_k, max_new_tokens, seed, chunk_chars],
        outputs=output_audio,
    )

if __name__ == "__main__":
    demo.queue().launch(server_name="127.0.0.1", theme=gr.themes.Citrus())
