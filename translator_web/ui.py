import base64
import gradio as gr

from . import config
from .languages import LANGUAGE_CHOICES, codes_from_default_pair
from .service import translate_and_correct
from .validation import ValidationError, validate_inputs_from_languages


LIGHT_CSS = """
html, body, .gradio-container, .dark, .dark .gradio-container {
  background: #ffffff !important;
  color: #111827 !important;
  color-scheme: light !important;
  font-family: "DM Sans", "Segoe UI", sans-serif !important;
  --body-background-fill: #ffffff !important;
  --background-fill-primary: #ffffff !important;
  --block-background-fill: #ffffff !important;
  --input-background-fill: #ffffff !important;
  --block-label-background-fill: transparent !important;
  --block-label-border-width: 0px !important;
  --block-title-background-fill: transparent !important;
  --block-title-border-width: 0px !important;
  --block-label-text-color: #4b5563 !important;
}

.gradio-container {
  max-width: min(1400px, 94vw) !important;
  width: 94vw !important;
  margin: 0 auto !important;
  padding: 1.25rem 1rem 2rem !important;
}

.main-title h1 {
  color: #111827 !important;
  font-weight: 700 !important;
  letter-spacing: -0.03em !important;
  margin-bottom: 0.35rem !important;
}

.brand-row {
  display: flex !important;
  align-items: center !important;
  gap: 0.9rem !important;
  margin-bottom: 0.9rem !important;
}

.brand-row img,
.brand-icon {
  width: 56px !important;
  height: 56px !important;
  border-radius: 14px !important;
  flex-shrink: 0 !important;
}

.brand-text h1 {
  margin: 0 !important;
}

.main-title p,
.main-title code {
  color: #4b5563 !important;
  font-size: 0.98rem !important;
  line-height: 1.45 !important;
  max-width: 52rem !important;
  margin: 0 0 0.85rem 0 !important;
}

.main-title code {
  background: #f3f4f6 !important;
  border: 1px solid #e5e7eb !important;
  color: #4b5563 !important;
}

.layout-row {
  display: grid !important;
  grid-template-columns: 1fr 1fr !important;
  gap: 1.15rem !important;
  align-items: stretch !important;
}

.layout-row > div {
  max-width: none !important;
  min-width: 0 !important;
  height: 100% !important;
  align-self: stretch !important;
  display: flex !important;
  flex-direction: column !important;
}

.card,
#left-card,
#right-card {
  background: #ffffff !important;
  border: 1px solid #e5e7eb !important;
  border-radius: 16px !important;
  box-shadow: 0 8px 24px rgba(17, 24, 39, 0.06) !important;
  padding: 1rem !important;
  height: 100% !important;
  box-sizing: border-box !important;
  display: flex !important;
  flex-direction: column !important;
  flex: 1 1 auto !important;
}

/* Tighten space under Languages heading (Gradio wraps HTML in a block). */
#left-card > div:first-child,
#left-card .html-container,
#left-card .prose {
  margin: 0 !important;
  padding: 0 !important;
  min-height: 0 !important;
}

#left-card {
  gap: 0.45rem !important;
}

#right-card {
  justify-content: center !important;
  gap: 0.45rem !important;
}

#right-card .html-container,
#right-card > .grow,
#right-card > div:has(.result-placeholder),
#right-card > div:has(.loading-box) {
  flex: 1 1 auto !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 100% !important;
}

label span,
.block .label-wrap span,
[class*="block-label"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #4b5563 !important;
  font-weight: 600 !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
}

input, textarea {
  background: #ffffff !important;
  color: #111827 !important;
  border: 1px solid #d1d5db !important;
  border-radius: 10px !important;
}

textarea {
  overflow-y: auto !important;
  resize: vertical !important;
}

input::placeholder, textarea::placeholder {
  color: #9ca3af !important;
  opacity: 1 !important;
}

button.primary {
  min-height: 46px !important;
  border-radius: 10px !important;
  font-weight: 650 !important;
  background: #2563eb !important;
  color: #ffffff !important;
  border: none !important;
}

button.primary:hover {
  background: #1d4ed8 !important;
  color: #ffffff !important;
}

.result-placeholder {
  color: #6b7280 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  min-height: 200px !important;
  height: 100% !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center !important;
  line-height: 1.5 !important;
  padding: 1rem !important;
}

.loading-box {
  min-height: 200px !important;
  height: 100% !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 0.9rem !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #374151 !important;
}

.spinner {
  width: 36px !important;
  height: 36px !important;
  border: 3px solid #dbeafe !important;
  border-top-color: #2563eb !important;
  border-radius: 50% !important;
  animation: spin 0.8s linear infinite !important;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  color: #111827 !important;
  font-size: 0.95rem !important;
  font-weight: 600 !important;
}

.form-message {
  min-height: 1.25rem;
  margin-top: 0.5rem !important;
  position: relative !important;
  z-index: 2 !important;
}

.form-message .msg-error {
  color: #7f1d1d !important;
  background: #fee2e2 !important;
  border: 1px solid #fca5a5 !important;
  border-radius: 10px !important;
  padding: 0.65rem 0.85rem !important;
  font-size: 0.95rem !important;
  font-weight: 600 !important;
  line-height: 1.4 !important;
}

.lang-row {
  display: grid !important;
  grid-template-columns: 1fr auto 1fr !important;
  gap: 0.75rem !important;
  align-items: center !important;
  margin: 0 0 0.55rem 0 !important;
}

.lang-section-label {
  margin: 0 0 0.15rem 0 !important;
  padding: 0 !important;
  color: #4b5563 !important;
  font-size: 0.95rem !important;
  font-weight: 600 !important;
}

.lang-section-hint {
  margin: 0 0 0.25rem 0 !important;
  padding: 0 !important;
  color: #6b7280 !important;
  font-size: 0.88rem !important;
  line-height: 1.35 !important;
}

.lang-arrow {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  color: #9ca3af !important;
  font-size: 1.25rem !important;
  line-height: 1 !important;
  user-select: none !important;
  padding: 0 0.15rem !important;
}

/* Single clean select — strip all Gradio wrapper borders */
.lang-row .block,
.lang-row .form,
.lang-row > div,
.lang-row .container,
.lang-row .wrap,
.lang-row .secondary-wrap,
.lang-row [class*="secondary-wrap"],
.lang-row [class*="wrap"],
.lang-select,
.lang-row .lang-select {
  background: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

.lang-row input {
  background: #ffffff !important;
  border: 1px solid #d1d5db !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  outline: none !important;
  min-height: 42px !important;
  color: #111827 !important;
  padding: 0.55rem 0.75rem !important;
}

.lang-row input:focus {
  border: 1px solid #9ca3af !important;
  box-shadow: none !important;
  outline: none !important;
}

/* Prevent focus ring on parent wrappers */
.lang-row *:focus,
.lang-row *:focus-within {
  outline: none !important;
}

.lang-row input:focus {
  border: 1px solid #9ca3af !important;
}

/* Light dropdown / autocomplete menu (no black background) */
ul[role="listbox"],
div[role="listbox"],
[role="listbox"],
.options,
.dropdown-options,
ul.options,
.wrap[role="listbox"],
.svelte-select-list,
[class*="options"] {
  background: #ffffff !important;
  background-color: #ffffff !important;
  color: #111827 !important;
  border: 1px solid #e5e7eb !important;
  border-radius: 10px !important;
  box-shadow: 0 10px 30px rgba(17, 24, 39, 0.12) !important;
}

li[role="option"],
[role="option"],
ul[role="listbox"] li,
.options li,
[class*="options"] li {
  background: #ffffff !important;
  background-color: #ffffff !important;
  color: #111827 !important;
}

li[role="option"]:hover,
[role="option"]:hover,
li[role="option"][aria-selected="true"],
[role="option"][aria-selected="true"],
.options li:hover,
[class*="options"] li:hover {
  background: #eff6ff !important;
  background-color: #eff6ff !important;
  color: #1d4ed8 !important;
}

/* Keep helper info readable */
span[data-testid="block-info"],
.dark span[data-testid="block-info"] {
  color: #374151 !important;
  font-size: 0.9rem !important;
}

/* Hide Gradio's default progress overlay/text that overlaps messages */
.progress-text,
.meta-text,
.eta-bar,
.wrap > .progress-level,
.pending,
[class*="progress-text"],
[class*="meta-text"] {
  display: none !important;
}

/* Copyable result fields */
.copyable-field {
  position: relative !important;
}

.copyable-field textarea {
  padding-top: 0.65rem !important;
  padding-right: 2.5rem !important;
  padding-bottom: 0.65rem !important;
}

.modern-copy-btn {
  position: absolute !important;
  top: 0 !important;
  right: 0 !important;
  z-index: 6 !important;
  width: 28px !important;
  min-width: 28px !important;
  max-width: 28px !important;
  height: 28px !important;
  min-height: 28px !important;
  padding: 0 !important;
  margin: 0 !important;
  border-radius: 6px !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  background-color: transparent !important;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='15' height='15' fill='none' stroke='%236b7280' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='5.5' y='5.5' width='8' height='8' rx='1.5'/%3E%3Cpath d='M3.5 10.5V3.8A1.3 1.3 0 0 1 4.8 2.5h6.7'/%3E%3C/svg%3E") !important;
  background-repeat: no-repeat !important;
  background-position: center !important;
  background-size: 15px 15px !important;
  color: transparent !important;
  font-size: 0 !important;
  line-height: 0 !important;
  overflow: hidden !important;
}

.modern-copy-btn:hover,
.modern-copy-btn:focus,
.modern-copy-btn:active {
  background-color: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='15' height='15' fill='none' stroke='%232563eb' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='5.5' y='5.5' width='8' height='8' rx='1.5'/%3E%3Cpath d='M3.5 10.5V3.8A1.3 1.3 0 0 1 4.8 2.5h6.7'/%3E%3C/svg%3E") !important;
  background-repeat: no-repeat !important;
  background-position: center !important;
  background-size: 15px 15px !important;
  color: transparent !important;
}

.modern-copy-btn.copied {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='15' height='15' fill='none' stroke='%2316a34a' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3.5 8.2 6.2 10.8 11.5 4.5'/%3E%3C/svg%3E") !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

footer {
  display: none !important;
}
"""

