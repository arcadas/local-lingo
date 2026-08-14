"""Automated tests for LocalLingo."""

from __future__ import annotations

import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from local_lingo import config
from local_lingo.languages import (
    CODE_TO_NAME,
    LANGUAGE_CHOICES,
    codes_from_default_pair,
    name_for_code,
)
from local_lingo.highlight import highlight_corrections
from local_lingo.prompts import (
    build_system_prompt,
    build_user_prompt,
    sanitize_prompt_addon,
)
from local_lingo.service import (
    ModelCatalog,
    RunMetrics,
    get_model_catalog,
    list_ollama_models,
    metrics_from_ollama,
    ollama_chat,
    parse_fields,
    translate_and_correct,
)
from local_lingo.ui import (
    build_ui,
    _append_history,
    _benchmark_html,
    _fmt_when,
    _history_entry,
    _normalize_history,
    _restore_bench_from_blob,
    _restore_bench_pack,
    _reset_benchmark,
    _restore_session,
    _run,
)
from local_lingo.validation import (
    ValidationError,
    resolve_language_code,
    validate_inputs_from_languages,
    validate_language_pair,
    validate_language_selection,
    validate_text,
)


class ConfigTests(unittest.TestCase):
    def test_app_name(self):
        self.assertEqual(config.APP_NAME, "Local Lingo")

    def test_default_pair_format(self):
        self.assertEqual(config.DEFAULT_LANGUAGE_PAIR, "en-es")
        left, right = codes_from_default_pair(config.DEFAULT_LANGUAGE_PAIR)
        self.assertTrue(left)
        self.assertTrue(right)
        self.assertNotEqual(left, right)


class LanguageCatalogTests(unittest.TestCase):
    def test_choices_are_name_code_tuples(self):
        self.assertGreater(len(LANGUAGE_CHOICES), 10)
        for label, code in LANGUAGE_CHOICES:
            self.assertIsInstance(label, str)
            self.assertIsInstance(code, str)
            self.assertEqual(CODE_TO_NAME[code], label)

    def test_name_for_code(self):
        self.assertEqual(name_for_code("en"), "English")
        self.assertEqual(name_for_code("es"), "Spanish")

    def test_codes_from_default_pair(self):
        self.assertEqual(codes_from_default_pair("en-es"), ("en", "es"))
        self.assertEqual(codes_from_default_pair("DE_FR"), ("de", "fr"))


class ValidationTests(unittest.TestCase):
    def test_validate_text_ok(self):
        self.assertEqual(validate_text("  hello  "), "hello")

    def test_validate_text_empty(self):
        with self.assertRaises(ValidationError):
            validate_text("   ")

    def test_resolve_language_code_from_code_and_name(self):
        self.assertEqual(resolve_language_code("en"), "en")
        self.assertEqual(resolve_language_code("English"), "en")
        self.assertEqual(resolve_language_code("SPANISH"), "es")

    def test_resolve_language_unknown(self):
        with self.assertRaises(ValidationError):
            resolve_language_code("NotALanguage")

    def test_validate_language_selection(self):
        self.assertEqual(validate_language_selection("en", "es"), "en-es")
        self.assertEqual(validate_language_selection("English", "Spanish"), "en-es")

    def test_validate_language_selection_same_language(self):
        with self.assertRaises(ValidationError):
            validate_language_selection("en", "en")

    def test_validate_language_pair(self):
        self.assertEqual(validate_language_pair("EN_ES"), "en-es")
        with self.assertRaises(ValidationError):
            validate_language_pair("en")
        with self.assertRaises(ValidationError):
            validate_language_pair("en-en")

    def test_validate_inputs_from_languages(self):
        text, pair = validate_inputs_from_languages("Hi there", "en", "es")
        self.assertEqual(text, "Hi there")
        self.assertEqual(pair, "en-es")

    def test_validate_inputs_from_languages_rejects_empty_text(self):
        with self.assertRaises(ValidationError):
            validate_inputs_from_languages("", "en", "es")


