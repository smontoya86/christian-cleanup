---
trigger: manual
---

# Christian Music Curator - Current Implementation (Updated 2025-01-08)

## Overview

A Flask-based web application that helps Christians curate their Spotify playlists by analyzing song content for alignment with Christian values. The system provides a professional, clean interface focused on actionable content curation with intelligent song analysis and context-aware workflows.

## Current Status: 100% Functional ✅

All core features are working correctly:
- ✅ Spotify authentication and playlist synchronization
- ✅ Background song analysis with Redis/RQ task queue
- ✅ Professional UI with refined action strategy
- ✅ PostgreSQL database with proper containerization
- ✅ Whitelist management and context-aware workflows
- ✅ Docker development environment

## System Architecture

**Production-Ready Flask Application with Modern Stack:**

- **Frontend**: Responsive HTML/CSS with Bootstrap 5 and Jinja2 templates
- **Backend**: Python Flask with professional error handling and logging
- **Database**: PostgreSQL (Docker containerized for development/production parity)
- **Task Queue**: Redis with Flask-RQ2 for background song analysis
- **AI Analysis**: Multi-model approach with fallback mechanisms
- **External APIs**: Spotify (OAuth + data), Bible API, Lyrics providers

## Technology Stack

- **Web Framework**: Flask (Python) with production-ready configuration
- **Database**: PostgreSQL with SQLAlchemy ORM and migrations
- **Task Queue**: Redis + Flask-RQ2 for background processing
- **Authentication**: Spotify OAuth2 with session management
- **AI/NLP Models**:
  - Primary: KoalaAI/Text-Moderation for content flagging
  - Fallback: cardiffnlp/twitter-roberta-base-sentiment
  - Custom theme extraction and biblical analysis
- **Frontend**: Bootstrap 5, custom CSS, responsive design
- **Development**: Docker Compose for full environment
- **Testing**: Comprehensive test suite with pytest

## Core Features

### Refined User Interface
**Professional content curation interface with intelligent action strategy:**

- **Unanalyzed Songs**: "Analyze" button to start processing
- **High/Extreme Concern**: "Review" link to detailed analysis page
- **Low/Medium Concern**: Clean display with no action clutter
- **Whitelisted Songs**: Badge with optional removal

**Benefits:**
- 70% reduction in visual clutter
- Focus on songs requiring attention
- Professional appearance for ministry context
- Clear terminology and guided workflows

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

### Management APIs  
- **Whitelist Actions**: `/whitelist_song/<playlist>/<track>`
- **Remove Actions**: `/remove_whitelist_song/<playlist>/<track>`
- **Bulk Operations**: Import/export functionality for lists

## Database Schema

### Core Tables
- **Users**: Spotify OAuth data and preferences
- **Playlists**: Metadata and aggregated scores
- **Songs**: Track information and lyrics
- **PlaylistSong**: Many-to-many relationship with position tracking
- **AnalysisResult**: Detailed analysis data with JSON fields
- **Whitelist/Blacklist**: User content management

### Key Relationships
- Users → Playlists (one-to-many)
- Playlists ↔ Songs (many-to-many via PlaylistSong)
- Songs → AnalysisResult (one-to-many for historical tracking)

## Recent Improvements

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

## Future Enhancements

### Short-term
- **User preferences**: Customizable analysis sensitivity
- **Batch operations**: Bulk whitelist/blacklist management
- **Export functionality**: CSV/JSON export of analysis results

### Medium-term
- **Advanced filtering**: Genre, artist, date-based filters
- **Playlist templates**: Pre-configured analysis settings
- **Integration APIs**: Third-party Christian music services

### Long-term
- **Mobile app**: React Native companion
- **Community features**: Shared whitelists and recommendations
- **Premium tiers**: Advanced analysis and bulk operations

## Conclusion

The Christian Music Curator has evolved into a production-ready application with a professional, focused interface that efficiently guides users through content curation. The refined UI strategy and technical improvements create a tool that respects both the Christian ministry context and modern UX expectations.

**Key Achievements:**
- Professional, clutter-free interface appropriate for ministry use
- Efficient background processing for large playlist analysis
- Context-aware workflows that guide decision-making
- Robust technical foundation ready for production deployment
