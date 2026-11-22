"""Mistral AI deck generator for Anki."""

from __future__ import annotations

import json
import random
import re
import threading
import urllib.error
import urllib.request
from collections import Counter

from aqt import mw
from aqt.qt import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QComboBox,
    QVBoxLayout,
    qconnect,
)
from aqt.utils import showInfo, showWarning

MENU_LABEL = "Mistral AI: Create Deck from Prompt..."
TAG = "ai-generated"
NO_SOURCE = "(none - prompt only)"
FOLLOW_SOURCE = "(same as style-reference deck)"
JSON_HINT = '{"deck_name": "...", "cards": [{"Field": "value", ...}]}'


def _conf() -> dict:
    return mw.addon_manager.getConfig(__name__) or {}


# ---------------------------------------------------------------- API helpers

def _post_json(url: str, api_key: str, payload: dict, timeout: int = 180) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "replace")[:500]
        except Exception:
            detail = ""
        raise RuntimeError(f"HTTP {e.code} from Mistral API: {detail}") from e


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in the model response.")
    return json.loads(text[start : end + 1])


# ------------------------------------------------------------ deck inspection

def _deck_note_ids(deck_name: str) -> list:
    return list(mw.col.find_notes(f'deck:"{deck_name}"'))


def _dominant_notetype(deck_name: str):
    nids = _deck_note_ids(deck_name)
    if not nids:
        return None
    sample = random.sample(nids, min(len(nids), 50))
    counts = Counter(mw.col.get_note(nid).mid for nid in sample)
    return mw.col.models.get(counts.most_common(1)[0][0])


def _sample_examples(deck_name: str, count: int, model) -> list:
    """Sample real notes from a deck so the AI can imitate their style."""
    nids = _deck_note_ids(deck_name)
    if not nids:
        return []
    nids = random.sample(nids, min(len(nids), max(1, count)))
    examples = []
    for nid in nids:
        note = mw.col.get_note(nid)
        if model is not None and note.mid != model["id"]:
            continue
        fields = {}
        for fld in model["flds"] if model is not None else []:
            name = fld["name"]
            if name in note:
                fields[name] = note[name]
        examples.append({"fields": fields, "tags": [t for t in note.tags][:5]})
    return examples


# ------------------------------------------------------------ prompt building

def _build_messages(prompt: str, examples: list, field_names: list,
                    is_cloze: bool, n_cards: int, deck_hint: str) -> list:
    field_desc = ", ".join(f'"{f}"' for f in field_names)
    system_lines = [
        "You are an expert Anki flashcard author.",
        "Create high-quality, atomic flashcards: one clear fact or question per card.",
        "Match the tone, language, formatting and level of detail of the EXAMPLE cards exactly.",
        "Output ONLY a valid JSON object, no extra text, with this exact shape: "
        + JSON_HINT,
        f'Use exactly these field names in every card: {field_desc}.',
        "Also propose a short, clear deck_name (3-6 words).",
    ]
    if is_cloze:
        system_lines += [
            "These are cloze cards: the main field must contain {{c1::...}} deletions,",
            "and the deletion number must increase across cards (c1, c2, c3, ...).",
            "You may include multiple deletions in one card.",
        ]
    else:
        system_lines += [
            "Write clear questions in the first field and concise answers in the later fields.",
            "Never put the answer inside the question field.",
        ]
    if deck_hint:
        system_lines.append(f'The deck should be about: {deck_hint}.')

    user_lines = [
        f"Create {n_cards} flashcards.",
        "",
        "EXAMPLE cards from the user's collection (imitate their style):",
    ]
    if examples:
        for ex in examples:
            user_lines.append(json.dumps(ex, ensure_ascii=False))
    else:
        user_lines.append("(no examples available - use best Anki practices)")
    user_lines += ["", "USER PROMPT:", prompt]

    return [
        {"role": "system", "content": "\n".join(system_lines)},
        {"role": "user", "content": "\n".join(user_lines)},
    ]


