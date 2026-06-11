import os
import tempfile

import gradio as gr
import requests

DEFAULT_API_BASE = os.environ.get("SGLANG_OMNI_API_BASE", "http://127.0.0.1:8000")

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
):
    text = (text or "").strip()
    if not text:
        raise gr.Error("Please enter some text to synthesize.")

    api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
    payload = {
        "input": text,
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

    try:
        health = requests.get(f"{api_base}/health", timeout=5)
        health.raise_for_status()
        response = requests.post(
            f"{api_base}/v1/audio/speech",
            json=payload,
            timeout=600,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise gr.Error(
            "No SGLang-Omni speech backend is running at this API base URL. "
            "Click Start Backend in Pinokio, start a compatible backend, or enter a remote backend URL. "
            f"Details: {exc}"
        ) from exc

    if not response.content:
        raise gr.Error("The speech server returned an empty response.")

    output = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    output.write(response.content)
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
                label="Reference transcript",
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
        inputs=[api_base, text, reference_audio, reference_text, temperature, top_p, top_k, max_new_tokens, seed],
        outputs=output_audio,
    )

demo.queue().launch(server_name="127.0.0.1", theme=gr.themes.Citrus())
