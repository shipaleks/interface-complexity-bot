# UI Interface Complexity Analyzer Bot

A Telegram bot that analyzes UI screenshots to identify usability issues, calculate complexity scores, and provide strategic recommendations for improvement.

## Overview

This bot allows users to upload interface screenshots and receive comprehensive analysis including:

- Overall complexity score (0-100)
- Breakdown by categories (visual organization, cognitive load, etc.)
- Heatmap visualization of problem areas
- Strategic recommendations for improvement
- Comprehensive PDF report

## Technical Architecture

The system consists of two main components:

1. **analyze_ui.py**: Core analysis pipeline that orchestrates the following processes:
   - Image analysis using GPT-4 Vision
   - Coordinate extraction with Gemini Pro Vision
   - Heatmap generation
   - Strategic recommendations
   - PDF report generation
   
2. **bot.py**: Telegram bot implementation that:
   - Handles user interactions
   - Processes screenshots
   - Manages conversation flow
   - Delivers analysis results

## Prerequisites

- Python 3.8+
- OpenAI API key (for GPT-4 Vision)
- Google Gemini API key
- Telegram Bot Token

## Environment Setup

Create a `.env` file with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/shipaleks/interface-complexity-bot.git
   cd interface-complexity-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the bot:
   ```bash
   python run.py
   ```

## Quick Start with start.sh

You can use the provided start script for easy setup:

```bash
chmod +x start.sh
./start.sh
```

This script will:
1. Create a virtual environment if needed
2. Install dependencies
3. Run setup checks
4. Start the bot

## Deployment on Railway

This bot is designed to be easily deployed on Railway:

1. Fork this repository
2. Create a new Railway project
3. Connect to your GitHub repository
4. Add environment variables (OPENAI_API_KEY, GEMINI_API_KEY, TELEGRAM_BOT_TOKEN) in Railway
5. Deploy!

Railway will automatically use the Dockerfile and requirements.txt to build the environment.

## Usage

1. Start a conversation with the bot via Telegram
2. Send `/start` to begin a new analysis
3. Upload a screenshot of the interface
4. Optionally provide a description of what's in the screenshot
5. Wait for the analysis to complete (typically 2-5 minutes)
6. Review the results and download the PDF report

## Project Structure

```
interface-complexity-bot/
├── bot.py                     # Telegram bot implementation
├── analyze_ui.py              # Core analysis pipeline
├── generate_report.py         # Report generation module
├── get_gemini_recommendations.py # Strategic recommendations module  
├── generate_heatmap.py        # Heatmap generation module
├── prompts/                   # Prompt templates for GPT and Gemini
└── requirements.txt           # Project dependencies
```

## License

MIT 