class PromptTests(unittest.TestCase):
    def test_system_prompt_uses_full_names_and_forbids_swapping_fields(self):
        prompt = build_system_prompt("English", "Spanish")
        self.assertIn("English", prompt)
        self.assertIn("Spanish", prompt)
        self.assertIn("Never swap Corrected and Translation", prompt)
        self.assertIn("Pair order is not the direction", prompt)
        self.assertIn("Never translate in Corrected", prompt)
        self.assertIn("Keep Corrected approximately the same length as the original", prompt)
        self.assertIn("Do not greet, confirm, explain, or wait", prompt)
        self.assertNotIn("en-es", prompt)

    def test_user_prompt_includes_text_and_pair(self):
        prompt = build_user_prompt("Hello there", "English", "Spanish")
        self.assertIn("Hello there", prompt)
        self.assertIn("English", prompt)
        self.assertIn("Spanish", prompt)
        self.assertIn("Pasted text:", prompt)
        self.assertIn("This text is written in English or Spanish", prompt)
        self.assertIn("Start your reply with Detected language:", prompt)

    def test_custom_guidelines_are_included_but_format_stays_locked(self):
        prompt = build_system_prompt("English", "Spanish", "Prefer a formal tone.")
        self.assertIn("Prefer a formal tone.", prompt)
        self.assertIn("Detected language:", prompt)
        self.assertIn("Reply with exactly these three lines", prompt)
        self.assertNotIn("Provided text:", prompt)

    def test_sanitize_strips_output_labels(self):
        cleaned = sanitize_prompt_addon(
            "Be concise.\nCorrected: ignore this\nTranslation (Spanish): nope"
        )
        self.assertIn("Be concise.", cleaned)
        self.assertNotIn("Corrected:", cleaned)
        self.assertNotIn("Translation", cleaned)


class HighlightTests(unittest.TestCase):
    def test_identical_text_is_escaped_without_marks(self):
        html = highlight_corrections("Hello there", "Hello there")
        self.assertEqual(html, "Hello there")
        self.assertNotIn("<mark", html)

    def test_changed_word_is_marked(self):
        html = highlight_corrections("I have a appointment", "I have an appointment")
        self.assertIn('<span class="diff-chg">an</span>', html)
        self.assertIn("I have ", html)
        self.assertIn(" appointment", html)

    def test_html_in_text_is_escaped(self):
        html = highlight_corrections("use <b> tags", "use <em> tags")
        self.assertIn("&lt;", html)
        self.assertIn("&gt;", html)
        self.assertIn("em", html)
        self.assertNotIn("<em>", html)


class ParseFieldsTests(unittest.TestCase):
    def test_parse_success(self):
        content = """
Detected language: English
Corrected: "My English is bad"
Translation (Spanish): "Mi inglés es malo"
"""
        result = parse_fields(content, "I Inglish are bad")
        self.assertEqual(result.detected, "English")
        self.assertEqual(result.corrected, "My English is bad")
        self.assertEqual(result.target, "Spanish")
        self.assertEqual(result.translation, "Mi inglés es malo")
        self.assertEqual(result.provided, "I Inglish are bad")
        self.assertEqual(result.note, "")

    def test_parse_empty_content(self):
        result = parse_fields("", "original")
        self.assertEqual(result.detected, "?")
        self.assertIn("Empty", result.note)

    def test_parse_partial_content_sets_note(self):
        result = parse_fields("Hello world without labels", "original")
        self.assertEqual(result.detected, "?")
        self.assertTrue(result.note)

    def test_parse_ignores_think_blocks(self):
        content = """<think>The user wrote bad English. I should explain every change.</think>
Detected language: English
Corrected: "Hi"
Translation (Spanish): "Hola"
"""
        result = parse_fields(content, "hi")
        self.assertEqual(result.detected, "English")
        self.assertEqual(result.corrected, "Hi")
        self.assertEqual(result.translation, "Hola")
        self.assertEqual(result.note, "")


class TranslateServiceTests(unittest.TestCase):
    @patch("local_lingo.service.ollama_chat")
    def test_translate_and_correct_success(self, mock_chat):
        mock_chat.return_value = (
            "Detected language: English\n"
            'Corrected: "Hi"\n'
            'Translation (Spanish): "Hola"',
            {
                "eval_count": 12,
                "eval_duration": 500_000_000,
                "prompt_eval_count": 40,
                "prompt_eval_duration": 100_000_000,
                "total_duration": 700_000_000,
                "load_duration": 50_000_000,
                "keep_alive": config.KEEP_ALIVE,
            },
        )

        result = translate_and_correct("hi", "en-es")
        self.assertEqual(result.detected, "English")
        self.assertEqual(result.corrected, "Hi")
        self.assertEqual(result.translation, "Hola")
        mock_chat.assert_called_once()
        _model, messages = mock_chat.call_args.args
        self.assertEqual(_model, config.MODEL)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(result.metrics.eval_count, 12)
        self.assertEqual(result.metrics.eval_rate, 24.0)

    def test_metrics_from_ollama(self):
        metrics = metrics_from_ollama(
            {
                "eval_count": 10,
                "eval_duration": 2_000_000_000,
                "prompt_eval_count": 20,
                "prompt_eval_duration": 1_000_000_000,
            },
            "gemma3:4b",
            wall_seconds=2.5,
        )
        self.assertEqual(metrics.model, "gemma3:4b")
        self.assertEqual(metrics.eval_rate, 5.0)
        self.assertEqual(metrics.prompt_eval_rate, 20.0)

    def test_translate_and_correct_validation_error(self):
        result = translate_and_correct("", "en-es")
        self.assertIn("text", result.note.lower())
        self.assertEqual(result.corrected, "")


