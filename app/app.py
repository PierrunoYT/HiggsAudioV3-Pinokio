try:
    import spaces
except ImportError:
    class spaces:
        @staticmethod
        def GPU(duration=None):
            def decorator(func):
                return func
            return decorator

import torch
import torchaudio
import soundfile as sf
import gradio as gr
from transformers import (
    AutoModelForCausalLM,
    AutoProcessor,
    AutoTokenizer,
    MoonshineForConditionalGeneration,
)

MODEL_REPO = "multimodalart/higgs-audio-v3-tts-4b-transformers"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.bfloat16 if DEVICE == "cuda" else torch.float32

tokenizer = AutoTokenizer.from_pretrained(MODEL_REPO)
model = (
    AutoModelForCausalLM.from_pretrained(
        MODEL_REPO, trust_remote_code=True, dtype=DTYPE
    )
    .to(DEVICE)
    .eval()
)
model.get_audio_codec()
SR = model.config.sample_rate

ASR_SAMPLE_RATE = 16000
asr_processor = AutoProcessor.from_pretrained("UsefulSensors/moonshine-base")
asr_model = MoonshineForConditionalGeneration.from_pretrained("UsefulSensors/moonshine-base").eval()


def transcribe(reference_audio):
    if not reference_audio:
        return gr.update()
    data, sr = sf.read(reference_audio, dtype="float32", always_2d=True)
    wav = torch.from_numpy(data).mean(dim=1)
    if sr != ASR_SAMPLE_RATE:
        wav = torchaudio.functional.resample(wav, orig_freq=sr, new_freq=ASR_SAMPLE_RATE)
    inputs = asr_processor(wav.numpy(), sampling_rate=ASR_SAMPLE_RATE, return_tensors="pt")
    with torch.no_grad():
        tokens = asr_model.generate(**inputs)
    return asr_processor.decode(tokens[0], skip_special_tokens=True).strip()


@spaces.GPU(duration=120)
def synthesize(text, reference_audio, reference_text, temperature, top_p, top_k, max_new_tokens, seed):
    text = (text or "").strip()
    if not text:
        raise gr.Error("Please enter some text to synthesize.")

    if seed is not None and int(seed) >= 0:
        torch.manual_seed(int(seed))

    kwargs = dict(
        max_new_tokens=int(max_new_tokens),
        temperature=float(temperature),
        top_p=float(top_p) if float(top_p) < 1.0 else None,
        top_k=int(top_k) if int(top_k) > 0 else None,
    )

    if reference_audio is not None:
        data, sr = sf.read(reference_audio, dtype="float32", always_2d=True)
        wav = torch.from_numpy(data).mean(dim=1)
        kwargs["reference_audio"] = wav
        kwargs["reference_sample_rate"] = sr
        if reference_text and reference_text.strip():
            kwargs["reference_text"] = reference_text.strip()

    audio = model.generate_speech(text, tokenizer, **kwargs)
    if audio.numel() == 0:
        raise gr.Error("Generation produced no audio — try again or adjust the text.")
    return (SR, audio.numpy())


with gr.Blocks(title="Higgs Audio v3 TTS") as demo:
    gr.Markdown(
        "# 🍋 Higgs Audio v3 TTS\n"
        "Zero-shot text-to-speech & voice cloning with "
        "[`higgs-audio-v3-tts-4b`](https://huggingface.co/bosonai/higgs-audio-v3-tts-4b), "
        "ported to run on plain 🤗 transformers "
        "([model repo](https://huggingface.co/multimodalart/higgs-audio-v3-tts-4b-transformers))."
    )
    with gr.Row():
        with gr.Column():
            text = gr.Textbox(
                label="Text to synthesize",
                placeholder="Type what you want the voice to say…",
                lines=4,
            )
            reference_audio = gr.Audio(
                label="Reference voice (optional — for cloning)",
                type="filepath",
            )
            reference_text = gr.Textbox(
                label="Reference transcript (auto-filled on upload, improves cloning)",
                lines=2,
            )
            with gr.Accordion("Advanced settings", open=False):
                temperature = gr.Slider(0.0, 1.5, value=0.7, step=0.05, label="Temperature")
                top_p = gr.Slider(0.1, 1.0, value=0.95, step=0.01, label="Top-p")
                top_k = gr.Slider(0, 1026, value=50, step=1, label="Top-k (0 = off)")
                max_new_tokens = gr.Slider(64, 4096, value=2048, step=64, label="Max new tokens")
                seed = gr.Number(value=-1, label="Seed (-1 = random)", precision=0)
            run = gr.Button("Generate speech", variant="primary")
        with gr.Column():
            output_audio = gr.Audio(label="Generated speech", type="numpy")

    gr.Examples(
        examples=[
            ["Higgs Audio version three, now running on plain transformers.", None, ""],
            ["The quick brown fox jumps over the lazy dog.", None, ""],
        ],
        inputs=[text, reference_audio, reference_text],
    )

    reference_audio.change(
        transcribe, inputs=[reference_audio], outputs=[reference_text], api_name="transcribe"
    )

    run.click(
        synthesize,
        inputs=[text, reference_audio, reference_text, temperature, top_p, top_k, max_new_tokens, seed],
        outputs=output_audio,
    )

demo.queue().launch(server_name="127.0.0.1", theme=gr.themes.Citrus())
