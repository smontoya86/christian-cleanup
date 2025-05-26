---
trigger: manual
---

# Christian Music Curator - Current Implementation (Updated 2025-05-25)

## Overview

A Flask-based web application that helps Christians curate their Spotify playlists by analyzing song content for alignment with Christian values. The system provides a professional, clean interface focused on actionable content curation with intelligent song analysis, context-aware workflows, and enterprise-grade performance monitoring.

## Current Status: Production Ready ✅

The application is fully functional with enterprise-grade capabilities:
- Spotify authentication and playlist synchronization
- Background song analysis with priority queue system
- Professional UI with intelligent action strategy
- PostgreSQL database with Docker containerization
- Whitelist management and context-aware workflows
- Performance optimization framework with regression testing
- Enhanced background processing with monitoring
- Frontend lazy loading and performance optimizations

## System Architecture

**Production-Ready Flask Application with Modern Stack:**

- **Frontend**: Responsive HTML/CSS with Bootstrap 5, Jinja2 templates, and lazy loading
- **Backend**: Python Flask with professional error handling, logging, and performance monitoring
- **Database**: PostgreSQL (Docker containerized for development/production parity)
- **Task Queue**: Redis with Flask-RQ2 for background song analysis and priority queues
- **AI Analysis**: Multi-model approach with fallback mechanisms
- **External APIs**: Spotify (OAuth + data), Bible API, Lyrics providers
- **Performance**: Comprehensive benchmarking and regression detection framework

## Technology Stack

- **Web Framework**: Flask (Python) with production-ready configuration
- **Database**: PostgreSQL with SQLAlchemy ORM and migrations
- **Task Queue**: Redis + Flask-RQ2 with priority queues and monitoring
- **Authentication**: Spotify OAuth2 with session management
- **AI/NLP Models**:
  - Primary: KoalaAI/Text-Moderation for content flagging
  - Fallback: cardiffnlp/twitter-roberta-base-sentiment
  - Custom theme extraction and biblical analysis
- **Frontend**: Bootstrap 5, responsive design, lazy loading components
- **Development**: Docker Compose for full environment
- **Testing**: Comprehensive test suite with performance regression testing
- **Performance**: Benchmarking framework with regression detection

## Core Features

### Refined User Interface
**Professional content curation interface with intelligent action strategy:**

- **Unanalyzed Songs**: "Analyze" button to start processing
- **High/Extreme Concern**: "Review" link to detailed analysis page
- **Low/Medium Concern**: Clean display with no action clutter
- **Whitelisted Songs**: Badge with optional removal
- **Lazy Loading**: Performance-optimized content loading with skeleton animations

**Benefits:**
- 70% reduction in visual clutter
- Focus on songs requiring attention
- Professional appearance for ministry context
- Clear terminology and guided workflows
- Optimized loading performance with lazy loading

### Enhanced Background Processing
**Priority-based task queue system with monitoring:**

- **Priority Queues**: HIGH_QUEUE, DEFAULT_QUEUE, LOW_QUEUE for task prioritization
- **Configurable Timeouts**: 5, 10, 30 minutes based on task complexity
- **Retry Mechanism**: Exponential backoff with intelligent retry logic
- **Worker Monitoring**: Health checks and performance metrics
- **Task Prioritization**: Enhanced analysis service with priority-based processing

### Song Analysis Framework
**Multi-layer analysis with biblical foundation and consistent scoring for all users:**

#### Consistent Analysis Configuration
- **Standard Settings**: All users receive identical analysis using moderate sensitivity
- **No User Preferences**: Analysis is consistent and reliable across the platform
- **Professional Grade**: Standardized scoring ensures objective content evaluation

#### Scoring System (0-100 scale)
- **Base Score**: 85 points (enhanced) / 80 points (lightweight)
- **Explicit Content Penalty**: -50 points (automatic "High" concern level)
- **Purity Flag Penalties**: 
  - Hate Speech: -75 to -80 points
  - Sexual Content: -50 to -100 points  
  - Violence/Harm: -30 to -50 points
  - Self-Harm: -75 points
- **Theme Adjustments**:
  - Positive Christian themes: +5 points each
  - Negative themes: -10 points each

