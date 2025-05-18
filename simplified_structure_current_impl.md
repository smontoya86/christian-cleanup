---
trigger: manual
---

# Christian Music Curation Application - Simplified Structure (Current Implementation as of 2025-05-18)

## Overview

The application helps Christians maintain Spotify playlists aligned with their values by analyzing song lyrics against Christian principles. It provides a simple web interface for viewing playlists, seeing alignment scores, managing content, and understanding the biblical context behind the analysis.

## System Architecture

The application follows a simplified monolithic architecture using Flask as the web framework and **PostgreSQL** as the database:

- **Frontend**: HTML/CSS with Jinja2 templates rendered by Flask
- **Backend**: Python Flask application
- **Database**: **PostgreSQL** (Stores user data, playlist info, song analysis results, and whitelist/blacklist status). **Managed via Docker Compose for development.**
- **AI Analysis**: Utilizes `app/services/analysis_service.py` which integrates:
  - `cardiffnlp/twitter-roberta-base-sensitive-multilabel` for detecting sensitive content
  - Custom logic for theme extraction and scoring
  - NLTK for sentiment analysis
- **External APIs**: 
  - Spotify API (via Spotipy)
  - Bible API (using BSB as primary and KJV as fallback)
  - Lyrics fetching via various providers

This approach avoids the complexity of microservices while providing a production-ready database setup from the beginning.

## Technology Stack

- **Web Framework**: Flask (Python)
- **Database**: **PostgreSQL** (using `SQLAlchemy` and `psycopg2`)
- **Task Queuing**: Flask-RQ2 with Redis
- **Local DB Management**: **Docker Compose**
- **Spotify Integration**: Spotipy library
- **Lyrics Retrieval**: Multiple providers with fallback mechanisms
- **AI/NLP**:
  - `cardiffnlp/twitter-roberta-base-sensitive-multilabel` for content analysis
  - NLTK VADER for sentiment analysis
  - Custom theme extraction and scoring logic
- **Bible API**: 
  - Primary: BSB (Berean Standard Bible)
  - Fallback: KJV (King James Version)
- **Frontend**:
  - Bootstrap 5 for responsive design
  - Jinja2 templating
  - Custom CSS for theme and layout
- **Testing**:
  - Pytest for unit and integration tests
  - Factory Boy for test data generation
  - Flask-Testing for Flask-specific test cases
- **Deployment Options**: Docker-based platforms (Render, Fly.io, AWS ECS, etc.), PaaS with PostgreSQL support (Heroku, Render).

## Christian Song Analysis Framework: Current Implementation

This section details the current implementation of the framework for analyzing song lyrics based on Christian values, including thematic analysis, scripture alignment, and the scoring system.

### Core Components

1. **Thematic Framework**
   - **Positive Themes (10):** Worship/Glorifying God, Holiness of God, Goodness & Faithfulness of God, Faith/Trust in God, Hope in Christ/Eternal Life, Love/Godly Compassion, Truth/Biblical Wisdom, Redemption/Grace through Christ, Peace/God's Comfort & Presence, Spiritual Growth/Discipleship/Sanctification.
   - **Negative Themes (8):** Worldliness/Idolatry, Pride/Self-Glorification, Lust/Impurity (as a message), Selfishness/Greed/Covetousness, Hopelessness/Despair (apart from God), Rebellion/Disobedience to God, Unjust Anger/Strife/Malice (as a message), Deception/Falsehood (as a message).
   - **Purity Flags (3):** Explicit Language/Corrupting Talk, Sexual Content/Impurity (overt), Glorification of Drugs/Violence/Works of Flesh (overt).

2. **Scripture Integration**
   - Primary: BSB (Berean Standard Bible)
   - Fallback: KJV (King James Version)
   - Scripture references are stored in `scripture_mappings.json`

3. **Content Analysis**
   - Uses `cardiffnlp/twitter-roberta-base-sensitive-multilabel` for detecting sensitive content
   - Implements custom logic for theme extraction and scoring
   - Utilizes NLTK VADER for sentiment analysis

### Scoring System

- **Base Score:** 100 points
- **Purity Flag Penalties:**
  - `hate speech` detected: -75 points
  - `offensive` or `abusive` detected (not `hate speech`): -50 points (triggers 'Explicit Language / Corrupting Talk' flag)
  - 'Sexual Content / Impurity' identified: -50 points
  - 'Glorification of Drugs / Violence / Works of Flesh' identified: -25 points
- **Theme Adjustments:**
  - Negative Themes: -10 points per distinct theme
  - Positive Themes: +5 points per distinct theme
- **Final Score Calculation:**
  ```
  Final Score = 100 - (Total Purity Flag Penalties) - (Total Negative Theme Penalties) + (Total Positive Theme Points)
  ```
  (Capped between 0 and 100)

### Concern Levels

- **High Concern:** Any Purity Flag triggered OR score 0-39
- **Medium Concern:** No Purity Flags AND score 40-69
- **Low Concern:** No Purity Flags AND score 70-100

