from .ui import build_ui
from . import config


def main() -> None:
    demo = build_ui()
    demo.launch(favicon_path=str(config.FAVICON_ICO if config.FAVICON_ICO.exists() else config.FAVICON_PNG))


if __name__ == "__main__":
    main()
