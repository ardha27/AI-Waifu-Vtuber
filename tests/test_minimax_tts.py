"""Unit tests for MiniMax TTS integration."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock heavy optional dependencies before importing TTS
for mod in ["MeCab", "unidic", "alkana", "torch"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from utils.TTS import MINIMAX_VOICES, minimax_tts


class TestMiniMaxVoices(unittest.TestCase):
    """Test MiniMax voice ID configuration."""

    def test_voices_list_not_empty(self):
        self.assertTrue(len(MINIMAX_VOICES) > 0)

    def test_contains_expected_voices(self):
        self.assertIn("lovely_girl", MINIMAX_VOICES)
        self.assertIn("English_Graceful_Lady", MINIMAX_VOICES)
        self.assertIn("sweet_girl", MINIMAX_VOICES)
        self.assertIn("Deep_Voice_Man", MINIMAX_VOICES)

    def test_no_invalid_chinese_voices(self):
        invalid = ["Chinese_Empress", "Chinese_Gentle_Boy", "Chinese_Cute_Girl"]
        for v in invalid:
            self.assertNotIn(v, MINIMAX_VOICES)


class TestMiniMaxTTS(unittest.TestCase):
    """Test minimax_tts function."""

    @patch("utils.TTS.requests.post")
    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"})
    def test_tts_calls_correct_endpoint(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {"audio": "48656c6c6f"}  # hex for "Hello"
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            out_path = f.name

        try:
            minimax_tts("Hello", output_file=out_path)
            mock_post.assert_called_once()
            call_url = mock_post.call_args[0][0]
            self.assertEqual(call_url, "https://api.minimax.io/v1/t2a_v2")
        finally:
            os.unlink(out_path)

    @patch("utils.TTS.requests.post")
    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"})
    def test_tts_sends_correct_payload(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"audio": "00"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            out_path = f.name

        try:
            minimax_tts("Test", voice_id="sweet_girl", model="speech-2.8-turbo", output_file=out_path)
            payload = mock_post.call_args[1]["json"]
            self.assertEqual(payload["model"], "speech-2.8-turbo")
            self.assertEqual(payload["text"], "Test")
            self.assertEqual(payload["voice_setting"]["voice_id"], "sweet_girl")
            self.assertEqual(payload["audio_setting"]["format"], "mp3")
        finally:
            os.unlink(out_path)

    @patch("utils.TTS.requests.post")
    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"})
    def test_tts_writes_audio_file(self, mock_post):
        mock_resp = MagicMock()
        audio_hex = b"Hello world".hex()
        mock_resp.json.return_value = {"data": {"audio": audio_hex}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            out_path = f.name

        try:
            minimax_tts("Test", output_file=out_path)
            with open(out_path, "rb") as f:
                content = f.read()
            self.assertEqual(content, b"Hello world")
        finally:
            os.unlink(out_path)

    @patch("utils.TTS.requests.post")
    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"})
    def test_tts_raises_on_empty_audio(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"audio": ""}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        with self.assertRaises(RuntimeError):
            minimax_tts("Test", output_file="/tmp/test_empty.mp3")

    @patch.dict(os.environ, {}, clear=True)
    def test_tts_raises_without_api_key(self):
        # Mock config import to also fail
        with patch.dict("sys.modules", {"config": MagicMock(spec=[])}):
            with self.assertRaises((ValueError, ImportError, AttributeError)):
                minimax_tts("Test")

    @patch("utils.TTS.requests.post")
    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"})
    def test_tts_sends_auth_header(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"audio": "00"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            out_path = f.name

        try:
            minimax_tts("Test", output_file=out_path)
            headers = mock_post.call_args[1]["headers"]
            self.assertEqual(headers["Authorization"], "Bearer test-key")
        finally:
            os.unlink(out_path)

    @patch("utils.TTS.requests.post")
    @patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"})
    def test_tts_default_model_is_hd(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"audio": "00"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            out_path = f.name

        try:
            minimax_tts("Test", output_file=out_path)
            payload = mock_post.call_args[1]["json"]
            self.assertEqual(payload["model"], "speech-2.8-hd")
        finally:
            os.unlink(out_path)


if __name__ == "__main__":
    unittest.main()
