import logging
import redis.asyncio as redis
import os
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
load_dotenv()


def setup_logger():
    logger = logging.getLogger()  
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = RotatingFileHandler(
            'app.log',
            maxBytes=5_000_000,  # 5 MB
            backupCount=3        # keep last 3 logs
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger

