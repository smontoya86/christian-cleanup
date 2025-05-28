"""
Error Tracking Utility for Christian Cleanup Application
Provides error tracking, aggregation, and alerting capabilities.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
from threading import Lock
from dataclasses import dataclass, asdict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .logging import get_logger

logger = get_logger('app.error_tracking')


@dataclass
class ErrorEvent:
    """Represents a tracked error event."""
    timestamp: datetime
    error_type: str
    message: str
    stack_trace: Optional[str] = None
    user_id: Optional[str] = None
    request_path: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    severity: str = 'error'  # error, warning, critical
    resolved: bool = False
    count: int = 1


@dataclass
class ErrorAlert:
    """Represents an error alert configuration."""
    name: str
    error_types: List[str]
    threshold_count: int
    time_window_minutes: int
    severity: str
    enabled: bool = True
    callback: Optional[Callable] = None


class ErrorTracker:
    """
    Comprehensive error tracking system with alerting capabilities.
    """
    
    def __init__(self, max_events: int = 10000, cleanup_interval_hours: int = 24):
        self.max_events = max_events
        self.cleanup_interval_hours = cleanup_interval_hours
        
        # Thread-safe storage
        self._lock = Lock()
        self._events: deque = deque(maxlen=max_events)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._hourly_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Alert configuration
        self._alerts: Dict[str, ErrorAlert] = {}
        self._alert_callbacks: Dict[str, Callable] = {}
        self._last_cleanup = datetime.utcnow()
        
        # Built-in alert rules
        self._setup_default_alerts()
        
        logger.info("Error tracker initialized")
    
    def _setup_default_alerts(self):
        """Setup default error alert rules."""
        default_alerts = [
            ErrorAlert(
                name='high_error_rate',
                error_types=['*'],  # All error types
                threshold_count=50,
                time_window_minutes=15,
                severity='warning'
            ),
            ErrorAlert(
                name='critical_errors',
                error_types=['DatabaseError', 'SpotifyAPIError', 'AnalysisServiceError'],
                threshold_count=5,
                time_window_minutes=5,
                severity='critical'
            ),
            ErrorAlert(
                name='analysis_failures',
                error_types=['AnalysisError', 'AnalysisTimeoutError', 'LyricsNotFoundError'],
                threshold_count=20,
                time_window_minutes=10,
                severity='warning'
            )
        ]
        
        for alert in default_alerts:
            self._alerts[alert.name] = alert
    
    def track_error(
        self,
        error_type: str,
        message: str,
        stack_trace: Optional[str] = None,
        user_id: Optional[str] = None,
        request_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        severity: str = 'error'
    ) -> str:
        """
        Track an error event.
        
        Args:
            error_type: Type of error (class name)
            message: Error message
            stack_trace: Full stack trace
            user_id: User associated with the error
            request_path: Request path where error occurred
            context: Additional context information
            severity: Error severity (error, warning, critical)
            
        Returns:
            Event ID for tracking
        """
        event = ErrorEvent(
            timestamp=datetime.utcnow(),
            error_type=error_type,
            message=message,
            stack_trace=stack_trace,
            user_id=user_id,
            request_path=request_path,
            context=context or {},
            severity=severity
        )
        
        with self._lock:
            # Add to events
            self._events.append(event)
            
            # Update counters
            self._error_counts[error_type] += 1
            hour_key = event.timestamp.strftime('%Y-%m-%d-%H')
            self._hourly_counts[hour_key][error_type] += 1
            
            # Check for alerts
            self._check_alerts(event)
            
            # Cleanup if needed
            self._cleanup_if_needed()
        
        logger.debug(f"Tracked error: {error_type} - {message}")
        
        return f"{error_type}_{int(event.timestamp.timestamp())}"
    
    def _check_alerts(self, event: ErrorEvent):
        """Check if any alerts should be triggered."""
        current_time = event.timestamp
        
        for alert_name, alert in self._alerts.items():
            if not alert.enabled:
                continue
                
            # Check if error type matches
            if '*' not in alert.error_types and event.error_type not in alert.error_types:
                continue
            
            # Count recent events
            window_start = current_time - timedelta(minutes=alert.time_window_minutes)
            recent_count = sum(
                1 for e in self._events
                if (e.timestamp >= window_start and 
                    ('*' in alert.error_types or e.error_type in alert.error_types))
            )
            
            # Trigger alert if threshold exceeded
            if recent_count >= alert.threshold_count:
                self._trigger_alert(alert, recent_count, event)
    
    def _trigger_alert(self, alert: ErrorAlert, count: int, trigger_event: ErrorEvent):
        """Trigger an alert."""
        alert_data = {
            'alert_name': alert.name,
            'severity': alert.severity,
            'error_count': count,
            'time_window': alert.time_window_minutes,
            'trigger_event': asdict(trigger_event),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.warning(f"Error alert triggered: {alert.name} - {count} errors in {alert.time_window_minutes} minutes")
        
        # Call alert callback if configured
        if alert.callback:
            try:
                alert.callback(alert_data)
            except Exception as e:
                logger.error(f"Alert callback failed for {alert.name}: {e}")
        
        # Call global callbacks
        for callback_name, callback in self._alert_callbacks.items():
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"Global alert callback {callback_name} failed: {e}")
    
    def add_alert_callback(self, name: str, callback: Callable):
        """Add a global alert callback function."""
        self._alert_callbacks[name] = callback
        logger.info(f"Added alert callback: {name}")
    
    def remove_alert_callback(self, name: str):
        """Remove an alert callback."""
        if name in self._alert_callbacks:
            del self._alert_callbacks[name]
            logger.info(f"Removed alert callback: {name}")
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the last N hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            recent_events = [e for e in self._events if e.timestamp >= cutoff_time]
            
            # Count by type
            error_counts = defaultdict(int)
            severity_counts = defaultdict(int)
            hourly_distribution = defaultdict(int)
            
            for event in recent_events:
                error_counts[event.error_type] += 1
                severity_counts[event.severity] += 1
                hour_key = event.timestamp.strftime('%H')
                hourly_distribution[hour_key] += 1
            
            return {
                'total_errors': len(recent_events),
                'error_types': dict(error_counts),
                'severity_breakdown': dict(severity_counts),
                'hourly_distribution': dict(hourly_distribution),
                'most_common_errors': sorted(
                    error_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10],
                'time_range_hours': hours,
                'summary_generated': datetime.utcnow().isoformat()
            }
    
    def get_recent_errors(self, limit: int = 100, error_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent error events."""
        with self._lock:
            events = list(self._events)
            
            if error_type:
                events = [e for e in events if e.error_type == error_type]
            
            # Sort by timestamp (newest first) and limit
            events.sort(key=lambda x: x.timestamp, reverse=True)
            return [asdict(event) for event in events[:limit]]
    
    def get_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get error trends and patterns."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            recent_events = [e for e in self._events if e.timestamp >= cutoff_time]
            
            # Calculate trends
            hourly_counts = defaultdict(int)
            for event in recent_events:
                hour_key = event.timestamp.strftime('%Y-%m-%d %H:00')
                hourly_counts[hour_key] += 1
            
            # Find patterns
            total_errors = len(recent_events)
            avg_per_hour = total_errors / max(hours, 1)
            
            # Get top error types
            type_counts = defaultdict(int)
            for event in recent_events:
                type_counts[event.error_type] += 1
            
            return {
                'total_errors': total_errors,
                'average_per_hour': round(avg_per_hour, 2),
                'hourly_breakdown': dict(hourly_counts),
                'top_error_types': sorted(
                    type_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5],
                'analysis_period_hours': hours
            }
    
    def update_alert_configuration(self, alert_name: str, **kwargs):
        """Update an alert configuration."""
        if alert_name in self._alerts:
            alert = self._alerts[alert_name]
            for key, value in kwargs.items():
                if hasattr(alert, key):
                    setattr(alert, key, value)
            logger.info(f"Updated alert configuration: {alert_name}")
        else:
            logger.warning(f"Alert not found: {alert_name}")
    
    def _cleanup_if_needed(self):
        """Clean up old data if needed."""
        current_time = datetime.utcnow()
        if (current_time - self._last_cleanup).total_seconds() > (self.cleanup_interval_hours * 3600):
            self._cleanup_old_data()
            self._last_cleanup = current_time
    
    def _cleanup_old_data(self):
        """Clean up old hourly counts data."""
        cutoff_time = datetime.utcnow() - timedelta(hours=48)  # Keep 48 hours
        cutoff_key = cutoff_time.strftime('%Y-%m-%d-%H')
        
        old_keys = [k for k in self._hourly_counts.keys() if k < cutoff_key]
        for key in old_keys:
            del self._hourly_counts[key]
        
        logger.debug(f"Cleaned up {len(old_keys)} old hourly count entries")
    
    def get_alert_status(self) -> Dict[str, Any]:
        """Get current alert configuration and status."""
        return {
            'alerts': {
                name: {
                    'error_types': alert.error_types,
                    'threshold_count': alert.threshold_count,
                    'time_window_minutes': alert.time_window_minutes,
                    'severity': alert.severity,
                    'enabled': alert.enabled
                }
                for name, alert in self._alerts.items()
            },
            'callbacks': list(self._alert_callbacks.keys()),
            'total_tracked_events': len(self._events)
        }


