import base64
import html
import json
import time
from datetime import datetime

import gradio as gr

from . import config
from .highlight import highlight_corrections
from .languages import CODE_TO_NAME, LANGUAGE_CHOICES, LANGUAGES, codes_from_default_pair
from .prompts import (
    DEFAULT_SYSTEM_GUIDELINES,
    DEFAULT_USER_EXTRA,
    LOCKED_OUTPUT_FORMAT,
    LOCKED_USER_SUFFIX,
    sanitize_prompt_addon,
)
from .service import RunMetrics, get_model_catalog, translate_and_correct
from .validation import ValidationError, validate_inputs_from_languages


LIGHT_CSS = """
html, body, .gradio-container, .dark, .dark .gradio-container {
  background: #ffffff !important;
  color: #111827 !important;
  color-scheme: light !important;
  font-family: Inter, ui-sans-serif, system-ui, sans-serif !important;
  -webkit-font-smoothing: antialiased;
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

button, input, textarea, select, label, .prose, .block, .form {
  font-family: Inter, ui-sans-serif, system-ui, sans-serif !important;
  -webkit-font-smoothing: antialiased;
}

.gradio-container {
  max-width: min(1400px, 94vw) !important;
  width: 94vw !important;
  margin: 0 auto !important;
  padding: 0.45rem 1rem 2rem !important;
}

.main-title h1 {
  color: #111827 !important;
  font-weight: 700 !important;
  letter-spacing: -0.03em !important;
  margin-bottom: 0.35rem !important;
}

.main-title {
  gap: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
}

.main-title .html-container,
.main-title .prose {
  margin: 0 !important;
  padding: 0 !important;
}

.brand-row {
  display: flex !important;
  align-items: center !important;
  gap: 0.9rem !important;
  margin-bottom: 0.75rem !important;
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
  max-width: none !important;
  margin: 0 0 0.12rem 0 !important;
}

.main-title code {
  background: #f3f4f6 !important;
  border: 1px solid #e5e7eb !important;
  color: #4b5563 !important;
}

#app-nav {
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 0.15rem 0.35rem !important;
  align-items: flex-end !important;
  border-bottom: 1px solid #e5e7eb !important;
  margin: 0 0 0.7rem 0 !important;
  padding: 0 !important;
  background: transparent !important;
}

#app-nav > div,
#app-nav .form,
#app-nav .block {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  width: auto !important;
  flex: 0 0 auto !important;
}

#app-nav button {
  background: transparent !important;
  background-color: transparent !important;
  color: #6b7280 !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  min-height: 40px !important;
  height: 40px !important;
  padding: 0.35rem 0.85rem !important;
  margin: 0 !important;
  font-weight: 600 !important;
  font-size: 0.95rem !important;
}

#app-nav button.primary {
  background: transparent !important;
  background-color: transparent !important;
  color: #2563eb !important;
  border-bottom: 2px solid #2563eb !important;
  box-shadow: none !important;
}

#page-prompts,
#page-benchmark {
  width: 100% !important;
}

#page-benchmark,
#page-benchmark > .column,
#page-benchmark > .form,
#page-benchmark > .gap,
#page-benchmark .card,
#page-benchmark .card > .column,
#page-benchmark .card > .form,
#page-benchmark .card > .gap {
  display: flex !important;
  flex-direction: column !important;
  flex-wrap: nowrap !important;
  grid-template-columns: 1fr !important;
}

#page-benchmark .card > *,
#page-benchmark .form > *,
#page-benchmark .gap > * {
  width: 100% !important;
  max-width: 100% !important;
  grid-column: 1 / -1 !important;
}

#bench-blob,
#bench-blob textarea {
  display: none !important;
  height: 0 !important;
  overflow: hidden !important;
}

.prompt-locked {
  background: #f9fafb !important;
  border: 1px solid #e5e7eb !important;
  border-radius: 10px !important;
  padding: 0.85rem 1rem !important;
  color: #4b5563 !important;
  font-size: 0.875rem !important;
  line-height: 1.5 !important;
  white-space: pre-wrap !important;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace !important;
}

#page-prompts .prompt-readonly textarea,
#page-prompts .prompt-readonly input {
  background: #f9fafb !important;
  color: #4b5563 !important;
  cursor: default !important;
}

.benchmark-empty {
  color: #6b7280 !important;
  text-align: center !important;
  padding: 2.4rem 1rem !important;
  background: #f9fafb !important;
  border: 1px dashed #e5e7eb !important;
  border-radius: 12px !important;
  font-size: 0.95rem !important;
}

.bench {
  display: flex !important;
  flex-direction: column !important;
  gap: 0.7rem !important;
}

.bench-stats {
  display: grid !important;
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  gap: 0.55rem !important;
}

.bench-stat {
  border: 1px solid #e5e7eb !important;
  border-radius: 10px !important;
  overflow: hidden !important;
  background: #ffffff !important;
  padding: 0 !important;
}

.bench-stat-wide {
  grid-column: 1 / -1 !important;
}

.bench-stat-head {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 0.6rem !important;
  background: #eff6ff !important;
  color: #1d4ed8 !important;
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  padding: 0.42rem 0.8rem !important;
}

.bench-stat-wide .bench-stat-head {
  background: #ecfdf5 !important;
  color: #166534 !important;
}

.bench-stat-info .bench-stat-head,
.bench-stat-wide.bench-stat-info .bench-stat-head {
  background: #f3f4f6 !important;
  color: #4b5563 !important;
}

.bench-info-grid {
  display: grid !important;
  grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
  gap: 0.55rem 1rem !important;
}

.bench-info-item {
  display: flex !important;
  flex-direction: column !important;
  gap: 0.12rem !important;
  min-width: 0 !important;
}

.bench-info-label {
  color: #6b7280 !important;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
}

.bench-info-value {
  color: #111827 !important;
  font-size: 0.95rem !important;
  font-weight: 700 !important;
  font-variant-numeric: tabular-nums !important;
  letter-spacing: -0.02em !important;
}

.bench-stat-body {
  padding: 0.7rem 0.8rem 0.75rem !important;
}

.bench-stat-value {
  font-size: 1.15rem !important;
  font-weight: 700 !important;
  letter-spacing: -0.03em !important;
  color: #111827 !important;
  line-height: 1.2 !important;
  text-align: left !important;
  font-variant-numeric: tabular-nums !important;
}

.bench-unit {
  font-weight: 400 !important;
  font-size: 0.8rem !important;
  color: #6b7280 !important;
  letter-spacing: 0 !important;
}

.bench-stat-help {
  margin: 0.35rem 0 0 0 !important;
  color: #6b7280 !important;
  font-size: 0.75rem !important;
  font-weight: 400 !important;
  line-height: 1.4 !important;
}

.bench-model {
  background: #ffffff !important;
  color: #1d4ed8 !important;
  border: 1px solid #93c5fd !important;
  font-size: 0.75rem !important;
  font-weight: 600 !important;
  padding: 0.12rem 0.55rem !important;
  border-radius: 999px !important;
  line-height: 1.3 !important;
  flex-shrink: 0 !important;
}

.bench-meta {
  color: #4b5563 !important;
  font-size: 0.82rem !important;
  line-height: 1.45 !important;
  margin: 0.1rem 0 0.15rem 0 !important;
}

.bench-history {
  border: 1px solid #e5e7eb !important;
  border-radius: 10px !important;
  overflow: hidden !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

.bench-history-head {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 0.6rem !important;
  background: #eff6ff !important;
  color: #1d4ed8 !important;
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  padding: 0.42rem 0.8rem !important;
}

.bench-history-title {
  margin: 0 !important;
  color: inherit !important;
  font-weight: inherit !important;
  font-size: inherit !important;
}

.bench-history-hint {
  margin: 0 !important;
  color: #3b82f6 !important;
  font-size: 0.75rem !important;
  font-weight: 500 !important;
}

.bench-grid {
  display: grid !important;
  grid-template-columns: 1.2fr 14% minmax(0, 1.2fr) 0.65fr 0.85fr 0.95fr 0.8fr 0.6fr !important;
  width: 100% !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  font-size: 0.8rem !important;
}

.bench-h,
.bench-c {
  padding: 0.48rem 0.65rem !important;
  border: none !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
  min-width: 0 !important;
}

.bench-h {
  color: #6b7280 !important;
  font-weight: 600 !important;
  font-size: 0.7rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
  padding: 0.4rem 0.65rem !important;
  background: #f3f4f6 !important;
  text-align: left !important;
}

.bench-c {
  color: #111827 !important;
  background: #ffffff !important;
}

.bench-h.num,
.bench-c.num {
  text-align: right !important;
  font-variant-numeric: tabular-nums !important;
}

.bench-c.num {
  font-weight: 600 !important;
}

.bench-c.odd {
  background: #f3f4f6 !important;
}

.bench-preview {
  color: #6b7280 !important;
  font-weight: 400 !important;
}

@media (max-width: 800px) {
  .bench-stats {
    grid-template-columns: 1fr !important;
  }

  .bench-info-grid {
    grid-template-columns: 1fr 1fr !important;
  }

  .bench-grid {
    grid-template-columns: 0.9fr 1fr 1.1fr 0.65fr 0.8fr 0.85fr 0.8fr 0.6fr !important;
    overflow-x: auto !important;
  }
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

#left-card,
#right-card,
#results-stack {
  gap: 0.5rem !important;
}

#right-card {
  justify-content: center !important;
}

#left-card .block,
#right-card .block,
#left-card .form,
#right-card .form,
.copyable-field {
  padding: 0 !important;
  margin: 0 !important;
  gap: 0 !important;
}

.block .label-wrap,
[class*="block-label"] {
  margin: 0 0 0.25rem 0 !important;
  padding: 0 !important;
}

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
[class*="block-label"],
.lang-section-label {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #111827 !important;
  font-weight: 600 !important;
  font-size: 0.95rem !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
}

input, textarea, select {
  background: #ffffff !important;
  color: #111827 !important;
  border: 1px solid #d1d5db !important;
  border-radius: 10px !important;
  font-size: 0.875rem !important;
  line-height: 1.5 !important;
  font-weight: 400 !important;
}

textarea {
  overflow-y: auto !important;
  resize: vertical !important;
}

.lang-name-field textarea,
.lang-name-field input {
  overflow: hidden !important;
  resize: none !important;
  min-height: 42px !important;
  height: 42px !important;
  max-height: 42px !important;
  line-height: 1.4 !important;
  padding-top: 0.55rem !important;
  padding-bottom: 0.55rem !important;
}

input::placeholder, textarea::placeholder {
  color: #9ca3af !important;
  opacity: 1 !important;
}

button.primary {
  min-height: 46px !important;
  margin-top: 0.55rem !important;
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

#page-prompts .prompt-actions {
  gap: 0.75rem !important;
  align-items: stretch !important;
}

#page-prompts .prompt-actions button {
  min-height: 46px !important;
  height: 46px !important;
  margin-top: 0.55rem !important;
  border-radius: 10px !important;
  font-weight: 650 !important;
  font-size: 0.95rem !important;
  padding: 0 1rem !important;
}

#page-prompts .prompt-actions button:not(.primary) {
  background: #ffffff !important;
  color: #111827 !important;
  border: 1px solid #d1d5db !important;
  box-shadow: none !important;
}

#page-prompts .prompt-actions button:not(.primary):hover {
  background: #f9fafb !important;
  border-color: #9ca3af !important;
}

#bench-reset,
#bench-reset button,
#page-benchmark .bench-reset-btn,
#page-benchmark .bench-reset-btn button {
  display: block !important;
  width: 100% !important;
  box-sizing: border-box !important;
  min-height: 42px !important;
  height: 42px !important;
  margin: 0.75rem 0 0 0 !important;
  padding: 0 1rem !important;
  border-radius: 10px !important;
  background: #fef2f2 !important;
  color: #b91c1c !important;
  border: 1px solid #fecaca !important;
  box-shadow: none !important;
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  cursor: pointer !important;
}

#bench-reset:hover,
#bench-reset button:hover,
#page-benchmark .bench-reset-btn:hover,
#page-benchmark .bench-reset-btn button:hover {
  background: #fee2e2 !important;
  border-color: #fca5a5 !important;
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

.loading-elapsed {
  color: #9ca3af !important;
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  font-variant-numeric: tabular-nums !important;
  min-height: 1.2em;
}

.run-timing {
  margin: 0.45rem 0 0 0 !important;
  padding: 0 !important;
  color: #9ca3af !important;
  font-size: 0.8rem !important;
  font-weight: 400 !important;
  text-align: right !important;
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

.form-message .msg-warn {
  color: #92400e !important;
  background: #dbeafe !important;
  border: 1px solid #fcd34d !important;
  border-radius: 10px !important;
  padding: 0.65rem 0.85rem !important;
  font-size: 0.92rem !important;
  font-weight: 600 !important;
  line-height: 1.4 !important;
}

.lang-row {
  display: grid !important;
  grid-template-columns: 1fr auto 1fr !important;
  gap: 0.75rem !important;
  align-items: center !important;
  margin: 0 !important;
}

.model-row {
  display: grid !important;
  grid-template-columns: 1fr !important;
  gap: 0.75rem !important;
  align-items: center !important;
  margin: 0 !important;
}

.lang-section-label {
  margin: 0 0 0.25rem 0 !important;
  padding: 0 !important;
  color: #111827 !important;
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
.lang-row .lang-select,
.model-row .block,
.model-row .form,
.model-row > div,
.model-row .container,
.model-row .wrap,
.model-row .secondary-wrap,
.model-row [class*="secondary-wrap"],
.model-row [class*="wrap"],
.model-select,
.model-row .model-select {
  background: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}

.lang-row input,
.model-row input {
  background: #ffffff !important;
  border: 1px solid #d1d5db !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  outline: none !important;
  min-height: 42px !important;
  color: #111827 !important;
  padding: 0.55rem 0.75rem !important;
  font-size: 0.875rem !important;
  line-height: 1.5 !important;
}

.lang-row input:focus,
.model-row input:focus {
  border: 1px solid #9ca3af !important;
  box-shadow: none !important;
  outline: none !important;
}

/* Prevent focus ring on parent wrappers */
.lang-row *:focus,
.lang-row *:focus-within,
.model-row *:focus,
.model-row *:focus-within {
  outline: none !important;
}

.lang-row input:focus,
.model-row input:focus {
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

.copyable-field .corrected-html,
.copyable-field .corrected-html .html-container,
.copyable-field .corrected-html .prose,
.copyable-field .corrected-block {
  max-width: none !important;
  width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
}

.copyable-field textarea,
.corrected-box,
.copyable-field .corrected-html .prose,
.copyable-field .corrected-html .prose .corrected-box,
.copyable-field .corrected-html .prose .corrected-box * {
  font-size: 0.875rem !important;
  font-weight: 400 !important;
  line-height: 1.5 !important;
  letter-spacing: normal !important;
  font-variant: normal !important;
  font-feature-settings: normal !important;
  color: #111827 !important;
  font-family: Inter, ui-sans-serif, system-ui, sans-serif !important;
}

.copyable-field textarea,
.corrected-box {
  padding: 0.65rem 2.5rem 0.65rem 0.75rem !important;
}

.result-field-label {
  margin: 0 0 0.25rem 0 !important;
  padding: 0 !important;
  color: #111827 !important;
  font-weight: 600 !important;
  font-size: 0.95rem !important;
  line-height: 1.4 !important;
  font-family: Inter, ui-sans-serif, system-ui, sans-serif !important;
}

.corrected-box {
  background: #ffffff !important;
  color: #111827 !important;
  border: 1px solid #d1d5db !important;
  border-radius: 10px !important;
  min-height: 7.4rem !important;
  max-height: 12rem !important;
  overflow-y: auto !important;
  white-space: pre-wrap !important;
  overflow-wrap: break-word !important;
  box-sizing: border-box !important;
}

.corrected-box .diff-chg,
.prose .diff-chg,
span.diff-chg {
  background: #dbeafe !important;
  background-color: #dbeafe !important;
  color: inherit !important;
  font: inherit !important;
  padding: 0 !important;
  margin: 0 !important;
  border-radius: 2px !important;
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
}

#corrected-plain,
#corrected-plain textarea {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
<style>
  html, body, .gradio-container, button, input, textarea, select, label {
    font-family: Inter, ui-sans-serif, system-ui, sans-serif !important;
    -webkit-font-smoothing: antialiased;
  }
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
  .diff-chg {
    background: #dbeafe !important;
    background-color: #dbeafe !important;
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
    const box = field.querySelector(".corrected-box") || field.querySelector("textarea");
    const btn = field.querySelector("button.modern-copy-btn");
    if (!box || !btn) return;
    const fieldRect = field.getBoundingClientRect();
    const taRect = box.getBoundingClientRect();
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

function formatElapsed(ms) {
  const total = Math.max(0, ms / 1000);
  if (total < 60) return total.toFixed(1) + "s";
  const minutes = Math.floor(total / 60);
  const secs = Math.round(total % 60);
  return minutes + "m " + String(secs).padStart(2, "0") + "s";
}

let loaderStartedAt = 0;
let loaderRunId = null;
let loaderClearTimer = null;

function tickLoader() {
  const box = document.querySelector(".loading-box");
  const elapsedEl = box ? box.querySelector(".loading-elapsed") : null;
  if (!box || !elapsedEl) {
    if (!loaderClearTimer && loaderStartedAt) {
      loaderClearTimer = setTimeout(() => {
        loaderStartedAt = 0;
        loaderRunId = null;
        loaderClearTimer = null;
      }, 400);
    }
    return;
  }
  if (loaderClearTimer) {
    clearTimeout(loaderClearTimer);
    loaderClearTimer = null;
  }
  const runId = box.getAttribute("data-run") || "loading";
  if (runId !== loaderRunId) {
    loaderRunId = runId;
    loaderStartedAt = Date.now();
  }
  elapsedEl.textContent = formatElapsed(Date.now() - loaderStartedAt);
}

setInterval(tickLoader, 100);
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", tickLoader);
} else {
  tickLoader();
}

let skipBenchPersistUntil = 0;
function persistBenchHistory() {
  if (Date.now() < skipBenchPersistUntil) return;
  const sources = [
    document.getElementById("bench-persist"),
    document.querySelector("#bench-blob textarea"),
    document.querySelector("#bench-blob input"),
  ];
  for (const el of sources) {
    if (!el) continue;
    const raw = (el.textContent || el.value || "").trim();
    if (!raw || raw === "[]") continue;
    try {
      const rows = JSON.parse(raw);
      if (Array.isArray(rows) && rows.length) {
        localStorage.setItem("local-lingo-bench", JSON.stringify(rows.slice(0, 10)));
        return;
      }
    } catch (e) {}
  }
}
const benchPersistObserver = new MutationObserver(persistBenchHistory);
window.addEventListener("load", () => {
  persistBenchHistory();
  benchPersistObserver.observe(document.body, { childList: true, subtree: true, characterData: true });
});
setInterval(persistBenchHistory, 800);
if (document.readyState !== "loading") persistBenchHistory();

document.addEventListener("click", (e) => {
  if (!e.target.closest("#bench-reset")) return;
  skipBenchPersistUntil = Date.now() + 2500;
  try { localStorage.removeItem("local-lingo-bench"); } catch (err) {}
});
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
    <p>Detects which language you pasted, rewrites it to sound natural, then translates it to the other language in your pair — privately on your machine via Ollama.</p>
    """