# ------------------------------------------------------------------- dialogs

class GeneratorDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Mistral AI — Create Deck from Prompt")
        self.setMinimumWidth(640)
        self._busy = False

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlaceholderText(
            "Describe the deck you want, e.g.\n"
            "\"Italian cooking vocabulary, basic to intermediate, "
            "same style as my Spanish food deck.\""
        )
        self.prompt_edit.setMinimumHeight(90)
        form.addRow("Prompt:", self.prompt_edit)

        self.source_combo = QComboBox()
        self.source_combo.addItem(NO_SOURCE)
        for name in sorted(mw.col.decks.all_names()):
            self.source_combo.addItem(name)
        form.addRow("Imitate style of deck:", self.source_combo)

        self.nt_combo = QComboBox()
        self.nt_combo.addItem(FOLLOW_SOURCE)
        for name in sorted(mw.col.models.all_names()):
            self.nt_combo.addItem(name)
        form.addRow("Note type:", self.nt_combo)

        self.deck_edit = QLineEdit()
        self.deck_edit.setPlaceholderText("(empty = let the AI name it)")
        form.addRow("Target deck name:", self.deck_edit)

        self.count_edit = QLineEdit("20")
        form.addRow("Number of cards:", self.count_edit)

        layout.addLayout(form)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        self.generate_btn = QPushButton("Generate")
        self.button_box.addButton(
            self.generate_btn, QDialogButtonBox.ButtonRole.ActionRole
        )
        qconnect(self.generate_btn.clicked, self._on_generate)
        qconnect(self.button_box.rejected, self.reject)
        layout.addWidget(self.button_box)

    # ---------------------------------------------------------------- helpers

    def _status(self, text: str) -> None:
        self.status_label.setText(text)

    def reject(self) -> None:
        if self._busy:
            showWarning("Still generating, please wait a moment.")
            return
        super().reject()

    # ---------------------------------------------------------------- generate

    def _on_generate(self) -> None:
        conf = _conf()
        api_key = (conf.get("api_key") or "").strip()
        if not api_key:
            showWarning(
                "No API key configured.\n\n"
                "Open Tools > Add-ons > Mistral AI Deck Generator > Config\n"
                "and paste your key from console.mistral.ai."
            )
            return
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            showWarning("Describe what the deck should contain first.")
            return
        try:
            count = int(self.count_edit.text().strip())
        except ValueError:
            showWarning("Number of cards must be a whole number.")
            return
        count = max(1, min(count, int(conf.get("max_cards", 60))))

        source = self.source_combo.currentText()
        src_model = None
        examples = []
        if source != NO_SOURCE:
            src_model = _dominant_notetype(source)
            examples = _sample_examples(
                source, int(conf.get("sample_count", 6)), src_model
            )

        note_type_name = self.nt_combo.currentText()
        if note_type_name == FOLLOW_SOURCE:
            note_type_name = src_model["name"] if src_model else "Basic"
        model = mw.col.models.by_name(note_type_name)
        if model is None:
            model = mw.col.models.by_name("Basic")
        if model is None:
            model = mw.col.models.all()[0]

        field_names = [f["name"] for f in model["flds"]]
        is_cloze = int(model.get("type", 0)) == 1
        self._resolved_model = model
        self._resolved_cloze = is_cloze

        payload = {
            "model": conf.get("model", "mistral-small-latest"),
            "messages": _build_messages(
                prompt,
                examples,
                field_names,
                is_cloze,
                count,
                self.deck_edit.text().strip(),
            ),
            "temperature": float(conf.get("temperature", 0.7)),
        }
        base_url = (conf.get("base_url", "https://api.mistral.ai/v1")).rstrip("/")

        self._busy = True
        self.generate_btn.setEnabled(False)
        self._status("Generating cards with Mistral, this can take up to a minute...")
        threading.Thread(
            target=self._worker, args=(base_url, api_key, payload), daemon=True
        ).start()

    def _worker(self, base_url: str, api_key: str, payload: dict) -> None:
        self._result = None
        self._error = None
        try:
            data = _post_json(base_url + "/chat/completions", api_key, payload)
            text = data["choices"][0]["message"]["content"]
            self._result = _extract_json(text)
        except Exception as e:  # noqa: BLE001 - show any failure to the user
            self._error = str(e)
        try:
            mw.taskman.run_on_main(self._on_finished)
        except Exception:
            pass

    def _on_finished(self) -> None:
        self._busy = False
        self.generate_btn.setEnabled(True)
        self._status("")
        if self._error is not None:
            showWarning(f"Generation failed:\n\n{self._error}")
            return
        PreviewDialog(
            self, self._result, self.deck_edit.text().strip(),
            self._resolved_model, self._resolved_cloze,
        ).exec()


