import os
import hashlib
import socket
import psycopg2
import yaml
import magic
import time
from psycopg2.extras import execute_batch
from datetime import datetime

from global_config.config import yaml_config_boxed
from global_config.config import yaml_config
from global_config.logger_config import logger

DB_CONFIG_STR = yaml_config_boxed.transcribe.db_conn

def query_existing_records(start_id:int, limit:int=1000):
    try:
        conn = psycopg2.connect(DB_CONFIG_STR)
        with conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT id, path FROM file_inventory WHERE id > %s AND deleted = 0 order by id limit %s", (start_id, limit,))
                rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.info(f"❌ 查询旧记录失败: {str(e)}")
        return None


def delete_illegal_record(file_id:int):
    delete_old_row_sql = f"""
UPDATE file_inventory
SET deleted = 1, scanned_at = CURRENT_TIMESTAMP
WHERE id= %s AND deleted = 0;
"""
    try:
        conn = psycopg2.connect(DB_CONFIG_STR)
        with conn:
            with conn.cursor() as cur:
                cur.execute(delete_old_row_sql, (file_id,))
        conn.close()
    except Exception as e:
        logger.info(f"❌ 删除旧记录失败: {str(e)}")
        return None

start_id = 0
rows = query_existing_records(start_id)
while len(rows)>0:
    logger.info(f'scanning from start_id:{start_id}')
    
    for file_id, path in rows:
        if not os.path.exists(path):
            delete_illegal_record(file_id)
        start_id = file_id
    rows = query_existing_records(start_id)
