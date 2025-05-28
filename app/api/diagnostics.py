"""
Diagnostic API Endpoints for Christian Cleanup Application
Provides comprehensive system monitoring, metrics, and health check endpoints.
"""

import os
import time
import psutil
import redis
from datetime import datetime
from flask import Blueprint, jsonify, current_app, request
from flask_login import login_required
from functools import wraps
from typing import Dict, Any, List

from ..utils.metrics import metrics_collector
from ..utils.logging import get_logger
from ..utils.performance_monitor import performance_monitor
from ..utils.error_tracking import error_tracker
from ..extensions import db, rq

logger = get_logger('app.monitoring')

diagnostics_bp = Blueprint('diagnostics', __name__, url_prefix='/api/diagnostics')


def admin_required(f):
    """Decorator to require admin access for diagnostic endpoints."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # For now, allow any authenticated user
        # In production, you might want to check for admin role
        return f(*args, **kwargs)
    return decorated_function


@diagnostics_bp.route('/health', methods=['GET'])
def health_check():
    """
    Basic health check endpoint.
    Returns 200 if the application is running.
    """
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        db_status = 'healthy'
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = 'unhealthy'
    
    try:
        # Test Redis connection
        redis_client = redis.Redis.from_url(current_app.config['REDIS_URL'])
        redis_client.ping()
        redis_status = 'healthy'
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = 'unhealthy'
    
    health_status = {
        'status': 'healthy' if db_status == 'healthy' and redis_status == 'healthy' else 'degraded',
        'timestamp': time.time(),
        'components': {
            'database': db_status,
            'redis': redis_status,
            'application': 'healthy'
        }
    }
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code


@diagnostics_bp.route('/metrics', methods=['GET'])
@admin_required
def get_metrics():
    """
    Get comprehensive application metrics.
    Returns detailed performance metrics for all components.
    """
    try:
        metrics_data = metrics_collector.get_metrics_summary()
        
        logger.info("Metrics requested", extra={
            'extra_fields': {
                'total_api_requests': sum(m['total_operations'] for m in metrics_data['api_requests'].values()),
                'total_analyses': metrics_data['analysis']['total_operations'],
                'total_errors': metrics_data['errors']['total_errors']
            }
        })
        
        return jsonify({
            'status': 'success',
            'data': metrics_data
        })
    
    except Exception as e:
        logger.error(f"Failed to retrieve metrics: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve metrics',
            'error': str(e)
        }), 500


@diagnostics_bp.route('/system', methods=['GET'])
@admin_required
def get_system_info():
    """
    Get system resource information.
    Returns CPU, memory, and disk usage statistics.
    """
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get process-specific metrics
        process = psutil.Process()
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent()
        
        # Track system metrics
        metrics_collector.track_system_metrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_percent=disk.percent
        )
        
        system_info = {
            'system': {
                'cpu_percent': cpu_percent,
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_percent': memory.percent,
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'disk_used_gb': round(disk.used / (1024**3), 2),
                'disk_percent': round((disk.used / disk.total) * 100, 2),
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
            },
            'process': {
                'pid': process.pid,
                'cpu_percent': process_cpu,
                'memory_rss_mb': round(process_memory.rss / (1024**2), 2),
                'memory_vms_mb': round(process_memory.vms / (1024**2), 2),
                'num_threads': process.num_threads(),
                'create_time': process.create_time()
            },
            'timestamp': time.time()
        }
        
        return jsonify({
            'status': 'success',
            'data': system_info
        })
    
    except Exception as e:
        logger.error(f"Failed to retrieve system info: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve system information',
            'error': str(e)
        }), 500


@diagnostics_bp.route('/redis', methods=['GET'])
@admin_required
def get_redis_info():
    """
    Get Redis connection and queue information.
    Returns Redis server stats and queue statistics.
    """
    try:
        redis_client = redis.Redis.from_url(current_app.config['REDIS_URL'])
        
        # Get Redis server info
        redis_info = redis_client.info()
        
        # Get queue statistics
        queue_stats = {}
        
        # Check if RQ is available and get queue info
        if hasattr(current_app, 'task_queue'):
            try:
                # Get queue lengths
                high_queue = current_app.high_queue
                default_queue = current_app.default_queue
                low_queue = current_app.low_queue
                
                queue_stats = {
                    'high_queue': {
                        'length': len(high_queue),
                        'failed_jobs': len(high_queue.failed_job_registry),
                        'scheduled_jobs': len(high_queue.scheduled_job_registry),
                        'started_jobs': len(high_queue.started_job_registry)
                    },
                    'default_queue': {
                        'length': len(default_queue),
                        'failed_jobs': len(default_queue.failed_job_registry),
                        'scheduled_jobs': len(default_queue.scheduled_job_registry),
                        'started_jobs': len(default_queue.started_job_registry)
                    },
                    'low_queue': {
                        'length': len(low_queue),
                        'failed_jobs': len(low_queue.failed_job_registry),
                        'scheduled_jobs': len(low_queue.scheduled_job_registry),
                        'started_jobs': len(low_queue.started_job_registry)
                    }
                }
                
                # Get worker information
                from rq import Worker
                workers = Worker.all(connection=redis_client)
                worker_info = []
                for worker in workers:
                    worker_info.append({
                        'name': worker.name,
                        'state': worker.get_state(),
                        'current_job': worker.get_current_job_id(),
                        'queues': [q.name for q in worker.queues],
                        'birth_date': worker.birth_date.isoformat() if worker.birth_date else None,
                        'last_heartbeat': worker.last_heartbeat.isoformat() if worker.last_heartbeat else None
                    })
                
                queue_stats['workers'] = worker_info
                queue_stats['total_workers'] = len(workers)
                queue_stats['active_workers'] = len([w for w in workers if w.get_state() == 'busy'])
                
            except Exception as e:
                logger.warning(f"Failed to get queue stats: {e}")
                queue_stats['error'] = str(e)
        
        redis_data = {
            'connection': {
                'connected': True,
                'url': current_app.config['REDIS_URL']
            },
            'server_info': {
                'redis_version': redis_info.get('redis_version'),
                'connected_clients': redis_info.get('connected_clients'),
                'used_memory_human': redis_info.get('used_memory_human'),
                'used_memory_peak_human': redis_info.get('used_memory_peak_human'),
                'total_connections_received': redis_info.get('total_connections_received'),
                'total_commands_processed': redis_info.get('total_commands_processed'),
                'uptime_in_seconds': redis_info.get('uptime_in_seconds'),
                'keyspace_hits': redis_info.get('keyspace_hits'),
                'keyspace_misses': redis_info.get('keyspace_misses')
            },
            'queues': queue_stats,
            'timestamp': time.time()
        }
        
        return jsonify({
            'status': 'success',
            'data': redis_data
        })
    
    except redis.ConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Redis connection failed',
            'error': str(e),
            'data': {
                'connection': {
                    'connected': False,
                    'url': current_app.config['REDIS_URL']
                }
            }
        }), 503
    
    except Exception as e:
        logger.error(f"Failed to retrieve Redis info: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve Redis information',
            'error': str(e)
        }), 500


@diagnostics_bp.route('/database', methods=['GET'])
@admin_required
def get_database_info():
    """
    Get database connection and performance information.
    Returns database statistics and connection pool info.
    """
    try:
        # Test database connection and get basic info
        result = db.session.execute(db.text('SELECT version()'))
        db_version = result.scalar()
        
        # Get connection pool info
        pool_info = {}
        if hasattr(db.engine.pool, 'size'):
            pool_info = {
                'pool_size': db.engine.pool.size(),
                'checked_in': db.engine.pool.checkedin(),
                'checked_out': db.engine.pool.checkedout(),
                'overflow': db.engine.pool.overflow(),
                'invalid': db.engine.pool.invalid()
            }
        
        # Get table statistics
        table_stats = {}
        try:
            # Get row counts for main tables
            tables = ['users', 'playlists', 'songs', 'analysis_results', 'lyrics_cache']
            for table in tables:
                try:
                    result = db.session.execute(db.text(f'SELECT COUNT(*) FROM {table}'))
                    table_stats[table] = result.scalar()
                except Exception:
                    table_stats[table] = 'N/A'
        except Exception as e:
            logger.warning(f"Failed to get table statistics: {e}")
            table_stats = {'error': str(e)}
        
        database_info = {
            'connection': {
                'connected': True,
                'url': current_app.config['SQLALCHEMY_DATABASE_URI'][:50] + '...',  # Truncate for security
                'version': db_version
            },
            'pool': pool_info,
            'tables': table_stats,
            'timestamp': time.time()
        }
        
        return jsonify({
            'status': 'success',
            'data': database_info
        })
    
    except Exception as e:
        logger.error(f"Failed to retrieve database info: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve database information',
            'error': str(e)
        }), 500


@diagnostics_bp.route('/logs', methods=['GET'])
@admin_required
def get_recent_logs():
    """
    Get recent log entries.
    Returns the most recent log entries from various log files.
    """
    try:
        log_dir = current_app.config.get('LOG_DIR', 'logs')
        lines = int(request.args.get('lines', 100))
        log_type = request.args.get('type', 'app')  # app, error, performance
        
        log_files = {
            'app': os.path.join(log_dir, 'app.log'),
            'error': os.path.join(log_dir, 'error.log'),
            'performance': os.path.join(log_dir, 'performance.log')
        }
        
        log_file = log_files.get(log_type, log_files['app'])
        
        if not os.path.exists(log_file):
            return jsonify({
                'status': 'error',
                'message': f'Log file not found: {log_file}'
            }), 404
        
        # Read the last N lines from the log file
        with open(log_file, 'r') as f:
            log_lines = f.readlines()
            recent_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines
        
        return jsonify({
            'status': 'success',
            'data': {
                'log_type': log_type,
                'log_file': log_file,
                'lines_requested': lines,
                'lines_returned': len(recent_lines),
                'logs': [line.strip() for line in recent_lines]
            }
        })
    
    except Exception as e:
        logger.error(f"Failed to retrieve logs: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve logs',
            'error': str(e)
        }), 500


@diagnostics_bp.route('/alerts', methods=['GET'])
@admin_required
def get_alerts():
    """
    Get recent performance alerts and warnings.
    Returns alerts based on configured thresholds.
    """
    try:
        # Get recent errors from metrics collector
        metrics_data = metrics_collector.get_metrics_summary()
        recent_errors = metrics_data['errors']['recent_errors']
        
        # Generate alerts based on current metrics
        alerts = []
        
        # Check error rates
        for endpoint, metrics in metrics_data['api_requests'].items():
            if metrics['total_operations'] > 10:  # Only check endpoints with significant traffic
                error_rate = 100 - metrics['success_rate']
                if error_rate > 5:  # 5% error rate threshold
                    alerts.append({
                        'type': 'high_error_rate',
                        'severity': 'warning' if error_rate < 10 else 'critical',
                        'message': f'High error rate for {endpoint}: {error_rate:.1f}%',
                        'data': {'endpoint': endpoint, 'error_rate': error_rate},
                        'timestamp': time.time()
                    })
        
        # Check slow operations
        if metrics_data['analysis']['total_operations'] > 0:
            avg_analysis_time = metrics_data['analysis']['average_duration_ms']
            if avg_analysis_time > 30000:  # 30 second threshold
                alerts.append({
                    'type': 'slow_analysis',
                    'severity': 'warning',
                    'message': f'Slow analysis performance: {avg_analysis_time:.0f}ms average',
                    'data': {'average_duration_ms': avg_analysis_time},
                    'timestamp': time.time()
                })
        
        # Check system resources
        system_metrics = metrics_data['system']
        if system_metrics['cpu_usage']['current'] > 80:
            alerts.append({
                'type': 'high_cpu',
                'severity': 'warning',
                'message': f'High CPU usage: {system_metrics["cpu_usage"]["current"]:.1f}%',
                'data': {'cpu_percent': system_metrics['cpu_usage']['current']},
                'timestamp': time.time()
            })
        
        if system_metrics['memory_usage']['current'] > 85:
            alerts.append({
                'type': 'high_memory',
                'severity': 'warning',
                'message': f'High memory usage: {system_metrics["memory_usage"]["current"]:.1f}%',
                'data': {'memory_percent': system_metrics['memory_usage']['current']},
                'timestamp': time.time()
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'alerts': alerts,
                'recent_errors': recent_errors,
                'alert_count': len(alerts),
                'timestamp': time.time()
            }
        })
    
    except Exception as e:
        logger.error(f"Failed to retrieve alerts: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve alerts',
            'error': str(e)
        }), 500


@diagnostics_bp.route('/config', methods=['GET'])
@admin_required
def get_config_info():
    """
    Get application configuration information (sanitized).
    Returns non-sensitive configuration values.
    """
    try:
        # Get sanitized config (remove sensitive values)
        sensitive_keys = [
            'SECRET_KEY', 'SPOTIPY_CLIENT_SECRET', 'GENIUS_ACCESS_TOKEN',
            'DATABASE_URL', 'REDIS_URL', 'BIBLE_API_KEY'
        ]
        
        config_info = {}
        for key, value in current_app.config.items():
            if key in sensitive_keys:
                config_info[key] = '***REDACTED***'
            elif isinstance(value, (str, int, float, bool)):
                config_info[key] = value
            else:
                config_info[key] = str(type(value))
        
        return jsonify({
            'status': 'success',
            'data': {
                'config': config_info,
                'environment': os.environ.get('FLASK_ENV', 'unknown'),
                'debug': current_app.debug,
                'testing': current_app.testing,
                'timestamp': time.time()
            }
        })
    
    except Exception as e:
        logger.error(f"Failed to retrieve config info: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve configuration information',
            'error': str(e)
        }), 500


@diagnostics_bp.route('/reset-metrics', methods=['POST'])
@admin_required
def reset_metrics():
    """
    Reset all collected metrics.
    Useful for testing or clearing historical data.
    """
    try:
        metrics_collector.reset_metrics()
        
        logger.info("Metrics reset by admin", extra={
            'extra_fields': {
                'action': 'metrics_reset',
                'user': 'admin'  # In production, get actual user
            }
        })
        
        return jsonify({
            'status': 'success',
            'message': 'Metrics have been reset',
            'timestamp': time.time()
        })
    
    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Failed to reset metrics',
            'error': str(e)
        }), 500


@diagnostics_bp.route('/performance/summary')
@admin_required
def performance_summary():
    """Get performance metrics summary."""
    try:
        hours = request.args.get('hours', 1, type=int)
        summary = performance_monitor.get_performance_summary(hours=hours)
        
        logger.info(f"Performance summary retrieved for last {hours} hours")
        return jsonify({
            'status': 'success',
            'performance_summary': summary,
            'hours': hours,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        return jsonify({'error': f'Failed to get performance summary: {str(e)}'}), 500


@diagnostics_bp.route('/performance/alerts')
@admin_required
def performance_alerts():
    """Get active performance alerts and alert history."""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        active_alerts = performance_monitor.get_active_alerts()
        alert_history = performance_monitor.get_alert_history(hours=hours)
        
        # Convert alerts to JSON-serializable format
        active_alerts_data = [
            {
                'timestamp': alert.timestamp.isoformat(),
                'rule_name': alert.rule_name,
                'metric_name': alert.metric_name,
                'current_value': alert.current_value,
                'threshold': alert.threshold,
                'severity': alert.severity,
                'message': alert.message,
                'resolved': alert.resolved,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
            }
            for alert in active_alerts
        ]
        
        alert_history_data = [
            {
                'timestamp': alert.timestamp.isoformat(),
                'rule_name': alert.rule_name,
                'metric_name': alert.metric_name,
                'current_value': alert.current_value,
                'threshold': alert.threshold,
                'severity': alert.severity,
                'message': alert.message,
                'resolved': alert.resolved,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
            }
            for alert in alert_history
        ]
        
        logger.info(f"Performance alerts retrieved - {len(active_alerts)} active, {len(alert_history)} in history")
        return jsonify({
            'status': 'success',
            'active_alerts': active_alerts_data,
            'alert_history': alert_history_data,
            'active_count': len(active_alerts),
            'history_hours': hours,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting performance alerts: {e}")
        return jsonify({'error': f'Failed to get performance alerts: {str(e)}'}), 500


@diagnostics_bp.route('/performance/health')
@admin_required
def performance_health():
    """Get overall system health status."""
    try:
        health_status = performance_monitor.get_health_status()
        
        logger.info(f"System health status: {health_status['status']}")
        return jsonify({
            'status': 'success',
            'health': health_status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return jsonify({'error': f'Failed to get system health: {str(e)}'}), 500


@diagnostics_bp.route('/performance/thresholds', methods=['GET', 'POST'])
@admin_required
def performance_thresholds():
    """Get or update performance thresholds."""
    try:
        if request.method == 'GET':
            # Return current thresholds
            thresholds_data = {}
            for metric_name, threshold in performance_monitor.thresholds.items():
                thresholds_data[metric_name] = {
                    'warning_threshold': threshold.warning_threshold,
                    'critical_threshold': threshold.critical_threshold,
                    'duration_seconds': threshold.duration_seconds,
                    'enabled': threshold.enabled
                }
                
            return jsonify({
                'status': 'success',
                'thresholds': thresholds_data,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        elif request.method == 'POST':
            # Update thresholds
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
                
            updated_metrics = []
            for metric_name, values in data.items():
                if metric_name in performance_monitor.thresholds:
                    warning = values.get('warning_threshold')
                    critical = values.get('critical_threshold')
                    performance_monitor.update_threshold(metric_name, warning, critical)
                    updated_metrics.append(metric_name)
                    
            logger.info(f"Updated performance thresholds for: {updated_metrics}")
            return jsonify({
                'status': 'success',
                'updated_metrics': updated_metrics,
                'timestamp': datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error managing performance thresholds: {e}")
        return jsonify({'error': f'Failed to manage thresholds: {str(e)}'}), 500


@diagnostics_bp.route('/performance/monitoring', methods=['POST'])
@admin_required
def control_performance_monitoring():
    """Start or stop performance monitoring."""
    try:
        data = request.get_json()
        action = data.get('action') if data else None
        
        if action == 'start':
            interval = data.get('interval_seconds', 30)
            performance_monitor.start_monitoring(interval_seconds=interval)
            logger.info(f"Performance monitoring started with {interval}s interval")
            return jsonify({
                'status': 'success',
                'action': 'started',
                'interval_seconds': interval,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        elif action == 'stop':
            performance_monitor.stop_monitoring()
            logger.info("Performance monitoring stopped")
            return jsonify({
                'status': 'success',
                'action': 'stopped',
                'timestamp': datetime.utcnow().isoformat()
            })
            
        else:
            return jsonify({'error': 'Invalid action. Use "start" or "stop"'}), 400
            
    except Exception as e:
        logger.error(f"Error controlling performance monitoring: {e}")
        return jsonify({'error': f'Failed to control monitoring: {str(e)}'}), 500


@diagnostics_bp.route('/errors/summary', methods=['GET'])
@admin_required
def error_summary():
    """Get error summary and statistics."""
    try:
        hours = request.args.get('hours', 24, type=int)
        summary = error_tracker.get_error_summary(hours=hours)
        
        logger.info(f"Error summary retrieved for last {hours} hours")
        return jsonify({
            'status': 'success',
            'error_summary': summary,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting error summary: {e}")
        return jsonify({'error': f'Failed to get error summary: {str(e)}'}), 500


@diagnostics_bp.route('/errors/recent', methods=['GET'])
@admin_required
def recent_errors():
    """Get recent error events."""
    try:
        limit = request.args.get('limit', 100, type=int)
        error_type = request.args.get('error_type')
        
        errors = error_tracker.get_recent_errors(limit=limit, error_type=error_type)
        
        # Convert datetime objects to ISO format
        for error in errors:
            if 'timestamp' in error:
                error['timestamp'] = error['timestamp'].isoformat()
        
        logger.info(f"Retrieved {len(errors)} recent errors")
        return jsonify({
            'status': 'success',
            'errors': errors,
            'count': len(errors),
            'filters': {
                'limit': limit,
                'error_type': error_type
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting recent errors: {e}")
        return jsonify({'error': f'Failed to get recent errors: {str(e)}'}), 500


@diagnostics_bp.route('/errors/trends', methods=['GET'])
@admin_required
def error_trends():
    """Get error trends and patterns."""
    try:
        hours = request.args.get('hours', 24, type=int)
        trends = error_tracker.get_error_trends(hours=hours)
        
        logger.info(f"Error trends retrieved for last {hours} hours")
        return jsonify({
            'status': 'success',
            'trends': trends,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting error trends: {e}")
        return jsonify({'error': f'Failed to get error trends: {str(e)}'}), 500


@diagnostics_bp.route('/errors/alerts', methods=['GET'])
@admin_required
def error_alerts_config():
    """Get error alert configuration and status."""
    try:
        alert_status = error_tracker.get_alert_status()
        
        logger.info("Error alert configuration retrieved")
        return jsonify({
            'status': 'success',
            'alert_configuration': alert_status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting alert configuration: {e}")
        return jsonify({'error': f'Failed to get alert configuration: {str(e)}'}), 500


@diagnostics_bp.route('/errors/alerts/update', methods=['POST'])
@admin_required
def update_error_alerts():
    """Update error alert configuration."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        alert_name = data.get('alert_name')
        if not alert_name:
            return jsonify({'error': 'alert_name is required'}), 400
            
        # Remove alert_name from data before passing to update function
        update_params = {k: v for k, v in data.items() if k != 'alert_name'}
        
        error_tracker.update_alert_configuration(alert_name, **update_params)
        
        logger.info(f"Updated error alert configuration: {alert_name}")
        return jsonify({
            'status': 'success',
            'message': f'Alert {alert_name} updated successfully',
            'updated_fields': list(update_params.keys()),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error updating alert configuration: {e}")
        return jsonify({'error': f'Failed to update alert configuration: {str(e)}'}), 500


@diagnostics_bp.route('/errors/track', methods=['POST'])
@admin_required
def track_error_manually():
    """Manually track an error event (for testing)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        error_type = data.get('error_type')
        message = data.get('message')
        
        if not error_type or not message:
            return jsonify({'error': 'error_type and message are required'}), 400
            
        event_id = error_tracker.track_error(
            error_type=error_type,
            message=message,
            stack_trace=data.get('stack_trace'),
            user_id=data.get('user_id'),
            request_path=data.get('request_path'),
            context=data.get('context'),
            severity=data.get('severity', 'error')
        )
        
        logger.info(f"Manually tracked error: {error_type}")
        return jsonify({
            'status': 'success',
            'message': 'Error tracked successfully',
            'event_id': event_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error tracking error manually: {e}")
        return jsonify({'error': f'Failed to track error: {str(e)}'}), 500 