class PreviewDialog(QDialog):
    def __init__(self, parent, data: dict, user_deck_name: str, model, is_cloze: bool):
        super().__init__(parent)
        cards = data.get("cards") or []
        suggested = (data.get("deck_name") or "").strip()
        prefix = (_conf().get("deck_prefix") or "AI").strip() or "AI"
        default_name = user_deck_name or suggested or f"{prefix} Generated"

        self.setWindowTitle("Mistral AI — Review generated cards")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.deck_edit = QLineEdit(default_name)
        form.addRow("Deck name:", self.deck_edit)
        self.info_label = QLabel(f"{len(cards)} cards generated. Review them, then click Add.")
        self.info_label.setWordWrap(True)
        layout.addLayout(form)
        layout.addWidget(self.info_label)

        self.cards_text = QPlainTextEdit()
        self.cards_text.setReadOnly(True)
        self.cards_text.setPlainText(self._render(cards))
        layout.addWidget(self.cards_text)

        self._cards = cards
        self._model = model
        self._is_cloze = is_cloze
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Add to Anki")
        qconnect(buttons.accepted, self._on_accept)
        qconnect(buttons.rejected, self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _render(cards: list) -> str:
        lines = []
        for i, card in enumerate(cards, 1):
            lines.append(f"--- Card {i} ---")
            for key, value in card.items():
                text = json.dumps(value, ensure_ascii=False) if isinstance(
                    value, (dict, list)
                ) else str(value)
                lines.append(f"{key}: {text}")
            lines.append("")
        return "\n".join(lines)

    def _on_accept(self) -> None:
        deck_name = self.deck_edit.text().strip() or "AI Generated"
        added, skipped = self._add_cards(deck_name)
        self.accept()
        if added:
            showInfo(f"Added {added} cards to '{deck_name}'.\n"
                     f"Cards are tagged '{TAG}' so you can find or remove them easily."
                     + (f"\n({skipped} unusable cards were skipped.)" if skipped else ""))
        else:
            showWarning("No cards could be added.")

    def _add_cards(self, deck_name: str):
        deck_id = mw.col.decks.id(deck_name, create=True)
        if not self._cards:
            return 0, 0
        model = self._model
        field_names = [f["name"] for f in model["flds"]]
        is_cloze = self._is_cloze

        added = skipped = 0
        for card in self._cards:
            note = mw.col.new_note(model)
            filled = False
            for fname in field_names:
                if fname not in card:
                    continue
                value = card[fname]
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                if value is None:
                    continue
                note[fname] = str(value)
                filled = True
            if not filled:
                skipped += 1
                continue
            if is_cloze and not re.search(r"{{c\d+::", note[field_names[0]]):
                skipped += 1
                continue
            note.add_tag(TAG)
            try:
                mw.col.add_note(note, deck_id)
                added += 1
            except Exception:
                skipped += 1
        return added, skipped


# ------------------------------------------------------------------ bootstrap

def _open_dialog() -> None:
    if mw.col is None:
        showWarning("Open a profile first.")
        return
    GeneratorDialog(mw).exec()


def _setup_menu() -> None:
    action = mw.form.menuTools.addAction(MENU_LABEL)
    qconnect(action.triggered, _open_dialog)


_setup_menu()
