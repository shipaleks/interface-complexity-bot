#!/usr/bin/env python3
"""
Entry point for Railway deployment.
This file imports and runs the main Telegram bot.
"""

# Re-export all from telegram_bot
from telegram_bot import *

if __name__ == "__main__":
    # Run the main function from telegram_bot
    asyncio.run(main())
