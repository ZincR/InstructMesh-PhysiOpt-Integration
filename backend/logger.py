#!/usr/bin/env python3
"""
Session-based Logger Module
Logs all backend terminal output for each session
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


class TeeOutput:
    """Writes to both file and original stream"""
    
    def __init__(self, original_stream, log_file, stream_name):
        self.original_stream = original_stream
        self.log_file = log_file
        self.stream_name = stream_name
    
    def write(self, text):
        # Write to console
        self.original_stream.write(text)
        self.original_stream.flush()
        
        # Write to log file
        if text.strip():
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] [{self.stream_name}] {text}")
                f.flush()
    
    def flush(self):
        self.original_stream.flush()
    
    def fileno(self):
        return self.original_stream.fileno()
    
    def isatty(self):
        return self.original_stream.isatty()
    
    def readable(self):
        return getattr(self.original_stream, 'readable', lambda: False)()
    
    def writable(self):
        return getattr(self.original_stream, 'writable', lambda: True)()
    
    def seekable(self):
        return getattr(self.original_stream, 'seekable', lambda: False)()


class SessionLogger:
    """
    Logger that creates a new log file for each session
    Captures stdout, stderr, and application logs
    """
    
    def __init__(self, log_dir: str = "logs", session_id: Optional[str] = None):
        # Setup paths
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate session ID
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.session_id = session_id
        self.log_file = self.log_dir / f"session_{session_id}.log"
        self._is_resuming = self.log_file.exists()
        
        # Store original streams (unwrap if already redirected)
        self.original_stdout = getattr(sys.stdout, 'original_stream', sys.stdout)
        self.original_stderr = getattr(sys.stderr, 'original_stream', sys.stderr)
        
        # Setup logging
        self._setup_logging()
        
        # Redirect stdout/stderr
        self._redirect_streams()
        
        # Log initialization
        print(f"[LOGGER] Session logger initialized: {self.log_file}")
        print(f"[LOGGER] Session ID: {self.session_id}")
    
    def _setup_logging(self):
        """Setup Python logging"""
        self.logger = logging.getLogger('backend')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []  # Clear existing handlers
        
        # File handler - logs everything
        file_handler = logging.FileHandler(self.log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', 
                           datefmt='%Y-%m-%d %H:%M:%S')
        )
        self.logger.addHandler(file_handler)
        
        # Console handler - INFO and above
        console_handler = logging.StreamHandler(self.original_stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        self.logger.addHandler(console_handler)
        
        # Log session start or resume
        if getattr(self, '_is_resuming', False):
            self.logger.info("--- worker restarted (same session) ---")
        else:
            self.logger.info("=" * 80)
            self.logger.info(f"Session started: {self.session_id}")
            self.logger.info(f"Log file: {self.log_file}")
            self.logger.info("=" * 80)
    
    def _redirect_streams(self):
        """Redirect stdout and stderr to both file and console"""
        sys.stdout = TeeOutput(self.original_stdout, self.log_file, 'STDOUT')
        sys.stderr = TeeOutput(self.original_stderr, self.log_file, 'STDERR')
    
    def get_logger(self) -> logging.Logger:
        """Get the logger instance"""
        return self.logger
    
    def get_log_path(self) -> Path:
        """Get the path to the current log file"""
        return self.log_file
    
    def cleanup(self):
        """Restore original streams and log session end"""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        self.logger.info("=" * 80)
        self.logger.info(f"Session ended: {self.session_id}")
        self.logger.info("=" * 80)


# Global session logger instance
_session_logger: Optional[SessionLogger] = None


def init_session_logger(log_dir: str = "logs", session_id: Optional[str] = None) -> SessionLogger:
    """
    Initialize the global session logger (singleton pattern)
    
    Args:
        log_dir: Directory to store log files
        session_id: Optional session ID
    
    Returns:
        SessionLogger instance
    """
    global _session_logger
    
    # Only create new logger if one doesn't exist
    # Check if already initialized by looking for redirected stdout
    if _session_logger is None and not hasattr(sys.stdout, 'original_stream'):
        _session_logger = SessionLogger(log_dir, session_id)
    elif _session_logger is None:
        # Logger is None but stdout is redirected - create logger anyway
        # This handles edge cases where module is reloaded
        _session_logger = SessionLogger(log_dir, session_id)
    
    return _session_logger


def get_logger() -> logging.Logger:
    """Get the global logger instance (auto-initializes if needed)"""
    global _session_logger
    if _session_logger is None:
        _session_logger = SessionLogger(session_id=os.environ.get("BACKEND_SESSION_ID"))
    return _session_logger.get_logger()


def get_session_logger() -> Optional[SessionLogger]:
    """Get the global session logger instance"""
    return _session_logger
