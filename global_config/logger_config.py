# logger_config.py
import logging
import os
from logging.handlers import RotatingFileHandler

base_dirs = ['/tmp',os.path.expanduser('~'),'']
for base_dir in base_dirs:
    LOG_DIR = os.path.join(base_dir, "logs")
    LOG_FILE = "app.log"
    os.makedirs(LOG_DIR, exist_ok=True)

    log_path = os.path.join(LOG_DIR, LOG_FILE)
    
    if os.path.exists(LOG_DIR):
        break

print(f'log_path:{log_path}')

# 只配置一次，避免重复添加 handler
logger = logging.getLogger("myapp")
if not logger.hasHandlers():
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        log_path, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
