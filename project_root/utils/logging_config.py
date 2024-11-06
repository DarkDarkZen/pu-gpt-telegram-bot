import logging
import os
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
import tempfile

# Debug mode flag from environment variable
DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

def setup_logging(name: str, log_file: str = None) -> logging.Logger:
    """Setup logging configuration"""
    logger = logging.getLogger(name)
    
    # Set base logging level
    base_level = logging.DEBUG if DEBUG_MODE else logging.INFO
    logger.setLevel(base_level)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # Debug console handler (only active in debug mode)
    if DEBUG_MODE:
        debug_console_handler = logging.StreamHandler(sys.stdout)
        debug_console_handler.setFormatter(detailed_formatter)
        debug_console_handler.setLevel(logging.DEBUG)
        debug_console_handler.addFilter(lambda record: record.levelno == logging.DEBUG)
        logger.addHandler(debug_console_handler)
    
    # File handler (if log_file is specified)
    if log_file:
        try:
            # Use system temp directory if we can't write to the specified directory
            log_dir = os.path.dirname(log_file)
            if not log_dir:
                log_dir = tempfile.gettempdir()
                log_file = os.path.join(log_dir, os.path.basename(log_file))
            else:
                try:
                    Path(log_dir).mkdir(parents=True, exist_ok=True)
                except (OSError, PermissionError):
                    # If we can't create the directory, use temp directory
                    log_dir = tempfile.gettempdir()
                    log_file = os.path.join(log_dir, os.path.basename(log_file))
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                mode='a',
                encoding='utf-8'
            )
            file_handler.setFormatter(detailed_formatter)
            file_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
            logger.addHandler(file_handler)
            
            logger.debug(f"Logging to file: {log_file}")
            
        except Exception as e:
            # If we can't set up file logging, log to console only
            logger.warning(f"Failed to set up file logging: {e}. Continuing with console logging only.")
    
    return logger

def log_function_call(logger: logging.Logger):
    """Decorator to log function calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(
                f"Calling {func_name} with args: {args}, kwargs: {kwargs}"
            )
            try:
                result = await func(*args, **kwargs)
                logger.debug(
                    f"{func_name} completed successfully"
                )
                return result
            except Exception as e:
                logger.error(
                    f"Error in {func_name}: {str(e)}",
                    exc_info=DEBUG_MODE
                )
                raise
        return wrapper
    return decorator 