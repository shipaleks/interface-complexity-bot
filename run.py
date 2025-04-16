#!/usr/bin/env python3
import os
import sys
import logging
import traceback
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set."""
    load_dotenv()
    
    # Check for required environment variables
    required_vars = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY', 'GEMINI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set them in .env file or environment")
        
        # For Railway deployment, we want to log but not exit
        if 'RAILWAY_ENVIRONMENT' not in os.environ:
            return False
    
    return True

def create_required_directories():
    """Create required directories if they don't exist."""
    dirs = [
        'output',
        'output/images',
        'output/reports',
        'output/data',
        'prompts',
        'temp_files'
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def main():
    """Main function to run the bot."""
    try:
        logger.info("Starting UI Complexity Analyzer Bot")
        
        # Check environment variables
        if not check_environment():
            return 1
        
        # Create required directories
        create_required_directories()
        
        # Import here to avoid circular imports
        from bot import main as run_bot
        
        # Run the bot
        run_bot()
        
        return 0
    
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 