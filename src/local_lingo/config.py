from pathlib import Path

APP_NAME = "LocalLingo"
MODEL = "gemma3:4b"
DEFAULT_LANGUAGE_PAIR = "en-hu"
OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY = "ollama"
REQUEST_TIMEOUT_SECONDS = 180.0
TEMPERATURE = 0.0
# Gemma 3 defaults to a huge context window; a smaller one is much faster for typical snippets.
NUM_CTX = 8192
# Keep the model in VRAM between requests so later runs skip the cold load.
KEEP_ALIVE = "30m"

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ICON_ORIGINAL = ASSETS_DIR / "icon-original.png"
ICON_TRANSPARENT = ASSETS_DIR / "icon-transparent.png"
ICON_HEADER = ASSETS_DIR / "icon-header.png"
ICON_MONO = ASSETS_DIR / "icon-mono.png"
FAVICON_ICO = ASSETS_DIR / "favicon.ico"
FAVICON_PNG = ASSETS_DIR / "favicon-32.png"
ICON_README = ASSETS_DIR / "icon-readme.png"
ICON_FAVICON_FULL = ASSETS_DIR / "icon-favicon-full.png"
