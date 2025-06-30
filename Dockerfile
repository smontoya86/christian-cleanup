# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies including Node.js and image processing tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    autotools-dev \
    automake \
    libtool \
    pkg-config \
    nasm \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy package.json and package-lock.json first for better caching
COPY package*.json ./

# Install Node.js dependencies (including dev dependencies for build tools)
RUN npm ci

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Set up HuggingFace model caching
ENV TRANSFORMERS_CACHE=/app/models
ENV HF_HOME=/app/models
RUN mkdir -p /app/models

# Pre-download HuggingFace models to cache them during build
RUN python -c "from transformers import pipeline; import logging; logging.basicConfig(level=logging.INFO); print('Pre-downloading HuggingFace models...'); pipeline('sentiment-analysis', model='cardiffnlp/twitter-roberta-base-sentiment-latest'); pipeline('text-classification', model='unitary/toxic-bert'); pipeline('text-classification', model='j-hartmann/emotion-english-distilroberta-base'); print('All models cached successfully')"