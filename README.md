# Christian Music Curator

## 🐳 **DOCKER-FIRST PROJECT**

**⚠️ IMPORTANT: This is a Docker-first application. All commands should be run through Docker containers, not locally.**

- **Web App**: `docker exec christiancleanupwindsurf-web-1 <command>`
- **Database**: `docker exec christiancleanupwindsurf-db-1 <command>`
- **Workers**: `docker exec christiancleanupwindsurf-worker-1 <command>`
- **Redis**: `docker exec christiancleanupwindsurf-redis-1 redis-cli`

## Overview

A production-ready Flask application that transforms Christian music curation from basic scoring into comprehensive discernment training. The system analyzes song lyrics using AI-powered analysis, provides biblical perspectives, and helps Christians develop discernment skills for music evaluation.

**Status**: ✅ **Production Ready** - Enhanced analysis system fully operational

## Key Features

### **Enhanced Educational Analysis**
- **Biblical Theme Detection**: Identifies 10+ core biblical themes (Faith, Worship, Savior, Jesus, God, etc.)
- **Supporting Scripture**: Automatically maps themes to relevant Bible passages with educational context
- **Concern Analysis**: 7+ concern categories with biblical perspectives and educational guidance
- **Discernment Training**: Educational explanations that teach rather than just score

### **Core Application Features**
- **Spotify Integration**: OAuth login and bi-directional playlist synchronization
- **AI-Powered Analysis**: HuggingFace transformers with educational focus
- **Multi-Provider Lyrics**: LRCLib → Lyrics.ovh → Genius fallback system
- **Background Processing**: Redis Queue with 6 worker containers
- **Progressive Web App**: Modern UI with offline capabilities
- **Docker Deployment**: Production-ready containerized environment

### **User Experience**
- **Real-time Analysis**: <1 second analysis time with rich educational output
- **Whitelist Management**: Context-aware song approval workflow
- **Dashboard Analytics**: Comprehensive stats and progress tracking
- **Mock Authentication**: Development-friendly testing environment

## Technology Stack

### **Backend**
- **Flask 2.3+** with application factory pattern
- **PostgreSQL 14+** with SQLAlchemy 2.0
- **Redis 6+** for caching, sessions, and job queue
- **Python 3.9+** with type hints and modern practices

### **AI & Analysis**
- **HuggingFace Transformers** for content analysis
- **Enhanced Scripture Mapper** with 30+ biblical references
- **Enhanced Concern Detector** with Christian perspectives
- **Multi-provider lyrics system** for comprehensive coverage

### **Frontend**
- **Bootstrap 5.3** responsive framework
- **Vanilla JavaScript (ES6+)** with modular architecture
- **Progressive Web App** features (service worker, manifest)
- **Real-time updates** with polling architecture

### **Deployment**
- **Docker & Docker Compose** for containerization
- **Nginx** reverse proxy for production
- **6 Worker Containers** for scalable background processing
- **Health monitoring** with metrics and alerting

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Spotify Developer Account (for API keys)
- Node.js 18+ (for frontend build process)

### Setup
1. **Clone and Setup Environment**
   ```bash
   git clone <repository-url>
   cd christian-cleanup-windsurf
   cp environments/env.example .env
   # Edit .env with your Spotify API credentials
   ```

2. **Install Frontend Dependencies & Build Assets**
   ```bash
   npm install
   npm run build
   ```

3. **Start Application**
   ```bash
   docker-compose up --build
   ```

4. **Access Application**
   - Web Interface: http://localhost:5001
   - Login with Spotify or use Mock Authentication for testing

### Testing with Mock Data
```bash
# Create sample data for testing
python scripts/create_minimal_mock_data.py

# Access mock authentication
# Visit: http://localhost:5001
# Click: "Use Mock Users for Testing"
# Login as: John Christian or Mary Worship
```

## Enhanced Analysis System

### **Educational Transformation**
The application has evolved from a basic scoring tool into a comprehensive Christian discernment training platform:

**Before**: Simple percentage scores with minimal context
**After**: Rich educational analysis with biblical perspectives, supporting scripture, detailed concern explanations, and discernment skill development

