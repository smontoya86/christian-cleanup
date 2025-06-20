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

# Copy frontend configuration files (simplified structure - skip for now)
# COPY postcss.config.js .eslintrc.js .stylelintrc.js ./

# Copy scripts directory (needed for build process) 
COPY scripts/ ./scripts/

# Copy frontend source files
COPY app/static ./app/static

# Build frontend assets for production (simplified structure - skip for now)
# ENV NODE_ENV=production
# RUN npm run build

# Copy the rest of the application (excluding files already copied)
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Expose the port the app runs on
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# The default command is overridden in docker-compose.yml
# This is just a fallback
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "run:app"]
