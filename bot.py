#!/usr/bin/env python3
"""
Entry point for Railway deployment.
This file imports and runs the main Telegram bot.
"""

import logging
from init_dirs import init_directories

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize directories first
logger.info("Starting directory initialization...")
init_directories()
logger.info("Directory initialization completed")

# Re-export all from telegram_bot
from telegram_bot import *

if __name__ == "__main__":
    try:
        # Run the main function from telegram_bot
        logger.info("Starting Telegram bot...")
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Fatal error in bot.py: {e}", exc_info=True)
