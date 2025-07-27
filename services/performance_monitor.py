"""
Performance monitoring service for MCP Base64 Server.

This module provides comprehensive performance monitoring capabilities including
request processing time tracking, error rate statistics, success rate monitoring,
and system resource usage tracking.
"""

import time
import threading
import psutil
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum

from .logging_service import get_logger


class MetricType(Enum):
    """Types of metrics that can be tracked."""
    REQUEST_DURATION = "request_duration"
    REQUEST_COUNT = "request_count"
    ERROR_COUNT = "error_count"
    SUCCESS_COUNT = "success_count"
    SYSTEM_CPU = "system_cpu"
    SYSTEM_MEMORY = "system_memory"
    ACTIVE_CONNECTIONS = "active_connections"


@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric point to dictionary."""
        return {
            'timestamp': self.timestamp,
            'value': self.value,
            'labels': self.labels,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat()
        }


@dataclass
class RequestMetrics:
    """Metrics for a specific request type."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    recent_durations: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def add_request(self, duration_ms: float, success: bool) -> None:
        """Add a request measurement."""
        self.total_requests += 1
        self.total_duration_ms += duration_ms
        self.recent_durations.append(duration_ms)
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100
    
    @property
    def average_duration_ms(self) -> float:
        """Calculate average request duration."""
        if self.total_requests == 0:
            return 0.0
        return self.total_duration_ms / self.total_requests
    
    @property
    def recent_average_duration_ms(self) -> float:
        """Calculate average duration for recent requests."""
        if not self.recent_durations:
            return 0.0
        return sum(self.recent_durations) / len(self.recent_durations)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.success_rate,
            'error_rate': self.error_rate,
            'average_duration_ms': self.average_duration_ms,
            'recent_average_duration_ms': self.recent_average_duration_ms,
            'min_duration_ms': self.min_duration_ms if self.min_duration_ms != float('inf') else 0.0,
            'max_duration_ms': self.max_duration_ms
        }


