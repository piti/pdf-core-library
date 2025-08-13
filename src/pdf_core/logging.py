"""
Logging configuration and utilities for PDF Pipeline
"""
import logging
import logging.config
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json
import time
from functools import wraps


def setup_logging(
    level: str = "INFO", 
    log_file: Optional[Path] = None,
    json_format: bool = False,
    include_performance: bool = True
) -> logging.Logger:
    """
    Set up logging configuration for the PDF Pipeline.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file to write logs to
        json_format: Use JSON format for structured logging
        include_performance: Include performance metrics in logs
        
    Returns:
        Configured logger instance
    """
    
    # Create formatters
    if json_format:
        formatter_class = JsonFormatter
        format_string = None
    else:
        formatter_class = logging.Formatter
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure logging
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'class': formatter_class.__module__ + '.' + formatter_class.__name__,
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': level,
                'formatter': 'standard',
                'stream': sys.stdout,
            },
        },
        'loggers': {
            'pdf_pipeline': {
                'level': level,
                'handlers': ['console'],
                'propagate': False,
            },
            'root': {
                'level': level,
                'handlers': ['console'],
            }
        }
    }
    
    # Add format string for non-JSON formatter
    if format_string:
        logging_config['formatters']['standard']['format'] = format_string
    
    # Add file handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logging_config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': level,
            'formatter': 'standard',
            'filename': str(log_file),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
        }
        logging_config['loggers']['pdf_pipeline']['handlers'].append('file')
        logging_config['loggers']['root']['handlers'].append('file')
    
    # Apply configuration
    logging.config.dictConfig(logging_config)
    
    # Get logger
    logger = logging.getLogger('pdf_pipeline')
    
    # Add performance logging if requested
    if include_performance:
        logger.info(f"Logging initialized with level: {level}")
        if log_file:
            logger.info(f"Log file: {log_file}")
    
    return logger


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'lineno', 
                          'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process',
                          'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class PerformanceMonitor:
    """Performance monitoring utilities."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger('pdf_pipeline.performance')
        self.metrics: Dict[str, Any] = {}
    
    def start_timer(self, operation: str) -> None:
        """Start timing an operation."""
        self.metrics[f"{operation}_start"] = time.time()
    
    def end_timer(self, operation: str) -> float:
        """End timing an operation and return duration."""
        start_key = f"{operation}_start"
        if start_key not in self.metrics:
            self.logger.warning(f"Timer not started for operation: {operation}")
            return 0.0
        
        duration = time.time() - self.metrics[start_key]
        self.metrics[f"{operation}_duration"] = duration
        del self.metrics[start_key]
        
        self.logger.info(f"Operation '{operation}' completed", extra={
            'operation': operation,
            'duration': duration,
            'duration_ms': round(duration * 1000, 2)
        })
        
        return duration
    
    def record_metric(self, name: str, value: Any, unit: str = None) -> None:
        """Record a custom metric."""
        self.metrics[name] = value
        extra = {'metric_name': name, 'metric_value': value}
        if unit:
            extra['metric_unit'] = unit
        
        self.logger.info(f"Metric recorded: {name} = {value}", extra=extra)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all recorded metrics."""
        return self.metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()


def timed_operation(operation_name: str = None):
    """Decorator to time function execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            logger = logging.getLogger('pdf_pipeline.performance')
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"Function '{name}' completed successfully", extra={
                    'operation': name,
                    'duration': duration,
                    'duration_ms': round(duration * 1000, 2),
                    'success': True
                })
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Function '{name}' failed", extra={
                    'operation': name,
                    'duration': duration,
                    'duration_ms': round(duration * 1000, 2),
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                raise
        return wrapper
    return decorator


def log_system_info(logger: logging.Logger) -> None:
    """Log system information for debugging."""
    import platform
    import psutil
    
    try:
        system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_usage': psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else None
        }
        
        logger.info("System information", extra=system_info)
        
    except ImportError:
        logger.warning("psutil not available - limited system info")
        logger.info("Basic system info", extra={
            'platform': platform.platform(),
            'python_version': platform.python_version()
        })
    except Exception as e:
        logger.error(f"Failed to gather system info: {e}")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Convenience functions
def get_logger(name: str = 'pdf_pipeline') -> logging.Logger:
    """Get a configured logger instance."""
    return logging.getLogger(name)


def configure_logging_from_env() -> logging.Logger:
    """Configure logging from environment variables."""
    import os
    
    level = os.getenv('PDF_PIPELINE_LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('PDF_PIPELINE_LOG_FILE')
    json_format = os.getenv('PDF_PIPELINE_LOG_JSON', 'false').lower() == 'true'
    
    log_file_path = Path(log_file) if log_file else None
    
    return setup_logging(
        level=level,
        log_file=log_file_path,
        json_format=json_format
    )


# Auto-configure logging if imported
_logger = configure_logging_from_env()