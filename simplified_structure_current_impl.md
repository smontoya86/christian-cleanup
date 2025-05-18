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
- **Task Queuing**: Flask-RQ2 with Redis
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

## Christian Song Analysis Framework: Design Details

This section details the framework for analyzing song lyrics based on Christian values, including thematic analysis, scripture alignment, and a scoring rubric.

*   **Objective:** To develop a system that analyzes song lyrics for alignment with Christian teachings, identifies potentially problematic content, and provides a clear, actionable assessment for users.
*   **Key Components:**
    *   **Thematic Framework (Finalized):**
        *   Identifies 10 positive themes, 8 negative themes, and 3 purity flags relevant to Christian values.
        *   Full list and details are captured in Memory (`1dbdbe3c-048b-4d4a-a954-dc2288237856`).
        *   **Positive Themes (10):** Worship/Glorifying God, Holiness of God, Goodness & Faithfulness of God, Faith/Trust in God, Hope in Christ/Eternal Life, Love/Godly Compassion, Truth/Biblical Wisdom, Redemption/Grace through Christ, Peace/God's Comfort & Presence, Spiritual Growth/Discipleship/Sanctification.
        *   **Negative Themes (8):** Worldliness/Idolatry, Pride/Self-Glorification, Lust/Impurity (as a message), Selfishness/Greed/Covetousness, Hopelessness/Despair (apart from God), Rebellion/Disobedience to God, Unjust Anger/Strife/Malice (as a message), Deception/Falsehood (as a message).
        *   **Purity Flags (3):** Explicit Language/Corrupting Talk, Sexual Content/Impurity (overt), Glorification of Drugs/Violence/Works of Flesh (overt).
    *   **Scripture Integration (API: BSB/KJV):**
        *   Goal: To provide scriptural context (primarily BSB, fallback KJV via API) for identified themes and flags.
        *   Storage: A file named `scripture_mappings.json` defines the structure for associating themes/flags with verse references. The scripture text itself is fetched via the Bible API. The user populates `scripture_mappings.json` with references.
    *   **NLP Model Application:**
        *   Sensitive Content Detection (`cardiffnlp/twitter-roberta-base-sensitive-multilabel`): Outputs will map to Purity Flags.
        *   **Future Enhancements for Multi-Modal Analysis Strategy:**
            1.  **Layered Purity Flag Detection:**
                *   **Initial Broad Pass:** Continue using `cardiffnlp/twitter-roberta-base-sensitive-multilabel` for initial detection of `hate speech`, `offensive`, `abusive`.
                *   **Secondary Specific Models:** If `offensive` is detected (and isn't `hate speech`), route the problematic text segment to more specialized models (to be researched/integrated) for classifying the *type* of offense, specifically:
                    *   Model for "Sexual Content / Impurity."
                    *   Model for "Glorification of Drugs / Substance Abuse."
                    *   Model for "Glorification of Violence."
                *   This provides more direct evidence for these specific Purity Flags.
            2.  **Dedicated Thematic Analysis Model(s):**
                *   Implement a separate NLP model or pipeline specifically for identifying the 10 positive and 8 negative themes from the song lyrics.
                *   **Approaches to consider:**
                    *   **Zero-Shot Classification Models:** (e.g., `facebook/bart-large-mnli`) providing theme names/descriptions as candidate labels.
                    *   **Fine-Tuning:** Fine-tune a language model on a custom dataset of lyrics tagged with our specific themes.
                    *   **LLM-based Thematic Extraction:** Utilize larger language models with carefully crafted prompts.
            3.  **Keyword and Pattern Augmentation:**
                *   Develop and maintain curated lists of keywords, phrases, and regex patterns associated with each Purity Flag and Theme to augment model-based detection.
            4.  **Confidence Scoring and Thresholds:**
                *   Utilize confidence scores from NLP models and set thresholds to determine if a detected flag or theme is considered present enough to impact the score.
            5.  **Contextual Analysis for Ambiguity:**
                *   For lyrics/themes flagged with lower confidence, implement logic to consider surrounding context to help disambiguate (advanced enhancement).
            6.  **User Feedback Loop for Model Improvement:**
                *   (Long-term) Design a mechanism for users to provide feedback on the accuracy of detected flags/themes to iteratively improve models.
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

## Launch Features (MVP) - Current Implementation

**(All features below correspond to the completed Tasks #1-11 and are considered part of the initial MVP.)**

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