class PerformanceMonitor:
    """
    Performance monitoring service for tracking system and application metrics.
    
    This service provides comprehensive monitoring capabilities including:
    - Request processing time tracking
    - Success/error rate monitoring
    - System resource usage tracking
    - Real-time metrics collection and reporting
    """
    
    def __init__(self, max_history_points: int = 1000):
        """
        Initialize performance monitor.
        
        Args:
            max_history_points: Maximum number of historical data points to keep
        """
        self.logger = get_logger(__name__)
        self.max_history_points = max_history_points
        
        # Metrics storage
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_points))
        self._request_metrics: Dict[str, RequestMetrics] = defaultdict(RequestMetrics)
        
        # System monitoring
        self._system_monitoring_enabled = False
        self._system_monitor_thread: Optional[threading.Thread] = None
        self._system_monitor_interval = 5.0  # seconds
        self._shutdown_event = threading.Event()
        
        # Active connections tracking
        self._active_connections = 0
        self._connection_lock = threading.Lock()
        
        # Start time for uptime calculation
        self._start_time = time.time()
        
        self.logger.info("Performance monitor initialized", extra={
            'extra_data': {
                'max_history_points': max_history_points,
                'system_monitoring': self._system_monitoring_enabled
            }
        })
    
    def start_system_monitoring(self, interval: float = 5.0) -> None:
        """
        Start system resource monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self._system_monitoring_enabled:
            self.logger.warning("System monitoring is already running")
            return
        
        self._system_monitor_interval = interval
        self._system_monitoring_enabled = True
        self._shutdown_event.clear()
        
        self._system_monitor_thread = threading.Thread(
            target=self._system_monitor_loop,
            daemon=True
        )
        self._system_monitor_thread.start()
        
        self.logger.info("System monitoring started", extra={
            'extra_data': {'interval': interval}
        })
    
    def stop_system_monitoring(self) -> None:
        """Stop system resource monitoring."""
        if not self._system_monitoring_enabled:
            return
        
        self._system_monitoring_enabled = False
        self._shutdown_event.set()
        
        if self._system_monitor_thread and self._system_monitor_thread.is_alive():
            self._system_monitor_thread.join(timeout=2.0)
        
        self.logger.info("System monitoring stopped")
    
    def _system_monitor_loop(self) -> None:
        """System monitoring loop running in background thread."""
        while self._system_monitoring_enabled and not self._shutdown_event.is_set():
            try:
                # Collect CPU usage
                cpu_percent = psutil.cpu_percent(interval=None)
                self.record_metric(MetricType.SYSTEM_CPU, cpu_percent)
                
                # Collect memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                self.record_metric(MetricType.SYSTEM_MEMORY, memory_percent)
                
                # Record active connections
                with self._connection_lock:
                    self.record_metric(MetricType.ACTIVE_CONNECTIONS, self._active_connections)
                
            except Exception as e:
                self.logger.error(f"Error in system monitoring: {e}")
            
            # Wait for next interval
            self._shutdown_event.wait(self._system_monitor_interval)
    
    def record_metric(self, metric_type: MetricType, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record a metric value.
        
        Args:
            metric_type: Type of metric
            value: Metric value
            labels: Optional labels for the metric
        """
        timestamp = time.time()
        metric_point = MetricPoint(
            timestamp=timestamp,
            value=value,
            labels=labels or {}
        )
        
        self._metrics[metric_type.value].append(metric_point)
    
    def record_request(self, operation: str, duration_ms: float, success: bool, 
                      labels: Optional[Dict[str, str]] = None) -> None:
        """
        Record a request with its performance metrics.
        
        Args:
            operation: Operation name (e.g., 'base64_encode', 'http_post')
            duration_ms: Request duration in milliseconds
            success: Whether the request was successful
            labels: Optional labels for categorization
        """
        # Update request-specific metrics
        self._request_metrics[operation].add_request(duration_ms, success)
        
        # Record general metrics
        self.record_metric(MetricType.REQUEST_DURATION, duration_ms, 
                          {**(labels or {}), 'operation': operation})
        self.record_metric(MetricType.REQUEST_COUNT, 1, 
                          {**(labels or {}), 'operation': operation})
        
        if success:
            self.record_metric(MetricType.SUCCESS_COUNT, 1, 
                              {**(labels or {}), 'operation': operation})
        else:
            self.record_metric(MetricType.ERROR_COUNT, 1, 
                              {**(labels or {}), 'operation': operation})
        
        self.logger.debug(f"Recorded request metric", extra={
            'extra_data': {
                'operation': operation,
                'duration_ms': duration_ms,
                'success': success,
                'labels': labels
            }
        })
    
    def increment_active_connections(self) -> None:
        """Increment active connections counter."""
        with self._connection_lock:
            self._active_connections += 1
    
    def decrement_active_connections(self) -> None:
        """Decrement active connections counter."""
        with self._connection_lock:
            self._active_connections = max(0, self._active_connections - 1)
    
    def get_request_metrics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get request metrics for specific operation or all operations.
        
        Args:
            operation: Specific operation name, or None for all operations
            
        Returns:
            Dictionary containing request metrics
        """
        if operation:
            if operation in self._request_metrics:
                return {operation: self._request_metrics[operation].to_dict()}
            else:
                return {operation: RequestMetrics().to_dict()}
        
        return {
            op: metrics.to_dict() 
            for op, metrics in self._request_metrics.items()
        }
    
    def get_system_metrics(self, time_range_minutes: int = 10) -> Dict[str, Any]:
        """
        Get system metrics for the specified time range.
        
        Args:
            time_range_minutes: Time range in minutes
            
        Returns:
            Dictionary containing system metrics
        """
        cutoff_time = time.time() - (time_range_minutes * 60)
        
        result = {}
        
        for metric_type in [MetricType.SYSTEM_CPU, MetricType.SYSTEM_MEMORY, MetricType.ACTIVE_CONNECTIONS]:
            metric_name = metric_type.value
            points = [
                point for point in self._metrics[metric_name]
                if point.timestamp >= cutoff_time
            ]
            
            if points:
                values = [point.value for point in points]
                result[metric_name] = {
                    'current': values[-1] if values else 0,
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'data_points': len(values),
                    'time_range_minutes': time_range_minutes
                }
            else:
                result[metric_name] = {
                    'current': 0,
                    'average': 0,
                    'min': 0,
                    'max': 0,
                    'data_points': 0,
                    'time_range_minutes': time_range_minutes
                }
        
        return result
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive performance summary.
        
        Returns:
            Dictionary containing performance summary
        """
        uptime_seconds = time.time() - self._start_time
        
        # Calculate overall statistics
        total_requests = sum(metrics.total_requests for metrics in self._request_metrics.values())
        total_successful = sum(metrics.successful_requests for metrics in self._request_metrics.values())
        total_failed = sum(metrics.failed_requests for metrics in self._request_metrics.values())
        
        overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        overall_error_rate = (total_failed / total_requests * 100) if total_requests > 0 else 0
        
        # Get current system metrics
        current_system = self.get_system_metrics(time_range_minutes=1)
        
        return {
            'uptime_seconds': uptime_seconds,
            'uptime_formatted': str(timedelta(seconds=int(uptime_seconds))),
            'total_requests': total_requests,
            'successful_requests': total_successful,
            'failed_requests': total_failed,
            'overall_success_rate': overall_success_rate,
            'overall_error_rate': overall_error_rate,
            'active_connections': self._active_connections,
            'system_monitoring_enabled': self._system_monitoring_enabled,
            'current_system_metrics': current_system,
            'request_metrics_by_operation': self.get_request_metrics(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_metrics_for_export(self, time_range_minutes: int = 60) -> Dict[str, Any]:
        """
        Get metrics formatted for external monitoring systems.
        
        Args:
            time_range_minutes: Time range in minutes
            
        Returns:
            Dictionary containing metrics in export format
        """
        cutoff_time = time.time() - (time_range_minutes * 60)
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'time_range_minutes': time_range_minutes,
            'metrics': {}
        }
        
        # Export all metric types
        for metric_name, points in self._metrics.items():
            recent_points = [
                point.to_dict() for point in points
                if point.timestamp >= cutoff_time
            ]
            
            if recent_points:
                export_data['metrics'][metric_name] = {
                    'data_points': recent_points,
                    'summary': {
                        'count': len(recent_points),
                        'latest_value': recent_points[-1]['value'],
                        'average': sum(p['value'] for p in recent_points) / len(recent_points),
                        'min': min(p['value'] for p in recent_points),
                        'max': max(p['value'] for p in recent_points)
                    }
                }
        
        return export_data
    
    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing)."""
        self._metrics.clear()
        self._request_metrics.clear()
        self._start_time = time.time()
        
        self.logger.info("Performance metrics reset")
    
    def shutdown(self) -> None:
        """Shutdown the performance monitor."""
        self.stop_system_monitoring()
        self.logger.info("Performance monitor shutdown")


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """
    Get global performance monitor instance.
    
    Returns:
        PerformanceMonitor instance
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def record_request(operation: str, duration_ms: float, success: bool, 
                  labels: Optional[Dict[str, str]] = None) -> None:
    """
    Record a request with performance monitoring.
    
    Args:
        operation: Operation name
        duration_ms: Request duration in milliseconds
        success: Whether the request was successful
        labels: Optional labels for categorization
    """
    monitor = get_performance_monitor()
    monitor.record_request(operation, duration_ms, success, labels)


def get_performance_summary() -> Dict[str, Any]:
    """
    Get performance summary.
    
    Returns:
        Dictionary containing performance summary
    """
    monitor = get_performance_monitor()
    return monitor.get_performance_summary()


def start_system_monitoring(interval: float = 5.0) -> None:
    """
    Start system monitoring.
    
    Args:
        interval: Monitoring interval in seconds
    """
    monitor = get_performance_monitor()
    monitor.start_system_monitoring(interval)


def stop_system_monitoring() -> None:
    """Stop system monitoring."""
    monitor = get_performance_monitor()
    monitor.stop_system_monitoring()