PLACEHOLDER_HTML = """
<div class="result-placeholder">
  Your corrected text and translation will appear here.
</div>
"""

def _loading_html(run_id: str) -> str:
    return f"""
<div class="loading-box" data-run="{run_id}">
  <div class="spinner"></div>
  <div class="loading-text">Working on your text…</div>
  <div class="loading-elapsed">0.0s</div>
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

SAVE_PREFS_JS = """
(lang_a, lang_b, text) => {
  try {
    localStorage.setItem("local-lingo-prefs", JSON.stringify({
      lang_a: lang_a || "",
      lang_b: lang_b || "",
      text: (text || "").slice(0, 50000)
    }));
  } catch (e) {}
}
"""

RESTORE_PREFS_JS = """
(lang_a, lang_b, text) => {
  try {
    const p = JSON.parse(localStorage.getItem("local-lingo-prefs") || "{}");
    return [
      p.lang_a || lang_a || "",
      p.lang_b || lang_b || "",
      typeof p.text === "string" ? p.text : (text || "")
    ];
  } catch (e) {
    return [lang_a || "", lang_b || "", text || ""];
  }
}
"""

SAVE_PROMPTS_JS = """
(_system_g, user_e) => {
  try {
    localStorage.setItem("local-lingo-prompts", JSON.stringify({
      user_extra: (user_e || "").slice(0, 4000)
    }));
  } catch (e) {}
}
"""

RESTORE_BENCH_JS = """
(blob, history, html) => {
  try {
    const saved = localStorage.getItem("local-lingo-bench");
    if (!saved) return [blob || "[]", history, html];
    const rows = JSON.parse(saved);
    if (!Array.isArray(rows)) return [blob || "[]", history, html];
    return [saved, history, html];
  } catch (e) {
    return [blob || "[]", history, html];
  }
}
"""

SAVE_BENCH_JS = """
(blob) => {
  try {
    const rows = JSON.parse(blob || "[]");
    if (Array.isArray(rows) && rows.length) {
      localStorage.setItem("local-lingo-bench", JSON.stringify(rows.slice(0, 10)));
    }
  } catch (e) {}
}
"""

RESET_BENCH_JS = """
() => {
  try {
    localStorage.removeItem("local-lingo-bench");
  } catch (e) {}
}
"""

RESTORE_PROMPTS_JS = """
(system_g, user_e) => {
  try {
    const p = JSON.parse(localStorage.getItem("local-lingo-prompts") || "{}");
    return [
      system_g || "",
      typeof p.user_extra === "string" ? p.user_extra : (user_e || "")
    ];
  } catch (e) {
    return [system_g || "", user_e || ""];
  }
}
"""

_PREFS_TEXT_LIMIT = 50_000


def _normalize_saved_lang(value: str, default: str) -> str:
    raw = (value or "").strip()
    if raw in CODE_TO_NAME:
        return raw
    lower = raw.lower()
    for name, code in LANGUAGES.items():
        if name.lower() == lower:
            return code
    return default


def _restore_session(lang_a: str, lang_b: str, text: str):
    default_a, default_b = codes_from_default_pair(config.DEFAULT_LANGUAGE_PAIR)
    a = _normalize_saved_lang(lang_a, default_a)
    b = _normalize_saved_lang(lang_b, default_b)
    if a == b:
        a, b = default_a, default_b
    saved = text if isinstance(text, str) else ""
    if len(saved) > _PREFS_TEXT_LIMIT:
        saved = saved[:_PREFS_TEXT_LIMIT]
    return a, b, saved


def _message_html(text: str = "", kind: str = "error") -> str:
    if not text:
        return '<div class="form-message"></div>'
    css = "msg-warn" if kind == "warn" else "msg-error"
    return f'<div class="form-message"><div class="{css}">{text}</div></div>'


def _model_hint_html(warning: str = "") -> str:
    if warning:
        return _message_html(warning, kind="warn")
    return (
        '<p class="lang-section-hint">Installed Ollama models on this machine. '
        "The list refreshes when you open the app.</p>"
    )


def _format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes}m {secs:02d}s"


def _timing_html(seconds: float | None = None) -> str:
    if seconds is None:
        return '<p class="run-timing"></p>'
    return f'<p class="run-timing">Completed in {_format_elapsed(seconds)}</p>'


def _corrected_display(original: str = "", corrected: str = "") -> str:
    body = highlight_corrections(original, corrected)
    return (
        '<div class="corrected-block">'
        '<div class="result-field-label">Corrected (native rewrite)</div>'
        f'<div class="corrected-box" style="font-family: Inter, ui-sans-serif, system-ui, sans-serif;">{body}</div>'
        "</div>"
    )


def _fmt_seconds(seconds: float) -> str:
    if seconds <= 0:
        return "—"
    if seconds < 0.01:
        return f"{seconds * 1000:.1f}ms"
    return _format_elapsed(seconds)


def _fmt_rate(rate: float | None) -> str:
    if rate is None:
        return "—"
    if rate >= 100:
        return f"{rate:.0f} tokens/s"
    return f"{rate:.1f} tokens/s"


def _fmt_ns(duration_ns: int) -> str:
    return _fmt_seconds(duration_ns / 1_000_000_000)


def _fmt_rate_num(rate: float | None) -> str:
    if rate is None:
        return "—"
    if rate >= 100:
        return f"{rate:.0f}"
    return f"{rate:.1f}"


_BENCH_HISTORY_LIMIT = 10


def _fmt_when(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "—"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return "—"
    if dt.tzinfo is not None:
        dt = dt.astimezone()
    return dt.strftime("%d %b %H:%M:%S")


def _history_entry(
    metrics: RunMetrics,
    text: str,
    pair: str,
    ok: bool = True,
) -> dict:
    preview = " ".join((text or "").split())
    if len(preview) > 42:
        preview = preview[:42].rstrip() + "…"
    load_s = (metrics.load_duration_ns or 0) / 1_000_000_000
    return {
        "model": metrics.model or "",
        "pair": pair or "",
        "preview": preview,
        "wall": round(float(metrics.wall_seconds or 0), 2),
        "eval_rate": metrics.eval_rate,
        "prompt_eval_rate": metrics.prompt_eval_rate,
        "prompt_tokens": int(metrics.prompt_eval_count or 0),
        "eval_tokens": int(metrics.eval_count or 0),
        "load_s": round(load_s, 2),
        "ok": bool(ok),
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def _append_history(history: list | None, entry: dict) -> list:
    rows = [entry]
    for item in _normalize_history(history):
        rows.append(item)
        if len(rows) >= _BENCH_HISTORY_LIMIT:
            break
    return rows[:_BENCH_HISTORY_LIMIT]


def _normalize_history(history: list | dict | None) -> list:
    if isinstance(history, dict):
        history = [history]
    rows: list[dict] = []
    for item in history or []:
        if isinstance(item, dict) and (item.get("model") or item.get("wall") is not None):
            rows.append(item)
        if len(rows) >= _BENCH_HISTORY_LIMIT:
            break
    return rows


def _history_blob(history: list | dict | None) -> str:
    return json.dumps(_normalize_history(history), separators=(",", ":"))


def _restore_bench_history(history: list | dict | None):
    rows = _normalize_history(history)
    return rows, _benchmark_html(history=rows)


def _restore_bench_from_blob(blob: str):
    try:
        data = json.loads(blob or "[]")
    except (TypeError, json.JSONDecodeError, ValueError):
        data = []
    return _restore_bench_history(data)


def _restore_bench_pack(blob: str, _history=None, _html=None):
    rows, markup = _restore_bench_from_blob(blob)
    return _history_blob(rows), rows, markup


def _bench_persist_html(rows: list) -> str:
    payload = html.escape(
        json.dumps(rows[:_BENCH_HISTORY_LIMIT], separators=(",", ":")),
        quote=True,
    )
    return f'<div id="bench-persist" hidden>{payload}</div>'


def _bench_info_card() -> str:
    timeout = config.REQUEST_TIMEOUT_SECONDS
    timeout_label = (
        f"{int(timeout)}s" if timeout == int(timeout) else f"{timeout:g}s"
    )
    items = (
        ("Temperature", str(config.TEMPERATURE)),
        ("Context (num_ctx)", f"{config.NUM_CTX:,}"),
        ("Keep alive", str(config.KEEP_ALIVE)),
        ("Timeout", timeout_label),
        ("Think", "off"),
    )
    cells = "".join(
        '<div class="bench-info-item">'
        f'<span class="bench-info-label">{html.escape(label)}</span>'
        f'<span class="bench-info-value">{html.escape(value)}</span>'
        "</div>"
        for label, value in items
    )
    return (
        '<div class="bench-stat bench-stat-wide bench-stat-info">'
        '<div class="bench-stat-head">Settings</div>'
        '<div class="bench-stat-body">'
        f'<div class="bench-info-grid">{cells}</div>'
        '<p class="bench-stat-help">'
        "Ollama options sent with every request. Edit temperature, context, "
        "keep alive, and timeout in <code>config.py</code>. Thinking stays off."
        "</p>"
        "</div></div>"
    )


def _benchmark_html(history: list | None = None, note: str = "") -> str:
    rows = _normalize_history(history)
    if not rows:
        return (
            '<div class="benchmark-empty">'
            "Run a translation to see timing, eval rate, and a history of the last 10 calls."
            "</div>"
        )

    latest = rows[0]
    model = latest.get("model") or "—"
    wall = float(latest.get("wall") or 0)
    prompt_tokens = int(latest.get("prompt_tokens") or 0)
    eval_tokens = int(latest.get("eval_tokens") or 0)
    load_s = float(latest.get("load_s") or 0)
    prompt_rate_num = _fmt_rate_num(latest.get("prompt_eval_rate"))
    eval_rate_num = _fmt_rate_num(latest.get("eval_rate"))
    total_tokens = prompt_tokens + eval_tokens
    note_html = ""
    if note:
        note_html = (
            f'<p class="lang-section-hint" style="margin:0">{html.escape(note[:400])}</p>'
        )

    def cell(text: str, *, num: bool = False, extra: str = "", title: str = "") -> str:
        classes = "bench-c"
        if num:
            classes += " num"
        if extra:
            classes += f" {extra}"
        title_attr = f' title="{title}"' if title else ""
        return f'<div class="{classes}"{title_attr}>{text}</div>'

    grid_cells = [
        '<div class="bench-h">When</div>',
        '<div class="bench-h">Model</div>',
        '<div class="bench-h">Input</div>',
        '<div class="bench-h num">Wall</div>',
        '<div class="bench-h num">Eval rate</div>',
        '<div class="bench-h num">Prompt eval</div>',
        '<div class="bench-h num">In / out</div>',
        '<div class="bench-h num">Load</div>',
    ]
    for index, item in enumerate(rows):
        stripe = "odd" if index % 2 else "even"
        when = _fmt_when(item.get("at"))
        preview = html.escape(str(item.get("preview") or "—"))
        grid_cells.extend(
            [
                cell(html.escape(when), extra=stripe, title=html.escape(str(item.get("at") or ""))),
                cell(html.escape(str(item.get("model") or "—")), extra=stripe),
                cell(preview, extra=f"bench-preview {stripe}", title=preview),
                cell(_format_elapsed(float(item.get("wall") or 0)), num=True, extra=stripe),
                cell(_fmt_rate_num(item.get("eval_rate")), num=True, extra=stripe),
                cell(_fmt_rate_num(item.get("prompt_eval_rate")), num=True, extra=stripe),
                cell(
                    f"{int(item.get('prompt_tokens') or 0)} / {int(item.get('eval_tokens') or 0)}",
                    num=True,
                    extra=stripe,
                ),
                cell(_fmt_seconds(float(item.get("load_s") or 0)), num=True, extra=stripe),
            ]
        )

    unit = '<span class="bench-unit"> tokens/s</span>'
    model_badge = f'<span class="bench-model">{html.escape(str(model))}</span>'
    persist = _bench_persist_html(rows)
    return f"""