FORCE_LIGHT_HEAD = """
<meta name="color-scheme" content="light only">
<style>
  ul[role="listbox"],
  div[role="listbox"],
  [role="listbox"] {
    background: #ffffff !important;
    color: #111827 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 10px !important;
    box-shadow: 0 10px 30px rgba(17, 24, 39, 0.12) !important;
  }
  li[role="option"],
  [role="option"] {
    background: #ffffff !important;
    color: #111827 !important;
  }
  li[role="option"]:hover,
  [role="option"]:hover,
  li[role="option"][aria-selected="true"],
  [role="option"][aria-selected="true"] {
    background: #eff6ff !important;
    color: #1d4ed8 !important;
  }
</style>
<script>
document.documentElement.classList.remove("dark");
document.documentElement.style.colorScheme = "light";
const darkObserver = new MutationObserver(() => {
  document.documentElement.classList.remove("dark");
});
darkObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

function positionCopyButtons() {
  document.querySelectorAll(".copyable-field").forEach((field) => {
    const textarea = field.querySelector("textarea");
    const btn = field.querySelector("button.modern-copy-btn");
    if (!textarea || !btn) return;
    const fieldRect = field.getBoundingClientRect();
    const taRect = textarea.getBoundingClientRect();
    // 12px inset from the textarea's top/right edges (inside the box)
    const top = taRect.top - fieldRect.top + 12;
    const right = fieldRect.right - taRect.right + 10;
    btn.style.setProperty("top", `${top}px`, "important");
    btn.style.setProperty("right", `${right}px`, "important");
  });
}

const layoutObserver = new MutationObserver(() => positionCopyButtons());
window.addEventListener("load", () => {
  positionCopyButtons();
  layoutObserver.observe(document.body, { childList: true, subtree: true, attributes: true });
  window.addEventListener("resize", positionCopyButtons);
});
setInterval(positionCopyButtons, 500);
</script>
"""


