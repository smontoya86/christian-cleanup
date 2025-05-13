---
trigger: manual
---

# Christian Music Curation Application - Simplified Structure (Current Implementation as of 2025-05-13)

## Overview

The application helps Christians maintain Spotify playlists aligned with their values by analyzing song lyrics against Christian principles. It provides a simple web interface for viewing playlists, seeing alignment scores, managing content, and understanding the biblical context behind the analysis.

## System Architecture

The application follows a simplified monolithic architecture using Flask as the web framework and **PostgreSQL** as the database:

- **Frontend**: HTML/CSS with Jinja2 templates rendered by Flask
- **Backend**: Python Flask application
- **Database**: **PostgreSQL** (Stores user data, playlist info, permanent song analysis results including themes and Bible references). **Managed locally via Docker Compose for development.**
- **AI Analysis**: Utilizes `app/utils/analysis.SongAnalyzer`, which integrates a pre-trained Hugging Face model for content analysis, NLTK for sentiment, custom logic for theme extraction, and scripture lookup.
- **External APIs**: Spotify API (via Spotipy), Lyrics (via `app/utils/lyrics.LyricsFetcher`), Bible API (`scripture.api.bible` via `app/utils/bible_client.BibleClient`).

This approach avoids the complexity of microservices while providing a production-ready database setup from the beginning.

## Technology Stack

- **Web Framework**: Flask (Python)
- **Database**: **PostgreSQL** (using `SQLAlchemy` and `psycopg2`)
- **Local DB Management**: **Docker Compose**
- **Spotify Integration**: Spotipy library
- **Lyrics Retrieval**: `app/utils/lyrics.LyricsFetcher` (The underlying library used by this fetcher, e.g., `lyricsgenius`, is encapsulated within this class).
- **AI Model**: 
    - Primary sensitive content analysis via `app/utils/analysis.SongAnalyzer` using Hugging Face `transformers` with the `michellejieli/inappropriate_text_classifier` model.
- **Theme/NLP**: 
    - Keyword-based theme extraction (defined in `app/utils/analysis.SongAnalyzer`).
    - Sentiment analysis using NLTK VADER (`nltk.sentiment.vader.SentimentIntensityAnalyzer`) within `app/utils/analysis.SongAnalyzer`.
- **Bible API**: `scripture.api.bible` accessed via `app/utils/bible_client.BibleClient` (used by `app/utils/analysis.SongAnalyzer`). An alternative `app/services/bible_service.BibleService` (using `apibible` library) exists, associated with the less-complete analyzer in `app/services/analysis_service.py`.
- **Deployment Options**: Docker-based platforms (Render, Fly.io, AWS ECS, etc.), PaaS with PostgreSQL support (Heroku, Render).

## Pre-trained AI Models (Current Implementation)

- **Sensitive Content Classification**: The `app/utils/analysis.SongAnalyzer` uses `michellejieli/inappropriate_text_classifier` loaded via the Hugging Face `transformers` library. This model helps identify if text is inappropriate, offensive, etc.

