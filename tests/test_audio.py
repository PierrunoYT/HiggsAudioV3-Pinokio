import io
import sys
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from audio_utils import chunk_text, concat_wavs


def wav_blob(rate=24000, channels=1, frames=b'\x00\x00' * 16):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as out:
        out.setparams((channels, 2, rate, 0, 'NONE', 'not compressed'))
        out.writeframes(frames)
    return buf.getvalue()


class AudioTests(unittest.TestCase):
    def test_unbroken_text_is_bounded_and_preserved(self):
        for text in ['a' * 1001, '\u4f60\u597d' * 501]:
            chunks = chunk_text(text, 100)
            self.assertEqual(''.join(chunks), text)
            self.assertTrue(all(len(chunk) <= 100 for chunk in chunks))

    def test_inline_tokens_stay_intact(self):
        text = 'a' * 98 + '<|sfx:laughter|>Haha' + 'b' * 110
        chunks = chunk_text(text, 100)
        self.assertEqual(''.join(chunks), text)
        self.assertTrue(any('<|sfx:laughter|>' in chunk for chunk in chunks))

    def test_delivery_changes_even_when_chunking_disabled(self):
        self.assertEqual(chunk_text('Hello. <|emotion:sadness|>Goodbye.', 0),
                         ['Hello.', '<|emotion:sadness|>Goodbye.'])

    def test_delivery_prefix_repeats(self):
        chunks = chunk_text('<|style:whispering|>' + 'a' * 250, 100)
        self.assertEqual(len(chunks), 3)
        self.assertTrue(all(c.startswith('<|style:whispering|>') for c in chunks))

    def test_wav_frames_join(self):
        with wave.open(io.BytesIO(concat_wavs([wav_blob(), wav_blob()]))) as result:
            self.assertEqual(result.getnframes(), 32)
            self.assertEqual(result.getframerate(), 24000)

    def test_mismatched_wavs_are_rejected(self):
        for second in [wav_blob(rate=48000), wav_blob(channels=2)]:
            with self.assertRaises(wave.Error):
                concat_wavs([wav_blob(), second])

    def test_invalid_single_empty_and_truncated_wavs(self):
        for blobs in [[], [b'bad'], [wav_blob(frames=b'')], [wav_blob()[:-2]]]:
            with self.assertRaises((wave.Error, EOFError)):
                concat_wavs(blobs)
