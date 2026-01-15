"""
TDD Tests for speakturbo CLI

Run with: uv run pytest speakturbo/tests/test_cli.py -v
"""

import os
import subprocess
import tempfile
import time
import wave

import pytest


# Path to CLI
CLI_PATH = os.path.join(os.path.dirname(__file__), "..", "cli.py")


def run_cli(*args, input_text=None, timeout=30):
    """Run the CLI with given arguments."""
    cmd = ["python", CLI_PATH] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=input_text,
        timeout=timeout,
        cwd=os.path.dirname(CLI_PATH),
    )
    return result


class TestCLIBasic:
    """Basic CLI functionality."""
    
    def test_help_works(self):
        result = run_cli("--help")
        assert result.returncode == 0
        assert "speakturbo" in result.stdout.lower() or "usage" in result.stdout.lower()
    
    def test_version_works(self):
        result = run_cli("--version")
        assert result.returncode == 0
    
    def test_list_voices(self):
        result = run_cli("--list-voices")
        assert result.returncode == 0
        assert "alba" in result.stdout
        assert "marius" in result.stdout


class TestCLIGeneration:
    """Audio generation via CLI."""
    
    def test_generate_to_file(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
        
        try:
            result = run_cli("Hello world", "-o", output_path)
            assert result.returncode == 0
            assert os.path.exists(output_path)
            
            # Verify it's a valid WAV
            with wave.open(output_path, 'rb') as wav:
                assert wav.getnchannels() == 1
                assert wav.getframerate() == 24000
                assert wav.getnframes() > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_generate_with_voice(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
        
        try:
            result = run_cli("Hello", "-v", "marius", "-o", output_path)
            assert result.returncode == 0
            assert os.path.exists(output_path)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_read_from_stdin(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
        
        try:
            result = run_cli("-o", output_path, input_text="Hello from stdin")
            assert result.returncode == 0
            assert os.path.exists(output_path)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestCLIValidation:
    """Input validation."""
    
    def test_invalid_voice_shows_error(self):
        result = run_cli("Hello", "-v", "nonexistent", "-o", "/tmp/test.wav")
        assert result.returncode != 0
        assert "invalid" in result.stderr.lower() or "error" in result.stderr.lower()
    
    def test_empty_text_shows_error(self):
        result = run_cli("", "-o", "/tmp/test.wav")
        assert result.returncode != 0


class TestCLIDaemon:
    """Daemon management."""
    
    def test_daemon_status(self):
        result = run_cli("--daemon-status")
        # Should work whether daemon is running or not
        assert result.returncode == 0
