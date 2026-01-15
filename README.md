# Speak-Turbo

Ultra-fast local text-to-speech. **~90ms to first sound.**

```bash
speakturbo "Hello world"
```

## Install

```bash
# Python dependencies
pip install pocket-tts uvicorn fastapi

# Build CLI (requires Rust)
cd speakturbo-cli && cargo build --release
cp target/release/speakturbo ~/.local/bin/
```

## Documentation

- **[SKILL.md](SKILL.md)** — Full usage guide, voices, troubleshooting
- **[AGENTS.md](AGENTS.md)** — Integration patterns for AI agents

## Architecture

```
speakturbo (Rust CLI) → HTTP :7125 → daemon (Python + pocket-tts) → audio
```

Daemon auto-starts on first use, auto-stops after 1hr idle.

## License

MIT. Built on [Kyutai's Pocket TTS](https://github.com/kyutai-labs/pocket-tts).
