"""Gradio reload entry: `uv run gradio app.py --watch-dirs src/local_lingo`."""

from local_lingo import config
from local_lingo.service import print_model_startup_status
from local_lingo.ui import build_ui

# Gradio's CLI greps this file for `demo = gr.Blocks` (or `with gr.Blocks() as demo`).
demo = build_ui()  # demo = gr.Blocks

# Do not use `if __name__ == "__main__"`: Gradio's reloader reads ast.Constant.s,
# which does not exist on Python 3.14, and the watch thread crashes.
_run_as_script = __name__ == "__main__"
if _run_as_script:
    print_model_startup_status()
    demo.launch(
        favicon_path=str(
            config.FAVICON_ICO if config.FAVICON_ICO.exists() else config.FAVICON_PNG
        )
    )
