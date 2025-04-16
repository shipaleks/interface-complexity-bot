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
| `WEBHOOK_MODE` | Set to `true` to force webhook mode (recommended for production) |
| `WEBHOOK_URL` | (Optional) Complete URL for the webhook (e.g., https://yourdomain.com/telegram_token) |
| `PORT` | Port for the webhook server (defaults to 8443) |

## Deployment on Railway

1. Fork or clone this repository
2. Connect your GitHub repo to Railway
3. Add the required environment variables in Railway's dashboard:
   - `TELEGRAM_TOKEN`: Your Telegram bot token
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `WEBHOOK_MODE`: Set to `true`
4. Deploy!

The bot will use webhooks in production (when `WEBHOOK_MODE` is true) and polling in development.

## Avoiding Multiple Instances

If you see the error `Conflict: terminated by other getUpdates request`, it means multiple instances of your bot are running. To fix this:

1. Make sure `WEBHOOK_MODE` is set to `true` in your Railway environment
2. Check that only one service is running
3. Restart the service if needed

## Local Development

To run the bot locally:

1. Clone the repository
2. Create a `.env` file with your environment variables
3. Install dependencies: `pip install -r requirements.txt`
4. Run the bot: `python bot.py`

In local development mode, the bot will use polling by default. 