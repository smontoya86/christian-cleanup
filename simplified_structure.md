---
trigger: manual
---

# Christian Music Curation Application - Simplified Structure (Revision 3 - PostgreSQL First)

## Overview

The application helps Christians maintain Spotify playlists aligned with their values by analyzing song lyrics against Christian principles. It provides a simple web interface for viewing playlists, seeing alignment scores, managing content, and understanding the biblical context behind the analysis.

## System Architecture

The application follows a simplified monolithic architecture using Flask as the web framework and **PostgreSQL** as the database:

- **Frontend**: HTML/CSS with Jinja2 templates rendered by Flask
- **Backend**: Python Flask application
- **Database**: **PostgreSQL** (Stores user data, playlist info, permanent song analysis results including themes and Bible references). **Managed locally via Docker Compose for development.**
- **AI Analysis**: Pre-trained Hugging Face RoBERTa model for content analysis, plus logic for theme extraction.
- **External APIs**: Spotify API (via Spotipy), Genius API (for lyrics), Bible API (for verse lookup/context).

This approach avoids the complexity of microservices while providing a production-ready database setup from the beginning.

## Technology Stack

- **Web Framework**: Flask (Python)
- **Database**: **PostgreSQL** (using `SQLAlchemy` and `psycopg2`)
- **Local DB Management**: **Docker Compose**
- **Spotify Integration**: Spotipy library
- **Lyrics Retrieval**: lyricsgenius library
- **AI Model**: Hugging Face `transformers` library with pre-trained RoBERTa model(s)
- **Theme/NLP**: Potentially `nltk`, `spacy`, or `scikit-learn` for theme extraction
- **Bible API**: A suitable Python library (e.g., `python-bible` or direct API calls)
- **Deployment Options**: Docker-based platforms (Render, Fly.io, AWS ECS, etc.), PaaS with PostgreSQL support (Heroku, Render).

## Pre-trained RoBERTa Models

Several existing pre-trained models are suitable for analyzing song lyrics for sensitivity:

1.  **cardiffnlp/twitter-roberta-base-sensitive-multilabel**: Detects sensitive content across multiple categories.
2.  **TostAI/nsfw-text-detection-large**: Specifically designed for detecting inappropriate content.
3.  **michellejieli/inappropriate_text_classifier**: Classifies text as appropriate or inappropriate.

These can be loaded via the Hugging Face `transformers` library. Theme extraction might require additional NLP techniques or models.

## Launch Features (MVP) - Simplified Approach (Revision 3 - PostgreSQL First)

### User Authentication via Spotify
**Strong** Enables users to securely sign up and log into the application using their existing Spotify credentials via a standard OAuth2 flow managed within the Flask application.
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
**Strong** Presents the user with a list of their Spotify playlists after logging in. Each playlist shows basic information and a calculated Christian alignment score.
*   Fetch all playlists for the authenticated user using Spotipy.
*   Render a dashboard page (HTML/Jinja2) displaying playlist names and cover art.
*   Trigger (or retrieve stored) analysis for songs in playlists to calculate aggregate scores.
*   Display the aggregate score next to each playlist.
*   Provide links to view individual playlist details.
#### Tech Involved
*   Flask (Backend Routes & Rendering)
*   Spotipy
*   **PostgreSQL** (Storing/retrieving scores)
*   SQLAlchemy
*   HTML/Jinja2 Templates
*   Background Task Runner (Optional, e.g., Celery or Flask-Executor for initial analysis)
#### Main Requirements
*   Fetch playlists efficiently.
*   Display playlist information clearly.
*   Calculate/retrieve and display playlist scores based on permanently stored song analyses in **PostgreSQL**.
*   Handle potential background processing for initial analysis of large libraries.

### Playlist Detail View
**Strong** Allows users to view the songs within a specific playlist, along with their individual Christian alignment scores and relevant Bible verses.
*   Fetch all tracks for the selected playlist using Spotipy.
*   Retrieve stored individual song analysis scores and identified themes from **PostgreSQL**.
*   For identified themes, retrieve associated Bible verse references from **PostgreSQL** (or via Bible API lookup).
*   Render a playlist detail page (HTML/Jinja2) showing song title, artist, album art, score, and linked Bible verses/themes.
*   Provide options next to each song (e.g., buttons/links) for whitelisting or removal.
#### Tech Involved
*   Flask (Backend Routes & Rendering)
*   Spotipy
*   **PostgreSQL** (Storing/retrieving song scores, themes, verse mappings)
*   SQLAlchemy
*   Bible API Python Library (For fetching verse text based on stored references)
*   HTML/Jinja2 Templates
#### Main Requirements
*   Fetch tracks for a specific playlist.
*   Display song details, stored scores, and relevant Bible verses clearly.
*   Link actions (whitelist/remove) to appropriate backend routes.

