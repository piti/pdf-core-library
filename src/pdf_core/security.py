"""
Security and rate limiting utilities for PDF Pipeline.

This module provides production hardening features including:
- Rate limiting for MCP server requests
- Request validation and sanitization
- Security monitoring and logging
- Resource usage controls
"""

import time
import hashlib
import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    
    requests_per_minute: int
    requests_per_hour: int
    burst_limit: int = 10
    cooldown_seconds: int = 60


@dataclass
class SecurityEvent:
    """Security event for monitoring and logging."""
    
    timestamp: datetime
    event_type: str
    client_id: str
    details: Dict[str, Any]
    severity: str = "info"  # info, warning, error, critical


class RateLimiter:
    """
    Thread-safe rate limiter for MCP server requests.
    
    Implements token bucket algorithm with burst handling.
    """
    
    def __init__(self, rules: Dict[str, RateLimitRule]):
        """
        Initialize rate limiter with rules.
        
        Args:
            rules: Dictionary mapping operation names to rate limit rules
        """
        self.rules = rules
        self.client_buckets = defaultdict(lambda: defaultdict(deque))
        self.lock = threading.RLock()
        
    def is_allowed(self, client_id: str, operation: str) -> Tuple[bool, Optional[str]]:
        """
        Check if request is allowed under rate limits.
        
        Args:
            client_id: Unique identifier for client
            operation: Operation being performed
            
        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        if operation not in self.rules:
            return True, None
            
        rule = self.rules[operation]
        current_time = time.time()
        
        with self.lock:
            # Clean old requests
            self._cleanup_old_requests(client_id, operation, current_time)
            
            # Get current request counts
            minute_requests = self._count_requests_in_window(
                client_id, operation, current_time, 60
            )
            hour_requests = self._count_requests_in_window(
                client_id, operation, current_time, 3600
            )
            
            # Check limits
            if minute_requests >= rule.requests_per_minute:
                return False, f"Rate limit exceeded: {minute_requests}/{rule.requests_per_minute} per minute"
            
            if hour_requests >= rule.requests_per_hour:
                return False, f"Rate limit exceeded: {hour_requests}/{rule.requests_per_hour} per hour"
                
            # Check burst limit
            recent_requests = self._count_requests_in_window(
                client_id, operation, current_time, 10  # Last 10 seconds
            )
            if recent_requests >= rule.burst_limit:
                return False, f"Burst limit exceeded: {recent_requests}/{rule.burst_limit} in 10s"
            
            # Allow request and record it
            self.client_buckets[client_id][operation].append(current_time)
            return True, None
    
    def _cleanup_old_requests(self, client_id: str, operation: str, current_time: float):
        """Remove requests older than 1 hour."""
        bucket = self.client_buckets[client_id][operation]
        cutoff_time = current_time - 3600  # 1 hour ago
        
        while bucket and bucket[0] < cutoff_time:
            bucket.popleft()
    
    def _count_requests_in_window(self, client_id: str, operation: str, 
                                current_time: float, window_seconds: int) -> int:
        """Count requests in a time window."""
        bucket = self.client_buckets[client_id][operation]
        cutoff_time = current_time - window_seconds
        
        return sum(1 for req_time in bucket if req_time >= cutoff_time)
    
    def get_client_stats(self, client_id: str) -> Dict[str, Dict[str, int]]:
        """Get rate limiting statistics for a client."""
        current_time = time.time()
        stats = {}
        
        with self.lock:
            for operation in self.client_buckets[client_id]:
                self._cleanup_old_requests(client_id, operation, current_time)
                
                stats[operation] = {
                    'last_minute': self._count_requests_in_window(client_id, operation, current_time, 60),
                    'last_hour': self._count_requests_in_window(client_id, operation, current_time, 3600),
                    'last_10_seconds': self._count_requests_in_window(client_id, operation, current_time, 10)
                }
        
        return stats


class RequestValidator:
    """
    Validates and sanitizes MCP server requests.
    """
    
    # Maximum sizes for different content types
    MAX_CONTENT_SIZE = 1024 * 1024  # 1MB for markdown content
    MAX_FILENAME_LENGTH = 255
    MAX_ASSET_SIZE = 10 * 1024 * 1024  # 10MB for assets
    
    # Allowed patterns
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
    SAFE_BRAND_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    
    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        re.compile(r'<script[^>]*>', re.IGNORECASE),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'data:.*base64', re.IGNORECASE),
        re.compile(r'file://', re.IGNORECASE),
        re.compile(r'\.\./'),  # Path traversal
    ]
    
    @classmethod
    def validate_markdown_content(cls, content: str) -> Tuple[bool, List[str]]:
        """
        Validate markdown content for security issues.
        
        Args:
            content: Markdown content to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check content size
        if len(content) > cls.MAX_CONTENT_SIZE:
            issues.append(f"Content too large: {len(content)} bytes > {cls.MAX_CONTENT_SIZE}")
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(content):
                issues.append(f"Dangerous pattern detected: {pattern.pattern}")
        
        # Check for excessive nesting or complexity
        if content.count('\n') > 10000:
            issues.append("Content has excessive line count (>10,000 lines)")
        
        return len(issues) == 0, issues
    
    @classmethod
    def validate_filename(cls, filename: str) -> Tuple[bool, List[str]]:
        """
        Validate filename for security.
        
        Args:
            filename: Filename to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check length
        if len(filename) > cls.MAX_FILENAME_LENGTH:
            issues.append(f"Filename too long: {len(filename)} > {cls.MAX_FILENAME_LENGTH}")
        
        # Check for safe characters
        if not cls.SAFE_FILENAME_PATTERN.match(filename):
            issues.append("Filename contains unsafe characters")
        
        # Check for reserved names
        reserved_names = ['con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 
                         'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 
                         'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9']
        if filename.lower() in reserved_names:
            issues.append(f"Filename is a reserved name: {filename}")
        
        return len(issues) == 0, issues
    
    @classmethod
    def validate_brand_name(cls, brand_name: str) -> Tuple[bool, List[str]]:
        """
        Validate brand name for security.
        
        Args:
            brand_name: Brand name to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check length
        if len(brand_name) < 2:
            issues.append("Brand name too short (minimum 2 characters)")
        if len(brand_name) > 50:
            issues.append("Brand name too long (maximum 50 characters)")
        
        # Check for safe characters
        if not cls.SAFE_BRAND_NAME_PATTERN.match(brand_name):
            issues.append("Brand name contains unsafe characters (only letters, numbers, hyphens, underscores allowed)")
        
        # Check for reserved names
        if brand_name.lower() in ['admin', 'root', 'system', 'default', 'test']:
            issues.append(f"Brand name is reserved: {brand_name}")
        
        return len(issues) == 0, issues
    
    @classmethod
    def validate_asset_data(cls, asset_data: str, asset_type: str) -> Tuple[bool, List[str]]:
        """
        Validate base64 asset data.
        
        Args:
            asset_data: Base64 encoded asset data
            asset_type: Type of asset
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check data size
        try:
            import base64
            decoded_size = len(base64.b64decode(asset_data))
            if decoded_size > cls.MAX_ASSET_SIZE:
                issues.append(f"Asset too large: {decoded_size} bytes > {cls.MAX_ASSET_SIZE}")
        except Exception as e:
            issues.append(f"Invalid base64 data: {e}")
        
        return len(issues) == 0, issues
    
    @classmethod
    def sanitize_text_input(cls, text: str, max_length: int = 1000) -> str:
        """
        Sanitize text input by removing dangerous content.
        
        Args:
            text: Text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        # Truncate to max length
        text = text[:max_length]
        
        # Remove dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            text = pattern.sub('', text)
        
        # Remove null bytes and control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        return text.strip()


