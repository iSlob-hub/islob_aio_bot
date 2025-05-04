import logging
import sys
from typing import Optional

from app.config import settings


def setup_logging(level: Optional[int] = None) -> None:
    """
    Configure logging for the application
    
    Args:
        level: Logging level (default: INFO)
    """
    if level is None:
        level = logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    
    # Set level for specific loggers
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    
    # Create logger for our app
    logger = logging.getLogger("app")
    logger.setLevel(level)
    
    return logger
