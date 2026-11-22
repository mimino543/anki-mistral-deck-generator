# Anki Mistral AI Deck Generator

An [Anki](https://apps.ankiweb.net/) add-on that creates flashcard decks from a
text prompt using the [Mistral AI API](https://mistral.ai) — including the
ability to **imitate the style of your existing decks**.

## Features

- **Prompt to deck**: describe what you want, get a full deck of cards
- **Style matching**: optionally pick one of your decks — the add-on samples
  real cards from it and tells the AI to imitate their tone, formatting and
  level of detail
- **Note type aware**: works with Basic, Cloze and your custom note types;
  for cloze cards it generates proper `{{c1::...}}` deletions
- **Review before adding**: every generation opens a preview window so you
  can check the cards (and rename the deck) before anything is saved
- **Background API calls**: Anki never freezes while generating
- **Safety tag**: every generated card is tagged `ai-generated`, so you can
  find them in the browser (`tag:ai-generated`) or bulk-delete them

## Install

1. Download or build `mistral_deck_generator.ankiaddon` (a zip of
   `__init__.py`, `config.json`, `config.md`)
2. In Anki: **Tools > Add-ons > Install from file** (or double-click the file)
3. Restart Anki

## Configure

**Tools > Add-ons > Mistral AI Deck Generator > Config**

| Key | Description | Default |
| --- | --- | --- |
| `api_key` | Your Mistral API key from [console.mistral.ai](https://console.mistral.ai) | *(empty)* |
| `base_url` | Mistral API endpoint | `https://api.mistral.ai/v1` |
| `model` | Any Mistral chat model, e.g. `mistral-small-latest` or `mistral-large-latest` | `mistral-small-latest` |
| `temperature` | 0.0 factual - 1.0 creative | `0.7` |
| `sample_count` | Cards sampled from the reference deck as style examples | `6` |
| `max_cards` | Upper limit on cards per generation | `60` |
| `deck_prefix` | Prefix used when the AI invents the deck name | `AI` |

## Usage

1. **Tools > Mistral AI: Create Deck from Prompt...**
2. Describe the deck you want, e.g.
   *"Italian cooking vocabulary, basic to intermediate, same style as my Spanish food deck."*
3. Optionally select a deck to imitate and/or a note type
4. Click **Generate**, review the cards, then **Add to Anki**

## Build the .ankiaddon yourself

The add-on folder is the repo root (`__init__.py`, `config.json`,
`config.md`). Zip those three files and rename the zip to
`mistral_deck_generator.ankiaddon`:

```sh
zip mistral_deck_generator.ankiaddon __init__.py config.json config.md
```

## Requirements

- Anki 2.1.50+ (23.x/24.x recommended)
- A Mistral API key

## License

MIT © Mark Matskin