class SecurityMonitor:
    """
    Monitor security events and provide alerting.
    """
    
    def __init__(self, log_file: Optional[Path] = None):
        """
        Initialize security monitor.
        
        Args:
            log_file: Optional file to log security events
        """
        self.events = deque(maxlen=1000)  # Keep last 1000 events
        self.log_file = log_file
        self.lock = threading.Lock()
        
    def log_event(self, event_type: str, client_id: str, details: Dict[str, Any], 
                  severity: str = "info"):
        """
        Log a security event.
        
        Args:
            event_type: Type of event (rate_limit, validation_error, etc.)
            client_id: Client identifier
            details: Event details
            severity: Event severity level
        """
        event = SecurityEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            client_id=client_id,
            details=details,
            severity=severity
        )
        
        with self.lock:
            self.events.append(event)
            
            # Log to file if configured
            if self.log_file:
                self._write_to_log_file(event)
        
        # Log to standard logger based on severity
        log_message = f"Security event [{event_type}] from {client_id}: {details}"
        if severity == "critical":
            logger.critical(log_message)
        elif severity == "error":
            logger.error(log_message)
        elif severity == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _write_to_log_file(self, event: SecurityEvent):
        """Write event to log file."""
        try:
            log_entry = {
                'timestamp': event.timestamp.isoformat(),
                'event_type': event.event_type,
                'client_id': event.client_id,
                'details': event.details,
                'severity': event.severity
            }
            
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write security event to log file: {e}")
    
    def get_recent_events(self, minutes: int = 60, 
                         severity: Optional[str] = None) -> List[SecurityEvent]:
        """
        Get recent security events.
        
        Args:
            minutes: Number of minutes to look back
            severity: Optional severity filter
            
        Returns:
            List of matching security events
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self.lock:
            events = [
                event for event in self.events
                if event.timestamp >= cutoff_time
                and (severity is None or event.severity == severity)
            ]
        
        return sorted(events, key=lambda e: e.timestamp, reverse=True)
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get summary of security events."""
        with self.lock:
            events_by_type = defaultdict(int)
            events_by_severity = defaultdict(int)
            recent_clients = set()
            
            # Analyze last hour of events
            recent_cutoff = datetime.now() - timedelta(hours=1)
            recent_events = [e for e in self.events if e.timestamp >= recent_cutoff]
            
            for event in recent_events:
                events_by_type[event.event_type] += 1
                events_by_severity[event.severity] += 1
                recent_clients.add(event.client_id)
        
        return {
            'total_events_last_hour': len(recent_events),
            'events_by_type': dict(events_by_type),
            'events_by_severity': dict(events_by_severity),
            'unique_clients_last_hour': len(recent_clients),
            'total_events_stored': len(self.events)
        }


