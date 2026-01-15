#!/usr/bin/env python3
"""
Raw TCP streaming server - bypasses HTTP buffering.

This is a proof of concept to show that true streaming works.
"""

import socket
import struct
import sys
import time

import torch
from pocket_tts import TTSModel

HOST = "127.0.0.1"
PORT = 7124


def make_wav_header(sample_rate: int) -> bytes:
    """Create WAV header with streaming-friendly size."""
    byte_rate = sample_rate * 2  # 16-bit mono
    data_size = 0x7FFFFFFF
    file_size = data_size + 36
    
    return struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', file_size, b'WAVE', b'fmt ', 16, 1, 1,
        sample_rate, byte_rate, 2, 16, b'data', data_size,
    )


def handle_client(conn, model, voice_states):
    """Handle a single client connection."""
    try:
        # Read request (simple protocol: voice_name\ntext)
        data = conn.recv(4096).decode('utf-8')
        lines = data.strip().split('\n')
        voice = lines[0] if len(lines) > 0 else "alba"
        text = lines[1] if len(lines) > 1 else "Hello world"
        
        print(f"Request: voice={voice}, text={text[:50]}...")
        
        # Get voice state
        if voice not in voice_states:
            voice_states[voice] = model.get_state_for_audio_prompt(voice)
        voice_state = voice_states[voice]
        
        # Send WAV header immediately
        conn.sendall(make_wav_header(model.sample_rate))
        print(f"  Sent WAV header")
        
        # Stream audio chunks as they're generated
        start = time.perf_counter()
        for i, chunk in enumerate(model.generate_audio_stream(voice_state, text)):
            # Convert to PCM bytes
            pcm = (chunk.clamp(-1, 1) * 32767).short().numpy().tobytes()
            conn.sendall(pcm)
            
            elapsed = (time.perf_counter() - start) * 1000
            if i < 5 or i % 20 == 0:
                print(f"  Chunk {i+1}: {len(pcm)} bytes at {elapsed:.0f}ms")
        
        # Add trailing silence
        silence = bytes(int(model.sample_rate * 0.2) * 2)
        conn.sendall(silence)
        
        print(f"  Done!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()


def main():
    print("Loading model...")
    model = TTSModel.load_model()
    voice_states = {"alba": model.get_state_for_audio_prompt("alba")}
    print(f"Model loaded. Starting server on {HOST}:{PORT}")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        print("Listening...")
        
        while True:
            conn, addr = s.accept()
            print(f"\nConnection from {addr}")
            handle_client(conn, model, voice_states)


if __name__ == "__main__":
    main()