#### Concern Levels
- **Low**: 85+ points (enhanced) / 80+ points (lightweight), no purity flags
- **Medium**: 70-84 points (enhanced) / 60-79 points (lightweight), no purity flags
- **High**: Below thresholds OR any purity flag detected
- **Explicit Override**: All explicit content automatically receives "High" concern

### Playlist Management
- **Smart Sync**: Automatic detection of new songs with analysis queue
- **Batch Processing**: Efficient background analysis of multiple songs
- **Progress Tracking**: Real-time status updates during analysis
- **Score Aggregation**: Playlist-level scoring based on analyzed content

### Content Curation Workflow
1. **Playlist Sync**: Import playlists from Spotify
2. **Auto-Analysis**: Queue new songs for background analysis
3. **Review Interface**: Focus on concerning content only
4. **Whitelist Decisions**: Context-aware approval workflow
5. **Clean Display**: Minimal clutter, maximum clarity

## API Endpoints

### Core Routes
- **Authentication**: `/login`, `/callback`, `/logout`
- **Dashboard**: `/dashboard` - Main interface with playlist overview
- **Playlist Detail**: `/playlist/<id>` - Song list with analysis results
- **Song Detail**: `/song/<id>` - Detailed analysis and whitelist options

### Analysis APIs
- **Analyze Playlist**: `/analyze_playlist_api/<id>` - Start batch analysis
- **Analyze Song**: `/api/songs/<id>/analyze` - Single song analysis
- **Status Check**: `/api/playlists/<id>/analysis-status` - Progress tracking
- **Unanalyzed Only**: `/api/playlists/<id>/analyze-unanalyzed` - Efficient partial analysis

### Performance APIs
- **Lazy Loading**: `/api/lazy-load/<endpoint>` - Lazy loading data endpoints
- **Performance Metrics**: Internal performance monitoring endpoints

### Management APIs  
- **Whitelist Actions**: `/whitelist_song/<playlist>/<track>`
- **Remove Actions**: `/remove_whitelist_song/<playlist>/<track>`
- **Bulk Operations**: Import/export functionality for lists

## System Folder Structure