<div class="bench">
  {persist}
  <div class="bench-stats">
    <div class="bench-stat bench-stat-wide">
      <div class="bench-stat-head"><span>Wall time</span>{model_badge}</div>
      <div class="bench-stat-body">
        <div class="bench-stat-value">{_format_elapsed(wall)}</div>
        <p class="bench-stat-help">Time from clicking Correct &amp; Translate until the result appeared, including model load.</p>
      </div>
    </div>
    {_bench_info_card()}
    <div class="bench-stat">
      <div class="bench-stat-head">Eval rate</div>
      <div class="bench-stat-body">
        <div class="bench-stat-value">{eval_rate_num}{unit}</div>
        <p class="bench-stat-help">How fast the model wrote the reply (generated tokens per second).</p>
      </div>
    </div>
    <div class="bench-stat">
      <div class="bench-stat-head">Prompt eval rate</div>
      <div class="bench-stat-body">
        <div class="bench-stat-value">{prompt_rate_num}{unit}</div>
        <p class="bench-stat-help">How fast the model read your input before generating.</p>
      </div>
    </div>
    <div class="bench-stat">
      <div class="bench-stat-head">Total tokens</div>
      <div class="bench-stat-body">
        <div class="bench-stat-value">{total_tokens}</div>
        <p class="bench-stat-help">Prompt tokens plus generated tokens for this request.</p>
      </div>
    </div>
  </div>
  <p class="bench-meta">Prompt used {prompt_tokens} tokens. The model generated {eval_tokens} tokens. Loading the model took {_fmt_seconds(load_s)}.</p>
  {note_html}
  <div class="bench-history">
    <div class="bench-history-head">
      <p class="bench-history-title">History</p>
      <p class="bench-history-hint">Last {len(rows)} · newest first</p>
    </div>
    <div class="bench-grid">{"".join(grid_cells)}</div>
  </div>
