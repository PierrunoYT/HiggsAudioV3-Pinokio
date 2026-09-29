"""Text chunking and PCM WAV validation shared by the UI and tests."""

import io
import re
import wave

import numpy as np

# Sentence-level delivery tokens (emotion / style / prosody speed-pitch-expressive)
# color the whole request, so a run of them anywhere in the text starts a new
# segment: each segment is synthesized as its own request(s) with its own
# delivery prefix re-applied to every chunk. Inline tokens (sfx, pauses) stay
# wherever they appear.
_DELIVERY_RUN_RE = re.compile(
    r"(?:<\|(?:emotion:[a-z_]+|style:[a-z_]+|prosody:(?:speed|pitch|expressive)_[a-z_]+)\|>\s*)+"
)
_CONTROL_TOKEN_RE = re.compile(r"<\|[a-z_]+:[a-z_]+\|>")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…؟])[ \t]+|(?<=[。！？])|\n+")
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
            # Keep control tokens intact when splitting text without spaces.
            if len(word) > max_chars:
                if current:
                    pieces.append(current)
                    current = ""
                for atom in re.findall(r"<\|[a-z_]+:[a-z_]+\|>|.", word):
                    if current and len(current) + len(atom) > max_chars:
                        pieces.append(current)
                        current = ""
                    current += atom
                continue
            candidate = f"{current} {word}".strip()
            if current and len(candidate) > max_chars:
                pieces.append(current)
                current = word
            else:
                current = candidate
        if current:
            pieces.append(current)
    return pieces


def _split_delivery_segments(text):
    """Split ``text`` into ``(prefix, body)`` segments at every run of
    delivery tokens. Each run replaces the previous delivery entirely, so the
    body after it is spoken with exactly those tokens (sfx/pause tokens stay
    inline within the body)."""
    segments = []
    prefix = ""
    pos = 0
    for match in _DELIVERY_RUN_RE.finditer(text):
        body = text[pos:match.start()].strip()
        if body:
            segments.append((prefix, body))
        prefix = "".join(match.group(0).split())
        pos = match.end()
    body = text[pos:].strip()
    if body:
        segments.append((prefix, body))
    return segments


def _chunk_segment(prefix, body, max_chars):
    """Split one delivery segment into sentence-packed chunks of roughly
    ``max_chars`` characters, re-applying ``prefix`` to every chunk."""
    if max_chars <= 0 or len(prefix) + len(body) <= max_chars:
        return [prefix + body]

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
    return [prefix + chunk for chunk in chunks]


def chunk_text(text, max_chars):
    """Split ``text`` into per-request chunks. The text is first cut at every
    mid-text run of delivery tokens (emotion / style / prosody), because the
    model applies those to the whole request — only a separate request makes a
    later emotion actually take over. Each segment is then sentence-packed
    into chunks of roughly ``max_chars`` characters (0 disables size-based
    chunking but keeps delivery-token splits)."""
    text = (text or "").strip()
    if not text:
        return []
    chunks = []
    for prefix, body in _split_delivery_segments(text):
        chunks.extend(_chunk_segment(prefix, body, max_chars))
    return chunks or [text]


def strip_control_tokens(text):
    return _CONTROL_TOKEN_RE.sub("", text or "").strip()


def concat_wavs(blobs):
    """Concatenate PCM WAV blobs into a single WAV (both backends emit PCM16)."""
    if not blobs:
        raise wave.Error("No audio chunks were returned.")
    params = None
    frames = []
    for blob in blobs:
        with wave.open(io.BytesIO(blob), "rb") as wav:
            if params is None:
                params = wav.getparams()
            elif (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (
                params.nchannels, params.sampwidth, params.framerate
            ):
                raise wave.Error("Audio chunks have different sample rates or channel formats.")
            data = wav.readframes(wav.getnframes())
            if not data or len(data) != wav.getnframes() * wav.getnchannels() * wav.getsampwidth():
                raise wave.Error("Audio chunk is empty or truncated.")
            frames.append(data)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setparams(params)
        out.writeframes(b"".join(frames))
    return buf.getvalue()


def wav_to_array(blob):
    """Decode a PCM16 WAV blob into ``(sample_rate, int16 array)`` for Gradio,
    shaped ``[frames]`` for mono or ``[frames, channels]`` otherwise."""
    with wave.open(io.BytesIO(blob), "rb") as wav:
        if wav.getsampwidth() != 2:
            raise wave.Error("Only 16-bit PCM audio is supported.")
        channels = wav.getnchannels()
        data = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")
        rate = wav.getframerate()
    if channels > 1:
        data = data.reshape(-1, channels)
    return rate, data


