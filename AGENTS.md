# AGENTS.md

Guidance for AI agents integrating Speak-Turbo for text-to-speech output.

## Overview

Speak-Turbo provides ultra-low-latency local TTS. Use it when you need to speak to users without blocking on cloud APIs or waiting for model loading.

**Key properties:**
- ~90ms to first audio (daemon warm)
- Fully local — no internet required after install
- 8 built-in voices (no voice cloning)
- Auto-managed daemon — just call the CLI

## Basic Usage

```bash
# Speak text (plays through default audio output)
speakturbo "Hello, I'm ready to help you."

# Different voice
speakturbo "This is a male voice" -v marius

# Save to file instead of playing
speakturbo "Saved audio" -o /tmp/output.wav

# Quiet mode (suppress status messages, still plays audio)
speakturbo "Quiet" -q

# Read from stdin (useful for long text)
cat article.txt | speakturbo
```

## Voice Selection

| Voice | Gender | Best For |
|-------|--------|----------|
| `alba` | Female | Default, neutral, clear |
| `marius` | Male | Authoritative, clear |
| `javert` | Male | Deeper, formal |
| `jean` | Male | Warm, conversational |
| `fantine` | Female | Soft, expressive |
| `cosette` | Female | Young, bright |
| `eponine` | Female | Warm, mid-range |
| `azelma` | Female | Clear, neutral |

```bash
# Example voice selection
speakturbo "Important announcement" -v marius
speakturbo "Let me explain this gently" -v fantine
```

## Daemon Management

The daemon starts automatically on first use. You rarely need to manage it manually.

```bash
# Check if daemon is running and healthy
curl -s http://127.0.0.1:7125/health
# Returns: {"status":"ready","voices":[...],"idle_timeout_mins":60}

# If daemon seems stuck, restart it
pkill -f "daemon_streaming"
speakturbo "Daemon restarted"  # Auto-restarts

# View daemon logs
cat /tmp/speakturbo.log
```

**Auto-shutdown:** The daemon automatically shuts down after 1 hour of inactivity to free memory.

## Error Handling

```bash
# Pattern: Check exit code
if speakturbo "Hello" 2>/dev/null; then
    echo "Speech succeeded"
else
    echo "Speech failed - daemon may be down"
    # Retry once
    pkill -f "daemon_streaming" 2>/dev/null
    sleep 1
    speakturbo "Retrying"
fi
```

**Exit codes:**
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (daemon down, invalid args, etc.) |

## Performance Expectations

| Scenario | Time to First Sound |
|----------|---------------------|
| Daemon warm (typical) | ~90ms |
| Daemon cold (first call) | 2-5 seconds |
| After 1hr idle | 2-5 seconds (daemon auto-stopped) |

**Tip:** If response time is critical, send a health check to keep the daemon warm:
```bash
curl -s http://127.0.0.1:7125/health > /dev/null
```

## Long Text

Speak-Turbo streams audio — it begins speaking before the full text is processed. Long inputs work fine:

```bash
# This works and streams as it generates
speakturbo "$(cat long_article.txt)"

# Or via stdin
cat long_article.txt | speakturbo
```

## Integration Patterns

### Pattern 1: Fire and Forget
```bash
# Speak in background, don't block
speakturbo "Processing your request" &
# ... do other work ...
```

### Pattern 2: Sequential Speech
```bash
# Speak multiple messages in order
speakturbo "First, let me check the data."
speakturbo "Found 42 results."
speakturbo "Here's what I found."
```

### Pattern 3: Conditional Voice
```bash
# Use different voices for different purposes
announce() { speakturbo "$1" -v marius; }
explain() { speakturbo "$1" -v alba; }
warn() { speakturbo "$1" -v javert; }

announce "Attention please"
explain "Let me walk you through this"
warn "Warning: this action cannot be undone"
```

### Pattern 4: Status Updates
```bash
# Quick status without verbose output
speakturbo -q "Done"
```

## What Speak-Turbo Is NOT For

- **Voice cloning** — Use `speak` (Chatterbox) skill instead
- **Emotion tags** — No support for `[laugh]`, `[sigh]`, etc.
- **Non-English** — English only
- **Real-time conversation** — Latency is good but not quite real-time

## HTTP API (Advanced)

For direct integration without the CLI:

```bash
# Stream TTS audio
curl "http://127.0.0.1:7125/tts?text=Hello%20world&voice=alba" \
  --output - | afplay -  # macOS
  
# Health check
curl http://127.0.0.1:7125/health
```

## Troubleshooting for Agents

| Problem | Solution |
|---------|----------|
| "Daemon not running?" error | `pkill -f daemon_streaming; sleep 2; speakturbo "test"` |
| No audio output | Check system audio: `speakturbo "test" -o /tmp/t.wav && afplay /tmp/t.wav` |
| Slow first call | Normal — model loading. Subsequent calls fast. |
| Port 7125 in use | `lsof -i :7125` to find conflict, then `pkill -f daemon_streaming` |

## Quick Reference

```bash
# Basic
speakturbo "text"           # Speak with default voice
speakturbo "text" -v NAME   # Speak with specific voice
speakturbo "text" -o FILE   # Save to WAV file
speakturbo "text" -q        # Quiet mode

# Management
curl http://127.0.0.1:7125/health  # Check daemon
pkill -f "daemon_streaming"         # Stop daemon
speakturbo --list-voices            # List voices

# Voices: alba, marius, javert, jean, fantine, cosette, eponine, azelma
```
