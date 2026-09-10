import contextlib
import importlib
import io
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.torch = MagicMock()
        cls.torch.cuda.is_available.return_value = False
        cls.torch.backends.mps.is_available.return_value = False
        cls.torch.inference_mode.side_effect = contextlib.nullcontext
        cls.model = MagicMock()
        cls.model.config.sample_rate = 24000
        transformers = MagicMock()
        transformers.AutoModelForCausalLM.from_pretrained.return_value.to.return_value.eval.return_value = cls.model
        with patch.dict(sys.modules, {'torch': cls.torch, 'transformers': transformers, 'uvicorn': MagicMock()}):
            cls.server = importlib.import_module('server')
        cls.client = TestClient(cls.server.app)

    def setUp(self):
        self.model.generate_speech.side_effect = None
        audio = MagicMock()
        audio.detach.return_value.cpu.return_value.float.return_value = audio
        audio.numel.return_value = 32
        audio.numpy.return_value = np.zeros(32, dtype=np.float32)
        self.model.generate_speech.return_value = audio

    def test_valid_speech(self):
        response = self.client.post('/v1/audio/speech', json={'input': 'Hello', 'seed': 42})
        self.assertEqual(response.status_code, 200)
        data, rate = sf.read(io.BytesIO(response.content))
        self.assertEqual((len(data), rate), (32, 24000))

    def test_invalid_settings(self):
        for field, value in [('temperature', -1), ('top_p', 0), ('top_p', 2),
                             ('top_k', -1), ('max_new_tokens', 0), ('max_new_tokens', 4097),
                             ('seed', -2), ('stream', True), ('response_format', 'mp3'),
                             ('references', [{'audio_path': 'x'}, {'audio_path': 'y'}])]:
            with self.subTest(field=field, value=value):
                response = self.client.post('/v1/audio/speech', json={'input': 'Hello', field: value})
                self.assertEqual(response.status_code, 422)

    def test_blank_input(self):
        self.assertEqual(self.client.post('/v1/audio/speech', json={'input': '  '}).status_code, 400)

    def test_invalid_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.wav'
            path.write_text('invalid')
            response = self.client.post('/v1/audio/speech', json={
                'input': 'Hello', 'references': [{'audio_path': str(path)}]})
            self.assertEqual(response.status_code, 400)

    def test_generations_are_serialized(self):
        active = 0
        peak = 0
        guard = threading.Lock()
        audio = self.model.generate_speech.return_value

        def generate(*args, **kwargs):
            nonlocal active, peak
            with guard:
                active += 1
                peak = max(peak, active)
            time.sleep(0.03)
            with guard:
                active -= 1
            return audio

        self.model.generate_speech.side_effect = generate
        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(lambda seed: self.client.post('/v1/audio/speech',
                json={'input': 'Hello', 'seed': seed}), range(4)))
        self.assertEqual([r.status_code for r in responses], [200] * 4)
        self.assertEqual(peak, 1)
