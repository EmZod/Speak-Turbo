"""
speakturbo daemon - Ultra-fast TTS server

Wraps pocket-tts with a TRUE STREAMING HTTP API.
Audio chunks are sent as they're generated, not buffered.
"""

import io
import logging
import struct
import wave
from typing import Iterator, Optional

import torch
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import StreamingResponse

from pocket_tts import TTSModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("speakturbo")

# Available voices
VOICES = ["alba", "marius", "javert", "jean", "fantine", "cosette", "eponine", "azelma"]

# Global model instance (loaded once)
_model: Optional[TTSModel] = None
_voice_states: dict = {}


def get_model() -> TTSModel:
    """Get or load the TTS model (singleton)."""
    global _model
    if _model is None:
        logger.info("Loading TTS model...")
        _model = TTSModel.load_model()
        logger.info("Model loaded successfully")
    return _model


def get_voice_state(voice: str) -> dict:
    """Get or compute voice state (cached)."""
    global _voice_states
    if voice not in _voice_states:
        model = get_model()
        logger.info(f"Loading voice state for: {voice}")
        _voice_states[voice] = model.get_state_for_audio_prompt(voice)
    return _voice_states[voice]


# FastAPI app
app = FastAPI(
    title="speakturbo",
    description="Ultra-fast TTS API powered by pocket-tts",
    version="0.2.0",
)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ready",
        "voices": VOICES,
    }


def make_wav_header(sample_rate: int, num_channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """
    Create a WAV header with a very large data size.
    
    This allows streaming: we don't know the final size, so we use 0x7FFFFFFF.
    Players handle this fine - they just read until EOF.
    """
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    
    # Use max int for sizes (streaming WAV trick)
    data_size = 0x7FFFFFFF
    file_size = data_size + 36
    
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        file_size,
        b'WAVE',
        b'fmt ',
        16,  # fmt chunk size
        1,   # PCM format
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b'data',
        data_size,
    )
    return header


def pcm_from_chunk(chunk: torch.Tensor) -> bytes:
    """Convert a torch audio chunk to PCM bytes."""
    # Clamp and convert to int16
    chunk_int16 = (chunk.clamp(-1, 1) * 32767).short()
    return chunk_int16.numpy().tobytes()


def generate_streaming_wav(
    audio_chunks: Iterator[torch.Tensor],
    sample_rate: int,
) -> Iterator[bytes]:
    """
    Generate WAV data as a stream.
    
    Yields:
        1. WAV header (44 bytes)
        2. PCM chunks as they're generated (~3840 bytes each = 80ms of audio)
    """
    # First, yield the WAV header
    yield make_wav_header(sample_rate)
    
    # Then yield each PCM chunk as it's generated
    for chunk in audio_chunks:
        yield pcm_from_chunk(chunk)
    
    # Add 200ms of silence at the end (prevents audio cutoff)
    silence_samples = int(sample_rate * 0.2)
    yield bytes(silence_samples * 2)


@app.post("/tts")
def text_to_speech(
    text: str = Form(...),
    voice: str = Form(default="alba"),
):
    """
    Generate speech from text with TRUE STREAMING.
    
    Audio chunks are sent as they're generated (every ~80ms).
    This enables ultra-low latency playback.
    """
    # Validate text
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    # Validate voice
    if voice not in VOICES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid voice '{voice}'. Available: {VOICES}"
        )
    
    # Get model and voice state
    model = get_model()
    voice_state = get_voice_state(voice)
    
    # Generate audio stream
    audio_chunks = model.generate_audio_stream(
        model_state=voice_state,
        text_to_generate=text.strip(),
    )
    
    # Return TRUE streaming response
    # Chunks are yielded as they're generated!
    return StreamingResponse(
        generate_streaming_wav(audio_chunks, model.sample_rate),
        media_type="audio/wav",
        headers={
            "Content-Disposition": "attachment; filename=speech.wav",
            "X-Sample-Rate": str(model.sample_rate),
            "X-Streaming": "true",
        },
    )


# Also provide a buffered endpoint for compatibility
@app.post("/tts/buffered")
def text_to_speech_buffered(
    text: str = Form(...),
    voice: str = Form(default="alba"),
):
    """
    Generate speech from text (buffered version).
    
    Waits for full audio before sending. Use /tts for streaming.
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if voice not in VOICES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid voice '{voice}'. Available: {VOICES}"
        )
    
    model = get_model()
    voice_state = get_voice_state(voice)
    
    # Collect all chunks
    audio_chunks = list(model.generate_audio_stream(
        model_state=voice_state,
        text_to_generate=text.strip(),
    ))
    
    if not audio_chunks:
        raise HTTPException(status_code=500, detail="No audio generated")
    
    # Concatenate and convert
    audio = torch.cat(audio_chunks)
    audio_int16 = (audio.clamp(-1, 1) * 32767).short().numpy()
    
    # Write proper WAV
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(model.sample_rate)
        wav.writeframes(audio_int16.tobytes())
    
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="audio/wav",
    )


def run_server(host: str = "127.0.0.1", port: int = 7123):
    """Run the daemon server."""
    import uvicorn
    
    # Pre-load model before starting server
    get_model()
    
    # Pre-warm default voice
    get_voice_state("alba")
    
    logger.info(f"Starting speakturbo daemon on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run_server()