def _page_head() -> str:
    favicon_tags = ""
    if config.FAVICON_PNG.exists():
        b64 = base64.b64encode(config.FAVICON_PNG.read_bytes()).decode("ascii")
        favicon_tags += (
            f'<link rel="icon" type="image/png" sizes="32x32" '
            f'href="data:image/png;base64,{b64}">\n'
        )
    if config.FAVICON_ICO.exists():
        b64_ico = base64.b64encode(config.FAVICON_ICO.read_bytes()).decode("ascii")
        favicon_tags += (
            f'<link rel="shortcut icon" type="image/x-icon" '
            f'href="data:image/x-icon;base64,{b64_ico}">\n'
        )
    return favicon_tags + FORCE_LIGHT_HEAD


def _brand_header_html() -> str:
    icon_path = config.ICON_HEADER if config.ICON_HEADER.exists() else config.ICON_ORIGINAL
    if icon_path.exists():
        b64 = base64.b64encode(icon_path.read_bytes()).decode("ascii")
        img = (
            f'<img class="brand-icon" src="data:image/png;base64,{b64}" '
            f'alt="{config.APP_NAME} icon" />'
        )
    else:
        img = ""
    return f"""
    <div class="brand-row">
      {img}
      <div class="brand-text">
        <h1>{config.APP_NAME}</h1>
      </div>
    </div>
    <p>Detects which language you pasted, rewrites it to sound natural, then translates it to the other language in your pair — privately on your machine via Ollama (<code>{config.MODEL}</code>).</p>
    """


