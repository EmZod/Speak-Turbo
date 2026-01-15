# Speak-Turbo

**Ultra-fast local text-to-speech for AI agents. ~90ms to first sound.**

```bash
speakturbo "Hello world"
# ⚡ 92ms → ▶ 93ms → ✓ 1245ms
```

Speak-Turbo wraps [Kyutai's Pocket TTS](https://github.com/kyutai-labs/pocket-tts) with a persistent daemon and streaming Rust CLI for near-instant audio playback. The model stays hot in memory — subsequent calls start speaking in under 100ms.

## Why This Exists

AI agents need voice output that doesn't block. Existing TTS solutions are either:
- **Cloud APIs** — 500ms+ latency, rate limits, costs money, privacy concerns
- **Local models** — Cold start every time, 2-5 second delay

Speak-Turbo solves this with a **daemon architecture**: the model loads once and stays resident. The Rust CLI connects via HTTP streaming and begins playback the instant the first audio chunk arrives.

## Quick Start

### Installation (macOS/Linux)

```bash
# 1. Install the daemon (Python)
pip install pocket-tts uvicorn fastapi

# 2. Install the CLI (Rust) - downloads pre-built binary
curl -fsSL https://raw.githubusercontent.com/EmZod/Speak-Turbo/main/install.sh | bash

# 3. Run it
speakturbo "The daemon starts automatically on first use"
```

### Building from Source

```bash
# Clone
git clone https://github.com/EmZod/Speak-Turbo.git
cd Speak-Turbo

# Install daemon dependencies
pip install pocket-tts uvicorn fastapi

# Build CLI
cd speakturbo-cli
cargo build --release
cp target/release/speakturbo ~/.local/bin/
```

## Usage

```bash
# Basic - plays immediately (default voice: alba)
speakturbo "Hello world"

# Different voice
speakturbo "Hello" -v marius

# Save to file (no playback)
speakturbo "Hello" -o output.wav

# Quiet mode (no status output)
speakturbo "Hello" -q

# Pipe from stdin
echo "Hello from stdin" | speakturbo

# List voices
speakturbo --list-voices
```

## Available Voices

| Voice | Type |
|-------|------|
| `alba` | Female (default) |
| `marius` | Male |
| `javert` | Male |
| `jean` | Male |
| `fantine` | Female |
| `cosette` | Female |
| `eponine` | Female |
| `azelma` | Female |

## Performance

| Metric | Value |
|--------|-------|
| Time to first sound | ~90ms (daemon warm) |
| Cold start | 2-5s (model loading) |
| Real-time factor | ~4-6x faster than real-time |
| Sample rate | 24kHz mono |
| Model size | ~100MB |
| Memory usage | ~500MB resident |

## Architecture

```
┌─────────────────────┐
│  speakturbo (Rust)  │  ← 2.2MB binary, instant startup
│  - HTTP streaming   │
│  - Audio playback   │
└──────────┬──────────┘
           │ HTTP :7125
           ▼
┌─────────────────────┐
│  speakturbo-daemon  │  ← Python, stays resident
│  - Pocket TTS model │
│  - Voice state cache│
│  - Auto-shutdown    │
└─────────────────────┘
```

The daemon auto-starts on first CLI invocation and auto-shuts down after 1 hour idle.

## API

The daemon exposes a simple HTTP API:

```bash
# Health check
curl http://127.0.0.1:7125/health
# {"status":"ready","voices":["alba","marius",...]}

# Generate audio (streams WAV)
curl "http://127.0.0.1:7125/tts?text=Hello&voice=alba" -o output.wav
```

## For AI Agents

See [AGENTS.md](AGENTS.md) for detailed integration guidance.

**TL;DR for agents:**
```bash
# Speak text immediately
speakturbo "Your message here"

# Check if daemon is running
curl -s http://127.0.0.1:7125/health | jq -r .status

# Restart daemon if needed
pkill -f "daemon_streaming" && speakturbo "Restarted"
```

## Daemon Management

```bash
# Check status
curl http://127.0.0.1:7125/health

# View logs
cat /tmp/speakturbo.log

# Manual stop
pkill -f "daemon_streaming"

# Manual start (usually not needed)
python -m speakturbo.daemon_streaming &
```

## Troubleshooting

**No audio:**
```bash
# Test by saving to file
speakturbo "test" -o /tmp/test.wav
afplay /tmp/test.wav  # macOS
aplay /tmp/test.wav   # Linux
```

**Daemon won't start:**
```bash
# Check port
lsof -i :7125

# Kill and retry
pkill -f "daemon_streaming"
speakturbo "test"
```

**First run is slow:**
This is expected. The model (~100MB) loads into memory on first use. Subsequent calls will be fast.

## License

MIT License. See [LICENSE](LICENSE).

Speak-Turbo wraps [Pocket TTS](https://github.com/kyutai-labs/pocket-tts) by Kyutai Labs (MIT License).

## Credits

- [Kyutai Labs](https://kyutai.org) — Pocket TTS model and library
- [rodio](https://github.com/RustAudio/rodio) — Rust audio playback
