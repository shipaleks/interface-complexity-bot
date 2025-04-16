# syntax=docker/dockerfile:1
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies including LaTeX and other required packages
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-latex-extra \
    git \
    build-essential \
    libmagic1 \
    libmagickwand-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create required directories
RUN mkdir -p output output/images output/reports output/data prompts temp_files

# Copy requirements first to leverage Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Environment variables will be provided by Railway

# Set PORT environment variable for Railway (if not set)
ENV PORT=5000

# Command to run the bot
CMD ["python", "run.py"]
