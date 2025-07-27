"""
Tests for the performance monitoring service.

This module contains comprehensive tests for the performance monitoring functionality,
including request tracking, system monitoring, and metrics collection.
"""

import unittest
import time
import threading
from unittest.mock import patch, MagicMock

from services.performance_monitor import (
    PerformanceMonitor, MetricPoint, RequestMetrics, MetricType,
    record_request, get_performance_summary, start_system_monitoring, stop_system_monitoring
)


class TestMetricPoint(unittest.TestCase):
    """Test MetricPoint data class."""
    
    def test_metric_point_creation(self):
        """Test creating a metric point."""
        timestamp = time.time()
        point = MetricPoint(
            timestamp=timestamp,
            value=123.45,
            labels={'operation': 'test', 'status': 'success'}
        )
        
        self.assertEqual(point.timestamp, timestamp)
        self.assertEqual(point.value, 123.45)
        self.assertEqual(point.labels['operation'], 'test')
        self.assertEqual(point.labels['status'], 'success')
    
    def test_metric_point_to_dict(self):
        """Test converting metric point to dictionary."""
        timestamp = time.time()
        point = MetricPoint(
            timestamp=timestamp,
            value=100.0,
            labels={'key': 'value'}
        )
        
        result = point.to_dict()
        
        self.assertEqual(result['timestamp'], timestamp)
        self.assertEqual(result['value'], 100.0)
        self.assertEqual(result['labels'], {'key': 'value'})
        self.assertIn('datetime', result)


