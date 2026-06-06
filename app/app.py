import gradio as gr

MODEL_ID = "bosonai/higgs-audio-v3-tts-4b"

EMOTIONS = [
    "elation",
    "amusement",
    "enthusiasm",
    "determination",
    "pride",
    "contentment",
    "affection",
    "relief",
    "contemplation",
    "confusion",
    "surprise",
    "awe",
    "longing",
    "arousal",
    "anger",
    "fear",
    "disgust",
    "bitterness",
    "sadness",
    "shame",
    "helplessness",
]

STYLES = ["none", "singing", "shouting", "whispering"]
PROSODY = [
    "none",
    "speed_very_slow",
    "speed_slow",
    "speed_fast",
    "speed_very_fast",
    "pitch_low",
    "pitch_high",
    "expressive_high",
    "expressive_low",
]


def build_prompt(text, emotion, style, prosody):
    tokens = []
    if emotion != "none":
        tokens.append(f"<|emotion:{emotion}|>")
    if style != "none":
        tokens.append(f"<|style:{style}|>")
    if prosody != "none":
        tokens.append(f"<|prosody:{prosody}|>")
    return "".join(tokens) + text


def synthesize(text, emotion, style, prosody, reference_audio, reference_text):
    prompt = build_prompt(text, emotion, style, prosody)
    reference_note = "No reference audio supplied."
    if reference_audio:
        reference_note = f"Reference audio supplied: {reference_audio}"
    if reference_text:
        reference_note += f"\nReference transcript: {reference_text}"
    return (
        "Placeholder only. Real Higgs Audio v3 inference is not wired yet.\n\n"
        f"Model: {MODEL_ID}\n\n"
        f"Request input:\n{prompt}\n\n"
        f"{reference_note}\n\n"
        "Next implementation step: connect this UI to an SGLang-Omni server or a local Transformers inference path."
    )


with gr.Blocks(title="Higgs Audio v3 TTS") as demo:
    gr.Markdown("# Higgs Audio v3 TTS")
    gr.Markdown(
        "Placeholder Pinokio app for `bosonai/higgs-audio-v3-tts-4b`. "
        "Use this UI to shape prompts while the real inference backend is added."
    )
    with gr.Row():
        with gr.Column():
            text = gr.Textbox(
                label="Text",
                value="Hello, how are you?",
                lines=6,
            )
            emotion = gr.Dropdown(["none"] + EMOTIONS, value="none", label="Emotion")
            style = gr.Dropdown(STYLES, value="none", label="Style")
            prosody = gr.Dropdown(PROSODY, value="none", label="Prosody")
            reference_audio = gr.Audio(label="Reference audio", type="filepath")
            reference_text = gr.Textbox(label="Reference transcript", lines=3)
            submit = gr.Button("Build placeholder request")
        with gr.Column():
            output = gr.Textbox(label="Placeholder output", lines=18)
    submit.click(
        synthesize,
        inputs=[text, emotion, style, prosody, reference_audio, reference_text],
        outputs=output,
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1")