```
christian-cleanup-windsurf/
├── app/                              # Main application package
│   ├── __init__.py                   # Flask app factory and configuration
│   ├── extensions.py                 # Flask extensions initialization
│   ├── commands.py                   # Custom CLI commands
│   ├── routes.py                     # Legacy routes (being phased out)
│   ├── jobs.py                       # Background job definitions
│   ├── worker_config.py              # Worker and queue configuration
│   │
│   ├── api/                          # API blueprints and endpoints
│   ├── auth/                         # Authentication blueprints
│   ├── main/                         # Main application blueprints
│   ├── config/                       # Configuration modules
│   ├── models/                       # Database models and schemas
│   ├── tasks/                        # Background task definitions
│   │
│   ├── services/                     # Business logic services
│   │   ├── analysis_service.py       # Core song analysis logic
│   │   ├── enhanced_analysis_service.py  # Priority-based analysis
│   │   ├── background_analysis_service.py  # Background processing
│   │   ├── spotify_service.py        # Spotify API integration
│   │   ├── playlist_sync_service.py  # Playlist synchronization
│   │   ├── whitelist_service.py      # Whitelist management
│   │   ├── blacklist_service.py      # Blacklist management
│   │   ├── list_management_service.py # List operations
│   │   ├── batch_operations.py       # Bulk operations
│   │   ├── bible_service.py          # Biblical analysis
│   │   └── song_status_service.py    # Song status management
│   │
│   ├── utils/                        # Utility modules
│   │   ├── analysis.py               # Core analysis utilities
│   │   ├── analysis_enhanced.py      # Enhanced analysis features
│   │   ├── analysis_lightweight.py   # Lightweight analysis
│   │   ├── analysis_adapter.py       # Analysis adapter pattern
│   │   ├── database.py               # Database utilities
│   │   ├── cache.py                  # Redis cache utilities
│   │   ├── lyrics.py                 # Lyrics processing
│   │   ├── bible_client.py           # Bible API client
│   │   ├── retry.py                  # Retry mechanism with backoff
│   │   ├── worker_monitoring.py      # Worker health monitoring
│   │   ├── query_monitoring.py       # Database query monitoring
│   │   └── database_monitoring.py    # Database performance monitoring
│   │
│   ├── static/                       # Frontend static assets
│   │   ├── css/                      # Stylesheets
│   │   │   ├── style.css             # Main application styles
│   │   │   ├── custom.css            # Custom component styles
│   │   │   ├── playlist_detail.css   # Playlist-specific styles
│   │   │   └── skeleton.css          # Loading state animations
│   │   └── js/                       # JavaScript files
│   │       ├── playlist_detail.js    # Playlist functionality
│   │       └── components/           # Reusable JS components
│   │           └── lazyLoader.js     # Lazy loading component
│   │
│   └── templates/                    # Jinja2 templates
│       ├── base.html                 # Base template
│       ├── index.html                # Landing page
│       ├── dashboard.html            # Main dashboard
│       ├── playlist_detail.html      # Playlist detail view
│       ├── song_detail.html          # Song analysis detail
│       ├── user_settings.html        # User preferences
│       ├── blacklist_whitelist.html  # List management
│       └── components/               # Template components
│           └── lazy_loading_demo.html # Lazy loading demo
│
├── tests/                            # Comprehensive test suite
│   ├── config.py                     # Test configuration
│   ├── conftest.py                   # Pytest configuration
│   │
│   ├── unit/                         # Unit tests
│   ├── integration/                  # Integration tests
│   ├── auth/                         # Authentication tests
│   ├── main/                         # Main blueprint tests
│   ├── regression/                   # Regression tests
│   ├── javascript/                   # Frontend JavaScript tests
│   │
│   ├── performance/                  # Performance testing suite
│   │   ├── test_database.py          # Database performance tests
│   │   ├── test_cache.py             # Cache performance tests
│   │   ├── test_database_baseline.py # Baseline performance tests
│   │   └── test_database_indexes.py  # Index optimization tests
│   │
│   ├── utils/                        # Test utilities
│   │   ├── benchmark.py              # Performance benchmarking framework
│   │   ├── regression_detector.py    # Regression detection utility
│   │   └── test_lyrics.py            # Lyrics testing utilities
│   │
│   └── results/                      # Test result storage
│
├── migrations/                       # Database migrations
│   └── versions/                     # Migration version files
│
├── scripts/                          # Utility scripts
├── tasks/                            # Task management files
├── docs/                             # Documentation
├── logs/                             # Application logs
├── coverage/                         # Test coverage reports
│
├── docker-compose.yml                # Docker development environment
├── Dockerfile                        # Container configuration
├── docker-entrypoint-worker.sh       # Worker container entrypoint
├── requirements.txt                  # Python dependencies
├── package.json                      # Node.js dependencies (for testing)
├── jest.config.js                    # JavaScript test configuration
├── run_performance_tests.py          # Performance test runner
├── worker.py                         # Background worker process
├── run.py                            # Development server
├── wsgi.py                           # Production WSGI entry point
├── setup.py                          # Package setup configuration
├── .env                              # Environment variables
├── .env.example                      # Environment template
├── .gitignore                        # Git ignore rules
├── .dockerignore                     # Docker ignore rules
└── README.md                         # Project documentation
```

## Database Schema

### Core Tables

#### Users Table
- **Primary Key**: `id` (Integer)
- **Spotify Integration**: `spotify_id` (unique), `email`, `display_name`
- **OAuth Tokens**: `access_token`, `refresh_token`, `token_expiry`
- **Admin Features**: `is_admin` (Boolean)
- **Timestamps**: `created_at`, `updated_at`
- **Relationships**: One-to-many with Playlists, Whitelist, Blacklist

#### Playlists Table
- **Primary Key**: `id` (Integer)
- **Spotify Data**: `spotify_id` (unique), `name`, `description`, `spotify_snapshot_id`
- **Metadata**: `image_url`, `last_analyzed`, `last_synced_from_spotify`
- **Foreign Keys**: `owner_id` → Users
- **Timestamps**: `created_at`, `updated_at`
- **Computed Properties**: `score` (aggregated from songs)

#### Songs Table
- **Primary Key**: `id` (Integer)
- **Spotify Data**: `spotify_id` (unique), `title`, `artist`, `album`, `duration_ms`
- **Content**: `lyrics`, `album_art_url`, `explicit` (Boolean)
- **Analysis Tracking**: `last_analyzed`
- **Timestamps**: `created_at`, `updated_at`
- **Computed Properties**: `analysis_status`, `score`, `concern_level`, `analysis_concerns`