PLACEHOLDER_HTML = """
<div class="result-placeholder">
  Your corrected text and translation will appear here.
</div>
"""

LOADING_HTML = """
<div class="loading-box">
  <div class="spinner"></div>
  <div class="loading-text">Working on your text…</div>
</div>
"""


COPY_JS = """
(text) => {
  const value = text || "";
  if (value) {
    navigator.clipboard.writeText(value);
  }
  const active = document.activeElement;
  if (active && active.classList.contains("modern-copy-btn")) {
    active.classList.add("copied");
    setTimeout(() => active.classList.remove("copied"), 1200);
  }
  return [];
}
"""


def _message_html(text: str = "") -> str:
    if not text:
        return '<div class="form-message"></div>'
    return f'<div class="form-message"><div class="msg-error">{text}</div></div>'


def _empty_results():
    return (
        gr.update(visible=True, value=PLACEHOLDER_HTML),
        gr.update(visible=False),
        "",
        "",
        "",
        "",
    )


def _run(text: str, lang_a: str, lang_b: str):
    try:
        cleaned, pair = validate_inputs_from_languages(text, lang_a, lang_b)
    except ValidationError as exc:
        yield (*_empty_results(), _message_html(str(exc)))
        return

    # Show modern loader while the model runs
    yield (
        gr.update(visible=True, value=LOADING_HTML),
        gr.update(visible=False),
        "",
        "",
        "",
        "",
        _message_html(""),
    )

    result = translate_and_correct(cleaned, pair)
    if result.note and (not result.corrected or result.corrected == "?"):
        yield (*_empty_results(), _message_html(result.note))
        return

    yield (
        gr.update(visible=False),
        gr.update(visible=True),
        result.detected,
        result.corrected,
        result.target,
        result.translation,
        _message_html(""),
    )


