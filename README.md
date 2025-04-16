# Interface Complexity Analyzer Bot

This Telegram bot analyzes interface screenshots using OpenAI's GPT-4.1 model to provide a comprehensive analysis of the UI's complexity.

## Features

- Analyzes UI screenshots using GPT-4.1
- Provides detailed feedback on interface complexity
- Optional description and user flow context
- Can be deployed to Railway with webhooks

## Environment Variables

You need to set the following environment variables:

| Variable | Description |
|----------|-------------|
| `TELEGRAM_TOKEN` | Your Telegram bot token from BotFather |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `FIREBASE_CRED_PATH` | (Optional) Path to Firebase credentials file for usage stats |
| `RAILWAY_STATIC_URL` | The URL of your Railway deployment (set automatically by Railway) |
| `PORT` | Port for the webhook server (defaults to 8443) |

## Deployment on Railway

1. Fork or clone this repository
2. Connect your GitHub repo to Railway
3. Add the required environment variables in Railway's dashboard
4. Deploy!

The bot will automatically detect it's running on Railway and will use webhooks instead of polling.

## Local Development

To run the bot locally:

1. Clone the repository
2. Create a `.env` file with your environment variables
3. Install dependencies: `pip install -r requirements.txt`
4. Run the bot: `python bot.py`

In local development mode, the bot will use polling instead of webhooks. 