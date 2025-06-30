"""
Production Health Monitoring System
Comprehensive health checks and monitoring for production deployment.
"""

import time
import psutil
import redis
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.extensions import db


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    WARNING = "warning" 
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class SystemHealth:
    """Overall system health status."""
    status: HealthStatus
    timestamp: datetime
    checks: List[HealthCheck]
    summary: Dict[str, Any]


class HealthMonitor:
    """Production health monitoring system."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._cache_ttl = 30  # Cache health results for 30 seconds
        self._last_check: Optional[SystemHealth] = None
        self._last_check_time: Optional[datetime] = None
    
    def get_system_health(self, force_refresh: bool = False) -> SystemHealth:
        """Get comprehensive system health status."""
        now = datetime.now(timezone.utc)
        
        # Return cached result if recent enough
        if (not force_refresh and 
            self._last_check and 
            self._last_check_time and
            (now - self._last_check_time).total_seconds() < self._cache_ttl):
            return self._last_check
        
        # Perform all health checks
        checks = [
            self._check_database(),
            self._check_redis(),
            self._check_priority_queue(),
            self._check_memory_usage(),
            self._check_disk_space(),
            self._check_response_time(),
            self._check_worker_status(),
            self._check_external_apis()
        ]
        
        # Determine overall status
        overall_status = self._determine_overall_status(checks)
        
        # Generate summary
        summary = self._generate_summary(checks)
        
        # Cache result
        system_health = SystemHealth(
            status=overall_status,
            timestamp=now,
            checks=checks,
            summary=summary
        )
        
        self._last_check = system_health
        self._last_check_time = now
        
        return system_health
    
    def _check_database(self) -> HealthCheck:
        """Check database connectivity and performance."""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            result = db.session.execute(text('SELECT 1')).scalar()
            if result != 1:
                raise Exception("Database query returned unexpected result")
            
            # Check connection pool status
            pool = db.engine.pool
            pool_status = {
                'size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout()
            }
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on response time
            if response_time > 1000:  # > 1 second
                status = HealthStatus.CRITICAL
                message = f"Database response too slow: {response_time:.1f}ms"
            elif response_time > 100:  # > 100ms
                status = HealthStatus.WARNING
                message = f"Database response slow: {response_time:.1f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = f"Database healthy: {response_time:.1f}ms"
            
            return HealthCheck(
                name="database",
                status=status,
                message=message,
                timestamp=datetime.now(timezone.utc),
                response_time_ms=response_time,
                details=pool_status
            )
            
        except SQLAlchemyError as e:
            return HealthCheck(
                name="database",
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {str(e)}",
                timestamp=datetime.now(timezone.utc),
                response_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return HealthCheck(
                name="database",
                status=HealthStatus.CRITICAL,
                message=f"Database check failed: {str(e)}",
                timestamp=datetime.now(timezone.utc),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    def _check_redis(self) -> HealthCheck:
        """Check Redis connectivity and performance."""
        start_time = time.time()
        
        try:
            redis_client = redis.from_url(current_app.config.get('RQ_REDIS_URL'))
            
            # Test basic connectivity
            pong = redis_client.ping()
            if not pong:
                raise Exception("Redis ping failed")
            
            # Get Redis info
            info = redis_client.info()
            memory_usage = info.get('used_memory_human', 'unknown')
            connected_clients = info.get('connected_clients', 0)
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status
            if response_time > 500:  # > 500ms
                status = HealthStatus.WARNING
                message = f"Redis response slow: {response_time:.1f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = f"Redis healthy: {response_time:.1f}ms"
            
            return HealthCheck(
                name="redis",
                status=status,
                message=message,
                timestamp=datetime.now(timezone.utc),
                response_time_ms=response_time,
                details={
                    'memory_usage': memory_usage,
                    'connected_clients': connected_clients,
                    'redis_version': info.get('redis_version', 'unknown')
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="redis",
                status=HealthStatus.CRITICAL,
                message=f"Redis check failed: {str(e)}",
                timestamp=datetime.now(timezone.utc),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    def _check_priority_queue(self) -> HealthCheck:
        """Check priority queue status and worker health."""
        try:
            # Get priority queue information
            redis_client = redis.from_url(current_app.config.get('RQ_REDIS_URL'))
            
            # Check priority queue size
            queue_size = redis_client.zcard('priority_analysis_queue')
            
            # Check active workers
            active_workers = redis_client.smembers('active_workers')
            worker_count = len(active_workers)
            
            # Check for any processing jobs
            processing_jobs = redis_client.scard('processing_jobs') if redis_client.exists('processing_jobs') else 0
            
            queue_info = {
                'queue_size': queue_size,
                'active_workers': worker_count,
                'processing_jobs': processing_jobs,
                'worker_ids': [w.decode() for w in active_workers]
            }
            
            # Determine status
            if worker_count == 0:
                status = HealthStatus.CRITICAL
                message = "No active workers found"
            elif queue_size > 1000:
                status = HealthStatus.WARNING
                message = f"High queue backlog: {queue_size} jobs"
            else:
                status = HealthStatus.HEALTHY
                message = f"Priority queue healthy: {worker_count} workers, {queue_size} jobs"
            
            return HealthCheck(
                name="priority_queue",
                status=status,
                message=message,
                timestamp=datetime.now(timezone.utc),
                details=queue_info
            )
            
        except Exception as e:
            return HealthCheck(
                name="priority_queue",
                status=HealthStatus.CRITICAL,
                message=f"Priority queue check failed: {str(e)}",
                timestamp=datetime.now(timezone.utc)
            )
    
    def _check_memory_usage(self) -> HealthCheck:
        """Check system memory usage."""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Determine status based on memory usage
            if memory.percent > 90:
                status = HealthStatus.CRITICAL
                message = f"Memory usage critical: {memory.percent:.1f}%"
            elif memory.percent > 80:
                status = HealthStatus.WARNING
                message = f"Memory usage high: {memory.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {memory.percent:.1f}%"
            
            return HealthCheck(
                name="memory",
                status=status,
                message=message,
                timestamp=datetime.now(timezone.utc),
                details={
                    'memory_percent': memory.percent,
                    'memory_available': memory.available,
                    'memory_total': memory.total,
                    'swap_percent': swap.percent,
                    'swap_total': swap.total
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message=f"Memory check failed: {str(e)}",
                timestamp=datetime.now(timezone.utc)
            )
    
    def _check_disk_space(self) -> HealthCheck:
        """Check disk space usage."""
        try:
            disk = psutil.disk_usage('/')
            
            # Determine status based on disk usage
            if disk.percent > 95:
                status = HealthStatus.CRITICAL
                message = f"Disk space critical: {disk.percent:.1f}%"
            elif disk.percent > 85:
                status = HealthStatus.WARNING
                message = f"Disk space low: {disk.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space normal: {disk.percent:.1f}%"
            
            return HealthCheck(
                name="disk_space",
                status=status,
                message=message,
                timestamp=datetime.now(timezone.utc),
                details={
                    'disk_percent': disk.percent,
                    'disk_free': disk.free,
                    'disk_total': disk.total
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="disk_space",
                status=HealthStatus.UNKNOWN,
                message=f"Disk check failed: {str(e)}",
                timestamp=datetime.now(timezone.utc)
            )
    
    def _check_response_time(self) -> HealthCheck:
        """Check application response time."""
        try:
            # Simple internal response time check
            start_time = time.time()
            
            # Simulate a lightweight operation
            result = db.session.execute(text('SELECT COUNT(*) FROM users')).scalar()
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on response time
            if response_time > 2000:  # > 2 seconds
                status = HealthStatus.CRITICAL
                message = f"App response critical: {response_time:.1f}ms"
            elif response_time > 500:  # > 500ms
                status = HealthStatus.WARNING
                message = f"App response slow: {response_time:.1f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = f"App response normal: {response_time:.1f}ms"
            
            return HealthCheck(
                name="response_time",
                status=status,
                message=message,
                timestamp=datetime.now(timezone.utc),
                response_time_ms=response_time,
                details={'user_count': result}
            )
            
        except Exception as e:
            return HealthCheck(
                name="response_time",
                status=HealthStatus.CRITICAL,
                message=f"Response time check failed: {str(e)}",
                timestamp=datetime.now(timezone.utc)
            )
    
    def _check_worker_status(self) -> HealthCheck:
        """Check background worker status."""
        try:
            # Check for any processing jobs
            processing_jobs = db.session.execute(text('SELECT COUNT(*) FROM processing_jobs')).scalar()
            
            # Determine status
            if processing_jobs == 0:
                status = HealthStatus.CRITICAL
                message = "No processing jobs found"
            elif processing_jobs > 1000:
                status = HealthStatus.WARNING
                message = f"High processing backlog: {processing_jobs} jobs"
            else:
                status = HealthStatus.HEALTHY
                message = f"Processing healthy: {processing_jobs} jobs"
            
            return HealthCheck(
                name="workers",
                status=status,
                message=message,
                timestamp=datetime.now(timezone.utc),
                details={
                    'processing_jobs': processing_jobs
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="workers",
                status=HealthStatus.CRITICAL,
                message=f"Worker check failed: {str(e)}",
                timestamp=datetime.now(timezone.utc)
            )
    
    def _check_external_apis(self) -> HealthCheck:
        """Check external API connectivity."""
        try:
            import requests
            
            # Test Spotify API (simple endpoint)
            spotify_status = "unknown"
            try:
                response = requests.get("https://api.spotify.com/v1/", timeout=5)
                spotify_status = "available" if response.status_code in [200, 401] else "unavailable"
            except:
                spotify_status = "unavailable"
            
            # Determine overall status
            if spotify_status == "unavailable":
                status = HealthStatus.WARNING
                message = "Some external APIs unavailable"
            else:
                status = HealthStatus.HEALTHY
                message = "External APIs accessible"
            
            return HealthCheck(
                name="external_apis",
                status=status,
                message=message,
                timestamp=datetime.now(timezone.utc),
                details={
                    'spotify_api': spotify_status
                }
            )
            
        except Exception as e:
            return HealthCheck(
                name="external_apis",
                status=HealthStatus.WARNING,
                message=f"External API check failed: {str(e)}",
                timestamp=datetime.now(timezone.utc)
            )
    
    def _determine_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """Determine overall system status from individual checks."""
        critical_count = sum(1 for check in checks if check.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for check in checks if check.status == HealthStatus.WARNING)
        
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif warning_count > 2:  # Multiple warnings = critical
            return HealthStatus.CRITICAL
        elif warning_count > 0:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def _generate_summary(self, checks: List[HealthCheck]) -> Dict[str, Any]:
        """Generate health summary statistics."""
        status_counts = {}
        for status in HealthStatus:
            status_counts[status.value] = sum(1 for check in checks if check.status == status)
        
        response_times = [check.response_time_ms for check in checks if check.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            'total_checks': len(checks),
            'status_counts': status_counts,
            'avg_response_time_ms': avg_response_time,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
    
    def to_dict(self, system_health: SystemHealth) -> Dict[str, Any]:
        """Convert SystemHealth to dictionary for JSON serialization."""
        return {
            'status': system_health.status.value,
            'timestamp': system_health.timestamp.isoformat(),
            'summary': system_health.summary,
            'checks': [
                {
                    'name': check.name,
                    'status': check.status.value,
                    'message': check.message,
                    'timestamp': check.timestamp.isoformat(),
                    'response_time_ms': check.response_time_ms,
                    'details': check.details
                } for check in system_health.checks
            ]
        }


# Global health monitor instance
health_monitor = HealthMonitor() 