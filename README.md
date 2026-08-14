<p align="center">
  <img src="./src/local_lingo/assets/icon-readme.png" width="88" alt="LocalLingo icon">
</p>

<h1 align="center">LocalLingo</h1>

A private, local proofreader and translator web app (**LocalLingo**). It rewrites text so it sounds natural in the detected language, then translates it to the other language in your pair — using [Ollama](https://ollama.com) on your machine.

## Features

- Bidirectional language pairs (e.g. `en-hu`, `de-fr`)
- Native-style rewrite, then translation
- Local Gradio UI (no data sent to cloud APIs)
- Copy buttons on corrected text and translation results

## Requirements

- macOS / Linux / Windows with enough RAM for your chosen model  
  (e.g. `gemma3:12b` works well on Apple Silicon with ~24 GB unified memory)
- [Ollama](https://ollama.com/download) installed and running
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended; it can install Python 3.11+ for you)
- Python 3.11+ (only if you skip uv and use pip)

## 1. Install and start Ollama

1. Download Ollama from [https://ollama.com/download](https://ollama.com/download).
2. Open the Ollama app (or run `ollama serve` in a terminal).
3. Confirm it is running:

```bash
curl http://localhost:11434
```

You should see a response like `Ollama is running`.

### Useful Ollama commands

```bash
# List installed models
ollama list

# See which models are currently loaded in memory
ollama ps

# Pull (download) a model
ollama pull gemma3:12b

# Run a model interactively (optional test)
ollama run gemma3:12b

# Unload a model from memory
ollama stop gemma3:12b

# Remove a model from disk
ollama rm gemma3:12b
```

### Suggested models

| Model | Approx. size | Notes |
|--------|---------------|--------|
| `gemma3:12b` | ~8 GB | Default in this app; good balance for rewrite + translate |
| `gemma3:4b` | ~3 GB | Faster / lighter, lower quality |
| `qwen2.5:7b` | ~4–5 GB | Strong multilingual alternative |
| `translategemma:12b` | ~8 GB | Strong for pure translation; weaker for rewrite prompts |

Default used by the app: **`gemma3:12b`**.

```bash
ollama pull gemma3:12b
```

First request after pulling can take longer while the model loads into memory.

## 2. Project setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you do not have it yet, then:

```bash
git clone git@github.com:arcadas/local-lingo.git
cd local-lingo
uv sync
```

`uv sync` creates `.venv` and installs locked dependencies. It will also fetch a compatible Python (3.11+) if needed.

### pip (alternative)

```bash
git clone git@github.com:arcadas/local-lingo.git
cd local-lingo
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -e .
```

On macOS and many Linux systems the interpreter is **`python3`**, not `python`. If `python3` is missing, install Python 3.11+ from [python.org](https://www.python.org/downloads/) or Homebrew (`brew install python`). Windows: `py -3 -m venv .venv`. After `source .venv/bin/activate`, `python` points at this project’s environment.

## 3. Start the web app

```bash
uv run local-lingo
```

Or equivalently: `uv run python -m local_lingo`.

Or with auto-reload while developing:

```bash
uv run gradio app.py --watch-dirs src/local_lingo
```

Then open the URL shown in the terminal (usually [http://127.0.0.1:7860](http://127.0.0.1:7860)).

If you installed with pip instead, activate the venv and run `local-lingo` (or `python -m local_lingo`).

### CLI (optional)

Same business logic, terminal UI:

```bash
uv run local-lingo-cli
```

## 4. How to use the app

1. Choose the two **Languages** (type to filter; full names like “English”).
2. Choose the **Model** (installed Ollama models; e.g. `gemma3:4b` vs `gemma3:12b`).
3. Paste your text (either language of the pair).
4. Click **Correct & Translate**.
5. Read:
   - Detected language  
   - Corrected (native rewrite)  
   - Target language  
   - Translation  
6. Use the **copy** buttons on the corrected and translation fields to copy results.

### Language selection

- Pick from the searchable dropdowns (full language names)
- The pair is **bidirectional**: the model detects which side the text is in, corrects it, then translates to the other
- Both languages must be different
- Defaults come from `DEFAULT_LANGUAGE_PAIR` in `src/local_lingo/config.py` (e.g. `en-hu` → English / Hungarian)

### Model selection

- The dropdown is filled from Ollama (`GET /api/tags`) when you open the app
- Embedding models are omitted
- `MODEL` in `config.py` is selected by default if that model is installed; otherwise the first installed model is used

## 5. Configuration

Edit `src/local_lingo/config.py`:

| Setting | Default | Meaning |
|---------|---------|---------|
| `MODEL` | `"gemma3:12b"` | Default Ollama model in the UI dropdown, if installed |
| `DEFAULT_LANGUAGE_PAIR` | `"en-hu"` | Default pair shown in the UI |
| `OLLAMA_BASE_URL` | `"http://localhost:11434/v1"` | Ollama OpenAI-compatible API |
| `OLLAMA_API_KEY` | `"ollama"` | Dummy key (required by the OpenAI client; Ollama ignores it) |
| `REQUEST_TIMEOUT_SECONDS` | `180.0` | Max wait for a model response |
| `NUM_CTX` | `8192` | Ollama context window; smaller is faster for typical snippets |
| `KEEP_ALIVE` | `"30m"` | How long to keep the model loaded in VRAM between requests |
| `TEMPERATURE` | `0.0` | Lower = more deterministic output |

Example: prefer a smaller model in the dropdown:

```python
MODEL = "gemma3:4b"
DEFAULT_LANGUAGE_PAIR = "en-de"
```

Then restart the app (or let `gradio` reload if you are in watch mode).

Prompts live in `src/local_lingo/prompts.py`. Parsing and Ollama calls live in `src/local_lingo/service.py`. Validation lives in `src/local_lingo/validation.py`. UI lives in `src/local_lingo/ui.py`.

## 6. Project layout

```text
.
  README.md
  pyproject.toml
  app.py                     # Gradio watch-friendly entry
  src/local_lingo/           # Installable package (`import local_lingo`)
    config.py                # Model and Ollama settings
    prompts.py               # System / user prompts
    validation.py            # Input validation
    service.py               # Business logic (Ollama + parsing)
    ui.py                    # Gradio UI
    app.py                   # Web entry (`uv run local-lingo`)
    cli.py                   # Terminal UI (`uv run local-lingo-cli`)
    languages.py             # Language catalog
    assets/                  # Brand icons and favicons
  tests/
```

## 7. Tests

```bash
uv run python -m unittest discover -s tests -v
```

These cover validation, language catalog, response parsing, mocked Ollama calls, and UI build.

## 8. Troubleshooting

| Problem | What to try |
|---------|-------------|
| `command not found: python` | Prefer `uv run …`. With pip: use `python3` to create the venv, then `source .venv/bin/activate` |
| App cannot reach the model | Ensure Ollama is running (`curl http://localhost:11434`) |
| `model not found` | `ollama pull` the name shown in the Model dropdown |
| Model dropdown is empty / only the default | Ensure Ollama is running, then reload the page. Pull a model with `ollama pull gemma3:12b` |
| First request is very slow | Normal cold start; the model is loading into RAM. Later requests stay warm for `KEEP_ALIVE` |
| Later requests still slow | Mostly the model itself (`gemma3:12b`). Try `gemma3:4b`, or lower `NUM_CTX` |
| Out of memory / Mac feels slow | Use a smaller model (`gemma3:4b`) or `ollama stop` unused models |
| Invalid languages | Choose two different languages from the dropdowns |
| Empty text error | Enter text before clicking the button |
| Port 7860 in use | Stop the other Gradio process, or change port in `demo.launch(server_port=...)` |

## 9. Privacy

All rewriting and translation run locally through Ollama. Nothing is sent to OpenAI or other cloud LLM APIs unless you change the client configuration yourself.
