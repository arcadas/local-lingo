"""
Web UI entrypoint.

Normal start:
  python -m translator_web

Dev mode (auto-reload on code changes):
  gradio run_translator_web.py --watch-dirs translator_web
"""

from translator_web import config
from translator_web.ui import build_ui

# Gradio's CLI looks for a top-level `demo` variable.
demo = build_ui()


def main() -> None:
    favicon = config.FAVICON_ICO if config.FAVICON_ICO.exists() else config.FAVICON_PNG
    demo.launch(favicon_path=str(favicon))


if __name__ == "__main__":
    main()