class TestRequestMetrics(unittest.TestCase):
    """Test RequestMetrics data class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.metrics = RequestMetrics()
    
    def test_initial_state(self):
        """Test initial state of request metrics."""
        self.assertEqual(self.metrics.total_requests, 0)
        self.assertEqual(self.metrics.successful_requests, 0)
        self.assertEqual(self.metrics.failed_requests, 0)
        self.assertEqual(self.metrics.total_duration_ms, 0.0)
        self.assertEqual(self.metrics.success_rate, 0.0)
        self.assertEqual(self.metrics.error_rate, 0.0)
        self.assertEqual(self.metrics.average_duration_ms, 0.0)
    
    def test_add_successful_request(self):
        """Test adding a successful request."""
        self.metrics.add_request(100.0, True)
        
        self.assertEqual(self.metrics.total_requests, 1)
        self.assertEqual(self.metrics.successful_requests, 1)
        self.assertEqual(self.metrics.failed_requests, 0)
        self.assertEqual(self.metrics.total_duration_ms, 100.0)
        self.assertEqual(self.metrics.success_rate, 100.0)
        self.assertEqual(self.metrics.error_rate, 0.0)
        self.assertEqual(self.metrics.average_duration_ms, 100.0)
        self.assertEqual(self.metrics.min_duration_ms, 100.0)
        self.assertEqual(self.metrics.max_duration_ms, 100.0)
    
    def test_add_failed_request(self):
        """Test adding a failed request."""
        self.metrics.add_request(200.0, False)
        
        self.assertEqual(self.metrics.total_requests, 1)
        self.assertEqual(self.metrics.successful_requests, 0)
        self.assertEqual(self.metrics.failed_requests, 1)
        self.assertEqual(self.metrics.success_rate, 0.0)
        self.assertEqual(self.metrics.error_rate, 100.0)
    
    def test_mixed_requests(self):
        """Test adding mixed successful and failed requests."""
        self.metrics.add_request(100.0, True)
        self.metrics.add_request(200.0, False)
        self.metrics.add_request(150.0, True)
        
        self.assertEqual(self.metrics.total_requests, 3)
        self.assertEqual(self.metrics.successful_requests, 2)
        self.assertEqual(self.metrics.failed_requests, 1)
        self.assertAlmostEqual(self.metrics.success_rate, 66.67, places=1)
        self.assertAlmostEqual(self.metrics.error_rate, 33.33, places=1)
        self.assertEqual(self.metrics.average_duration_ms, 150.0)
        self.assertEqual(self.metrics.min_duration_ms, 100.0)
        self.assertEqual(self.metrics.max_duration_ms, 200.0)
    
    def test_recent_average_duration(self):
        """Test recent average duration calculation."""
        # Add some requests
        for i in range(5):
            self.metrics.add_request(100.0 + i * 10, True)
        
        expected_recent_avg = (100 + 110 + 120 + 130 + 140) / 5
        self.assertEqual(self.metrics.recent_average_duration_ms, expected_recent_avg)
    
    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        self.metrics.add_request(100.0, True)
        self.metrics.add_request(200.0, False)
        
        result = self.metrics.to_dict()
        
        self.assertEqual(result['total_requests'], 2)
        self.assertEqual(result['successful_requests'], 1)
        self.assertEqual(result['failed_requests'], 1)
        self.assertEqual(result['success_rate'], 50.0)
        self.assertEqual(result['error_rate'], 50.0)
        self.assertEqual(result['average_duration_ms'], 150.0)
        self.assertEqual(result['min_duration_ms'], 100.0)
        self.assertEqual(result['max_duration_ms'], 200.0)


class TestPerformanceMonitor(unittest.TestCase):
    """Test PerformanceMonitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = PerformanceMonitor(max_history_points=100)
    
    def tearDown(self):
        """Clean up after tests."""
        self.monitor.stop_system_monitoring()
    
    def test_initialization(self):
        """Test monitor initialization."""
        self.assertEqual(self.monitor.max_history_points, 100)
        self.assertFalse(self.monitor._system_monitoring_enabled)
        self.assertEqual(self.monitor._active_connections, 0)
    
    def test_record_metric(self):
        """Test recording a metric."""
        self.monitor.record_metric(MetricType.REQUEST_DURATION, 123.45, {'op': 'test'})
        
        metrics = self.monitor._metrics[MetricType.REQUEST_DURATION.value]
        self.assertEqual(len(metrics), 1)
        
        point = metrics[0]
        self.assertEqual(point.value, 123.45)
        self.assertEqual(point.labels['op'], 'test')
    
    def test_record_request(self):
        """Test recording a request."""
        self.monitor.record_request('test_operation', 100.0, True, {'client': 'test'})
        
        # Check request metrics
        request_metrics = self.monitor.get_request_metrics('test_operation')
        self.assertIn('test_operation', request_metrics)
        
        metrics = request_metrics['test_operation']
        self.assertEqual(metrics['total_requests'], 1)
        self.assertEqual(metrics['successful_requests'], 1)
        self.assertEqual(metrics['success_rate'], 100.0)
    
    def test_connection_tracking(self):
        """Test active connection tracking."""
        self.assertEqual(self.monitor._active_connections, 0)
        
        self.monitor.increment_active_connections()
        self.assertEqual(self.monitor._active_connections, 1)
        
        self.monitor.increment_active_connections()
        self.assertEqual(self.monitor._active_connections, 2)
        
        self.monitor.decrement_active_connections()
        self.assertEqual(self.monitor._active_connections, 1)
        
        self.monitor.decrement_active_connections()
        self.assertEqual(self.monitor._active_connections, 0)
        
        # Test that it doesn't go below 0
        self.monitor.decrement_active_connections()
        self.assertEqual(self.monitor._active_connections, 0)
    
    def test_get_request_metrics_all(self):
        """Test getting all request metrics."""
        self.monitor.record_request('op1', 100.0, True)
        self.monitor.record_request('op2', 200.0, False)
        
        all_metrics = self.monitor.get_request_metrics()
        
        self.assertIn('op1', all_metrics)
        self.assertIn('op2', all_metrics)
        self.assertEqual(all_metrics['op1']['success_rate'], 100.0)
        self.assertEqual(all_metrics['op2']['error_rate'], 100.0)
    
    def test_get_request_metrics_specific(self):
        """Test getting specific operation metrics."""
        self.monitor.record_request('specific_op', 150.0, True)
        
        metrics = self.monitor.get_request_metrics('specific_op')
        
        self.assertIn('specific_op', metrics)
        self.assertEqual(metrics['specific_op']['average_duration_ms'], 150.0)
    
    def test_get_request_metrics_nonexistent(self):
        """Test getting metrics for non-existent operation."""
        metrics = self.monitor.get_request_metrics('nonexistent')
        
        self.assertIn('nonexistent', metrics)
        self.assertEqual(metrics['nonexistent']['total_requests'], 0)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_system_monitoring(self, mock_memory, mock_cpu):
        """Test system monitoring functionality."""
        # Mock system metrics
        mock_cpu.return_value = 50.0
        mock_memory.return_value = MagicMock(percent=75.0)
        
        # Start monitoring with short interval
        self.monitor.start_system_monitoring(interval=0.1)
        
        # Wait a bit for metrics to be collected
        time.sleep(0.2)
        
        # Stop monitoring
        self.monitor.stop_system_monitoring()
        
        # Check that metrics were recorded
        cpu_metrics = self.monitor._metrics[MetricType.SYSTEM_CPU.value]
        memory_metrics = self.monitor._metrics[MetricType.SYSTEM_MEMORY.value]
        
        self.assertGreater(len(cpu_metrics), 0)
        self.assertGreater(len(memory_metrics), 0)
    
    def test_get_system_metrics(self):
        """Test getting system metrics."""
        # Record some test metrics
        self.monitor.record_metric(MetricType.SYSTEM_CPU, 50.0)
        self.monitor.record_metric(MetricType.SYSTEM_CPU, 60.0)
        self.monitor.record_metric(MetricType.SYSTEM_MEMORY, 70.0)
        
        system_metrics = self.monitor.get_system_metrics(time_range_minutes=10)
        
        self.assertIn('system_cpu', system_metrics)
        self.assertIn('system_memory', system_metrics)
        
        cpu_metrics = system_metrics['system_cpu']
        self.assertEqual(cpu_metrics['current'], 60.0)
        self.assertEqual(cpu_metrics['average'], 55.0)
        self.assertEqual(cpu_metrics['min'], 50.0)
        self.assertEqual(cpu_metrics['max'], 60.0)
    
    def test_get_performance_summary(self):
        """Test getting performance summary."""
        # Add some test data
        self.monitor.record_request('test_op', 100.0, True)
        self.monitor.record_request('test_op', 200.0, False)
        self.monitor.increment_active_connections()
        
        summary = self.monitor.get_performance_summary()
        
        self.assertIn('uptime_seconds', summary)
        self.assertIn('total_requests', summary)
        self.assertIn('successful_requests', summary)
        self.assertIn('failed_requests', summary)
        self.assertIn('overall_success_rate', summary)
        self.assertIn('overall_error_rate', summary)
        self.assertIn('active_connections', summary)
        self.assertIn('request_metrics_by_operation', summary)
        
        self.assertEqual(summary['total_requests'], 2)
        self.assertEqual(summary['successful_requests'], 1)
        self.assertEqual(summary['failed_requests'], 1)
        self.assertEqual(summary['overall_success_rate'], 50.0)
        self.assertEqual(summary['overall_error_rate'], 50.0)
        self.assertEqual(summary['active_connections'], 1)
    
    def test_get_metrics_for_export(self):
        """Test getting metrics for export."""
        # Record some metrics
        self.monitor.record_metric(MetricType.REQUEST_DURATION, 100.0, {'op': 'test'})
        self.monitor.record_metric(MetricType.REQUEST_DURATION, 200.0, {'op': 'test'})
        
        export_data = self.monitor.get_metrics_for_export(time_range_minutes=10)
        
        self.assertIn('timestamp', export_data)
        self.assertIn('time_range_minutes', export_data)
        self.assertIn('metrics', export_data)
        
        metrics = export_data['metrics']
        self.assertIn('request_duration', metrics)
        
        duration_metrics = metrics['request_duration']
        self.assertIn('data_points', duration_metrics)
        self.assertIn('summary', duration_metrics)
        
        summary = duration_metrics['summary']
        self.assertEqual(summary['count'], 2)
        self.assertEqual(summary['latest_value'], 200.0)
        self.assertEqual(summary['average'], 150.0)
    
    def test_reset_metrics(self):
        """Test resetting metrics."""
        # Add some data
        self.monitor.record_request('test_op', 100.0, True)
        self.monitor.record_metric(MetricType.SYSTEM_CPU, 50.0)
        
        # Verify data exists
        self.assertGreater(len(self.monitor._request_metrics), 0)
        self.assertGreater(len(self.monitor._metrics), 0)
        
        # Reset metrics
        self.monitor.reset_metrics()
        
        # Verify data is cleared
        self.assertEqual(len(self.monitor._request_metrics), 0)
        self.assertEqual(len(self.monitor._metrics), 0)


