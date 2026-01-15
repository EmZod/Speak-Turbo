---
name: speakturbo
description: Ultra-fast text-to-speech with 8 built-in voices only. ~90ms to first sound. Cannot clone custom voices. Use when users need instant audio with standard voices. For custom voice cloning (Morgan Freeman, celebrities, personal voices), use the `speak` skill instead.
---

# speakturbo - Ultra-Fast TTS

Blazingly fast text-to-speech with streaming playback. Audio starts in ~90ms.

> **Need custom voices (Morgan Freeman, celebrities)?** speakturbo only has 8 built-in voices. Use the `speak` skill instead:
> ```bash
> speak "Your text" --voice ~/.chatter/voices/morgan_freeman.wav
> ```
> Voice files are 10-30 second WAV samples in `~/.chatter/voices/`. See the `speak` skill for setup.

## Quick Start

```bash
# Play immediately - you should hear "Hello world" through your speakers
speakturbo "Hello world"
# Output: ⚡ 92ms → ▶ 93ms → ✓ 1245ms

# Verify it's working by saving to file
speakturbo "Hello world" -o test.wav
ls -lh test.wav  # Should show ~50-100KB file
```

**Output explained:** `⚡` = first audio received, `▶` = playback started, `✓` = done

## First Run

The **first execution takes 2-5 seconds** while the daemon starts and loads the model into memory. Subsequent calls are ~90ms to first sound.

```bash
# First run (slow - daemon starting)
speakturbo "Starting up"  # ~2-5 seconds

# Second run (fast - daemon already running)
speakturbo "Now I'm fast"  # ~90ms
```

## Usage

```bash
# Basic - plays immediately (default voice: alba)
speakturbo "Hello world"

# Different voice (male: marius, javert, jean)
speakturbo "Hello" -v marius

# Save to file (no audio playback)
speakturbo "Hello" -o output.wav

# Combine voice + output
speakturbo "Goodbye" -v jean -o goodbye.wav

# Quiet mode (suppress status messages, still plays audio)
speakturbo "Hello" -q

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
| First run | 2-5s (daemon startup) |
| Real-time factor | ~4x faster |
| Sample rate | 24kHz mono |

## Architecture

```
speakturbo (Rust CLI, 2.2MB)
    │
    │ HTTP streaming (port 7125)
    ▼
speakturbo-daemon (Python + pocket-tts)
    │
    │ Model in memory, auto-shutdown after 1hr idle
    ▼
Audio playback (rodio)
```

## Text Input

- **Encoding:** UTF-8
- **Quotes in text:** Use escaping: `speakturbo "She said \"hello\""`
- **Long text:** Supported, streams as it generates

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (audio played/saved) |
| 1 | Error (daemon connection failed, invalid args) |

## When to Use

**Use speakturbo when:**
- You need instant audio feedback (~90ms)
- Speed matters more than voice variety
- Built-in voices are sufficient

**Use `speak` instead when:**
- You need custom voice cloning (Morgan Freeman, etc.)
  → `speak "text" --voice ~/.chatter/voices/morgan_freeman.wav`
- You need emotion tags like `[laugh]`, `[sigh]`
- Quality/variety matters more than speed

See the `speak` skill documentation for full usage.

## Troubleshooting

**No audio plays:**
```bash
# Check daemon is running
curl http://127.0.0.1:7125/health
# Expected: {"status":"ready","voices":["alba","marius",...]}

# Verify by saving to file and playing manually
speakturbo "test" -o /tmp/test.wav
afplay /tmp/test.wav  # macOS
aplay /tmp/test.wav   # Linux
```

**Daemon won't start:**
```bash
# Check port availability
lsof -i :7125

# Manually kill and restart
pkill -f "daemon_streaming"
speakturbo "test"  # Auto-restarts daemon
```

**First run is slow:**
This is expected. The daemon needs to load the ~100MB model into memory. Subsequent calls will be fast (~90ms).

## Daemon Management

The daemon auto-starts on first use and **auto-shuts down after 1 hour idle**.

```bash
# Check status
curl http://127.0.0.1:7125/health

# Manual stop
pkill -f "daemon_streaming"

# View logs
cat /tmp/speakturbo.log
```

## Comparison with speak

| Feature | speakturbo | speak |
|---------|------------|-------|
| Time to first sound | ~90ms | ~4-8s |
| Voice cloning | ❌ | ✅ |
| Emotion tags | ❌ | ✅ |
| Voices | 8 built-in | Custom wav files |
| Engine | pocket-tts | Chatterbox |
