/**
 * Session Timeout Warning System (Manus recommendation)
 *
 * Provides user-friendly session timeout handling with warnings
 * and the ability to extend sessions before they expire.
 */

class SessionTimeoutManager {
    constructor(options = {}) {
        this.timeoutSeconds = options.timeoutSeconds || 28800; // 8 hours default
        this.warningSeconds = options.warningSeconds || 600; // 10 minutes warning
        this.checkInterval = options.checkInterval || 60000; // Check every minute
        this.extendUrl = options.extendUrl || '/auth/extend-session';

        this.lastActivity = Date.now();
        this.warningShown = false;

        this.init();
    }

    init() {
        // Track user activity
        this.trackActivity();

        // Start timeout checking
        this.startTimeoutCheck();

        // Create warning modal
        this.createWarningModal();
    }

    trackActivity() {
        const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        events.forEach(event => {
            document.addEventListener(event, () => {
                this.lastActivity = Date.now();
                this.hideWarning();
            }, { passive: true });
        });
    }

    startTimeoutCheck() {
        setInterval(() => {
            this.checkTimeout();
        }, this.checkInterval);
    }

    checkTimeout() {
        const now = Date.now();
        const timeSinceActivity = (now - this.lastActivity) / 1000;
        const timeUntilTimeout = this.timeoutSeconds - timeSinceActivity;

        if (timeUntilTimeout <= 0) {
            // Session expired
            this.handleSessionExpired();
        } else if (timeUntilTimeout <= this.warningSeconds && !this.warningShown) {
            // Show warning
            this.showWarning(Math.floor(timeUntilTimeout));
        }
    }

    showWarning(secondsLeft) {
        this.warningShown = true;
        const modal = document.getElementById('session-warning-modal');
        const countdown = document.getElementById('session-countdown');

        if (modal && countdown) {
            countdown.textContent = Math.max(0, secondsLeft);
            modal.style.display = 'flex';

            // Update countdown every second
            this.countdownInterval = setInterval(() => {
                secondsLeft--;
                countdown.textContent = Math.max(0, secondsLeft);

                if (secondsLeft <= 0) {
                    clearInterval(this.countdownInterval);
                    this.handleSessionExpired();
                }
            }, 1000);
        }
    }

    hideWarning() {
        if (this.warningShown) {
            this.warningShown = false;
            const modal = document.getElementById('session-warning-modal');
            if (modal) {
                modal.style.display = 'none';
            }
            if (this.countdownInterval) {
                clearInterval(this.countdownInterval);
            }
        }
    }

    async extendSession() {
        try {
            const response = await fetch(this.extendUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            if (response.ok) {
                this.lastActivity = Date.now();
                this.hideWarning();
                console.log('Session extended successfully');
            } else {
                throw new Error('Failed to extend session');
            }
        } catch (error) {
            console.error('Error extending session:', error);
            this.handleSessionExpired();
        }
    }

    handleSessionExpired() {
        // Redirect to login with a helpful message
        window.location.href = '/auth/login?reason=session_expired';
    }

    createWarningModal() {
        // Only create if it doesn't already exist
        if (document.getElementById('session-warning-modal')) {
            return;
        }

        const modal = document.createElement('div');
        modal.id = 'session-warning-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 10000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
        `;

        const dialog = document.createElement('div');
        dialog.style.cssText = `
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            max-width: 400px;
            width: 90%;
            text-align: center;
        `;

        dialog.innerHTML = `
            <h3 style="margin: 0 0 1rem 0; color: #333;">Session Expiring Soon</h3>
            <p style="margin: 0 0 1.5rem 0; color: #666; line-height: 1.5;">
                Your session will expire in <strong id="session-countdown">--</strong> seconds due to inactivity.
                Would you like to extend your session?
            </p>
            <div style="display: flex; gap: 1rem; justify-content: center;">
                <button id="extend-session-btn" style="
                    background: #1db954;
                    color: white;
                    border: none;
                    padding: 0.75rem 1.5rem;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 500;
                ">Extend Session</button>
                <button id="logout-btn" style="
                    background: #666;
                    color: white;
                    border: none;
                    padding: 0.75rem 1.5rem;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 500;
                ">Logout Now</button>
            </div>
        `;

        modal.appendChild(dialog);
        document.body.appendChild(modal);

        // Add event listeners
        document.getElementById('extend-session-btn').addEventListener('click', () => {
            this.extendSession();
        });

        document.getElementById('logout-btn').addEventListener('click', () => {
            window.location.href = '/auth/logout';
        });
    }
}

// Initialize session timeout manager when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Get timeout configuration from server (could be passed via template)
    const timeoutConfig = window.sessionTimeoutConfig || {};
    new SessionTimeoutManager(timeoutConfig);
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SessionTimeoutManager;
}