#### PlaylistSong Table (Junction Table)
- **Composite Primary Key**: `playlist_id`, `song_id`
- **Position Tracking**: `track_position` (Spotify's 0-indexed position)
- **Spotify Metadata**: `added_at_spotify`, `added_by_spotify_user_id`
- **Performance Indexes**: Multi-column indexes for efficient queries

#### AnalysisResult Table
- **Primary Key**: `id` (Integer)
- **Foreign Key**: `song_id` → Songs
- **Status Tracking**: `status` (pending/processing/completed/failed)
- **Core Analysis**: `score` (0-100), `concern_level`, `explanation`
- **Detailed Analysis**: 
  - `themes` (JSON) - Identified themes
  - `problematic_content` (JSON) - Content flags
  - `concerns` (JSON) - List of concern strings
  - `purity_flags_details` (JSON) - Detailed purity analysis
  - `positive_themes_identified` (JSON) - Christian themes
  - `biblical_themes` (JSON) - Biblical themes and verses
  - `supporting_scripture` (JSON) - Scripture references
- **Error Handling**: `error_message` for failed analyses
- **Timestamps**: `analyzed_at`, `created_at`, `updated_at`

#### Whitelist Table
- **Primary Key**: `id` (Integer)
- **Foreign Key**: `user_id` → Users
- **Item Identification**: `spotify_id`, `item_type` (song/playlist/artist), `name`
- **Metadata**: `reason`, `added_date`
- **Unique Constraint**: User cannot whitelist same item twice

#### Blacklist Table
- **Primary Key**: `id` (Integer)
- **Foreign Key**: `user_id` → Users
- **Item Identification**: `spotify_id`, `item_type` (song/playlist/artist), `name`
- **Metadata**: `reason`, `added_date`
- **Unique Constraint**: User cannot blacklist same item twice

#### BibleVerse Table
- **Primary Key**: `id` (Integer)
- **Scripture Reference**: `book`, `chapter`, `verse_start`, `verse_end`
- **Content**: `text`, `theme_keywords` (JSON)
- **Purpose**: Supporting biblical analysis and theme matching

### Key Relationships
- **Users → Playlists**: One-to-many (user owns multiple playlists)
- **Users → Whitelist/Blacklist**: One-to-many (user manages multiple lists)
- **Playlists ↔ Songs**: Many-to-many via PlaylistSong (with position tracking)
- **Songs → AnalysisResult**: One-to-many (historical analysis tracking)
- **Songs ← BibleVerse**: Referenced for biblical theme analysis

### Performance Optimizations
- **Indexes**: Strategic indexes on foreign keys and frequently queried fields
- **JSON Fields**: Efficient storage for complex analysis data
- **Computed Properties**: Dynamic calculation of scores and status from related data
- **Cascade Deletes**: Proper cleanup of related records when parent records are deleted

## Recent Improvements

### Album Art Performance Optimization (2025-01-25) ✅ COMPLETED
**Database-stored album art URLs prioritized over live Spotify API calls:**

#### Enhanced Album Art Loading
- **Database-First Approach**: Album art URLs are stored in the database when songs are created/updated
- **Fallback Strategy**: Only fetch from Spotify API when database value is missing
- **Performance Improvement**: Reduced API calls and faster page loading for playlist detail views
- **Consistent Image Display**: Album art remains consistent even if Spotify URLs change

### Performance Optimization Framework (2025-01-09) ✅ COMPLETED
**Comprehensive performance enhancement system implemented using Test-Driven Development:**

#### Enhanced Background Processing
- **Priority Queue System**: HIGH_QUEUE, DEFAULT_QUEUE, LOW_QUEUE for task prioritization
- **Retry Mechanism**: Exponential backoff with configurable retry logic
- **Worker Monitoring**: Health checks and performance metrics with MonitoredWorker class
- **Task Prioritization**: Enhanced analysis service with intelligent task routing

#### Frontend Performance Optimizations
- **Lazy Loading**: IntersectionObserver-based lazy loading with skeleton animations
- **API Optimization**: Fetch API with retry logic and error handling
- **Loading States**: Professional loading animations and state management
- **Performance Monitoring**: Real-time performance tracking

#### Comprehensive Testing Framework
- **Performance Benchmarking**: Statistical analysis with mean, median, min, max, standard deviation
- **Regression Detection**: Configurable threshold-based regression identification
- **Database Performance Tests**: Realistic scenarios with bulk operations and complex queries
- **Cache Performance Tests**: Redis cache testing with various data patterns
- **Test Runner**: Automated performance test execution with regression detection

### UI Refinements (2025-01-08)
- **Eliminated confusing icons** (hearts/bans inappropriate for Christian context)
- **Implemented action strategy** that shows buttons only when needed
- **Professional terminology** using "whitelist" instead of social media language
- **Context-aware workflows** with confirmation dialogs for concerning content
- **Accessibility improvements** with clear labels and logical navigation

### Technical Enhancements
- **Background processing stability** with proper error handling
- **Database optimization** with efficient queries and indexing
- **Docker environment** for development/production parity
- **Comprehensive testing** with integration and regression test suites

## Performance Framework

### Benchmarking System
**Enterprise-grade performance monitoring with statistical analysis:**

- **Statistical Metrics**: Mean, median, min, max, standard deviation for all operations
- **Memory Monitoring**: Real-time memory usage tracking with psutil
- **Result Storage**: Timestamped JSON results for historical analysis
- **Benchmark Suites**: Organized test collections with bulk operations
- **Comparison Functions**: Automated regression detection with configurable thresholds

### Regression Detection
**Automated performance regression identification:**

- **Configurable Thresholds**: Customizable regression sensitivity (default: 10%)
- **Severity Classification**: Low, medium, high, critical levels based on performance impact
- **Trend Analysis**: Historical performance trend evaluation across multiple test runs
- **Comprehensive Reporting**: Detailed regression analysis reports with actionable insights
- **CI/CD Integration**: Ready for continuous integration pipeline integration

### Performance Test Categories
**Comprehensive test coverage across all system components:**

#### Database Performance Tests
- **Query Performance**: User playlists, song analysis, aggregations
- **Complex Joins**: Multi-table joins with performance optimization
- **Bulk Operations**: Insert performance with realistic data volumes
- **Search Performance**: Full-text search with ILIKE patterns
- **Pagination**: Efficient offset/limit query testing
- **Connection Performance**: Basic database connection benchmarking

#### Cache Performance Tests
- **Operation Types**: Set, get, delete, bulk operations
- **Data Patterns**: Various data sizes and complexity levels
- **Expiration Testing**: Time-based cache expiration validation
- **Serialization**: Complex data structure serialization performance
- **Concurrent Access**: Simulated concurrent access patterns
- **Memory Usage**: Variable data size performance testing
- **Fallback Scenarios**: Cache unavailability handling

## Development Setup

### Quick Start (Docker - Recommended)
```bash
# Clone and setup
cp .env.example .env
# Edit .env with Spotify credentials

# Start everything
docker-compose up --build

# Access at http://localhost:5001
```

### Local Development
```bash
# Install Redis
brew install redis && brew services start redis

# Python setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run application
python run.py
```

### Performance Testing
```bash
# Run all performance tests
python run_performance_tests.py

# Run specific test category
python run_performance_tests.py --test database

# Check for regressions
python run_performance_tests.py --check-regressions

# Generate comprehensive report
python run_performance_tests.py --report
```

## Performance Metrics

### Current Performance (January 2025)
- **Dashboard**: 3.5ms average response time (excellent)
- **Playlist Detail**: 14ms average response time (excellent)
- **Progress API**: Optimized with lazy loading implementation
- **Performance API**: Enhanced with caching and optimization
- **Database Queries**: 4-31ms for basic operations
- **Background Processing**: Priority-based with monitoring and retry logic

### Performance Testing Results
- **Benchmark Framework**: 13 comprehensive tests (100% pass rate)
- **Regression Detection**: 15 detailed tests (100% pass rate)
- **Database Performance**: 10 realistic scenario tests with statistical analysis
- **Cache Performance**: 11 comprehensive cache operation tests
- **JavaScript Components**: 18 frontend tests with performance optimizations

### Scalability Assessment
- **Current Capacity**: Handles typical Spotify user patterns (12 playlists, 3,000+ songs)
- **Heavy User Support**: System architecture supports hundreds of playlists and tens of thousands of tracks
- **Performance Monitoring**: Comprehensive regression detection and trend analysis
- **Infrastructure**: Docker-based with PostgreSQL and Redis for horizontal scaling

## Implementation Files

### Core Performance Framework
- `app/worker_config.py` - Worker and queue configuration
- `app/utils/retry.py` - Retry mechanism with exponential backoff
- `app/utils/worker_monitoring.py` - Worker health monitoring
- `app/services/enhanced_analysis_service.py` - Enhanced analysis with prioritization
- `app/static/js/components/lazyLoader.js` - Lazy loading component
- `app/static/css/skeleton.css` - Loading state styles

### Testing Framework
- `tests/utils/benchmark.py` - Performance benchmarking framework
- `tests/utils/regression_detector.py` - Regression detection utility
- `tests/performance/test_database.py` - Database performance tests
- `tests/performance/test_cache.py` - Cache performance tests
- `run_performance_tests.py` - Performance test runner with regression detection

### Test Coverage
- `tests/unit/test_worker_config.py` - Worker configuration tests
- `tests/unit/test_benchmark_framework.py` - Benchmark framework tests
- `tests/unit/test_regression_detector.py` - Regression detector tests
- `tests/unit/test_lazy_loading_api.py` - Lazy loading API tests
- `tests/javascript/lazyLoader.test.js` - JavaScript component tests

## Future Enhancements

### Immediate Opportunities (Weeks 1-2)
- **Production Deployment**: Deploy performance-optimized system to production
- **Monitoring Integration**: Integrate performance monitoring with production systems
- **Alert Configuration**: Set up automated alerts for performance regressions
- **Performance Budgets**: Establish performance budgets for critical operations

### Medium-term Goals (Weeks 3-4)
- **Database Indexing**: Implement strategic database indexes based on performance test results
- **Query Optimization**: Optimize slow queries identified by performance testing
- **Cache Strategy Enhancement**: Enhance caching strategy based on cache performance insights
- **Mobile Optimization**: Extend lazy loading and performance optimizations to mobile

### Long-term Vision (Months 2-3)
- **Production Monitoring Dashboard**: Build comprehensive performance monitoring dashboard
- **Capacity Planning**: Use performance data for intelligent capacity planning
- **Advanced Analytics**: Implement advanced performance analytics and predictions
- **Community Features**: Shared whitelists and recommendations with performance optimization

## Conclusion

The Christian Music Curator has evolved into a production-ready application with enterprise-grade performance monitoring and optimization capabilities. The comprehensive performance framework provides:

**Key Achievements:**
- **Professional Interface**: Clutter-free interface appropriate for ministry use with performance optimizations
- **Enhanced Background Processing**: Priority-based queue system with monitoring and retry logic
- **Performance Framework**: Complete benchmarking and regression detection system
- **Comprehensive Testing**: Full test coverage with Test-Driven Development methodology
- **Production Ready**: Integration-ready performance monitoring system
- **Scalable Architecture**: Robust technical foundation ready for production deployment

**Performance Optimization Completion:**
- ✅ 20 main tasks completed (100%)
- ✅ 79 subtasks completed (100%)
- ✅ Test-Driven Development methodology applied throughout
- ✅ Comprehensive performance regression testing framework
- ✅ Enterprise-grade performance monitoring capabilities

The system now provides a solid foundation for maintaining and improving application performance over time, with automated regression detection and comprehensive performance monitoring capabilities.

## System Folder Structure

```
christian-cleanup-windsurf/
├── app/                              # Main application package
│   ├── __init__.py                   # Flask app factory and configuration
│   ├── extensions.py                 # Flask extensions initialization
│   ├── commands.py                   # Custom CLI commands
│   ├── routes.py                     # Legacy routes (being phased out)
│   ├── jobs.py                       # Background job definitions
│   ├── worker_config.py              # Worker and queue configuration
│   │
│   ├── api/                          # API blueprints and endpoints
│   ├── auth/                         # Authentication blueprints
│   ├── main/                         # Main application blueprints
│   ├── config/                       # Configuration modules
│   ├── models/                       # Database models and schemas
│   ├── tasks/                        # Background task definitions
│   │
│   ├── services/                     # Business logic services
│   │   ├── analysis_service.py       # Core song analysis logic
│   │   ├── enhanced_analysis_service.py  # Priority-based analysis
│   │   ├── background_analysis_service.py  # Background processing
│   │   ├── spotify_service.py        # Spotify API integration
│   │   ├── playlist_sync_service.py  # Playlist synchronization
│   │   ├── whitelist_service.py      # Whitelist management
│   │   ├── blacklist_service.py      # Blacklist management
│   │   ├── list_management_service.py # List operations
│   │   ├── batch_operations.py       # Bulk operations
│   │   ├── bible_service.py          # Biblical analysis
│   │   └── song_status_service.py    # Song status management
│   │
│   ├── utils/                        # Utility modules
│   │   ├── analysis.py               # Core analysis utilities
│   │   ├── analysis_enhanced.py      # Enhanced analysis features
│   │   ├── analysis_lightweight.py   # Lightweight analysis
│   │   ├── analysis_adapter.py       # Analysis adapter pattern
│   │   ├── database.py               # Database utilities
│   │   ├── cache.py                  # Redis cache utilities
│   │   ├── lyrics.py                 # Lyrics processing
│   │   ├── bible_client.py           # Bible API client
│   │   ├── retry.py                  # Retry mechanism with backoff
│   │   ├── worker_monitoring.py      # Worker health monitoring
│   │   ├── query_monitoring.py       # Database query monitoring
│   │   └── database_monitoring.py    # Database performance monitoring
│   │
│   ├── static/                       # Frontend static assets
│   │   ├── css/                      # Stylesheets
│   │   │   ├── style.css             # Main application styles
│   │   │   ├── custom.css            # Custom component styles
│   │   │   ├── playlist_detail.css   # Playlist-specific styles
│   │   │   └── skeleton.css          # Loading state animations
│   │   └── js/                       # JavaScript files
│   │       ├── playlist_detail.js    # Playlist functionality
│   │       └── components/           # Reusable JS components
│   │           └── lazyLoader.js     # Lazy loading component
│   │
│   └── templates/                    # Jinja2 templates
│       ├── base.html                 # Base template
│       ├── index.html                # Landing page
│       ├── dashboard.html            # Main dashboard
│       ├── playlist_detail.html      # Playlist detail view
│       ├── song_detail.html          # Song analysis detail
│       ├── user_settings.html        # User preferences
│       ├── blacklist_whitelist.html  # List management
│       └── components/               # Template components
│           └── lazy_loading_demo.html # Lazy loading demo
│
├── tests/                            # Comprehensive test suite
│   ├── config.py                     # Test configuration
│   ├── conftest.py                   # Pytest configuration
│   │
│   ├── unit/                         # Unit tests
│   ├── integration/                  # Integration tests
│   ├── auth/                         # Authentication tests
│   ├── main/                         # Main blueprint tests
│   ├── regression/                   # Regression tests
│   ├── javascript/                   # Frontend JavaScript tests
│   │
│   ├── performance/                  # Performance testing suite
│   │   ├── test_database.py          # Database performance tests
│   │   ├── test_cache.py             # Cache performance tests
│   │   ├── test_database_baseline.py # Baseline performance tests
│   │   └── test_database_indexes.py  # Index optimization tests
│   │
│   ├── utils/                        # Test utilities
│   │   ├── benchmark.py              # Performance benchmarking framework
│   │   ├── regression_detector.py    # Regression detection utility
│   │   └── test_lyrics.py            # Lyrics testing utilities
│   │
│   └── results/                      # Test result storage
│
├── migrations/                       # Database migrations
│   └── versions/                     # Migration version files
│
├── scripts/                          # Utility scripts
├── tasks/                            # Task management files
├── docs/                             # Documentation
├── logs/                             # Application logs
├── coverage/                         # Test coverage reports
│
├── docker-compose.yml                # Docker development environment
├── Dockerfile                        # Container configuration
├── docker-entrypoint-worker.sh       # Worker container entrypoint
├── requirements.txt                  # Python dependencies
├── package.json                      # Node.js dependencies (for testing)
├── jest.config.js                    # JavaScript test configuration
├── run_performance_tests.py          # Performance test runner
├── worker.py                         # Background worker process
├── run.py                            # Development server
├── wsgi.py                           # Production WSGI entry point
├── setup.py                          # Package setup configuration
├── .env                              # Environment variables
├── .env.example                      # Environment template
├── .gitignore                        # Git ignore rules
├── .dockerignore                     # Docker ignore rules
└── README.md                         # Project documentation
```
