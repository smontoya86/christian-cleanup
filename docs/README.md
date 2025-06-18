# Christian Cleanup Application Documentation

## Overview

Christian Cleanup is a comprehensive Spotify playlist analysis application that helps users identify and manage songs that may not align with Christian values. The application provides sophisticated lyrical analysis, biblical theme detection, and content scoring to help users curate their music collections.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Getting Started](#getting-started)
3. [Service Layer](#service-layer)
4. [Analysis Engine](#analysis-engine)
5. [API Documentation](#api-documentation)
6. [Database Schema](#database-schema)
7. [Configuration](#configuration)
8. [Development Workflow](#development-workflow)
9. [Testing](#testing)
10. [Deployment](#deployment)

## Architecture Overview

The application follows a modern, layered architecture with clear separation of concerns:

```
├── Presentation Layer (Flask Blueprints)
│   ├── Web Interface (Templates & Static Files)
│   └── REST API Endpoints
├── Service Layer (Business Logic)
│   ├── Analysis Services
│   ├── Spotify Integration
│   └── User Management
├── Repository Layer (Data Access)
│   ├── Database Repositories
│   └── External API Clients
└── Infrastructure Layer
    ├── Database (PostgreSQL)
    ├── Cache (Redis)
    └── Background Jobs (RQ)
```

### Key Architectural Principles

- **Domain-Driven Design (DDD)**: Clear domain boundaries and entities
- **Dependency Injection**: Service registry for loose coupling
- **Repository Pattern**: Abstracted data access layer
- **SOLID Principles**: Single responsibility, open/closed, dependency inversion
- **Exception Hierarchy**: Comprehensive error handling with context

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Spotify Developer Account

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd christian-cleanup
   ```

2. **Set up virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize database**:
   ```bash
   flask db upgrade
   ```

5. **Start the application**:
   ```bash
   python run.py
   ```

## Service Layer

The service layer provides the core business logic and is organized into several key domains:

### Analysis Services

- **[UnifiedAnalysisService](service_layer_architecture.md#unified-analysis-service)**: Comprehensive biblical song analysis
- **[EnhancedSongAnalyzer](../app/utils/analysis_enhanced.py)**: Advanced pattern matching and scoring
- **[QualityAssurance](service_layer_architecture.md#quality-assurance)**: Analysis validation and quality control

### Core Services

- **[SpotifyService](../app/services/spotify_service.py)**: Spotify API integration
- **[WhitelistService](../app/services/whitelist_service_standardized.py)**: User preference management
- **[PlaylistSyncService](../app/services/playlist_sync_service.py)**: Playlist synchronization

### Infrastructure Services

- **[OptimizedQueryService](../app/services/optimized_query_service.py)**: Database query optimization
- **[ServiceRegistry](../app/services/service_registry.py)**: Dependency injection container

## Analysis Engine

The analysis engine is the heart of the application, providing sophisticated content analysis:

### Components

1. **Pattern Matching**: Context-aware lyric analysis
2. **Biblical Theme Detection**: Identification of Christian themes and supporting scripture
3. **Concern Level Assessment**: Graduated scoring system
4. **Quality Validation**: Multi-dimensional quality assurance

### Analysis Flow

```
Song Input → Lyrics Fetch → Pattern Analysis → Biblical Detection → Scoring → Quality Validation → Result Storage
```

For detailed information, see [Analysis Engine Documentation](analysis_engine.md).

## API Documentation

The application provides a comprehensive REST API for all operations:

### Authentication Endpoints

- `POST /auth/login` - User authentication via Spotify OAuth
- `POST /auth/logout` - User logout
- `GET /auth/callback` - OAuth callback handler

### Analysis Endpoints

- `POST /api/songs/{id}/analyze` - Analyze a specific song
- `GET /api/analysis/{id}` - Retrieve analysis results
- `POST /api/playlists/{id}/analyze` - Analyze entire playlist

### User Endpoints

- `GET /api/user/profile` - User profile information
- `GET /api/user/playlists` - User's playlists
- `POST /api/user/preferences` - Update user preferences

For complete API documentation, see [API Reference](api_reference.md).

## Database Schema

The application uses PostgreSQL with the following main entities:

### Core Entities

- **Users**: User accounts and authentication
- **Songs**: Track information and metadata
- **Playlists**: User playlists and sync information
- **AnalysisResults**: Analysis outcomes and scores
- **Whitelist/Blacklist**: User preference overrides

### Relationships

- Users have many Playlists
- Playlists contain many Songs (through PlaylistSong)
- Songs have many AnalysisResults
- Users have Whitelist/Blacklist entries

For detailed schema, see [Database Documentation](database_schema.md).

## Configuration

The application supports multiple configuration methods:

### Environment Variables

Core configuration via `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Spotify API
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret

# Redis
REDIS_URL=redis://localhost:6379

# Application
FLASK_ENV=development
SECRET_KEY=your_secret_key
```

### TaskMaster Configuration

Task management via `.taskmasterconfig`:

```json
{
  "projectName": "Christian Cleanup",
  "models": {
    "main": "gpt-4",
    "research": "gpt-4",
    "fallback": "gpt-3.5-turbo"
  }
}
```

For complete configuration options, see [Configuration Guide](configuration.md).

## Development Workflow

The project follows a structured development approach:

### Task Management

- **TaskMaster Integration**: AI-assisted task breakdown and tracking
- **Test-Driven Development**: Write tests first, then implementation
- **Code Quality**: Comprehensive type hints and documentation

### Code Standards

- **Type Hints**: Full type annotation coverage
- **Documentation**: Google-style docstrings
- **Testing**: Unit, integration, and performance tests
- **Linting**: mypy, flake8, and black formatting

### Git Workflow

1. Create feature branch from main
2. Implement changes with tests
3. Run full test suite
4. Update documentation
5. Create pull request

For detailed workflow, see [Development Guide](development_guide.md).

## Testing

Comprehensive testing strategy across multiple layers:

### Test Types

- **Unit Tests**: Individual function/method testing
- **Integration Tests**: Service layer integration
- **API Tests**: Endpoint functionality
- **Performance Tests**: Query optimization validation
- **Regression Tests**: Breaking change prevention

### Running Tests

```bash
# All tests
pytest

# Specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/

# With coverage
pytest --cov=app --cov-report=html
```

For testing guidelines, see [Testing Documentation](testing.md).

## Deployment

The application supports multiple deployment methods:

### Docker Deployment

```bash
# Build image
docker build -t christian-cleanup .

# Run with compose
docker-compose up -d
```

### Production Considerations

- **Environment**: Set `FLASK_ENV=production`
- **Database**: Use managed PostgreSQL service
- **Redis**: Use managed Redis service
- **Logging**: Configure structured logging
- **Monitoring**: Set up health checks and metrics

For deployment guide, see [Deployment Documentation](deployment.md).

## Project Structure

```
christian-cleanup/
├── app/                          # Application package
│   ├── blueprints/              # Flask blueprints (routes)
│   ├── models/                  # Database models
│   ├── services/                # Business logic layer
│   │   ├── analysis/           # Analysis domain services
│   │   └── repositories/       # Data access layer
│   ├── utils/                   # Utility modules
│   ├── static/                  # Static web assets
│   └── templates/               # HTML templates
├── docs/                        # Documentation
├── tests/                       # Test suite
├── scripts/                     # Utility scripts
├── migrations/                  # Database migrations
└── tasks/                       # TaskMaster task files
```

## Contributing

1. **Read the Documentation**: Understand the architecture and patterns
2. **Follow Code Standards**: Use type hints, write tests, document code
3. **Update Documentation**: Keep docs in sync with code changes
4. **Run Tests**: Ensure all tests pass before submitting
5. **Use TaskMaster**: Track work with the integrated task management

For contribution guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Documentation**: Check this documentation for common questions

## License

This project is licensed under the MIT License. See [LICENSE](../LICENSE) for details.

---

*This documentation is automatically updated with the codebase. Last updated: {{ current_date }}* 