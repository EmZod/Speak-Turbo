# AGENTS.md

Guidance for AI agents working on the Speak-Turbo codebase.

> **Using speakturbo?** See [SKILL.md](SKILL.md) instead.

## Project Structure

```
speakturbo/              # Python daemon
├── daemon_streaming.py  # Main FastAPI server (port 7125)
├── cli.py               # Python CLI fallback
└── tests/               # pytest tests

speakturbo-cli/          # Rust CLI (primary interface)
├── Cargo.toml
└── src/main.rs          # Streaming HTTP client + audio playback
```

## Architecture

```
User → speakturbo (Rust) → HTTP GET /tts → daemon (Python) → pocket-tts → audio stream
                                              ↓
                                         Model in memory (TTSModel)
                                         Voice states cached (LRU)
```

The Rust CLI exists purely for latency — it starts in ~1ms vs Python's ~100ms interpreter startup.

## Development

```bash
# Python daemon
pip install -e .
python -m speakturbo.daemon_streaming

# Rust CLI
cd speakturbo-cli
cargo build --release
./target/release/speakturbo "test"

# Tests
pytest speakturbo/tests/ -v
```

## Key Files

| File | Purpose |
|------|---------|
| `daemon_streaming.py` | FastAPI app, `/health` and `/tts` endpoints |
| `speakturbo-cli/src/main.rs` | HTTP streaming, audio buffer, rodio playback |
| `SKILL.md` | User-facing documentation |

## Design Decisions

1. **Daemon architecture**: Model loading is slow (~3s). Keep it resident.
2. **Rust CLI**: Python startup adds 100ms. Rust adds ~1ms.
3. **HTTP streaming**: Start playback before generation completes.
4. **Auto-shutdown**: Free memory after 1hr idle. Users don't manage daemons.
5. **No voice cloning**: Simplicity. Use `speak` (Chatterbox) for that.

## API

```
GET /health → {"status": "ready", "voices": [...]}
GET /tts?text=Hello&voice=alba → audio/wav (streaming)
```

## Common Tasks

**Add a voice**: Voices come from pocket-tts. Update `VOICES` list in `daemon_streaming.py`.

**Change port**: Update `DAEMON_URL` in `main.rs` and port in `daemon_streaming.py`.

**Reduce latency**: The bottleneck is pocket-tts generation (~40ms per frame). CLI/daemon overhead is <10ms.
