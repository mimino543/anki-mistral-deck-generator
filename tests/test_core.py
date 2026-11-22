"""Unit tests for the pure/helper parts of the add-on.

The add-on imports `aqt` at module load, so we stub it before importing
`__init__.py` as a standalone module. Run with:
    python3 -m unittest discover -s tests -v
"""

import importlib.util
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_addon():
    aqt = types.ModuleType("aqt")
    aqt.mw = mock.MagicMock()
    qt = types.ModuleType("aqt.qt")
    for name in (
        "QDialog", "QDialogButtonBox", "QFormLayout", "QLabel", "QLineEdit",
        "QPlainTextEdit", "QPushButton", "QComboBox", "QVBoxLayout",
    ):
        setattr(qt, name, type(name, (), {}))
    qt.qconnect = lambda *args, **kwargs: None
    utils = types.ModuleType("aqt.utils")
    utils.showInfo = lambda *args, **kwargs: None
    utils.showWarning = lambda *args, **kwargs: None
    aqt.qt = qt
    aqt.utils = utils
    sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils})
    spec = importlib.util.spec_from_file_location("anki_addon", REPO_ROOT / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


addon = _load_addon()


class ExtractJsonTests(unittest.TestCase):
    def test_plain_json(self):
        self.assertEqual(addon._extract_json('{"a": 1}'), {"a": 1})

    def test_fenced_json(self):
        text = 'Here you go:\n```json\n{"deck_name": "X", "cards": []}\n```'
        self.assertEqual(addon._extract_json(text)["deck_name"], "X")

    def test_json_embedded_in_prose(self):
        text = 'Sure! {"cards": [{"Q": "a } b"}]} hope that helps'
        self.assertEqual(addon._extract_json(text), {"cards": [{"Q": "a } b"}]})

    def test_no_json_raises(self):
        with self.assertRaises(ValueError):
            addon._extract_json("no json here")


class BuildMessagesTests(unittest.TestCase):
    def test_basic_fields_and_prompt(self):
        msgs = addon._build_messages("italian food", [], ["Front", "Back"], False, 5, "")
        system = msgs[0]["content"]
        self.assertIn('"Front"', system)
        self.assertIn('"Back"', system)
        self.assertNotIn("c1::", system)
        user = msgs[1]["content"]
        self.assertIn("Create 5 flashcards.", user)
        self.assertIn("italian food", user)

    def test_cloze_instructions_and_hint(self):
        msgs = addon._build_messages("x", [], ["Text"], True, 3, "history")
        system = msgs[0]["content"]
        self.assertIn("{{c1::", system)
        self.assertIn("history", system)

    def test_examples_included(self):
        ex = [{"fields": {"Front": "q"}, "tags": ["t"]}]
        msgs = addon._build_messages("x", ex, ["Front"], False, 1, "")
        self.assertIn('"Front": "q"', msgs[1]["content"])


class ConfigHelperTests(unittest.TestCase):
    def test_conf_int_default(self):
        self.assertEqual(addon._conf_int({}, "max_cards", 60, 1, 500), 60)

    def test_conf_int_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            addon._conf_int({"max_cards": 9999}, "max_cards", 60, 1, 60)

    def test_conf_int_invalid_raises(self):
        with self.assertRaises(ValueError):
            addon._conf_int({"max_cards": "lots"}, "max_cards", 60, 1, 60)

    def test_conf_float_invalid_raises(self):
        with self.assertRaises(ValueError):
            addon._conf_float({"temperature": "hot"}, "temperature", 0.7, 0.0, 2.0)

    def test_conf_float_ok(self):
        self.assertEqual(addon._conf_float({"temperature": "0.3"}, "temperature", 0.7, 0.0, 2.0), 0.3)

    def test_base_url_https_ok(self):
        self.assertEqual(
            addon._validate_base_url("https://api.mistral.ai/v1/"),
            "https://api.mistral.ai/v1",
        )

    def test_base_url_http_rejected(self):
        with self.assertRaises(ValueError):
            addon._validate_base_url("http://api.mistral.ai/v1")

    def test_base_url_localhost_http_allowed(self):
        self.assertEqual(
            addon._validate_base_url("http://localhost:8080/v1"),
            "http://localhost:8080/v1",
        )


class ManifestTests(unittest.TestCase):
    """Mirror Anki's _manifest_schema (qt/aqt/addons.py): 'package' and 'name'
    are required strings; 'package' must be a plain folder name."""

    def test_manifest_matches_anki_schema(self):
        manifest = json.loads((REPO_ROOT / "manifest.json").read_text("utf-8"))
        self.assertIsInstance(manifest.get("package"), str)
        self.assertTrue(manifest["package"])
        self.assertEqual(os.path.basename(manifest["package"]), manifest["package"])
        self.assertIsInstance(manifest.get("name"), str)
        self.assertTrue(manifest["name"])
        for key in ("human_version", "homepage"):
            if key in manifest:
                self.assertIsInstance(manifest[key], str)


class DeckSearchTests(unittest.TestCase):
    def test_deck_name_quotes_escaped(self):
        addon.mw.col.find_notes.return_value = []
        addon._deck_note_ids('My "Weird" Deck')
        query = addon.mw.col.find_notes.call_args[0][0]
        self.assertEqual(query, 'deck:"My \\"Weird\\" Deck"')


if __name__ == "__main__":
    unittest.main()