### Implementation Details

- Analysis is performed in `app/services/analysis_service.py`
- Results are stored in the `analysis_results` table
- Playlist scores are calculated based on the average of analyzed songs
- The system automatically analyzes newly added songs during playlist sync
    *   **Scoring Rubric (Finalized v3 - See MEMORY[062db178-ddbd-4491-80d6-f3012dec9ec6]):**
        *   **Score Scale:** 0-100 (Baseline: 100 points. Points are deducted/added from this baseline).
        *   **Purity Flag Impact & `cardiffnlp` Mapping:**
            *   If `hate speech` detected by `cardiffnlp`: **-75 points**.
            *   Else if `offensive` OR `abusive` detected by `cardiffnlp` (and not `hate speech`): **-50 points**. (This triggers the 'Explicit Language / Corrupting Talk' Purity Flag).
            *   'Sexual Content / Impurity (overt)' identified: **-50 points**. 
                *   *MVP Trigger:* If `offensive` is detected and contextual review implies sexual content. Future enhancements aim for more direct model detection.
                *   This penalty stacks with the general `offensive` penalty if applicable.
            *   'Glorification of Drugs / Violence / Works of Flesh (overt)' identified: **-25 points**.
                *   *MVP Trigger:* If `offensive` is detected and contextual review implies this. Future enhancements aim for more direct model detection.
                *   This penalty stacks with the general `offensive` penalty if applicable.
        *   **Negative Themes Impact:** -10 points for each distinct negative theme identified.
        *   **Positive Themes Impact:** +5 points for each distinct positive theme identified.
        *   **Score Calculation Logic:** `Final Score = 100 - (Total Purity Flag Penalties) - (Total Negative Theme Penalties) + (Total Positive Theme Points)`. The score will be capped between 0 and 100.
        *   **Concern Levels (based on Final Score and Purity Flags):**
            *   **High Concern:** If any Purity Flag is triggered, OR if no Purity Flags are triggered but the Final Score is 0-39.
            *   **Medium Concern:** If no Purity Flags are triggered AND the Final Score is 40-69.
            *   **Low Concern:** If no Purity Flags are triggered AND the Final Score is 70-100.

## Current Features

### User Authentication
- OAuth2 login with Spotify
- Session management
- User profile display

### Playlist Management
- View all Spotify playlists
- Sync playlists with Spotify
- View detailed playlist information
- Track analysis status

### Song Analysis
- Automatic analysis of song lyrics
- Content scoring based on Christian values
- Theme detection (positive/negative themes)
- Purity flag detection
- Detailed analysis reports

### User Interface
- Responsive dashboard
- Playlist cards with scores
- Detailed song analysis views
- Status indicators for analysis progress
- Error handling and user feedback

### Analysis Results
- `id`: Primary key
- `song_id`: Reference to Songs table
- `score`: Overall alignment score (0-100)
- `concern_level`: High/Medium/Low
- `themes`: JSON array of detected themes
- `purity_flags`: JSON array of purity flags
- `explanation`: Detailed analysis explanation
- `analyzed_at`: Timestamp of analysis

## API Endpoints

### Authentication
- `GET /login`: Initiate Spotify OAuth flow
- `GET /callback`: OAuth callback handler
- `GET /logout`: Log out the current user
*   Spotipy (Potentially for fresh song data if needed, though primarily uses local DB)
*   **PostgreSQL** (Storing/retrieving songs, `AnalysisResult`)
*   SQLAlchemy
*   `app/utils/analysis.SongAnalyzer` (Primary analysis logic)
*   `app/utils/lyrics.LyricsFetcher`
*   `app/utils/bible_client.BibleClient` (using `scripture.api.bible`)
*   Hugging Face `transformers` library (for `michellejieli/inappropriate_text_classifier`)
*   NLTK (for VADER sentiment)
*   HTML/Jinja2 Templates

*(Note on `app/services/analysis_service.py :: SongAnalyzer`: This file also contains a `SongAnalyzer` class. However, its AI analysis component is currently mocked, and it appears to be less complete or intended for a different purpose (e.g., placeholder for playlist-level analysis or an older version). The primary song analysis flow described above uses the analyzer from `app/utils/analysis.py`.)*

### Song & Playlist Management Actions
**Status: Implemented**
Allows users to perform actions like whitelisting/blacklisting songs or playlists, with changes reflected in Spotify and the local database.
*   Implement Flask routes to handle actions (e.g., `whitelist_song`, `blacklist_playlist`).
*   Use Spotipy to modify Spotify playlists (e.g., removing songs via `remove_tracks_from_spotify_playlist`).
*   Update **PostgreSQL** database (e.g., `Whitelist`, `Blacklist` tables) to mark songs/playlists.
*   Redirect user back with a confirmation message.
#### Tech Involved
*   Flask (Backend Routes)
*   Spotipy (Playlist modification)
*   **PostgreSQL** (Tracking whitelisted/blacklisted items)
*   SQLAlchemy
*   HTML/Jinja2 Templates (For user feedback)

