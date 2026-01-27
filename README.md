# Speak-Turbo

Ultra-fast local TTS. ~90ms to first sound.

```bash
speakturbo "Hello world"
```

## Install as Agent Skill

Add this skill to Claude Code, Cursor, Windsurf, and other AI agents:

```bash
npx skills add EmZod/Speak-Turbo
```

## Install CLI

```bash
pip install pocket-tts uvicorn fastapi
cd speakturbo-cli && cargo build --release
cp target/release/speakturbo ~/.local/bin/
```

## Docs

| File | For | Content |
|------|-----|---------|
| [SKILL.md](SKILL.md) | Using speakturbo | CLI usage, voices, troubleshooting |
| [AGENTS.md](AGENTS.md) | Developing speakturbo | Architecture, code structure |

## License

MIT. Built on [Pocket TTS](https://github.com/kyutai-labs/pocket-tts).
