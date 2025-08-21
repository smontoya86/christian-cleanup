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

# Pre-download small embedding model if enabled at build time
ARG ENABLE_EMBEDDINGS=0
ENV ENABLE_EMBEDDINGS=${ENABLE_EMBEDDINGS}
ARG EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENV EMBEDDING_MODEL=${EMBEDDING_MODEL}
RUN if [ "$ENABLE_EMBEDDINGS" = "1" ]; then \
      python -c "import os; from sentence_transformers import SentenceTransformer; m=os.getenv('EMBEDDING_MODEL','sentence-transformers/all-MiniLM-L6-v2'); SentenceTransformer(m); print('Downloaded embedding model:', m)"; \
    fi

# Set up HuggingFace model caching
ENV TRANSFORMERS_CACHE=/app/models
ENV HF_HOME=/app/models
RUN mkdir -p /app/models

# Skip heavyweight HF pre-download since MVP uses LLM analyzer by default
