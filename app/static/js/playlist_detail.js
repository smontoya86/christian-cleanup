/**
 * Playlist Detail Page JavaScript
 * This file now serves as a simple entry point that leverages the modular architecture
 */

// Import the main application module
import app from './main.js';

// The main.js module automatically detects this is a playlist detail page
// and initializes the PlaylistAnalysis module with all required functionality.

// All previous functionality is now handled by:
// - PlaylistAnalysis module (playlist and song analysis operations)
// - UIHelpers (UI state management, progress tracking, error handling)
// - ApiService (HTTP requests with proper error handling)

// The main app will automatically:
// 1. Detect this is a playlist detail page
// 2. Extract the playlist ID from the data attribute
// 3. Initialize the PlaylistAnalysis module
// 4. Set up all event listeners for analysis buttons
// 5. Handle view toggling between list and grid
// 6. Manage progress tracking and error display

// For legacy compatibility, expose some functionality globally if needed
window.playlistDetailPage = {
    getPlaylistAnalysis() {
        return app.getModule('playlistAnalysis');
    },
    
    showError(message) {
        window.showNotification(message, 'error');
    },
    
    showSuccess(message) {
        window.showNotification(message, 'success');
    }
};

// Log successful module load
console.log('Playlist detail page module loaded - using modular architecture');
