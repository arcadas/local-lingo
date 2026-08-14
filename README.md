# LocalLingo

![LocalLingo icon](./translator_web/assets/icon-readme.png)

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
- Python 3.11+

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

```bash
git clone git@github.com:arcadas/local-lingo.git
cd local-lingo
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv sync
source .venv/bin/activate
```

## 3. Start the web app

```bash
python -m translator_web
```

Or with auto-reload while developing:

```bash
gradio run_translator_web.py --watch-dirs translator_web
```

Then open the URL shown in the terminal (usually [http://127.0.0.1:7860](http://127.0.0.1:7860)).

### CLI (optional)

Same business logic, terminal UI:

```bash
python translator.py
```

## 4. How to use the app

1. Choose the two **Languages** (type to filter; full names like “English”).
2. Paste your text (either language of the pair).
3. Click **Correct & Translate**.
4. Read:
   - Detected language  
   - Corrected (native rewrite)  
   - Target language  
   - Translation  
5. Use the **copy** buttons on the corrected and translation fields to copy results.

### Language selection

- Pick from the searchable dropdowns (full language names)
- The pair is **bidirectional**: the model detects which side the text is in, corrects it, then translates to the other
- Both languages must be different
- Defaults come from `DEFAULT_LANGUAGE_PAIR` in `translator_web/config.py` (e.g. `en-hu` → English / Hungarian)

## 5. Configuration

Edit `translator_web/config.py`:

| Setting | Default | Meaning |
|---------|---------|---------|
| `MODEL` | `"gemma3:12b"` | Ollama model name (`ollama pull` this first) |
| `DEFAULT_LANGUAGE_PAIR` | `"en-hu"` | Default pair shown in the UI |
| `OLLAMA_BASE_URL` | `"http://localhost:11434/v1"` | Ollama OpenAI-compatible API |
| `OLLAMA_API_KEY` | `"ollama"` | Dummy key (required by the OpenAI client; Ollama ignores it) |
| `REQUEST_TIMEOUT_SECONDS` | `180.0` | Max wait for a model response |
| `TEMPERATURE` | `0.0` | Lower = more deterministic output |

Example: switch to a smaller model:

```python
MODEL = "gemma3:4b"
DEFAULT_LANGUAGE_PAIR = "en-de"
```

Then restart the app (or let `gradio` reload if you are in watch mode).

Prompts live in `translator_web/prompts.py`. Parsing and Ollama calls live in `translator_web/service.py`. Validation lives in `translator_web/validation.py`. UI lives in `translator_web/ui.py`.

## 6. Project layout

```text
.
  README.md
  pyproject.toml
  translator.py              # CLI entry
  run_translator_web.py      # Gradio watch-friendly entry
  translator_web/
    config.py                # Model and Ollama settings
    prompts.py               # System / user prompts
    validation.py            # Input validation
    service.py               # Business logic (Ollama + parsing)
    ui.py                    # Gradio UI
    app.py                   # python -m translator_web
    languages.py             # Language catalog
    assets/                  # Brand icons and favicons
    tests/
```

## 7. Tests

```bash
python -m unittest translator_web.tests.test_locallingo -v
```

These cover validation, language catalog, response parsing, mocked Ollama calls, and UI build.

## 8. Troubleshooting

| Problem | What to try |
|---------|-------------|
| App cannot reach the model | Ensure Ollama is running (`curl http://localhost:11434`) |
| `model not found` | `ollama pull <MODEL>` matching `config.MODEL` |
| First request is very slow | Normal cold start; model is loading into RAM |
| Out of memory / Mac feels slow | Use a smaller model (`gemma3:4b`) or `ollama stop` unused models |
| Invalid languages | Choose two different languages from the dropdowns |
| Empty text error | Enter text before clicking the button |
| Port 7860 in use | Stop the other Gradio process, or change port in `demo.launch(server_port=...)` |

## 9. Privacy

All rewriting and translation run locally through Ollama. Nothing is sent to OpenAI or other cloud LLM APIs unless you change the client configuration yourself.
