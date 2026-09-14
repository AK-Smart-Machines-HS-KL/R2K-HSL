#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "  opencode team package — installer"
echo "=========================================="
echo

# 1. Check if opencode binary exists
if [ ! -f "$HOME/.opencode/bin/opencode" ]; then
    echo "❌ opencode binary not found at ~/.opencode/bin/opencode"
    echo "   Install it first:"
    echo "   curl -fsSL https://opencode.ai/install | bash"
    echo
    echo "   Then re-run this script."
    exit 1
fi

echo "✅ opencode binary found: $(opencode --version 2>/dev/null || echo 'unknown version')"
echo

# 2. Copy global config
echo "Installing global config..."
mkdir -p "$HOME/.config/opencode"
cp -f "$SCRIPT_DIR/config/opencode.json" "$HOME/.config/opencode/opencode.json"
cp -f "$SCRIPT_DIR/config/opencode.jsonc" "$HOME/.config/opencode/opencode.jsonc"
echo "  → ~/.config/opencode/opencode.json"
echo "  → ~/.config/opencode/opencode.jsonc"

# 3. Copy model favorites
echo "Installing model favorites..."
mkdir -p "$HOME/.local/share/opencode"
cp -f "$SCRIPT_DIR/share/model.json" "$HOME/.local/share/opencode/model.json"
echo "  → ~/.local/share/opencode/model.json (11 favorites)"

# 4. Copy project .opencode if repo exists
if [ -d "$HOME/R2K-HSL/.opencode" ]; then
    echo "Installing project .opencode..."
    cp -f "$SCRIPT_DIR/project-opencode/opencode.json" "$HOME/R2K-HSL/.opencode/opencode.json"
    echo "  → ~/R2K-HSL/.opencode/opencode.json"
else
    echo "⚠️  ~/R2K-HSL/.opencode/ not found — skip project config."
    echo "   If you have the repo elsewhere, copy project-opencode/opencode.json"
    echo "   to <repo>/.opencode/opencode.json manually."
fi

echo
echo "=========================================="
echo "  Installation complete!"
echo "=========================================="
echo
echo "ACTION REQUIRED — replace these placeholders with your API keys:"
echo

# Check which keys still need filling in
KEYS_NEEDED=()

if grep -q "YOUR_OPENROUTER_KEY_HERE" "$HOME/.config/opencode/opencode.json" 2>/dev/null; then
    KEYS_NEEDED+=("  OpenRouter:  <YOUR_OPENROUTER_KEY_HERE>  → https://openrouter.ai/keys")
fi
if grep -q "YOUR_UNI_MAINZ_KEY_HERE" "$HOME/.config/opencode/opencode.json" 2>/dev/null; then
    KEYS_NEEDED+=("  Uni Mainz:   <YOUR_UNI_MAINZ_KEY_HERE>   → https://ki-chat.uni-mainz.de")
fi
if grep -q "YOUR_OLLAMA_CLOUD_KEY_HERE" "$HOME/.config/opencode/opencode.json" 2>/dev/null; then
    KEYS_NEEDED+=("  Ollama Cloud: <YOUR_OLLAMA_CLOUD_KEY_HERE> → https://ollama.com/settings/api-keys")
fi
if grep -q "YOUR_GOOGLE_KEY_HERE" "$HOME/.config/opencode/opencode.jsonc" 2>/dev/null; then
    KEYS_NEEDED+=("  Google:      <YOUR_GOOGLE_KEY_HERE>      → https://aistudio.google.com/apikey")
fi

if [ ${#KEYS_NEEDED[@]} -gt 0 ]; then
    echo "Edit these files and replace the placeholders:"
    echo "  ~/.config/opencode/opencode.json"
    echo "  ~/.config/opencode/opencode.jsonc"
    echo
    printf '%s\n' "${KEYS_NEEDED[@]}"
else
    echo "✅ All API keys already configured."
fi

echo
echo "Ollama Cloud is pre-configured with a shared team key."
echo "Local Ollama models (qwen2.5:3b, qwen2.5-coder:7b, qwen2.5-coder:32b)"
echo "work without any API keys if Ollama is installed locally."
echo
echo "To start: cd ~/R2K-HSL && opencode"
echo