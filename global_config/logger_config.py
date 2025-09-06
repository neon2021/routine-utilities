# logger_config.py
import logging
import os
from logging.handlers import RotatingFileHandler


base_dirs = ['/tmp',os.path.expanduser('~'),'']

def get_logger(logger_name:str="app"):
    for base_dir in base_dirs:
        LOG_DIR = os.path.join(base_dir, "logs")
        LOG_FILE = f"{logger_name}.log"
        os.makedirs(LOG_DIR, exist_ok=True)

        log_path = os.path.join(LOG_DIR, LOG_FILE)
        print(f'created log_path:{log_path}')
        
        if os.path.exists(LOG_DIR):
            break
        
    logger0 = logging.getLogger(logger_name)
    logger0.propagate=False
    if not logger0.hasHandlers():
        logger0.setLevel(logging.INFO)

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | pid=%(process)d | %(name)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler = RotatingFileHandler(
            log_path, maxBytes=100*1024*1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger0.addHandler(file_handler)
        logger0.addHandler(console_handler)
    return logger0


# 只配置一次，避免重复添加 handler
logger = get_logger("global")
global_logger = logger