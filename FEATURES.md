# Christian Music Curator - Feature Documentation

## Overview
Christian Music Curator is a web application that helps Christians make informed decisions about their music choices by analyzing songs for alignment with Christian values. The platform integrates with Spotify to automatically evaluate music content and provide guidance for faith-based music curation.

## Core Features

### 🎵 **Spotify Integration & Authentication**
Seamless OAuth integration with Spotify that allows users to connect their accounts securely. Users can authorize the application to access their playlists, liked songs, and music library for comprehensive analysis.

### 📊 **Intelligent Song Analysis**
Advanced AI-powered analysis engine that evaluates songs across multiple dimensions including sentiment, toxicity, emotional content, and Christian value alignment. Each song receives a comprehensive score indicating its suitability for Christian listeners.

### 🎯 **Real-Time Progress Tracking**
Unified progress tracking system that provides real-time updates on analysis status across the dashboard. Users can monitor background analysis jobs with accurate progress bars, completion estimates, and processing rates.

### 📋 **Playlist Management & Sync**
Automatic synchronization of user's Spotify playlists with intelligent categorization and scoring. Users can view all their playlists with analysis results, completion percentages, and recommended actions.

### 🏠 **Comprehensive Dashboard**
Centralized dashboard displaying user statistics, analysis progress, playlist overview, and key metrics. Provides at-a-glance insights into music library composition and Christian content alignment.

### ⚡ **Background Analysis Processing**
Scalable background job system that processes large music libraries without blocking the user interface. Handles bulk analysis operations with queue management and progress reporting.

### 🔍 **Song Scoring & Recommendations**
Multi-dimensional scoring system that evaluates songs based on:
- **Sentiment Analysis**: Positive vs negative emotional content
- **Toxicity Detection**: Identification of harmful or inappropriate language
- **Emotion Classification**: Detection of specific emotional themes
- **Christian Value Alignment**: Assessment of content compatibility with Christian principles

### 📈 **Analytics & Insights**
Detailed analytics showing music consumption patterns, content analysis trends, and recommendations for improving playlist alignment with Christian values.

### 🎨 **Modern Responsive UI**
Clean, intuitive interface built with Bootstrap that works seamlessly across desktop and mobile devices. Features dark/light mode support and accessibility compliance.

### 🔐 **Secure User Management**
Robust authentication system with session management, secure API key handling, and user data protection following privacy best practices.

## Technical Architecture

### **Backend Technologies**
- **Python 3.x** - Core application logic
- **Flask** - Web framework with RESTful API design
- **SQLAlchemy** - Database ORM for data modeling
- **PostgreSQL** - Primary database for user data and analysis results
- **Celery** - Distributed task queue for background processing
- **Redis** - In-memory cache and message broker

### **Frontend Technologies**
- **HTML5/CSS3** - Modern web standards
- **JavaScript (ES6+)** - Interactive functionality
- **Bootstrap 5** - Responsive UI framework
- **Jinja2** - Server-side templating

### **AI/ML Components**
- **Hugging Face Transformers** - Pre-trained models for NLP tasks
- **CardiffNLP RoBERTa** - Sentiment analysis model
- **Unitary Toxic-BERT** - Toxicity detection model
- **J-Hartmann Emotion** - Emotion classification model

### **External APIs**
- **Spotify Web API** - Music data and playlist access
- **Spotify OAuth 2.0** - Secure authentication flow

### **Infrastructure & DevOps**
- **Docker** - Containerized deployment
- **Docker Compose** - Multi-service orchestration
- **Git/GitHub** - Version control and CI/CD
- **Environment Variables** - Secure configuration management

## Feature Requirements

### **Functional Requirements**

#### User Authentication
- Users must authenticate via Spotify OAuth
- Session management with secure token handling
- Automatic token refresh for long-running sessions

#### Music Analysis
- Analyze individual songs and entire playlists
- Multi-model AI evaluation for comprehensive scoring
- Batch processing for large music libraries
- Real-time progress tracking with accurate ETAs

#### Data Management
- Persistent storage of analysis results
- User preference and settings management
- Playlist synchronization with Spotify
- Historical analysis data retention

#### User Interface
- Responsive design for all device types
- Real-time updates without page refresh
- Intuitive navigation and clear data presentation
- Accessibility compliance (WCAG 2.1)

