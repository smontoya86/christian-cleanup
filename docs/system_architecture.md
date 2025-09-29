# System Architecture

This document outlines the system architecture of the Christian music analysis application.

## Overview

The application is a Flask-based web application that integrates with Spotify to analyze the lyrical content of songs based on a Christian framework. The analysis is performed by a large language model (LLM) accessed through a router, and the results are stored in a PostgreSQL database.

## Tech Stack

*   **Backend:** Flask (Gunicorn), Python 3.11
*   **Database:** PostgreSQL (SQLAlchemy 2.x)
*   **Cache/Queue:** Redis
*   **LLM Integration:** OpenAI-compatible HTTP router (RunPod vLLM or Ollama)
*   **Containerization:** Docker + docker-compose

## System Components

### Web Application

The Flask web application provides the user interface for the application. It includes the following key components:

*   **Authentication:** Users can log in with their Spotify account.
*   **Dashboard:** Displays the user's Spotify playlists.
*   **Playlist Detail:** Shows the songs in a selected playlist and allows the user to initiate the analysis.
*   **Song Detail:** Displays the analysis results for a selected song.

### Analysis Service

The analysis service is responsible for orchestrating the analysis of songs. It performs the following steps:

1.  Fetches the lyrics for a song.
2.  Sends the lyrics to the LLM router for analysis.
3.  Parses the analysis results and stores them in the database.

### LLM Router

The LLM router is an OpenAI-compatible HTTP client that sends requests to the configured LLM endpoint. It supports both RunPod vLLM and Ollama.

### Database

The PostgreSQL database stores all the application data, including:

*   Users
*   Playlists
*   Songs
*   Analysis results

## Hot-Reloading

The application now includes a hot-reloading mechanism for the analyzer. This allows for rapid iteration and testing of the analysis logic without restarting the entire application. The reloader monitors the `router_analyzer.py` file for changes and automatically restarts the application when a change is detected.

## Code Cleanup

The codebase has been cleaned up by removing the following directories and files:

*   `tests`
*   `training_data`
*   `.pytest_cache`
*   `__pycache__` directories

This has resulted in a smaller and more manageable codebase.

## System Architecture Diagram

```mermaid
graph LR
    A[Browser/UI] -->|HTTPS| W[Flask/Gunicorn (web)]
    W <-->|SQL| P[(PostgreSQL)]
    W <-->|Cache| R[(Redis)]
    subgraph LLM Router
        V[Runpod vLLM]
        O[Ollama]
    end
    W -->|OpenAI-compatible /v1| V
    W -.fallback.-> O
```

