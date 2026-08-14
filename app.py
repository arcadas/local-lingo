"""Gradio reload entry: `uv run gradio app.py --watch-dirs src/local_lingo`."""

from local_lingo.app import demo, main

__all__ = ["demo", "main"]

if __name__ == "__main__":
    main()
