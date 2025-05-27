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

4. **Start Background Workers**
   ```bash
   # Option 1: Use the macOS-optimized startup script (recommended for macOS)
   ./start_worker_macos.sh
   
   # Option 2: Threading-based worker (alternative for macOS)
   ./start_worker_threading.sh
   
   # Option 3: Direct Python execution (worker auto-detects macOS)
   python worker.py
   
   # Option 4: Direct threading mode
   python worker.py --threading
   ```

### macOS Development Notes
The application includes comprehensive macOS fork safety measures for background workers:

**Automatic Detection & Configuration:**
- Workers automatically detect the macOS environment
- Sets `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` to prevent Objective-C runtime conflicts
- Provides console feedback when macOS compatibility mode is active

**Startup Options:**
- **Recommended**: Use `./start_worker_macos.sh` for optimal macOS compatibility
- **Threading Mode**: Use `./start_worker_threading.sh` for alternative execution model
- **Direct Execution**: `python worker.py` (auto-detects macOS) or `python worker.py --threading`

**What's Fixed:**
- ✅ Eliminates "objc[PID]: +[NSMutableString initialize] may have been in progress" errors
- ✅ Prevents worker crashes with "waitpid returned 6 (signal 6)"
- ✅ Enables complex Flask application jobs to run successfully
- ✅ Maintains full compatibility with Linux/Docker environments

No manual configuration is required - the system handles macOS-specific requirements automatically.

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
- **Docker Environment**: `docs/DOCKER_ENVIRONMENT_FIXES.md`
- **macOS Development**: `docs/MACOS_FORK_SAFETY.md`
- **Threading Workers**: `docs/THREADING_WORKER_CONFIG.md`
- **UI Improvements**: `docs/UI_IMPROVEMENTS_SUMMARY.md`
- **API Documentation**: `docs/api_docs.md`
- **Parallel Processing**: `docs/PARALLEL_PROCESSING.md`
- **Optimal Configuration**: `docs/OPTIMAL_PARALLEL_CONFIG.md`
- **Analysis Improvements**: `docs/ANALYSIS_IMPROVEMENTS.md`
- **Implementation Summary**: `docs/IMPLEMENTATION_SUMMARY.md`
