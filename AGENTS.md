# AGENTS.md — Stealth Scribe

## Project Overview

Stealth Scribe is an on-device meeting transcription and diarization tool built for the Raspberry Pi 5. It records audio, transcribes via whisper.cpp, identifies speakers via pyannote.audio, summarizes via a cloud LLM API, and serves transcripts through a Django-ninja web UI. The name "stealth" comes from running silently on a headless Pi — no cloud dependency for the transcription pipeline itself.

## Tech Stack

| Layer           | Technology                                      |
| --------------- | ----------------------------------------------- |
| Language        | Python 3.13                                     |
| Package manager | uv (never pip, never poetry)                    |
| Web framework   | Django-ninja (API) + Django templates + HTMX    |
| Database        | SQLite                                          |
| Transcription   | whisper.cpp (compiled from source, CLI subprocess) |
| Diarization     | pyannote.audio ≥ 4.0.4                          |
| Summarization   | Cloud LLM API (OpenAI, Anthropic)               |
| Email           | TBD                                             |
| Testing         | pytest                                          |
| Linting         | ruff                                            |
| Target hardware | Raspberry Pi 5 (development can happen on macOS) |

## Setup

### First-time setup on a Raspberry Pi

```bash
# 1. Clone the repo
git clone <repo-url> && cd stealth-scribe

# 2. Run the hardware-aware setup script
#    This compiles whisper.cpp with Pi-specific optimizations (ARM NEON, etc.)
#    and downloads quantized model weights.
./setup.sh

# 3. Install Python dependencies
uv sync

# 4. Run migrations
uv run manage.py migrate

# 5. Start the dev server
uv run manage.py runserver 0.0.0.0:8000
```

### Development on macOS

Same steps, but `setup.sh` detects the platform and compiles accordingly. On macOS, `make` produces a Metal-optimized binary.

### Environment variables

| Variable              | Purpose                          | Required |
| --------------------- | -------------------------------- | -------- |
| `WHISPER_MODEL_PATH`  | Path to the quantized ggml model | yes      |
| `OPENAI_API_KEY`      | Cloud LLM for summarization      | yes      |
| `PYANNOTE_AUTH_TOKEN` | HuggingFace token for pyannote   | yes      |
| `SMTP_*`              | Email configuration              | TBD      |

## Project Structure

```
stealth-scribe/
├── setup.sh              # One-time setup: compile whisper.cpp + download models
├── pyproject.toml        # uv project config + dependencies
├── main.py               # Entry point (may become manage.py)
├── vendor/               # External C/C++ code (whisper.cpp) — NEVER edit files here
│   └── whisper.cpp/      #   shallow clone, built locally
├── models/               # Quantized whisper model weights (gitignored, large binaries)
├── src/
│   ├── config.py         # Configuration loading, env var parsing, paths
│   ├── recorder.py       # Audio capture from microphone
│   ├── transcriber.py    # whisper.cpp subprocess wrapper
│   ├── diarizer.py       # pyannote.audio speaker diarization
│   ├── summarizer.py     # Cloud LLM API client for summary generation
│   ├── mailer.py         # Email delivery of transcripts (TBD)
│   └── web-ui/           # Django-ninja application
│       ├── api.py        # API routes (django-ninja Router)
│       ├── urls.py       # URL configuration
│       ├── views.py      # View handlers
│       ├── models.py     # Django models
│       └── templates/    # Django templates with HTMX fragments
└── tests/                # pytest test suite
```

## Development Conventions

### uv commands

```bash
uv sync                          # Install/update dependencies from lockfile
uv add <package>                 # Add a new dependency
uv run manage.py <django-cmd>    # Run Django management commands
uv run pytest                    # Run tests
uv run ruff check .              # Lint
uv run ruff format .             # Format
```

### whisper.cpp integration

- whisper.cpp lives in `vendor/whisper.cpp/` and is compiled by `setup.sh`.
- **Never commit binary artifacts or model weights.** `vendor/` and `models/` are gitignored (except `vendor/.gitkeep`).
- The transcriber calls the whisper binary via `subprocess.run()`. Do not use Python bindings.
- Model path is configured via `WHISPER_MODEL_PATH` env var pointing to a `.bin` file in `models/`.

### Django-ninja patterns

- API routes use `django-ninja`'s `Router` on `/api/`.
- Pages use Django templates. No separate JS frontend.
- HTMX is used for dynamic UI updates (swap fragments, not full page reloads).
- Alpine.js is available for client-side-only state (dropdowns, toggles). Prefer HTMX over Alpine if server interaction is involved.
- Template fragments (HTMX partials) go in `src/web-ui/templates/partials/`.

### Database

- SQLite, no PostgreSQL. The database file is gitignored.
- Always provide migrations — do not rely on `makemigrations` at runtime.

### Performance constraints (Raspberry Pi)

- Roughly 1-4 GB RAM depending on Pi model. Be mindful of memory usage.
- whisper.cpp with a quantized model (e.g., `tiny.en.q4_0.bin`) should use ~200-400 MB RAM during inference.
- pyannote.audio models are also loaded into memory — avoid loading both transcription and diarization models simultaneously unless sufficient RAM is available.
- Favor disk-based queues (SQLite) over in-memory queues for long-running jobs.
- Test memory usage on target hardware before adding new large dependencies.

### Code style

- Follow PEP 8. ruff handles enforcement.
- Use type hints on public function signatures. Not required on internal helpers.
- Prefer `pathlib.Path` over `os.path` for file paths.
- Use `subprocess.run()` with `capture_output=True` and explicit timeouts for CLI calls.
- Log with the standard `logging` module — print statements are not allowed in library code.

## Testing

```bash
uv run pytest                    # Run all tests
uv run pytest tests/transcriber/ # Run a specific test directory
uv run pytest -k "test_diarize"  # Run tests matching a keyword
```

Tests live in `tests/` mirroring the `src/` structure. Use pytest fixtures for shared setup (temp audio files, mock subprocess calls, in-memory SQLite).

## Linting & Formatting

```bash
uv run ruff check .              # Lint
uv run ruff format .             # Format (auto-fix)
```

Run both before committing. CI will enforce them.