class TestGlobalFunctions(unittest.TestCase):
    """Test global performance monitoring functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset global monitor
        import services.performance_monitor
        services.performance_monitor._performance_monitor = None
    
    def test_record_request_global(self):
        """Test global record_request function."""
        record_request('global_test', 123.45, True, {'client': 'test'})
        
        summary = get_performance_summary()
        self.assertEqual(summary['total_requests'], 1)
        self.assertEqual(summary['successful_requests'], 1)
    
    def test_get_performance_summary_global(self):
        """Test global get_performance_summary function."""
        record_request('test_op', 100.0, True)
        
        summary = get_performance_summary()
        
        self.assertIn('total_requests', summary)
        self.assertIn('uptime_seconds', summary)
        self.assertEqual(summary['total_requests'], 1)
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_system_monitoring_global(self, mock_memory, mock_cpu):
        """Test global system monitoring functions."""
        mock_cpu.return_value = 25.0
        mock_memory.return_value = MagicMock(percent=50.0)
        
        # Start monitoring
        start_system_monitoring(interval=0.1)
        
        # Wait briefly
        time.sleep(0.15)
        
        # Stop monitoring
        stop_system_monitoring()
        
        # Check that monitoring was active
        summary = get_performance_summary()
        self.assertIn('system_monitoring_enabled', summary)


if __name__ == '__main__':
    unittest.main()