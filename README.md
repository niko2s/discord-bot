# Discord Bot

A Discord bot built with [discord.py](https://github.com/Rapptz/discord.py).

Containerised with Docker and deployed to AWS EC2. Infrastructure is managed with Terraform; GitHub Actions builds and deploys on every push to `main`.

## Commands

| Command | Description |
|---|---|
| `/triviaquiz` | Multiplayer trivia with configurable category, difficulty, and question count ([Open Trivia DB](https://opentdb.com/)) |
| `/quiz` | Quick single-player trivia ([The Trivia API](https://the-trivia-api.com/)) |
| `/ai` | Chat and image generation via OpenAI-compatible APIs |
| `/dictionary` | Definitions, pronunciation, synonyms, antonyms ([Free Dictionary API](https://dictionaryapi.dev/)) |
| `/urban` | Slang and informal word lookup ([Urban Dictionary](https://rapidapi.com/archergardinersheridan/api/urban-dictionary7)) |
| `/cat` | Random cat image ([The Cat API](https://thecatapi.com)) |
| `/resize` | Scale images by percentage or to a specific pixel dimension |

## Local Development

1. Register a bot on the [Discord Developer Portal](https://discord.com/developers/applications)
2. Copy `.env.example` to `.env` and fill in your credentials
3. Run `docker compose up`
4. Type `/` in any channel the bot has access to, to browse all commands