</div>
"""


def _reset_benchmark():
    return [], _benchmark_html(), "[]"


def _locked_prompt_preview() -> str:
    locked = html.escape(LOCKED_OUTPUT_FORMAT.strip())
    suffix = html.escape(LOCKED_USER_SUFFIX)
    return (
        '<p class="lang-section-label">Required result fields</p>'
        '<p class="lang-section-hint">'
        "Always appended so the app can fill the result boxes. These labels cannot be edited."
        "</p>"
        f'<div class="prompt-locked">{locked}\n\n{suffix}</div>'
    )


def _show_page(page: str):
    return (
        gr.update(visible=page == "translate"),
        gr.update(visible=page == "prompts"),
        gr.update(visible=page == "benchmark"),
        gr.update(variant="primary" if page == "translate" else "secondary"),
        gr.update(variant="primary" if page == "prompts" else "secondary"),
        gr.update(variant="primary" if page == "benchmark" else "secondary"),
    )


def _save_prompts(_system_g: str, user_e: str):
    extra_clean = sanitize_prompt_addon(user_e)
    return DEFAULT_SYSTEM_GUIDELINES, extra_clean, "Saved. The next run will use this extra instruction."


def _reset_prompts():
    return DEFAULT_SYSTEM_GUIDELINES, DEFAULT_USER_EXTRA, "Cleared the extra user instruction."


def _empty_results():
    return (
        gr.update(visible=True, value=PLACEHOLDER_HTML),
        gr.update(visible=False),
        "",
        "",
        "",
        "",
    )


def _run(
    text: str,
    lang_a: str,
    lang_b: str,
    model: str | None = None,
    system_guidelines: str | None = None,
    user_extra: str | None = None,
    history: list | None = None,
):
    history = _normalize_history(history)
    try:
        cleaned, pair = validate_inputs_from_languages(text, lang_a, lang_b)
    except ValidationError as exc:
        yield (*_empty_results(), _message_html(str(exc)), _timing_html(), "", gr.update(), history, _history_blob(history))
        return

    chosen_model = (model or "").strip()
    catalog = get_model_catalog()
    if not catalog.selected:
        yield (
            *_empty_results(),
            _message_html(catalog.warning, kind="warn"),
            _timing_html(),
            "",
            gr.update(),
            history,
            _history_blob(history),
        )
        return
    if chosen_model not in catalog.choices:
        chosen_model = catalog.selected

    yield (
        gr.update(visible=True, value=_loading_html(str(time.time_ns()))),
        gr.update(visible=False),
        "",
        "",
        "",
        "",
        _message_html(""),
        _timing_html(),
        "",
        gr.update(),
        history,
        _history_blob(history),
    )

    started = time.perf_counter()
    result = translate_and_correct(
        cleaned,
        pair,
        model=chosen_model,
        system_guidelines=DEFAULT_SYSTEM_GUIDELINES,
        user_extra=user_extra,
    )
    elapsed = time.perf_counter() - started
    result.metrics.wall_seconds = elapsed
    if not result.metrics.model:
        result.metrics.model = chosen_model
    failed = bool(result.note and (not result.corrected or result.corrected == "?"))
    history = _append_history(
        history,
        _history_entry(result.metrics, cleaned, pair, ok=not failed),
    )
    bench = _benchmark_html(history=history, note=result.note if failed else "")

    if failed:
        yield (
            *_empty_results(),
            _message_html(result.note),
            _timing_html(elapsed),
            "",
            bench,
            history,
            _history_blob(history),
        )
        return

    yield (
        gr.update(visible=False),
        gr.update(visible=True),
        result.detected,
        result.corrected,
        result.target,
        result.translation,
        _message_html(""),
        _timing_html(elapsed),
        _corrected_display(cleaned, result.corrected),
        bench,
        history,
        _history_blob(history),
    )


def _refresh_models():
    catalog = get_model_catalog()
    has_models = bool(catalog.choices)
    return (
        gr.update(
            choices=catalog.choices,
            value=catalog.selected,
            interactive=has_models,
        ),
        _model_hint_html(catalog.warning),
        gr.update(interactive=has_models),
    )


def build_ui() -> gr.Blocks:
    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="slate",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
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
        bench_history = gr.State([])
        bench_blob = gr.Textbox(value="[]", visible=False, elem_id="bench-blob")
        with gr.Column(elem_classes=["main-title"]):
            gr.HTML(_brand_header_html())

        with gr.Row(elem_id="app-nav"):
            nav_translate = gr.Button("Translate", variant="primary")
            nav_prompts = gr.Button("Prompts")
            nav_benchmark = gr.Button("Benchmark")

        with gr.Column(visible=True, elem_id="page-translate") as page_translate:
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
                    gr.HTML('<p class="lang-section-label">Model</p>')
                    model_hint = gr.HTML(value=_model_hint_html())
                    with gr.Row(elem_classes=["model-row"]):
                        model = gr.Dropdown(
                            choices=[],
                            value=None,
                            show_label=False,
                            filterable=True,
                            allow_custom_value=False,
                            container=False,
                            interactive=False,
                            elem_classes=["model-select"],
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
                    with gr.Column(visible=False, elem_id="results-stack") as results:
                        detected = gr.Textbox(
                            label="Detected language",
                            interactive=False,
                            lines=1,
                            max_lines=1,
                            elem_classes=["lang-name-field"],
                        )

                        with gr.Column(elem_classes=["copyable-field"]):
                            corrected_view = gr.HTML(
                                value=_corrected_display(),
                                padding=False,
                                elem_classes=["corrected-html"],
                            )
                            corrected = gr.Textbox(
                                visible=False,
                                show_label=False,
                                elem_id="corrected-plain",
                            )
                            copy_corrected = gr.Button(
                                "Copy",
                                elem_classes=["modern-copy-btn"],
                                size="sm",
                            )

                        target = gr.Textbox(
                            label="Target language",
                            interactive=False,
                            lines=1,
                            max_lines=1,
                            elem_classes=["lang-name-field"],
                        )

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
                        run_timing = gr.HTML(value=_timing_html())

        with gr.Column(visible=False, elem_id="page-prompts") as page_prompts:
            with gr.Column(elem_classes=["card"]):
                gr.HTML(
                    """
                    <p class="lang-section-label">Prompt instructions</p>
                    <p class="lang-section-hint">
                    Add an extra user instruction if you want. The system prompt is shown for
                    reference and cannot be edited yet. Placeholders
                    <code>{name_a}</code> and <code>{name_b}</code> become the selected language names.
                    </p>
                    """
                )
                system_guidelines = gr.Textbox(
                    label="System instructions (read-only)",
                    value=DEFAULT_SYSTEM_GUIDELINES,
                    lines=12,
                    max_lines=20,
                    interactive=False,
                    elem_classes=["prompt-readonly"],
                )
                user_extra = gr.Textbox(
                    label="Extra user instruction (optional)",
                    value=DEFAULT_USER_EXTRA,
                    lines=4,
                    max_lines=8,
                    placeholder="e.g. Prefer a formal tone. Keep names unchanged.",
                )
                gr.HTML(_locked_prompt_preview())
                with gr.Row(elem_classes=["prompt-actions"]):
                    save_prompts_btn = gr.Button("Save instructions", variant="primary")
                    reset_prompts_btn = gr.Button("Reset to defaults")
                prompt_status = gr.HTML(value=_message_html())

        with gr.Column(visible=False, elem_id="page-benchmark") as page_benchmark:
            with gr.Column(elem_classes=["card"]):
                gr.HTML(
                    """
                    <p class="lang-section-label">Last run</p>
                    <p class="lang-section-hint">
                    Timing, eval rate, and a history of the last 10 calls — useful for comparing models.
                    </p>
                    """
                )
                benchmark_view = gr.HTML(value=_benchmark_html())
            reset_bench_btn = gr.Button(
                "Reset",
                elem_id="bench-reset",
                elem_classes=["bench-reset-btn"],
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

        for component in (lang_a, lang_b, text):
            component.change(
                fn=None,
                inputs=[lang_a, lang_b, text],
                js=SAVE_PREFS_JS,
                show_progress="hidden",
            )

        nav_translate.click(
            fn=lambda: _show_page("translate"),
            outputs=[page_translate, page_prompts, page_benchmark, nav_translate, nav_prompts, nav_benchmark],
            show_progress="hidden",
        )
        nav_prompts.click(
            fn=lambda: _show_page("prompts"),
            outputs=[page_translate, page_prompts, page_benchmark, nav_translate, nav_prompts, nav_benchmark],
            show_progress="hidden",
        )
        nav_benchmark.click(
            fn=lambda: _show_page("benchmark"),
            outputs=[page_translate, page_prompts, page_benchmark, nav_translate, nav_prompts, nav_benchmark],
            show_progress="hidden",
        )

        save_prompts_btn.click(
            fn=_save_prompts,
            inputs=[system_guidelines, user_extra],
            outputs=[system_guidelines, user_extra, prompt_status],
            show_progress="hidden",
        ).then(
            fn=None,
            inputs=[system_guidelines, user_extra],
            js=SAVE_PROMPTS_JS,
            show_progress="hidden",
        )
        reset_prompts_btn.click(
            fn=_reset_prompts,
            outputs=[system_guidelines, user_extra, prompt_status],
            show_progress="hidden",
        ).then(
            fn=None,
            inputs=[system_guidelines, user_extra],
            js=SAVE_PROMPTS_JS,
            show_progress="hidden",
        )

        reset_bench_btn.click(
            fn=_reset_benchmark,
            outputs=[bench_history, benchmark_view, bench_blob],
            show_progress="hidden",
        ).then(
            fn=None,
            js=RESET_BENCH_JS,
            show_progress="hidden",
        )

        btn.click(
            fn=_run,
            inputs=[text, lang_a, lang_b, model, system_guidelines, user_extra, bench_history],
            outputs=[
                placeholder,
                results,
                detected,
                corrected,
                target,
                translation,
                form_message,
                run_timing,
                corrected_view,
                benchmark_view,
                bench_history,
                bench_blob,
            ],
            show_progress="hidden",
        ).then(
            fn=None,
            inputs=[bench_blob],
            js=SAVE_BENCH_JS,
            show_progress="hidden",
        )

        demo.load(
            fn=_restore_session,
            inputs=[lang_a, lang_b, text],
            outputs=[lang_a, lang_b, text],
            js=RESTORE_PREFS_JS,
            show_progress="hidden",
        )
        demo.load(
            fn=lambda _system_g, user_e: (
                DEFAULT_SYSTEM_GUIDELINES,
                sanitize_prompt_addon(user_e),
            ),
            inputs=[system_guidelines, user_extra],
            outputs=[system_guidelines, user_extra],
            js=RESTORE_PROMPTS_JS,
            show_progress="hidden",
        )
        demo.load(
            fn=_restore_bench_pack,
            inputs=[bench_blob, bench_history, benchmark_view],
            outputs=[bench_blob, bench_history, benchmark_view],
            js=RESTORE_BENCH_JS,
            show_progress="hidden",
        )
        demo.load(
            fn=_refresh_models,
            outputs=[model, model_hint, btn],
            show_progress="hidden",
        )

    return demo