### **Non-Functional Requirements**

#### Performance
- Support for concurrent user analysis jobs
- Sub-second response times for dashboard interactions
- Efficient handling of large playlist processing
- Scalable architecture for user growth

#### Security
- Secure API key and token management
- Data encryption in transit and at rest
- Privacy-compliant data handling
- Protection against common web vulnerabilities

#### Reliability
- 99.9% uptime availability
- Graceful error handling and recovery
- Data backup and disaster recovery
- Monitoring and alerting systems

#### Scalability
- Horizontal scaling capability
- Database optimization for large datasets
- CDN integration for static assets
- Load balancing for high traffic

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│  Web Browser (Chrome, Firefox, Safari, Mobile)                 │
│  ├── HTML/CSS/JavaScript Frontend                              │
│  ├── Bootstrap UI Components                                   │
│  └── Real-time Progress Updates                                │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  │ HTTPS
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  Flask Web Application (Python)                                │
│  ├── Authentication Routes (/auth/*)                           │
│  ├── Dashboard Routes (/dashboard, /)                          │
│  ├── API Routes (/api/*)                                       │
│  ├── Playlist Management (/playlist/*)                         │
│  └── Settings Routes (/settings)                               │
└─────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
┌─────────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│   EXTERNAL APIs     │ │  DATA LAYER     │ │  PROCESSING LAYER   │
├─────────────────────┤ ├─────────────────┤ ├─────────────────────┤
│ Spotify Web API     │ │ PostgreSQL DB   │ │ Background Jobs     │
│ ├── OAuth 2.0       │ │ ├── Users       │ │ ├── Celery Workers  │
│ ├── Playlists       │ │ ├── Songs       │ │ ├── Analysis Queue  │
│ ├── Track Data      │ │ ├── Playlists   │ │ └── Progress Track  │
│ └── User Profile    │ │ ├── Analysis    │ │                     │
│                     │ │ └── Results     │ │ Redis Cache         │
│                     │ │                 │ │ ├── Session Store   │
│                     │ │ SQLAlchemy ORM  │ │ ├── Job Queue       │
│                     │ │ ├── Models      │ │ └── Temp Data       │
│                     │ │ ├── Migrations  │ │                     │
│                     │ │ └── Relationships│ │                     │
└─────────────────────┘ └─────────────────┘ └─────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AI/ML LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  Hugging Face Transformers                                     │
│  ├── Sentiment Analysis (CardiffNLP RoBERTa)                   │
│  ├── Toxicity Detection (Unitary Toxic-BERT)                  │
│  ├── Emotion Classification (J-Hartmann)                      │
│  └── Custom Christian Values Scoring Algorithm                │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                         │
├─────────────────────────────────────────────────────────────────┤
│  Docker Containers                                             │
│  ├── Web Application Container                                 │
│  ├── Database Container (PostgreSQL)                           │
│  ├── Redis Container                                           │
│  └── Worker Containers (Celery)                                │
│                                                                 │
│  Orchestration: Docker Compose                                 │
│  Monitoring: Logs, Health Checks, Metrics                      │
│  Storage: Persistent Volumes, Model Cache                      │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### **User Authentication Flow**
1. User clicks "Login with Spotify"
2. Redirected to Spotify OAuth authorization
3. User grants permissions
4. Spotify returns authorization code
5. Application exchanges code for access/refresh tokens
6. User session established with secure token storage

### **Analysis Processing Flow**
1. User initiates playlist analysis
2. Background job queued in Redis
3. Celery worker picks up job
4. Songs fetched from Spotify API
5. Each song processed through AI models
6. Results stored in PostgreSQL
7. Real-time progress updates sent to frontend
8. Completion notification and results display

### **Dashboard Data Flow**
1. User loads dashboard
2. Real-time data fetched from database
3. Progress status checked from background jobs
4. Statistics calculated and cached
5. Unified progress system updates all displays
6. WebSocket/polling for live updates

## Development Status

### ✅ **Completed Features**
- Spotify OAuth integration
- User authentication and session management
- Playlist synchronization
- AI-powered song analysis
- Background job processing
- Real-time progress tracking
- Responsive dashboard UI
- Database schema and models

### 🚧 **In Development**
- Advanced filtering and search
- Playlist recommendation engine
- API rate limiting optimization
- Enhanced analytics dashboard
