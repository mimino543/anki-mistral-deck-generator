# Mistral AI Deck Generator

Creates new Anki decks from a text prompt, and can imitate the style of your
existing decks by sampling real cards from them.

## Settings

- **api_key** (required): Your Mistral API key. Create one at
  https://console.mistral.ai (API Keys page) and paste it here.
- **base_url**: Mistral API endpoint. Only change this if you use a proxy.
  Should end with `/v1`.
- **model**: Any Mistral chat model, e.g. `mistral-small-latest` (fast, cheap,
  good for cards) or `mistral-large-latest` (higher quality).
- **temperature**: 0.0 = conservative and factual, 0.7 = more creative. For
  factual_subjects, consider lowering to 0.2-0.3.
- **sample_count**: How many cards from the reference deck are shown to the AI
  as style examples. 4-8 is usually enough.
- **max_cards**: Upper limit on the card count per generation.
- **deck_prefix**: Prefix used when the AI invents the deck name.

## Usage

1. Tools > Mistral AI: Create Deck from Prompt...
2. Describe the deck you want.
3. Optionally pick a deck to imitate and a note type.
4. Generate, review the cards, then Add to Anki.

All generated cards get the tag `ai-generated` so you can find them in the
browser (search `tag:ai-generated`) or bulk-delete them if needed.
