import logging
import os
from logging.handlers import RotatingFileHandler
import sys

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
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
        logger.addHandler(file_handler)
    
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