### **Analysis Pipeline**
```
Lyrics Input → AI Analysis → Theme Detection → Scripture Mapping → Concern Analysis → Educational Output
```

### **Sample Educational Output**

#### **Biblical Themes Detected**
- **Faith**: "Found in lyrics: 'Faith' appears in song content and reflects biblical values"
- **Worship**: "Found in lyrics: 'Worship' appears in song content and reflects biblical values"
- **Savior**: "Found in lyrics: 'Savior' appears in song content and reflects biblical values"

#### **Supporting Scripture**
- **Hebrews 11:1**: "Defines faith as confident trust in God's promises"
- **Psalm 95:6**: "Calls for reverent worship acknowledging God as Creator"
- **John 14:6**: "Establishes Jesus as the exclusive path to salvation"

#### **Educational Guidance**
- **Comprehensive analysis**: "This content has high concern level with 7 area(s) requiring discernment... Use this analysis as a tool for developing your own discernment skills"
- **Biblical perspective integration** throughout all analysis components
- **Constructive feedback** rather than just warnings

## Services & Architecture

### **Core Application Services**

#### **Web Application**
- **URL**: http://localhost:5001
- **Service**: Flask web interface with Gunicorn WSGI server
- **Features**: Spotify OAuth, playlist management, enhanced analysis UI
- **Health Check**: `/api/health` endpoint

#### **Background Workers**
- **Service**: Redis Queue (RQ) workers for asynchronous processing
- **Workers**: 6 parallel workers for optimal performance
- **Tasks**: Enhanced song analysis, playlist synchronization, batch operations
- **Monitoring**: Worker health checks and performance metrics

#### **Database**
- **Service**: PostgreSQL 14 with optimized schema
- **Features**: Enhanced analysis JSON fields, persistent data storage
- **Health Check**: Built-in monitoring

#### **Cache & Queue**
- **Service**: Redis 7 with Alpine Linux
- **Features**: Session storage, task queue, analysis result caching
- **Health Check**: Built-in monitoring

### **Enhanced Analysis Services**

#### **SimplifiedChristianAnalysisService**
- AI-powered analysis with HuggingFace models
- Biblical theme detection (10+ core themes)
- Educational explanations with Christian perspectives
- Performance optimized (<1 second analysis time)

#### **EnhancedScriptureMapper**
- 10 biblical themes with 30+ scripture passages
- Educational context for each reference
- Relevance scoring and application guidance
- Comprehensive coverage of Christian doctrine

#### **EnhancedConcernDetector**
- 7+ concern categories with biblical perspectives
- Educational guidance for discernment training
- Severity assessment with Christian worldview
- Constructive feedback rather than just warnings

## API Endpoints

### **Authentication**
- `GET /auth/login` - Initiate Spotify OAuth
- `GET /auth/callback` - OAuth callback handling
- `POST /auth/logout` - Session termination
- `GET /auth/mock` - Development mock authentication

### **Core Application**
- `GET /` - Application dashboard with enhanced analytics
- `GET /playlist/<id>` - Playlist detail with educational analysis
- `GET /song/<id>` - Song detail with biblical themes and scripture
- `GET /user/settings` - User preferences

### **JSON API**
- `GET /api/health` - Health check endpoint
- `POST /api/analyze/song/<id>` - Enhanced single song analysis
- `POST /api/analyze/playlist/<id>` - Enhanced playlist analysis
- `GET /api/analysis/status/<job_id>` - Analysis progress tracking
- `POST /api/blacklist` - Blacklist management
- `POST /api/whitelist` - Whitelist management

## Frontend Build Process

### **Build Tools & Features**
- **ESBuild**: Fast JavaScript bundling and minification
- **PostCSS**: CSS processing with autoprefixer and minification
- **ESLint**: JavaScript code quality enforcement
- **Stylelint**: CSS code quality enforcement
- **Image Optimization**: Automatic compression for production
- **Source Maps**: Debug-friendly development mapping

### **Available Commands**

