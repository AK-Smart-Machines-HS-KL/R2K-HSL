# opencode team package

## What is this?

opencode is an AI coding agent that runs in your terminal. It reads the ROS2K
codebase, understands the architecture (via the META-ROUTER knowledge base),
and helps you code, debug, and document.

This package installs the team configuration with 14 pre-configured model
favorites across 5 providers.

## Prerequisites

1. **Node.js 18+** — opencode needs it for npm auto-install of AI SDK packages.
   Check: `node --version`. If missing: `sudo apt install nodejs npm`.

2. **opencode binary** — install the binary first:
   ```bash
   curl -fsSL https://opencode.ai/install | bash
   ```
   This downloads the 177 MB binary to `~/.opencode/bin/opencode` and the 63 MB
   node_modules. Internet required.

3. **Ollama (optional but recommended)** — for local models (zero API cost, zero
   latency, works offline):
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull qwen2.5:3b qwen2.5-coder:7b
   ```

## Installation

```bash
tar xzf opencode-team-package.tar.gz
cd opencode-team-package
./install.sh
```

The installer copies config files to `~/.config/opencode/` and model favorites
to `~/.local/share/opencode/`. It does NOT touch the opencode binary or
node_modules (those come from the official installer in step 2 above).

## API Keys

After installation, edit `~/.config/opencode/opencode.json` and replace these
placeholders with your own API keys:

| Placeholder | Provider | Sign up at |
|-------------|----------|------------|
| `<YOUR_OPENROUTER_KEY_HERE>` | OpenRouter | https://openrouter.ai/keys |
| `<YOUR_UNI_MAINZ_KEY_HERE>` | Uni Mainz | https://ki-chat.uni-mainz.de |
| `<YOUR_GOOGLE_KEY_HERE>` | in `opencode.jsonc` | https://aistudio.google.com/apikey |

**Ollama Cloud** uses a shared team key that is NOT in this repo (public!).
Replace `REPLACE_WITH_SHARED_OLLAMA_CLOUD_KEY` in the installed
`~/.config/opencode/opencode.json` with the key you received individually
from the maintainer (or via the tarball, which is built per-recipient and
never committed).

## Available Models (14 favorites)

### Local Ollama (no API key needed)
| Model | Use case |
|-------|---------|
| `qwen2.5:3b` | Summarize, chat — fast, 2 GB VRAM |
| `qwen2.5-coder:7b` | Search, explore — 5 GB VRAM |
| `qwen2.5-coder:32b` | Coding (main) — 20 GB VRAM |
| `glm-4.7-flash:latest` | Deep think (local) |

### Ollama Cloud (shared team key — insert individually, see API Keys above)
| Model | Use case |
|-------|---------|
| `qwen3.5:397b` | Deep think — Qwen 3.5 397B |
| `kimi-k3` | Deep think — Kimi K3 |
| `gpt-oss:120b` | Deep think — GPT OSS 120B |
| `glm-5.2` | Deep think — GLM 5.2 |

### Uni Mainz (get your own key)
| Model | Use case |
|-------|---------|
| `Qwen3 Coder 30B` | Coding (fallback) |
| `Qwen3 235B Thinking` | Deep think (fallback) |
| `GPT OSS 120B` | Deep think (fallback) |
| `qwen3.6-35b` | Chat (fallback) |

### OpenRouter (get your own key)
| Model | Use case |
|-------|---------|
| `z-ai/glm-5.3-flash` | Offer: complex coding, deep think (50% off, expires Sep 9) |
| `meta/muse-spark-1.2-contributor` | Offer: coding agent (cheap, Meta trains on data) |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | Offer: deep think (free, slow, 79% uptime) |
| `@preset/ros2k-auto` | Auto-router |
| `z-ai/glm-5.3` | Complex coding, deep think |

### Google (get your own key, in opencode.jsonc)
| Model | Use case |
|-------|---------|
| `gemini-3.5-flash` | Fallback |

## Running

```bash
cd ~/R2K-HSL
opencode
```

opencode reads `~/R2K-HSL/.opencode/opencode.json` which points it to the
ROS2K knowledge base (META-ROUTER + agent prompt). It automatically knows about
the project architecture, axioms, and conventions.

## Notes

- The default model is `qwen2.5-coder:32b` (local Ollama). If your GPU has
  less than 20 GB VRAM, change it to `qwen2.5-coder:7b` or use a cloud model.
- The `explore` and `plan` sub-agents use `qwen2.5-coder:7b` (local). If you
  don't have Ollama installed, change these to a cloud model in
  `~/.config/opencode/opencode.json`.
- The shared Ollama Cloud key has a quota. If you hit rate limits, get your
  own key at https://ollama.com/settings/api-keys.