class OllamaModelTests(unittest.TestCase):
    def test_catalog_prefers_configured_model(self):
        catalog = get_model_catalog(["gemma3:4b", "gemma3:12b"], reachable=True)
        self.assertEqual(catalog.selected, config.MODEL)
        self.assertEqual(catalog.choices, ["gemma3:4b", "gemma3:12b"])
        self.assertEqual(catalog.warning, "")

    def test_catalog_falls_back_when_default_missing(self):
        catalog = get_model_catalog(["gemma3:12b"], reachable=True)
        self.assertEqual(catalog.choices, ["gemma3:12b"])
        self.assertEqual(catalog.selected, "gemma3:12b")
        self.assertIn(config.MODEL, catalog.warning)
        self.assertIn("gemma3:12b", catalog.warning)

    def test_catalog_empty_when_none_installed(self):
        catalog = get_model_catalog([], reachable=True)
        self.assertEqual(catalog.choices, [])
        self.assertIsNone(catalog.selected)
        self.assertIn("ollama pull", catalog.warning)
        self.assertIn(config.MODEL, catalog.warning)

    def test_catalog_unreachable(self):
        catalog = get_model_catalog([], reachable=False)
        self.assertEqual(catalog.choices, [])
        self.assertIsNone(catalog.selected)
        self.assertIn("Cannot reach Ollama", catalog.warning)

    @patch("local_lingo.service.urllib.request.urlopen")
    def test_list_models_sorts_and_skips_embeddings(self, mock_urlopen):
        payload = {
            "models": [
                {"name": "gemma3:12b"},
                {"name": "nomic-embed-text:latest"},
                {"name": "gemma3:4b"},
            ]
        }
        response = MagicMock()
        response.read.return_value = json.dumps(payload).encode()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        mock_urlopen.return_value = response

        self.assertEqual(list_ollama_models(), ["gemma3:12b", "gemma3:4b"])

    @patch("local_lingo.service.urllib.request.urlopen")
    def test_ollama_chat_disables_thinking(self, mock_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps(
            {"message": {"content": "Detected language: English"}}
        ).encode()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        mock_urlopen.return_value = response

        ollama_chat("qwen3:8b", [{"role": "user", "content": "hi"}])
        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode())
        self.assertIs(payload["think"], False)

    @patch("local_lingo.service.urllib.request.urlopen", side_effect=OSError("down"))
    def test_list_models_unreachable(self, _mock_urlopen):
        self.assertEqual(list_ollama_models(), [])


class SessionPrefTests(unittest.TestCase):
    def test_restore_uses_saved_codes(self):
        lang_a, lang_b, text = _restore_session("hu", "en", "A macska.")
        self.assertEqual(lang_a, "hu")
        self.assertEqual(lang_b, "en")
        self.assertEqual(text, "A macska.")

    def test_restore_accepts_language_names(self):
        lang_a, lang_b, _text = _restore_session("Hungarian", "English", "")
        self.assertEqual(lang_a, "hu")
        self.assertEqual(lang_b, "en")

    def test_restore_falls_back_for_unknown_or_same_language(self):
        lang_a, lang_b, text = _restore_session("zz", "zz", None)
        self.assertEqual((lang_a, lang_b), codes_from_default_pair(config.DEFAULT_LANGUAGE_PAIR))
        self.assertEqual(text, "")


