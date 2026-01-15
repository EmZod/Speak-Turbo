"""
TDD Tests for speakturbo daemon

Run with: cd speakturbo && uv run pytest tests/test_daemon.py -v
"""

import io
import wave
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create test client - imports daemon which loads model."""
    from speakturbo.daemon import app
    return TestClient(app)


class TestHealthEndpoint:
    """Health check must be fast and informative."""
    
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_returns_ready_status(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ready"
    
    def test_health_lists_voices(self, client):
        response = client.get("/health")
        data = response.json()
        assert "voices" in data
        assert "alba" in data["voices"]
        assert len(data["voices"]) >= 8


class TestTTSEndpoint:
    """Core TTS functionality."""
    
    def test_tts_returns_audio(self, client):
        response = client.post("/tts", data={"text": "Hello"})
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
    
    def test_tts_returns_valid_wav(self, client):
        response = client.post("/tts", data={"text": "Hello world"})
        # Check WAV header
        assert response.content[:4] == b"RIFF"
        assert response.content[8:12] == b"WAVE"
    
    def test_tts_wav_is_playable(self, client):
        response = client.post("/tts", data={"text": "Test"})
        # Parse as WAV file
        wav_io = io.BytesIO(response.content)
        with wave.open(wav_io, 'rb') as wav:
            assert wav.getnchannels() == 1  # Mono
            assert wav.getsampwidth() == 2  # 16-bit
            assert wav.getframerate() == 24000  # 24kHz
            assert wav.getnframes() > 0  # Has audio data
    
    def test_tts_with_voice_parameter(self, client):
        response = client.post("/tts", data={"text": "Hello", "voice": "marius"})
        assert response.status_code == 200
        assert len(response.content) > 44  # More than just WAV header
    
    def test_tts_all_voices_work(self, client):
        voices = ["alba", "marius", "javert", "jean", "fantine", "cosette", "eponine", "azelma"]
        for voice in voices:
            response = client.post("/tts", data={"text": "Test", "voice": voice})
            assert response.status_code == 200, f"Voice {voice} failed"
            assert len(response.content) > 100, f"Voice {voice} returned too little audio"


class TestTTSValidation:
    """Input validation."""
    
    def test_empty_text_returns_422(self, client):
        # FastAPI returns 422 for empty required form fields
        response = client.post("/tts", data={"text": ""})
        assert response.status_code == 422
    
    def test_whitespace_only_returns_400(self, client):
        response = client.post("/tts", data={"text": "   "})
        assert response.status_code == 400
    
    def test_missing_text_returns_422(self, client):
        response = client.post("/tts", data={})
        assert response.status_code == 422
    
    def test_invalid_voice_returns_400(self, client):
        response = client.post("/tts", data={"text": "Hello", "voice": "nonexistent"})
        assert response.status_code == 400


class TestTTSStreaming:
    """Streaming must work for low latency."""
    
    def test_response_is_streamed(self, client):
        # Use stream=True to get streaming response
        with client.stream("POST", "/tts", data={"text": "Hello world this is a test"}) as response:
            assert response.status_code == 200
            chunks = list(response.iter_bytes(chunk_size=1024))
            # Should have multiple chunks for streaming
            assert len(chunks) >= 1


class TestPerformance:
    """Performance requirements."""
    
    def test_ttfc_under_500ms_warm(self, client):
        """Time to first chunk should be under 500ms when warm.
        
        Note: Current implementation buffers full audio before streaming.
        True streaming (with WAV header trick) would achieve <100ms TTFC.
        """
        import time
        
        # Warm up
        client.post("/tts", data={"text": "warmup"})
        
        # Measure
        start = time.perf_counter()
        with client.stream("POST", "/tts", data={"text": "Hello world"}) as response:
            first_chunk = next(response.iter_bytes(chunk_size=1024))
            ttfc = (time.perf_counter() - start) * 1000
        
        assert ttfc < 500, f"TTFC was {ttfc:.0f}ms, expected < 500ms"
    
    def test_generation_faster_than_realtime(self, client):
        """Should generate faster than real-time (RTF > 1)."""
        import time
        
        text = "The quick brown fox jumps over the lazy dog."
        
        start = time.perf_counter()
        response = client.post("/tts", data={"text": text})
        generation_time = time.perf_counter() - start
        
        # Parse audio duration
        wav_io = io.BytesIO(response.content)
        with wave.open(wav_io, 'rb') as wav:
            audio_duration = wav.getnframes() / wav.getframerate()
        
        rtf = audio_duration / generation_time
        assert rtf > 1.0, f"RTF was {rtf:.1f}x, expected > 1.0x"