def build_ui() -> gr.Blocks:
    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="slate",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("DM Sans"),
    ).set(
        body_background_fill="#ffffff",
        body_background_fill_dark="#ffffff",
        body_text_color="#111827",
        body_text_color_dark="#111827",
        block_background_fill="#ffffff",
        block_background_fill_dark="#ffffff",
        block_label_text_color="#4b5563",
        block_label_text_color_dark="#4b5563",
        block_label_background_fill="transparent",
        block_label_background_fill_dark="transparent",
        block_label_border_width="0px",
        block_label_border_width_dark="0px",
        block_title_background_fill="transparent",
        block_title_background_fill_dark="transparent",
        block_title_border_width="0px",
        block_title_border_width_dark="0px",
        input_background_fill="#ffffff",
        input_background_fill_dark="#ffffff",
        button_primary_background_fill="#2563eb",
        button_primary_background_fill_dark="#2563eb",
        button_primary_background_fill_hover="#1d4ed8",
        button_primary_background_fill_hover_dark="#1d4ed8",
        button_primary_text_color="#ffffff",
        button_primary_text_color_dark="#ffffff",
    )

    with gr.Blocks(
        title=config.APP_NAME,
        theme=theme,
        css=LIGHT_CSS,
        head=_page_head(),
        fill_width=True,
    ) as demo:
        with gr.Column(elem_classes=["main-title"]):
            gr.HTML(_brand_header_html())

        with gr.Row(elem_classes=["layout-row"]):
            with gr.Column(scale=1, min_width=320, elem_id="left-card", elem_classes=["card"]):
                default_a, default_b = codes_from_default_pair(config.DEFAULT_LANGUAGE_PAIR)
                gr.HTML(
                    """
                    <p class="lang-section-label">Languages</p>
                    <p class="lang-section-hint">Bidirectional pair — paste text in either language. No direction to choose.</p>
                    """
                )
                with gr.Row(elem_classes=["lang-row"]):
                    lang_a = gr.Dropdown(
                        choices=LANGUAGE_CHOICES,
                        value=default_a,
                        show_label=False,
                        filterable=True,
                        allow_custom_value=False,
                        container=False,
                        elem_classes=["lang-select"],
                    )
                    gr.HTML('<div class="lang-arrow" aria-hidden="true">⇄</div>')
                    lang_b = gr.Dropdown(
                        choices=LANGUAGE_CHOICES,
                        value=default_b,
                        show_label=False,
                        filterable=True,
                        allow_custom_value=False,
                        container=False,
                        elem_classes=["lang-select"],
                    )
                text = gr.Textbox(
                    lines=8,
                    max_lines=8,
                    label="Your text",
                    placeholder="Paste text in either language of the pair…",
                    autoscroll=True,
                )
                btn = gr.Button("Correct & Translate", variant="primary")
                form_message = gr.HTML(value=_message_html())

            with gr.Column(scale=1, min_width=320, elem_id="right-card", elem_classes=["card"]):
                placeholder = gr.HTML(value=PLACEHOLDER_HTML, visible=True)
                with gr.Column(visible=False) as results:
                    detected = gr.Textbox(label="Detected language", interactive=False)

                    with gr.Column(elem_classes=["copyable-field"]):
                        corrected = gr.Textbox(
                            lines=5,
                            max_lines=5,
                            label="Corrected (native rewrite)",
                            interactive=False,
                            show_copy_button=False,
                            autoscroll=True,
                        )
                        copy_corrected = gr.Button(
                            "Copy",
                            elem_classes=["modern-copy-btn"],
                            size="sm",
                        )

                    target = gr.Textbox(label="Target language", interactive=False)

                    with gr.Column(elem_classes=["copyable-field"]):
                        translation = gr.Textbox(
                            lines=5,
                            max_lines=5,
                            label="Translation",
                            interactive=False,
                            show_copy_button=False,
                            autoscroll=True,
                        )
                        copy_translation = gr.Button(
                            "Copy",
                            elem_classes=["modern-copy-btn"],
                            size="sm",
                        )

        copy_corrected.click(
            fn=None,
            inputs=[corrected],
            js=COPY_JS,
            show_progress="hidden",
        )
        copy_translation.click(
            fn=None,
            inputs=[translation],
            js=COPY_JS,
            show_progress="hidden",
        )

        btn.click(
            fn=_run,
            inputs=[text, lang_a, lang_b],
            outputs=[
                placeholder,
                results,
                detected,
                corrected,
                target,
                translation,
                form_message,
            ],
            show_progress="hidden",
        )

    return demo
