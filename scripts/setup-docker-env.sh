#!/bin/bash

# Docker Environment Setup Script
# This script helps set up the Docker environment configuration

set -e

echo "🐳 Docker Environment Setup for Christian Cleanup"
echo "=================================================="

# Check if .env.docker already exists
if [ -f ".env.docker" ]; then
    echo "⚠️  .env.docker already exists."
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelled."
        exit 1
    fi
fi

# Copy template to .env.docker
if [ -f "env.docker.example" ]; then
    cp env.docker.example .env.docker
    echo "✅ Created .env.docker from template"
else
    echo "❌ Template file env.docker.example not found"
    exit 1
fi

echo ""
echo "📝 Configuration Setup Required"
echo "==============================="
echo "Please edit .env.docker and update the following values:"
echo ""
echo "🔑 Required (Application will not work without these):"
echo "   - SPOTIFY_CLIENT_ID"
echo "   - SPOTIFY_CLIENT_SECRET"
echo "   - SECRET_KEY (use a strong, random secret for production)"
echo ""
echo "🎯 Optional (Recommended for full functionality):"
echo "   - GENIUS_API_TOKEN"
echo "   - ANTHROPIC_API_KEY"
echo "   - PERPLEXITY_API_KEY"
echo "   - BIBLE_API_KEY"
echo ""
echo "💡 Tips:"
echo "   - Get Spotify API credentials from: https://developer.spotify.com/"
echo "   - Update SPOTIFY_REDIRECT_URI if deploying to a different domain"
echo "   - Use docker-compose up -d to start the application"
echo ""

# Check if user wants to edit the file now
read -p "Do you want to edit .env.docker now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Try to open with common editors
    if command -v code >/dev/null 2>&1; then
        code .env.docker
    elif command -v nano >/dev/null 2>&1; then
        nano .env.docker
    elif command -v vim >/dev/null 2>&1; then
        vim .env.docker
    else
        echo "Please edit .env.docker with your preferred text editor"
    fi
fi

echo ""
echo "🚀 Next Steps:"
echo "=============="
echo "1. Edit .env.docker with your API credentials"
echo "2. Run: docker-compose up -d"
echo "3. Visit: http://localhost:5001"
echo ""
echo "For more information, see docs/configuration.md" 