### AI-Powered Song Analysis & Rating (with Bible Linking)
**Strong** Analyzes song lyrics using a pre-trained RoBERTa model, identifies key themes, links themes to relevant Bible verses, generates an alignment score, and permanently stores the results in the **PostgreSQL** database.
*   Given a song, check if analysis results are already stored in **PostgreSQL**. If yes, return stored data.
*   If not, attempt to fetch lyrics using a Genius API library (e.g., `lyricsgenius`).
*   If lyrics are found:
    *   Pass lyrics to a loaded Hugging Face Transformers model for sensitivity/content analysis.
    *   Additionally, use NLP techniques to identify pre-defined relevant themes.
    *   Interpret model output(s) to generate a Christian alignment score.
    *   For identified themes, look up associated Bible verse references.
*   Handle instrumental tracks.
*   Permanently store the song details, score, identified themes, and associated Bible verse references in the **PostgreSQL** database.
#### Tech Involved
*   Flask (or background task runner)
*   `lyricsgenius`
*   Hugging Face `transformers` library
*   Pre-trained Model(s)
*   NLP Libraries (Optional)
*   Bible API Python Library
*   **PostgreSQL** (Database for permanently storing analysis results)
*   SQLAlchemy
#### Main Requirements
*   Reliable lyric fetching.
*   Load and run inference with chosen model(s).
*   Implement theme identification logic.
*   Implement Bible verse reference mapping/lookup.
*   Define a clear mapping from model output/themes to the scoring system.
*   Efficiently and permanently store analysis results in **PostgreSQL**.
*   Consider memory/CPU usage for model inference.

### Song & Playlist Management Actions
**Strong** Allows users to perform actions like removing songs or whitelisting content, with changes reflected in Spotify.
*   Implement Flask routes to handle actions.
*   Use Spotipy to modify Spotify playlists.
*   Update **PostgreSQL** database to mark songs/playlists as whitelisted.
*   Redirect user back with a confirmation message.
#### Tech Involved
*   Flask (Backend Routes)
*   Spotipy (Playlist modification)
*   **PostgreSQL** (Tracking whitelisted items)
*   SQLAlchemy
*   HTML/Jinja2 Templates (For user feedback)
#### Main Requirements
*   Correctly identify tracks and playlists for modification.
*   Reliable interaction with Spotify API for removal.
*   Update local whitelist status in **PostgreSQL**.
*   Provide clear user feedback.

### Basic UI & Threshold Display
**Strong** Provides a simple web interface rendered by Flask using templates, displays the basic concept of the alignment scoring, and shows linked Bible verses.
*   Use Jinja2 templates with basic HTML/CSS for the UI.
*   Include a section explaining the scoring concept.
*   Display the threshold used for any potential bulk removal features.
*   Display identified themes and linked Bible verses on the playlist detail page.
#### Tech Involved
*   Flask (Rendering)
*   HTML/CSS/Jinja2 Templates
#### Main Requirements
*   Functional, clear user interface.
*   Basic explanation of the scoring system visible to the user.
*   Clear presentation of themes and linked Bible verses.

## Future Features (Post-MVP) - Simplified Approach

(These remain largely the same but assume PostgreSQL as the database)

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
*   Implement a robust background task queue (e.g., Celery with Redis) if needed.
#### Tech Involved
*   Celery, Message Broker (Redis/RabbitMQ), Flask, JavaScript

### Basic Admin Interface
*   Create a simple admin section.
#### Tech Involved
*   Flask, **PostgreSQL** (Queries for statistics), SQLAlchemy, HTML/Jinja2 Templates

## Implementation Guidelines for AI Agent (Cursor AI) - Revision 4 (PostgreSQL-First)

**(Refer to the separate `implementation_guidelines_rev4.md` document for detailed steps focusing on the PostgreSQL-first approach using Docker Compose for local development.)**

## Conclusion

This revised simplified approach focuses on:

1.  **Simplicity**: Using a monolithic Flask application.
2.  **Environment Parity**: Using **PostgreSQL** via Docker Compose locally and in production.
3.  **No Migration Hassle**: Avoids SQLite-to-PostgreSQL migration.
4.  **Core Value**: Including permanent analysis storage and Bible verse linking in the MVP.
5.  **Implementability**: Detailed guidelines tailored for an AI agent.

This provides a solid foundation that is easy to develop locally (with Docker) and deploy reliably while delivering the essential features.