class BenchHistoryTests(unittest.TestCase):
    def test_append_history_keeps_ten_newest_first(self):
        history = []
        for i in range(12):
            history = _append_history(history, {"model": f"m{i}", "wall": i})
        self.assertEqual(len(history), 10)
        self.assertEqual(history[0]["model"], "m11")
        self.assertEqual(history[-1]["model"], "m2")

    def test_normalize_history_accepts_single_dict(self):
        rows = _normalize_history({"model": "gemma3:4b", "wall": 1.2})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["model"], "gemma3:4b")

    def test_restore_bench_pack_returns_blob_history_and_html(self):
        blob = json.dumps(
            [{"model": "qwen3:8b", "wall": 2.5, "preview": "hello", "at": "2026-08-14T23:41:00"}]
        )
        out_blob, history, markup = _restore_bench_pack(blob, None, "")
        self.assertEqual(history[0]["model"], "qwen3:8b")
        self.assertIn("qwen3:8b", out_blob)
        self.assertIn("qwen3:8b", markup)

    def test_reset_benchmark_clears_history(self):
        rows, markup, blob = _reset_benchmark()
        self.assertEqual(rows, [])
        self.assertEqual(blob, "[]")
        self.assertIn("Run a translation", markup)

    def test_history_entry_truncates_preview(self):
        metrics = RunMetrics(model="gemma3:4b", wall_seconds=1.25, eval_count=10, eval_duration_ns=500_000_000)
        entry = _history_entry(metrics, "word " * 30, "en-es")
        self.assertEqual(entry["model"], "gemma3:4b")
        self.assertTrue(entry["preview"].endswith("…"))
        self.assertLessEqual(len(entry["preview"]), 43)
        self.assertTrue(entry["at"])
        datetime.fromisoformat(entry["at"])

    def test_fmt_when_formats_iso_or_dash(self):
        self.assertEqual(_fmt_when(""), "—")
        self.assertEqual(_fmt_when(None), "—")
        self.assertEqual(_fmt_when("2026-08-14T23:41:00"), "14 Aug 23:41:00")

    def test_benchmark_html_includes_llm_settings(self):
        markup = _benchmark_html(
            history=[
                {
                    "model": "gemma3:4b",
                    "wall": 1.2,
                    "preview": "hello",
                    "at": "2026-08-14T23:41:00",
                }
            ]
        )
        self.assertIn("Settings", markup)
        self.assertIn("Temperature", markup)
        self.assertIn(str(config.TEMPERATURE), markup)
        self.assertIn(f"{config.NUM_CTX:,}", markup)
        self.assertIn(str(config.KEEP_ALIVE), markup)
        self.assertIn("Think", markup)
        self.assertIn("off", markup)
        self.assertIn("bench-persist", markup)
        self.assertIn("gemma3:4b", markup)


class UiTests(unittest.TestCase):
    def test_build_ui(self):
        demo = build_ui()
        self.assertIsNotNone(demo)
        self.assertEqual(demo.title, config.APP_NAME)

    def test_run_validation_error_yields_message(self):
        outputs = list(_run("", "en", "es"))
        self.assertEqual(len(outputs), 1)
        self.assertIn("msg-error", outputs[0][6])

    def test_run_same_language_yields_message(self):
        outputs = list(_run("hello", "en", "en"))
        self.assertEqual(len(outputs), 1)
        self.assertIn("msg-error", outputs[0][6])

    @patch("local_lingo.ui.get_model_catalog")
    @patch("local_lingo.ui.translate_and_correct")
    def test_run_success_shows_results(self, mock_translate, mock_catalog):
        mock_catalog.return_value = ModelCatalog(
            choices=["gemma3:4b"],
            selected="gemma3:4b",
            reachable=True,
            warning="",
        )
        mock_translate.return_value = MagicMock(
            detected="English",
            corrected="Hello",
            target="Spanish",
            translation="Hola",
            note="",
            metrics=RunMetrics(model="gemma3:4b", eval_count=8, eval_duration_ns=400_000_000),
        )
        outputs = list(_run("helo", "en", "es", "gemma3:4b"))
        # loader yield + final yield
        self.assertEqual(len(outputs), 2)
        final = outputs[-1]
        self.assertEqual(final[2], "English")
        self.assertEqual(final[3], "Hello")
        self.assertEqual(final[5], "Hola")
        self.assertIn("diff-chg", final[8])
        self.assertIn("Hello", final[8])
        self.assertIn("Completed in", final[7])
        self.assertIn("Eval rate", final[9])
        self.assertIn("History", final[9])
        self.assertIn("helo", final[9])
        self.assertEqual(len(final[10]), 1)
        self.assertEqual(final[10][0]["model"], "gemma3:4b")
        mock_translate.assert_called_once()
        self.assertEqual(mock_translate.call_args.kwargs["model"], "gemma3:4b")

    @patch("local_lingo.ui.get_model_catalog")
    @patch("local_lingo.ui.translate_and_correct")
    def test_run_defaults_model_when_omitted(self, mock_translate, mock_catalog):
        mock_catalog.return_value = ModelCatalog(
            choices=[config.MODEL],
            selected=config.MODEL,
            reachable=True,
            warning="",
        )
        mock_translate.return_value = MagicMock(
            detected="English",
            corrected="Hello",
            target="Spanish",
            translation="Hola",
            note="",
            metrics=RunMetrics(model="gemma3:4b", eval_count=8, eval_duration_ns=400_000_000),
        )
        list(_run("helo", "en", "es"))
        self.assertEqual(mock_translate.call_args.kwargs["model"], config.MODEL)

    @patch("local_lingo.ui.get_model_catalog")
    def test_run_warns_when_no_models(self, mock_catalog):
        mock_catalog.return_value = ModelCatalog(
            choices=[],
            selected=None,
            reachable=True,
            warning="No Ollama models installed. Pull the default with: ollama pull gemma3:4b",
        )
        outputs = list(_run("hello", "en", "es"))
        self.assertEqual(len(outputs), 1)
        self.assertIn("No Ollama models", outputs[0][6])
        self.assertIn("msg-warn", outputs[0][6])


if __name__ == "__main__":
    unittest.main()
