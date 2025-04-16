# syntax=docker/dockerfile:1
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies including LaTeX
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-latex-extra \
    git \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directories for user data
RUN mkdir -p user_analyses

# Command to run the bot
CMD ["python", "bot.py"]