# Global error tracker instance
error_tracker = ErrorTracker()


def track_error_from_exception(
    exception: Exception,
    user_id: Optional[str] = None,
    request_path: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Convenience function to track an error from an exception.
    
    Args:
        exception: The exception to track
        user_id: User associated with the error
        request_path: Request path where error occurred
        context: Additional context information
        
    Returns:
        Event ID for tracking
    """
    import traceback
    
    # Determine severity based on exception type
    severity = 'error'
    if 'Critical' in type(exception).__name__ or 'Fatal' in type(exception).__name__:
        severity = 'critical'
    elif 'Warning' in type(exception).__name__:
        severity = 'warning'
    
    return error_tracker.track_error(
        error_type=type(exception).__name__,
        message=str(exception),
        stack_trace=traceback.format_exc(),
        user_id=user_id,
        request_path=request_path,
        context=context,
        severity=severity
    )


def email_alert_callback(alert_data: Dict[str, Any]):
    """
    Email alert callback function.
    Configure with SMTP settings for production use.
    """
    try:
        # This is a placeholder - configure SMTP settings as needed
        logger.info(f"Email alert would be sent: {alert_data['alert_name']}")
        
        # Example implementation:
        # msg = MIMEMultipart()
        # msg['From'] = 'alerts@example.com'
        # msg['To'] = 'admin@example.com'
        # msg['Subject'] = f"Error Alert: {alert_data['alert_name']}"
        # 
        # body = f"""
        # Alert: {alert_data['alert_name']}
        # Severity: {alert_data['severity']}
        # Error Count: {alert_data['error_count']}
        # Time Window: {alert_data['time_window']} minutes
        # 
        # Trigger Event:
        # Type: {alert_data['trigger_event']['error_type']}
        # Message: {alert_data['trigger_event']['message']}
        # """
        # 
        # msg.attach(MIMEText(body, 'plain'))
        # 
        # server = smtplib.SMTP('smtp.example.com', 587)
        # server.starttls()
        # server.login('username', 'password')
        # text = msg.as_string()
        # server.sendmail('alerts@example.com', 'admin@example.com', text)
        # server.quit()
        
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")


def slack_alert_callback(alert_data: Dict[str, Any]):
    """
    Slack alert callback function.
    Configure with Slack webhook URL for production use.
    """
    try:
        import requests
        
        # This is a placeholder - configure Slack webhook URL
        logger.info(f"Slack alert would be sent: {alert_data['alert_name']}")
        
        # Example implementation:
        # webhook_url = 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        # 
        # message = {
        #     'text': f"🚨 Error Alert: {alert_data['alert_name']}",
        #     'attachments': [{
        #         'color': 'danger' if alert_data['severity'] == 'critical' else 'warning',
        #         'fields': [
        #             {'title': 'Severity', 'value': alert_data['severity'], 'short': True},
        #             {'title': 'Error Count', 'value': str(alert_data['error_count']), 'short': True},
        #             {'title': 'Time Window', 'value': f"{alert_data['time_window']} minutes", 'short': True},
        #             {'title': 'Error Type', 'value': alert_data['trigger_event']['error_type'], 'short': True}
        #         ]
        #     }]
        # }
        # 
        # response = requests.post(webhook_url, json=message)
        # response.raise_for_status()
        
    except Exception as e:
        logger.error(f"Failed to send Slack alert: {e}")


# Setup default alert callbacks
error_tracker.add_alert_callback('email', email_alert_callback)
error_tracker.add_alert_callback('slack', slack_alert_callback) 