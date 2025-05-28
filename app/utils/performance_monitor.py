"""
Performance Monitoring and Alerting System for Christian Cleanup Application
Tracks performance metrics, detects anomalies, and triggers alerts for critical issues.
"""

import time
import threading
import statistics
import psutil
import redis
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from flask import current_app
import logging
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .metrics import metrics_collector
from .logging import get_logger

logger = get_logger('app.performance')


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    duration_seconds: int = 300  # 5 minutes
    enabled: bool = True


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    condition: str  # 'greater_than', 'less_than', 'equals'
    threshold: float
    duration_seconds: int
    severity: str  # 'warning', 'critical'
    enabled: bool = True
    cooldown_seconds: int = 3600  # 1 hour cooldown between alerts


@dataclass
class PerformanceAlert:
    """Performance alert data."""
    timestamp: datetime
    rule_name: str
    metric_name: str
    current_value: float
    threshold: float
    severity: str
    message: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system that tracks application metrics,
    detects performance issues, and triggers alerts.
    """
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.monitoring_active = False
        self.monitor_thread = None
        self.lock = threading.Lock()
        
        # Performance data storage
        self.performance_history = defaultdict(lambda: deque(maxlen=1000))
        self.active_alerts = {}
        self.alert_history = deque(maxlen=500)
        self.last_alert_times = {}
        
        # Default performance thresholds
        self.thresholds = {
            'response_time_ms': PerformanceThreshold(
                metric_name='response_time_ms',
                warning_threshold=2000,  # 2 seconds
                critical_threshold=5000  # 5 seconds
            ),
            'memory_usage_percent': PerformanceThreshold(
                metric_name='memory_usage_percent',
                warning_threshold=80,
                critical_threshold=95
            ),
            'cpu_usage_percent': PerformanceThreshold(
                metric_name='cpu_usage_percent',
                warning_threshold=80,
                critical_threshold=95
            ),
            'database_query_time_ms': PerformanceThreshold(
                metric_name='database_query_time_ms',
                warning_threshold=1000,  # 1 second
                critical_threshold=3000  # 3 seconds
            ),
            'redis_operation_time_ms': PerformanceThreshold(
                metric_name='redis_operation_time_ms',
                warning_threshold=500,
                critical_threshold=1000
            ),
            'analysis_time_ms': PerformanceThreshold(
                metric_name='analysis_time_ms',
                warning_threshold=30000,  # 30 seconds
                critical_threshold=60000  # 1 minute
            ),
            'queue_size': PerformanceThreshold(
                metric_name='queue_size',
                warning_threshold=100,
                critical_threshold=500
            ),
            'error_rate_percent': PerformanceThreshold(
                metric_name='error_rate_percent',
                warning_threshold=5,
                critical_threshold=15
            )
        }
        
        # Alert rules
        self.alert_rules = {
            'high_response_time': AlertRule(
                name='high_response_time',
                condition='greater_than',
                threshold=3000,
                duration_seconds=300,
                severity='warning'
            ),
            'critical_response_time': AlertRule(
                name='critical_response_time',
                condition='greater_than',
                threshold=8000,
                duration_seconds=60,
                severity='critical'
            ),
            'high_memory_usage': AlertRule(
                name='high_memory_usage',
                condition='greater_than',
                threshold=85,
                duration_seconds=600,
                severity='warning'
            ),
            'critical_memory_usage': AlertRule(
                name='critical_memory_usage',
                condition='greater_than',
                threshold=95,
                duration_seconds=300,
                severity='critical'
            ),
            'high_error_rate': AlertRule(
                name='high_error_rate',
                condition='greater_than',
                threshold=10,
                duration_seconds=300,
                severity='critical'
            ),
            'queue_backup': AlertRule(
                name='queue_backup',
                condition='greater_than',
                threshold=200,
                duration_seconds=600,
                severity='warning'
            )
        }
        
        # Alert callbacks
        self.alert_callbacks = []
        
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add a callback function to be called when alerts are triggered."""
        self.alert_callbacks.append(callback)
        
    def start_monitoring(self, interval_seconds: int = 30):
        """Start the performance monitoring thread."""
        if self.monitoring_active:
            logger.warning("Performance monitoring is already active")
            return
            
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"Performance monitoring started with {interval_seconds}s interval")
        
    def stop_monitoring(self):
        """Stop the performance monitoring thread."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
        
    def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop that runs in a separate thread."""
        while self.monitoring_active:
            try:
                self._collect_system_metrics()
                self._collect_application_metrics()
                self._check_alert_conditions()
                self._cleanup_old_data()
                
                time.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in performance monitoring loop: {e}", exc_info=True)
                time.sleep(interval_seconds)
                
    def _collect_system_metrics(self):
        """Collect system-level performance metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self._record_metric('cpu_usage_percent', cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self._record_metric('memory_usage_percent', memory.percent)
            self._record_metric('memory_available_mb', memory.available / 1024 / 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self._record_metric('disk_usage_percent', disk_percent)
            
            # Network I/O
            network = psutil.net_io_counters()
            self._record_metric('network_bytes_sent', network.bytes_sent)
            self._record_metric('network_bytes_recv', network.bytes_recv)
            
            logger.debug(f"System metrics collected - CPU: {cpu_percent}%, Memory: {memory.percent}%")
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            
    def _collect_application_metrics(self):
        """Collect application-specific performance metrics."""
        try:
            # Get metrics from the metrics collector
            metrics_summary = metrics_collector.get_metrics_summary()
            
            # API response times
            if 'api' in metrics_summary:
                api_metrics = metrics_summary['api']
                if api_metrics.get('average_duration_ms'):
                    self._record_metric('response_time_ms', api_metrics['average_duration_ms'])
                if api_metrics.get('error_rate'):
                    self._record_metric('error_rate_percent', api_metrics['error_rate'])
                    
            # Database query times
            if 'database' in metrics_summary:
                db_metrics = metrics_summary['database']
                if db_metrics.get('average_duration_ms'):
                    self._record_metric('database_query_time_ms', db_metrics['average_duration_ms'])
                    
            # Redis operation times
            if 'redis' in metrics_summary:
                redis_metrics = metrics_summary['redis']
                if redis_metrics.get('average_duration_ms'):
                    self._record_metric('redis_operation_time_ms', redis_metrics['average_duration_ms'])
                    
            # Analysis times
            if 'analysis' in metrics_summary:
                analysis_metrics = metrics_summary['analysis']
                if analysis_metrics.get('average_duration_ms'):
                    self._record_metric('analysis_time_ms', analysis_metrics['average_duration_ms'])
                    
            # Queue sizes (if Redis is available)
            if self.redis_client:
                try:
                    queue_sizes = {
                        'high': self.redis_client.llen('rq:queue:high'),
                        'default': self.redis_client.llen('rq:queue:default'),
                        'low': self.redis_client.llen('rq:queue:low')
                    }
                    total_queue_size = sum(queue_sizes.values())
                    self._record_metric('queue_size', total_queue_size)
                    
                    for queue_name, size in queue_sizes.items():
                        self._record_metric(f'queue_size_{queue_name}', size)
                        
                except Exception as e:
                    logger.warning(f"Could not collect queue metrics: {e}")
                    
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
            
    def _record_metric(self, metric_name: str, value: float):
        """Record a metric value with timestamp."""
        with self.lock:
            timestamp = datetime.utcnow()
            self.performance_history[metric_name].append({
                'timestamp': timestamp,
                'value': value
            })
            
    def _check_alert_conditions(self):
        """Check if any alert conditions are met."""
        current_time = datetime.utcnow()
        
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
                
            try:
                # Check cooldown period
                last_alert_time = self.last_alert_times.get(rule_name)
                if last_alert_time:
                    time_since_last = (current_time - last_alert_time).total_seconds()
                    if time_since_last < rule.cooldown_seconds:
                        continue
                        
                # Get recent metric values
                metric_name = rule_name.replace('high_', '').replace('critical_', '')
                metric_values = self._get_recent_metric_values(
                    metric_name,
                    rule.duration_seconds
                )
                
                if not metric_values:
                    continue
                    
                # Check condition
                avg_value = statistics.mean(metric_values)
                condition_met = self._evaluate_condition(avg_value, rule.condition, rule.threshold)
                
                if condition_met:
                    # Check if this is a new alert or update to existing
                    if rule_name not in self.active_alerts:
                        alert = PerformanceAlert(
                            timestamp=current_time,
                            rule_name=rule_name,
                            metric_name=metric_name,
                            current_value=avg_value,
                            threshold=rule.threshold,
                            severity=rule.severity,
                            message=f"{rule.severity.upper()}: {rule_name} - {avg_value:.2f} {rule.condition} {rule.threshold}"
                        )
                        
                        self.active_alerts[rule_name] = alert
                        self.alert_history.append(alert)
                        self.last_alert_times[rule_name] = current_time
                        
                        # Trigger alert callbacks
                        self._trigger_alert_callbacks(alert)
                        
                        logger.warning(f"Performance alert triggered: {alert.message}")
                else:
                    # Check if we should resolve an active alert
                    if rule_name in self.active_alerts:
                        alert = self.active_alerts[rule_name]
                        alert.resolved = True
                        alert.resolved_at = current_time
                        del self.active_alerts[rule_name]
                        
                        logger.info(f"Performance alert resolved: {rule_name}")
            except Exception as e:
                logger.error(f"Error checking alert condition for {rule_name}: {e}")
                
    def _get_recent_metric_values(self, metric_name: str, duration_seconds: int) -> List[float]:
        """Get metric values from the last duration_seconds."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=duration_seconds)
        
        # Try different metric name variations and mappings
        possible_names = [
            metric_name,
            f"{metric_name}_ms",
            f"{metric_name}_percent",
            f"{metric_name}_time_ms"
        ]
        
        # Add specific mappings for alert rule names to actual metric names
        rule_to_metric_mapping = {
            'high_response_time': ['response_time_ms', 'response_time'],
            'critical_response_time': ['response_time_ms', 'response_time'],
            'high_memory_usage': ['memory_usage_percent', 'memory_usage'],
            'critical_memory_usage': ['memory_usage_percent', 'memory_usage'],
            'high_error_rate': ['error_rate_percent', 'error_rate'],
            'queue_backup': ['queue_size'],
            'high_test_metric': ['test_metric'],  # For testing
            'test_metric': ['test_metric']  # Direct mapping
        }
        
        # If this is an alert rule name, use the mapping
        if metric_name in rule_to_metric_mapping:
            possible_names.extend(rule_to_metric_mapping[metric_name])
        
        for name in possible_names:
            if name in self.performance_history:
                all_entries = self.performance_history[name]
                recent_values = [
                    entry['value'] for entry in all_entries
                    if entry['timestamp'] >= cutoff_time
                ]
                
                if recent_values:
                    return recent_values
                    
        return []
        
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate if a condition is met."""
        if condition == 'greater_than':
            return value > threshold
        elif condition == 'less_than':
            return value < threshold
        elif condition == 'equals':
            return abs(value - threshold) < 0.01
        return False
        
    def _trigger_alert_callbacks(self, alert: PerformanceAlert):
        """Trigger all registered alert callbacks."""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
                
    def _cleanup_old_data(self):
        """Clean up old performance data to prevent memory leaks."""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        with self.lock:
            for metric_name in self.performance_history:
                # Remove entries older than 24 hours
                history = self.performance_history[metric_name]
                while history and history[0]['timestamp'] < cutoff_time:
                    history.popleft()
                    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get a summary of performance metrics for the last N hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        summary = {}
        
        with self.lock:
            for metric_name, history in self.performance_history.items():
                recent_values = [
                    entry['value'] for entry in history
                    if entry['timestamp'] >= cutoff_time
                ]
                
                if recent_values:
                    summary[metric_name] = {
                        'count': len(recent_values),
                        'average': statistics.mean(recent_values),
                        'min': min(recent_values),
                        'max': max(recent_values),
                        'median': statistics.median(recent_values)
                    }
                    
                    if len(recent_values) > 1:
                        summary[metric_name]['std_dev'] = statistics.stdev(recent_values)
                        
        return summary
        
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all currently active alerts."""
        return list(self.active_alerts.values())
        
    def get_alert_history(self, hours: int = 24) -> List[PerformanceAlert]:
        """Get alert history for the last N hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history
            if alert.timestamp >= cutoff_time
        ]
        
    def update_threshold(self, metric_name: str, warning: float = None, critical: float = None):
        """Update performance thresholds for a metric."""
        if metric_name in self.thresholds:
            threshold = self.thresholds[metric_name]
            if warning is not None:
                threshold.warning_threshold = warning
            if critical is not None:
                threshold.critical_threshold = critical
            logger.info(f"Updated thresholds for {metric_name}: warning={warning}, critical={critical}")
        else:
            logger.warning(f"Unknown metric for threshold update: {metric_name}")
            
    def enable_alert_rule(self, rule_name: str):
        """Enable an alert rule."""
        if rule_name in self.alert_rules:
            self.alert_rules[rule_name].enabled = True
            logger.info(f"Enabled alert rule: {rule_name}")
            
    def disable_alert_rule(self, rule_name: str):
        """Disable an alert rule."""
        if rule_name in self.alert_rules:
            self.alert_rules[rule_name].enabled = False
            logger.info(f"Disabled alert rule: {rule_name}")
            
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status based on current metrics."""
        summary = self.get_performance_summary(hours=1)
        active_alerts = self.get_active_alerts()
        
        # Determine overall health
        critical_alerts = [a for a in active_alerts if a.severity == 'critical']
        warning_alerts = [a for a in active_alerts if a.severity == 'warning']
        
        if critical_alerts:
            health_status = 'critical'
        elif warning_alerts:
            health_status = 'warning'
        else:
            health_status = 'healthy'
            
        return {
            'status': health_status,
            'active_alerts_count': len(active_alerts),
            'critical_alerts_count': len(critical_alerts),
            'warning_alerts_count': len(warning_alerts),
            'monitoring_active': self.monitoring_active,
            'metrics_summary': summary,
            'active_alerts': [
                {
                    'rule_name': alert.rule_name,
                    'severity': alert.severity,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat()
                }
                for alert in active_alerts
            ]
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def setup_email_alerts(smtp_server: str, smtp_port: int, username: str, password: str, 
                      from_email: str, to_emails: List[str]):
    """Setup email alerts for performance issues."""
    
    def send_email_alert(alert: PerformanceAlert):
        try:
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = f"[{alert.severity.upper()}] Christian Cleanup Performance Alert"
            
            body = f"""
Performance Alert Triggered

Alert: {alert.rule_name}
Severity: {alert.severity.upper()}
Metric: {alert.metric_name}
Current Value: {alert.current_value:.2f}
Threshold: {alert.threshold}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

Message: {alert.message}

Please check the application monitoring dashboard for more details.
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent for {alert.rule_name}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            
    performance_monitor.add_alert_callback(send_email_alert)


def setup_slack_alerts(webhook_url: str):
    """Setup Slack alerts for performance issues."""
    import requests
    
    def send_slack_alert(alert: PerformanceAlert):
        try:
            color = '#ff0000' if alert.severity == 'critical' else '#ffaa00'
            
            payload = {
                'attachments': [{
                    'color': color,
                    'title': f"{alert.severity.upper()}: Performance Alert",
                    'fields': [
                        {'title': 'Alert', 'value': alert.rule_name, 'short': True},
                        {'title': 'Metric', 'value': alert.metric_name, 'short': True},
                        {'title': 'Current Value', 'value': f"{alert.current_value:.2f}", 'short': True},
                        {'title': 'Threshold', 'value': f"{alert.threshold}", 'short': True},
                        {'title': 'Time', 'value': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'), 'short': False}
                    ],
                    'footer': 'Christian Cleanup Monitoring'
                }]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Slack alert sent for {alert.rule_name}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            
    performance_monitor.add_alert_callback(send_slack_alert) 