# Christian Music Curator

## Overview

A Flask-based web application that helps Christians curate their Spotify playlists by analyzing song content for alignment with Christian values. The system analyzes lyrics, scores content based on biblical principles, and provides an intuitive interface for managing playlists with professional-grade content curation tools.

## Key Features

- **Spotify Integration**: OAuth login and playlist synchronization
- **AI-Powered Analysis**: Automated lyric analysis using advanced NLP models
- **Christian Values Scoring**: 0-100 scale with biblical theme detection using consistent, reliable algorithms
- **Refined UI**: Clean, professional interface focused on songs needing attention
- **Whitelist Management**: Context-aware song approval workflow
- **Background Processing**: Asynchronous analysis using Redis/RQ
- **Parallel Processing**: Multi-worker analysis (2 workers optimal) for faster bulk operations
- **Docker Support**: Complete containerized development environment

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Spotify Developer Account (for API keys)

### Setup
1. **Clone and Setup Environment**
   ```bash
   git clone <repository-url>
   cd christian-cleanup-windsurf
   cp .env.example .env
   # Edit .env with your Spotify API credentials
   ```

2. **Start Application**
   ```bash
   docker-compose up --build
   ```

3. **Access Application**
   - Web Interface: http://localhost:5001
   - Login with your Spotify account to start

### Local Development (Alternative)
If you prefer local development without Docker:

1. **Install Redis**
   ```bash
   # macOS with Homebrew
   brew install redis
   brew services start redis
   ```

2. **Setup Python Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

3. **Run Application**
   ```bash
   python run.py
   ```

## System Status

✅ **100% Functional** - All core features working correctly:
- Spotify authentication and playlist sync
- Background song analysis processing  
- Professional UI with refined action strategy
- Database connectivity and data persistence
- Docker containerization

## Parallel Analysis Processing

The system supports high-performance parallel analysis for bulk operations:

### **Performance Metrics (2 Workers + Throttling)**
- **Processing Rate**: ~35-40 songs/minute (with rate limiting)
- **API Usage**: ~2,100-2,400 Genius API calls/hour (within safe limits)
- **Optimal Configuration**: 2 workers + 1.5s pause interval

### **Usage Examples**
```bash
# Run parallel analysis with optimal throttling (recommended)
docker-compose exec web python scripts/bulk_reanalyze_parallel.py --workers 2 --batch-size 500

# Conservative approach for large batches
docker-compose exec web python scripts/bulk_reanalyze_parallel.py --workers 2 --batch-size 1000 --pause-interval 2.0

# Dry run to see what would be processed
docker-compose exec web python scripts/bulk_reanalyze_parallel.py --workers 2 --batch-size 100 --dry-run
```

### **Rate Limiting Considerations**
- **2 Workers**: Optimal performance (~1,800 API calls/hour)
- **3 Workers**: Near API limits (~2,700 API calls/hour) 
- **4+ Workers**: Not recommended (will hit Genius API rate limits)

## Documentation

- **Setup Instructions**: See `.env.example` for configuration
- **Architecture Overview**: `docs/simplified_structure_current_impl.md`
- **UI Improvements**: `docs/UI_IMPROVEMENTS_SUMMARY.md`
- **API Documentation**: `docs/api_docs.md`
- **Parallel Processing**: `docs/PARALLEL_PROCESSING.md`
- **Optimal Configuration**: `docs/OPTIMAL_PARALLEL_CONFIG.md`
- **Analysis Improvements**: `docs/ANALYSIS_IMPROVEMENTS.md`
- **Implementation Summary**: `docs/IMPLEMENTATION_SUMMARY.md`
