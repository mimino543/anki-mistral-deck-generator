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

1. Download `mistral_deck_generator.ankiaddon` from the
   [releases page](../../releases) — it is built automatically from the repo
   sources whenever a release is published
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

## Making a release

Two ways, both fully automated:

**Option A — one click from the Actions tab:**
1. Go to **Actions > Build .ankiaddon > Run workflow**
2. Enter the tag (e.g. `v1.0.0`) and click **Run workflow**
3. The workflow creates the tag, publishes the release, and attaches the
   built `mistral_deck_generator.ankiaddon` automatically

**Option B — draft on GitHub:**
1. Go to **Releases > Draft a new release**
2. Tag a version (e.g. `v1.0.0`) and publish it
3. The [Build workflow](.github/workflows/build.yml) packages the add-on and
   attaches `mistral_deck_generator.ankiaddon` to that release

## Build the .ankiaddon yourself

The add-on folder is the repo root (`__init__.py`, `config.json`,
`config.md`, `manifest.json`). Zip those files and rename the zip to
`mistral_deck_generator.ankiaddon`:

```sh
zip mistral_deck_generator.ankiaddon __init__.py config.json config.md manifest.json
```

## Development

Run the unit tests (they stub out `aqt`, so no Anki installation is needed):

```sh
python3 -m unittest discover -s tests -v
```

Tests also run automatically on every push and pull request via the
[Tests workflow](.github/workflows/test.yml).

## Requirements

- Anki 2.1.50+ (works on 23.x/24.x/25.x and 26.x)
- A Mistral API key

## License

MIT © Mark Matskin