#### Development Commands
```bash
# Install dependencies
npm install

# Development build with watch mode
npm run dev

# Individual component watching
npm run build:css:watch
npm run build:js:watch
```

#### Production Commands
```bash
# Clean previous builds
npm run clean

# Production build with optimization
npm run build

# Lint code quality
npm run lint
npm run lint:css
npm run lint:js

# Fix linting issues
npm run lint:fix
```

## Database Schema

### **Enhanced Analysis Fields**
The database includes enhanced JSON fields for educational analysis:

#### **analysis_results Table**
```sql
-- Enhanced educational analysis fields
purity_flags_details (JSON)         -- Detailed concern analysis
positive_themes_identified (JSON)   -- Biblical theme detection
biblical_themes (JSON)              -- Enhanced theme mapping
supporting_scripture (JSON)         -- Scripture references with context
```

#### **Enhanced JSON Schemas**

**Biblical Themes**:
```json
[
  {
    "theme": "God",
    "relevance": "Identified through keyword analysis",
    "confidence": 0.85
  }
]
```

**Supporting Scripture**:
```json
[
  {
    "reference": "Psalm 46:1",
    "text": "God is our refuge and strength...",
    "theme": "God",
    "relevance": "Establishes God as our source of strength",
    "educational_value": "Helps understand biblical truth"
  }
]
```

## Development & Testing

### **Testing Strategy**
- **Unit Tests**: 22+ tests covering enhanced analysis components
- **Integration Tests**: End-to-end API testing with enhanced features
- **Service Tests**: Individual enhanced service testing
- **Mock Testing**: Complete application testing with sample data

### **Quality Assurance**
- **Type Hints**: Throughout Python codebase
- **Code Formatting**: Consistent style enforcement
- **Error Handling**: Comprehensive exception management
- **Documentation**: Inline comments and architectural docs

## Production Deployment

### **Container Strategy**
```yaml
services:
  web:          # Flask application (port 5001)
  worker:       # Enhanced analysis processing (6 containers)
  postgres:     # PostgreSQL with enhanced schema
  redis:        # Cache and job queue
  nginx:        # Reverse proxy (production)
```

### **Performance Metrics**
- **Analysis Time**: <1 second per song with enhanced features
- **Educational Content**: 100+ character explanations with biblical insights
- **Database Queries**: Optimized with indexes and connection pooling
- **Concurrent Users**: Scales horizontally with Docker containers

### **Security Implementation**
- **OAuth 2.0 with PKCE** for secure Spotify integration
- **Token Encryption** for stored access/refresh tokens
- **Session Security** with Redis backend and secure cookies
- **CSRF Protection** with Flask-WTF
- **Input Validation** and sanitization throughout

## Educational Impact

### **Transformation Achievement**
- **Before**: Basic scoring tool with minimal educational value
- **After**: Comprehensive Christian discernment training platform

### **Educational Features**
- **Biblical Perspective Integration** throughout all analysis
- **Supporting Scripture** with educational context and application
- **Discernment Training** that teaches evaluation skills
- **Constructive Guidance** for Christian music curation

### **User Benefits**
- **Skill Development**: Users learn to evaluate music independently
- **Biblical Grounding**: All analysis rooted in scriptural principles
- **Educational Growth**: Progressive learning through detailed explanations
- **Practical Application**: Real-world music curation with biblical wisdom

## Documentation

### **Available Documentation**
- **[Technical Architecture](docs/simplified_structure_rebuild.md)** - Comprehensive technical documentation
- **[Educational Roadmap](docs/educational_enhancement_roadmap.md)** - Educational feature development
- **[API Documentation](docs/api_docs.md)** - Complete API reference
- **[Security Practices](docs/SECURE_CODING_PRACTICES.md)** - Security implementation
- **[Production Deployment](docs/PRODUCTION_DEPLOYMENT.md)** - Deployment guide

---

**Current Status**: The application is production-ready with a fully operational enhanced analysis system that transforms Christian music curation into comprehensive discernment training. All core functionality has been preserved and enhanced while dramatically improving educational value and maintainability.
