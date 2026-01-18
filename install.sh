#!/bin/bash
set -e

echo "Installing Speak-Turbo..."

# Detect OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$ARCH" in
    x86_64) ARCH="x86_64" ;;
    arm64|aarch64) ARCH="aarch64" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Install Python dependencies
echo "→ Installing Python dependencies..."
pip install --quiet pocket-tts uvicorn fastapi "python-dateutil>=2.7"

# Create bin directory
mkdir -p ~/.local/bin

# Check if Rust is available for building
if command -v cargo &> /dev/null; then
    echo "→ Building CLI from source..."
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    if [ -d "$SCRIPT_DIR/speakturbo-cli" ]; then
        cd "$SCRIPT_DIR/speakturbo-cli"
        cargo build --release --quiet
        cp target/release/speakturbo ~/.local/bin/
    else
        # Clone and build
        TEMP_DIR=$(mktemp -d)
        git clone --quiet https://github.com/EmZod/Speak-Turbo.git "$TEMP_DIR"
        cd "$TEMP_DIR/speakturbo-cli"
        cargo build --release --quiet
        cp target/release/speakturbo ~/.local/bin/
        rm -rf "$TEMP_DIR"
    fi
else
    echo "→ Rust not found. Installing Python CLI wrapper..."
    # Create a Python wrapper as fallback
    cat > ~/.local/bin/speakturbo << 'EOF'
#!/bin/bash
# Fallback wrapper - runs Python CLI
python -m speakturbo.cli "$@"
EOF
    chmod +x ~/.local/bin/speakturbo
fi

# Copy daemon
echo "→ Installing daemon..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/speakturbo" ]; then
    pip install --quiet -e "$SCRIPT_DIR"
fi

# Add to PATH if needed
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "Add to your shell profile:"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
    echo ""
fi

echo "✓ Speak-Turbo installed!"
echo ""
echo "Test it:"
echo "  speakturbo \"Hello world\""
