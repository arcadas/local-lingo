from .ui import build_ui
from . import config
from .service import print_model_startup_status

# Gradio's CLI looks for a top-level `demo` (re-exported from the repo-root app.py).
demo = build_ui()


def main() -> None:
    print_model_startup_status()
    favicon = config.FAVICON_ICO if config.FAVICON_ICO.exists() else config.FAVICON_PNG
    demo.launch(favicon_path=str(favicon))


if __name__ == "__main__":
    main()
