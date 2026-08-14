"""Automated tests for LocalLingo."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from local_lingo import config
from local_lingo.languages import (
    CODE_TO_NAME,
    LANGUAGE_CHOICES,
    codes_from_default_pair,
    name_for_code,
)
from local_lingo.prompts import build_system_prompt, build_user_prompt
from local_lingo.service import (
    ModelCatalog,
    get_model_catalog,
    list_ollama_models,
    parse_fields,
    translate_and_correct,
)
from local_lingo.ui import build_ui, _run
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
        self.assertEqual(config.APP_NAME, "LocalLingo")

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
        self.assertIn("Never put the translation into Corrected", prompt)
        self.assertIn('Translation (Spanish): "Hola, ¿cómo estás hoy?"', prompt)
        self.assertNotIn("en-es", prompt)

    def test_user_prompt_includes_text_and_pair(self):
        prompt = build_user_prompt("Hello there", "English", "Spanish")
        self.assertIn("Hello there", prompt)
        self.assertIn("English", prompt)
        self.assertIn("Spanish", prompt)


class ParseFieldsTests(unittest.TestCase):
    def test_parse_success(self):
        content = """
Provided text: "I Inglish are bad"
Detected language: English
Corrected: "My English is bad"
Translation (Spanish): "Mi inglés es malo"
"""
        result = parse_fields(content, "I Inglish are bad")
        self.assertEqual(result.detected, "English")
        self.assertEqual(result.corrected, "My English is bad")
        self.assertEqual(result.target, "Spanish")
        self.assertEqual(result.translation, "Mi inglés es malo")
        self.assertEqual(result.note, "")

    def test_parse_empty_content(self):
        result = parse_fields("", "original")
        self.assertEqual(result.detected, "?")
        self.assertIn("Empty", result.note)

    def test_parse_partial_content_sets_note(self):
        result = parse_fields("Hello world without labels", "original")
        self.assertEqual(result.detected, "?")
        self.assertTrue(result.note)


class TranslateServiceTests(unittest.TestCase):
    @patch("local_lingo.service._client")
    def test_translate_and_correct_success(self, mock_client_factory):
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=(
                            'Provided text: "hi"\n'
                            "Detected language: English\n"
                            'Corrected: "Hi"\n'
                            'Translation (Spanish): "Hola"'
                        )
                    )
                )
            ]
        )

        result = translate_and_correct("hi", "en-es")
        self.assertEqual(result.detected, "English")
        self.assertEqual(result.corrected, "Hi")
        self.assertEqual(result.translation, "Hola")
        mock_client.chat.completions.create.assert_called_once()
        kwargs = mock_client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["extra_body"]["keep_alive"], config.KEEP_ALIVE)
        self.assertEqual(kwargs["extra_body"]["options"]["num_ctx"], config.NUM_CTX)

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

    @patch("local_lingo.service.urllib.request.urlopen", side_effect=OSError("down"))
    def test_list_models_unreachable(self, _mock_urlopen):
        self.assertEqual(list_ollama_models(), [])


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
        )
        outputs = list(_run("helo", "en", "es", "gemma3:4b"))
        # loader yield + final yield
        self.assertEqual(len(outputs), 2)
        final = outputs[-1]
        self.assertEqual(final[2], "English")
        self.assertEqual(final[3], "Hello")
        self.assertEqual(final[5], "Hola")
        self.assertIn("Completed in", final[7])
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
