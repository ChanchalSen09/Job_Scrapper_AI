import logging
import os
from logging.handlers import RotatingFileHandler
import config

def setup_logger(name: str='job_hunter') -> logging.Logger:
    os.makedirs(config.LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    file_handler = RotatingFileHandler(config.LOG_FILE, maxBytes=config.LOG_MAX_BYTES, backupCount=config.LOG_BACKUP_COUNT, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter('[%(asctime)s] [%(levelname)-8s] [%(name)-20s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_fmt)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter('[%(asctime)s] [%(levelname)-8s] %(message)s', datefmt='%H:%M:%S')
    console_handler.setFormatter(console_fmt)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

def get_logger(module_name: str) -> logging.Logger:
    return logging.getLogger(f'job_hunter.{module_name}')