class ProductionSecurityManager:
    """
    Main security manager for production deployments.
    """
    
    def __init__(self, 
                 rate_limit_rules: Optional[Dict[str, RateLimitRule]] = None,
                 log_file: Optional[Path] = None):
        """
        Initialize production security manager.
        
        Args:
            rate_limit_rules: Custom rate limiting rules
            log_file: Security event log file
        """
        # Default rate limiting rules
        default_rules = {
            'generate_pdf': RateLimitRule(
                requests_per_minute=10,
                requests_per_hour=100,
                burst_limit=3,
                cooldown_seconds=30
            ),
            'upload_asset': RateLimitRule(
                requests_per_minute=20,
                requests_per_hour=200,
                burst_limit=5,
                cooldown_seconds=10
            ),
            'create_brand': RateLimitRule(
                requests_per_minute=5,
                requests_per_hour=20,
                burst_limit=2,
                cooldown_seconds=60
            ),
            'list_brands': RateLimitRule(
                requests_per_minute=30,
                requests_per_hour=500,
                burst_limit=10,
                cooldown_seconds=5
            )
        }
        
        self.rate_limiter = RateLimiter(rate_limit_rules or default_rules)
        self.validator = RequestValidator()
        self.monitor = SecurityMonitor(log_file)
    
    def check_request_allowed(self, client_id: str, operation: str, 
                            request_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Comprehensive request validation and rate limiting.
        
        Args:
            client_id: Client identifier
            operation: Operation being performed
            request_data: Request data to validate
            
        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        # Rate limiting check
        allowed, rate_reason = self.rate_limiter.is_allowed(client_id, operation)
        if not allowed:
            self.monitor.log_event(
                'rate_limit_exceeded',
                client_id,
                {'operation': operation, 'reason': rate_reason},
                'warning'
            )
            return False, rate_reason
        
        # Request validation
        validation_issues = self._validate_request_data(operation, request_data)
        if validation_issues:
            self.monitor.log_event(
                'validation_error',
                client_id,
                {'operation': operation, 'issues': validation_issues},
                'error'
            )
            return False, f"Validation failed: {'; '.join(validation_issues)}"
        
        # Log successful request
        self.monitor.log_event(
            'request_allowed',
            client_id,
            {'operation': operation},
            'info'
        )
        
        return True, ""
    
    def _validate_request_data(self, operation: str, data: Dict[str, Any]) -> List[str]:
        """Validate request data based on operation type."""
        issues = []
        
        if operation == 'generate_pdf':
            if 'content' in data:
                valid, content_issues = self.validator.validate_markdown_content(data['content'])
                if not valid:
                    issues.extend(content_issues)
            
            if 'output_filename' in data:
                valid, filename_issues = self.validator.validate_filename(data['output_filename'])
                if not valid:
                    issues.extend(filename_issues)
        
        elif operation == 'upload_asset':
            if 'brand_name' in data:
                valid, brand_issues = self.validator.validate_brand_name(data['brand_name'])
                if not valid:
                    issues.extend(brand_issues)
            
            if 'asset_data' in data and 'asset_type' in data:
                valid, asset_issues = self.validator.validate_asset_data(
                    data['asset_data'], data['asset_type']
                )
                if not valid:
                    issues.extend(asset_issues)
        
        elif operation == 'create_brand':
            if 'brand_name' in data:
                valid, brand_issues = self.validator.validate_brand_name(data['brand_name'])
                if not valid:
                    issues.extend(brand_issues)
        
        return issues
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status."""
        return {
            'monitor_summary': self.monitor.get_security_summary(),
            'rate_limiting_active': True,
            'validation_active': True,
            'timestamp': datetime.now().isoformat()
        }


def create_production_security_manager(log_dir: Optional[Path] = None) -> ProductionSecurityManager:
    """
    Create a production security manager with recommended settings.
    
    Args:
        log_dir: Directory for security logs
        
    Returns:
        Configured ProductionSecurityManager
    """
    log_file = None
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"security_{datetime.now().strftime('%Y%m%d')}.log"
    
    return ProductionSecurityManager(log_file=log_file)