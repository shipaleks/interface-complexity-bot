#!/usr/bin/env python3
import os
import sys
import subprocess
import pkg_resources
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_python_version():
    """Check if Python version is at least 3.8."""
    required_version = (3, 8)
    current_version = sys.version_info
    
    if current_version < required_version:
        logger.error(f"Python {required_version[0]}.{required_version[1]} or higher is required. "
                     f"You are using Python {current_version[0]}.{current_version[1]}.{current_version[2]}")
        return False
    
    return True

def check_dependencies():
    """Check if all required packages are installed."""
    with open("requirements.txt", "r") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    missing_packages = []
    
    for req in requirements:
        # Skip markers like 'package; python_version > "3.6"'
        if ";" in req:
            req = req.split(";")[0].strip()
        
        # Skip version specifiers
        if "==" in req:
            req = req.split("==")[0].strip()
        elif ">=" in req:
            req = req.split(">=")[0].strip()
        elif "<=" in req:
            req = req.split("<=")[0].strip()
        
        try:
            pkg_resources.get_distribution(req)
        except pkg_resources.DistributionNotFound:
            missing_packages.append(req)
    
    if missing_packages:
        logger.warning(f"Missing required packages: {', '.join(missing_packages)}")
        logger.warning("You can install them with: pip install -r requirements.txt")
        return False
    
    return True

def check_environment_variables():
    """Check if required environment variables are available."""
    # Check if .env file exists
    if not os.path.exists(".env"):
        logger.warning("No .env file found. Checking if example file exists...")
        
        if os.path.exists(".env.example"):
            logger.info("Found .env.example file. Creating .env file from example...")
            with open(".env.example", "r") as example, open(".env", "w") as env:
                env.write(example.read())
            logger.info("Created .env file. Please edit it to add your API keys.")
        else:
            logger.warning("No .env.example file found. Creating a basic .env file...")
            with open(".env", "w") as f:
                f.write("# API Keys\n")
                f.write("OPENAI_API_KEY=your_openai_api_key_here\n")
                f.write("GEMINI_API_KEY=your_gemini_api_key_here\n")
                f.write("TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here\n")
            logger.info("Created basic .env file. Please edit it to add your API keys.")
    
    # Remind about required variables
    logger.info("Required environment variables in .env file:")
    logger.info("- OPENAI_API_KEY: Your OpenAI API key")
    logger.info("- GEMINI_API_KEY: Your Google Gemini API key")
    logger.info("- TELEGRAM_BOT_TOKEN: Your Telegram Bot token")
    
    return True

def create_required_directories():
    """Create required directories if they don't exist."""
    directories = [
        "output",
        "output/images",
        "output/reports",
        "output/data",
        "prompts",
        "temp_files"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.info(f"Created directory: {directory}")
    
    return True

def check_latex():
    """Check if LaTeX is installed for PDF generation."""
    try:
        subprocess.run(
            ["pdflatex", "--version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            check=True
        )
        logger.info("LaTeX is installed. PDF generation will be available.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("LaTeX (pdflatex) is not installed or not in PATH.")
        logger.warning("PDF report generation will not work without LaTeX.")
        logger.warning("On Ubuntu/Debian, you can install it with: sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-fonts-extra texlive-latex-extra")
        logger.warning("On macOS with Homebrew, use: brew install --cask mactex")
        logger.warning("On Windows, install MiKTeX or TeX Live.")
        return False

def main():
    """Run all setup checks and preparation."""
    logger.info("Running setup checks for UI Complexity Analyzer Bot...")
    
    # Check Python version
    if not check_python_version():
        logger.error("Setup failed: Python version check failed")
        return 1
    
    # Create directories
    if not create_required_directories():
        logger.error("Setup failed: Could not create required directories")
        return 1
    
    # Check environment variables
    check_environment_variables()
    
    # Check dependencies
    if not check_dependencies():
        logger.warning("Some dependencies are missing. The bot may not work correctly.")
    
    # Check LaTeX
    check_latex()
    
    logger.info("Setup completed successfully. The bot is ready to run.")
    logger.info("To start the bot, run: python run.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 