*(The document previously listed other potential models like `cardiffnlp/twitter-roberta-base-sensitive-multilabel` and `TostAI/nsfw-text-detection-large` as general examples, but the above is what's currently integrated in the primary analyzer.)*

## Launch Features (MVP) - Current Implementation

### User Authentication via Spotify
**Status: Implemented**
Enables users to securely sign up and log into the application using their existing Spotify credentials via a standard OAuth2 flow managed within the Flask application.
*   User clicks "Login with Spotify" button.
*   Flask route redirects to Spotify for authorization.
*   Spotify redirects back to a callback route in Flask.
*   Flask app (using Spotipy) exchanges code for tokens, fetches user profile, stores necessary info (user ID, tokens) in **PostgreSQL**.
*   User session is established (e.g., using Flask sessions).
#### Tech Involved
*   Flask (Backend Framework)
*   Spotipy (Spotify API Python Library)
*   **PostgreSQL** (Database for storing user tokens/info)
*   SQLAlchemy (ORM)
*   HTML/Jinja2 Templates (Frontend rendering within Flask)
#### Main Requirements
*   Implement Spotify OAuth2 Authorization Code Flow.
*   Securely store and refresh access/refresh tokens in **PostgreSQL**.
*   Manage user sessions within Flask.
*   Request necessary Spotify scopes (`playlist-read-private`, `playlist-modify-public`, `playlist-modify-private`).

### Playlist Dashboard
**Status: Implemented**
Presents the user with a list of their Spotify playlists after logging in. Each playlist shows basic information. (Aggregate Christian alignment score display is part of playlist detail view).
*   Fetch all playlists for the authenticated user using Spotipy and sync with local DB (`sync_user_playlists_with_db`).
*   Render a dashboard page (HTML/Jinja2) displaying playlist names and cover art.
*   Analysis is triggered on-demand when viewing playlist details.
#### Tech Involved
*   Flask (Backend Routes & Rendering)
*   Spotipy
*   **PostgreSQL** (Storing/retrieving playlist and song metadata)
*   SQLAlchemy
*   HTML/Jinja2 Templates

### Playlist Detail View & On-Demand Song Analysis
**Status: Implemented**
Displays tracks for a selected playlist. If a song hasn't been analyzed, analysis is performed and results (including themes and linked Bible verses) are displayed.
*   Route: `app/main/routes.py :: playlist_detail(playlist_id)`
*   Fetches playlist and songs from the local **PostgreSQL** database.
*   For each song:
    *   Checks if an `AnalysisResult` exists in the database.
    *   If not, instantiates `app/utils/analysis.SongAnalyzer`.
    *   Calls `song_analyzer.analyze_song(song.title, song.artist)`.
        *   `SongAnalyzer` internally uses `app/utils/lyrics.LyricsFetcher` to get lyrics.
        *   Performs sensitive content detection (Hugging Face model), theme extraction (keywords), sentiment analysis (NLTK VADER), and scripture lookup (via `app/utils/bible_client.BibleClient` using `scripture.api.bible`).
        *   Returns a dictionary of analysis results.
    *   The route receives this dictionary and saves relevant fields (e.g., `detailed_theme_analysis` containing themes and scriptures) into the `AnalysisResult` model (specifically `AnalysisResult.themes` as JSON) in **PostgreSQL** using `SQLAlchemy`.
    *   Displays song details, analysis status, and retrieved themes/scriptures.
#### Tech Involved
*   Flask (Backend Routes & Rendering)
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
**Status: Partially Implemented**
Provides a simple web interface. Identified themes and linked Bible verses are displayed on the playlist detail page.
*   Use Jinja2 templates with basic HTML/CSS for the UI.
*   Display identified themes and linked Bible verses on the `playlist_detail.html` page (via `detailed_theme_analysis` from `AnalysisResult.themes`).
*   (A section explaining the scoring concept and threshold display for bulk removal is less developed or pending.)
#### Tech Involved
*   Flask (Rendering)
*   HTML/CSS/Jinja2 Templates

## Future Features (Post-MVP) - Simplified Approach

(These remain largely the same conceptual goals but assume PostgreSQL as the database and should build upon the currently implemented services and utils.)

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

## Implementation Guidelines for AI Agent (Cursor AI)

**(This section would typically refer to separate detailed guidelines. The focus remains on the PostgreSQL-first approach using Docker Compose for local development.)**

## Conclusion

This document reflects the current implementation state, focusing on:

1.  **Simplicity**: Using a monolithic Flask application.
2.  **Environment Parity**: Using **PostgreSQL** via Docker Compose locally and in production.
3.  **No Migration Hassle**: Avoids SQLite-to-PostgreSQL migration.
4.  **Core Value**: The MVP includes song analysis with sensitive content detection (Hugging Face model), theme extraction, sentiment analysis (NLTK), and Bible verse linking (`scripture.api.bible`), with results stored permanently in **PostgreSQL**.
5.  **Clarity on Components**: Differentiating between the primary analysis utilities in `app/utils/` (analyzer, lyrics fetcher, bible client) and other service files.

This provides a solid foundation that is easy to develop locally (with Docker) and deploy reliably while delivering the essential features. Please replace YYYY-MM-DD in the title with the current date 2025-05-13.