### Basic UI & Threshold Display
**Status: Partially Implemented (Core display of themes/verses functional; Comprehensive UI planned in Phase 2)**
Provides a simple web interface. Identified themes and linked Bible verses are displayed on the playlist detail page.
*   Use Jinja2 templates with basic HTML/CSS for the UI.
*   Display identified themes and linked Bible verses on the `playlist_detail.html` page (via `detailed_theme_analysis` from `AnalysisResult.themes`).
*   (A section explaining the scoring concept, providing user controls for thresholds, and a more polished overall interface is planned for development in Phase 2 under Task #13: Build Comprehensive UI).
#### Tech Involved
*   Flask (Rendering)
*   HTML/CSS/Jinja2 Templates

## Future Features (Post-MVP) - Simplified Approach

(These remain largely the same conceptual goals but assume PostgreSQL as the database and should build upon the currently implemented services and utils. Some items will be directly addressed in Phase 2.)

### Stripe Payment Integration
*   Implement subscription tiers.
*   Handle payment processing via Stripe.
*   Manage user subscription status in **PostgreSQL**.
#### Tech Involved
*   Stripe Python Library, Flask, **PostgreSQL**, SQLAlchemy, HTML/Jinja2

### Advanced Filtering and Sorting
*   Allow filtering/sorting by genre, artist, etc.
*   Provide advanced sorting options.
#### Tech Involved
*   Flask, **PostgreSQL** (More complex queries, potentially add indexes), SQLAlchemy, HTML/Jinja2 Templates & potentially JavaScript

### Customizable Analysis Parameters
**Note: This will be a key focus of planned Task #12: Refine Song Analysis and Scoring Logic.**
*   Allow users to adjust analysis sensitivity/thresholds.
#### Tech Involved
*   Flask, **PostgreSQL** (Store user settings), SQLAlchemy, HTML/Jinja2 Templates

### Improved Background Task Handling
*   Implement a robust background task queue (e.g., Celery with Redis) if needed for more extensive or deferred analyses.
#### Tech Involved
*   Celery, Message Broker (Redis/RabbitMQ), Flask, JavaScript

### Basic Admin Interface
*   Create a simple admin section.
#### Tech Involved
*   Flask, **PostgreSQL** (Queries for statistics), SQLAlchemy, HTML/Jinja2 Templates

## Phase 2: Planned Development

With the initial MVP (Tasks #1-11) complete, the next phase of development focuses on enhancing the core analysis capabilities and building a comprehensive user interface.

### Task #12: Refine Song Analysis and Scoring Logic
**Status: Planned**
This task will focus on improving the existing song analysis capabilities. Key objectives include:
*   Researching and evaluating alternative/additional NLP models for more accurate sensitive content detection and nuanced theme extraction.
*   Designing and implementing an improved theme extraction mechanism that goes beyond simple keywords.
*   Developing a more sophisticated and configurable song scoring algorithm considering multiple factors (e.g., sensitivity, sentiment, thematic alignment, user preferences).
*   Adding functionality for users to customize analysis parameters or sensitivity thresholds (see "Customizable Analysis Parameters" above).
*   Thoroughly testing and validating all refined analysis and scoring logic.

### Task #13: Build Comprehensive UI for Analysis and Management
**Status: Planned**
This task aims to develop a user-friendly and feature-complete interface for all application functionalities. Key objectives include:
*   Designing mockups/wireframes for key UI screens: dashboard, playlist detail, song detail views, analysis results presentation, user settings, and blacklist/whitelist management interfaces.
*   Implementing responsive and modern HTML/CSS/JavaScript for these screens using Flask templates.
*   Integrating UI elements to seamlessly trigger song analysis, clearly display detailed results (scores, themes, scriptures), and manage user settings.
*   Creating intuitive forms and controls for managing blacklisted/whitelisted items.
*   Ensuring the UI provides clear user feedback and a smooth overall user experience.
*   Conducting usability testing to refine the interface.

## Conclusion

This document reflects the current implementation state, focusing on:
1.  **Simplicity**: Using a monolithic Flask application.
2.  **Environment Parity**: Using **PostgreSQL** via Docker Compose locally and in production.
3.  **No Migration Hassle**: Avoids SQLite-to-PostgreSQL migration.
4.  **Core Value**: The MVP includes song analysis with sensitive content detection (Hugging Face model), theme extraction, sentiment analysis (NLTK), and Bible verse linking (`scripture.api.bible`), with results stored permanently in **PostgreSQL**.
5.  **Clarity on Components**: Differentiating between the primary analysis utilities in `app/utils/` (analyzer, lyrics fetcher, bible client) and other service files.

This provides a solid foundation that is easy to develop locally (with Docker) and deploy reliably while delivering the essential features. Please replace YYYY-MM-DD in the title with the current date 2025-05-13.
