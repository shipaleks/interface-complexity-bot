#!/bin/bash
# Start script for UI Complexity Analyzer Bot

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Please install venv using 'pip install virtualenv'"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run setup script
echo "Running setup..."
python setup.py

# Check if .env file has been edited
if grep -q "your_telegram_bot_token_here" .env; then
    echo "⚠️  WARNING: You need to edit the .env file with your API keys before starting the bot."
    echo "   Please open .env in a text editor and add your API keys."
    echo "   When done, run this script again."
    exit 1
fi

# Start the bot
echo "Starting UI Complexity Analyzer Bot..."
python run.py

# Deactivate virtual environment on exit
deactivate 