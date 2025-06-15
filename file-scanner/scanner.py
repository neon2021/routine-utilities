import os
import hashlib
import socket
import psycopg2
import yaml
import magic
import time
from psycopg2.extras import execute_batch
from datetime import datetime

# === 从配置文件读取参数 ===
def load_config():
    config_name = "file-scanner-config.yml"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_home = os.path.expanduser("~")
    paths_to_try = [
        os.path.join(script_dir, config_name),
        os.path.join(user_home, config_name),
    ]
    for path in paths_to_try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return yaml.safe_load(f)
    raise FileNotFoundError("配置文件 file-scanner-config.yml 未找到")

config = load_config()
print("✅ Loaded config:")
print(config)

ROOT_DIRS = [os.path.expanduser(p) for p in config.get('scan_dirs', ['/tmp'])]
DB_CONFIG = config.get('db', {})
TABLE_NAME = config.get('table_name', 'file_inventory')
BATCH_SIZE = config.get('batch_size', 100)
FORCE_UPDATE = config.get('force_update', False)

# === 获取本机主机名 ===
machine_name = socket.gethostname()

# === 工具函数 ===
def calculate_md5(filepath, block_size=65536):
    md5 = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(block_size), b''):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception:
        return None

def get_mime_type(filepath):
    try:
        return magic.from_file(filepath, mime=True)
    except Exception:
        return 'application/octet-stream'

# === 创建数据表（如不存在） ===
create_table_sql = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id SERIAL PRIMARY KEY,
    machine VARCHAR(255),
    path TEXT UNIQUE,
    mime_type VARCHAR(100),
    md5 CHAR(32),
    size BIGINT,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    gmt_create TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scan_duration_secs REAL,
    deleted SMALLINT DEFAULT 0
);
"""

insert_sql = f"""
INSERT INTO {TABLE_NAME} (machine, path, mime_type, md5, size, scanned_at, gmt_create, scan_duration_secs, deleted)
VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, 0);
"""

mark_old_sql = f"""
UPDATE {TABLE_NAME}
SET deleted = 1, scanned_at = CURRENT_TIMESTAMP
WHERE path = %s AND deleted = 0;
"""

# === 扫描并处理文件 ===
def get_existing_record(path):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT md5, size FROM {TABLE_NAME} WHERE path = %s AND deleted = 0;", (path,))
                row = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        print(f"❌ 查询旧记录失败: {str(e)}")
        return None

def mark_old_record(path):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn:
            with conn.cursor() as cur:
                cur.execute(mark_old_sql, (path,))
        conn.close()
    except Exception as e:
        print(f"❌ 标记旧记录失败: {str(e)}")

insert_batch = []
total_inserted = 0

for root_dir in ROOT_DIRS:
    print(f"� 正在扫描目录: {root_dir}")
    for root, _, files in os.walk(root_dir):
        for name in files:
            full_path = os.path.join(root, name)
            try:
                if os.path.isfile(full_path):
                    start_time = time.time()
                    mime_type = get_mime_type(full_path)
                    md5_hash = calculate_md5(full_path)
                    file_size = os.path.getsize(full_path)
                    duration = round(time.time() - start_time, 4)
                    if not md5_hash:
                        continue

                    if FORCE_UPDATE:
                        mark_old_record(full_path)
                        insert_batch.append((machine_name, full_path, mime_type, md5_hash, file_size, duration))
                    else:
                        old_record = get_existing_record(full_path)
                        if old_record is None:
                            insert_batch.append((machine_name, full_path, mime_type, md5_hash, file_size, duration))
                        else:
                            old_md5, old_size = old_record
                            if md5_hash != old_md5 or file_size != old_size:
                                mark_old_record(full_path)
                                insert_batch.append((machine_name, full_path, mime_type, md5_hash, file_size, duration))

                    if len(insert_batch) >= BATCH_SIZE:
                        insert_records = insert_batch[:]
                        insert_batch.clear()
                        try:
                            conn = psycopg2.connect(**DB_CONFIG)
                            with conn:
                                with conn.cursor() as cur:
                                    execute_batch(cur, insert_sql, insert_records)
                            conn.close()
                            total_inserted += len(insert_records)
                        except Exception as e:
                            print(f"❌ 批量写入失败: {str(e)}")
            except Exception:
                continue

# === 写入剩余数据 ===
if insert_batch:
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn:
            with conn.cursor() as cur:
                execute_batch(cur, insert_sql, insert_batch)
        conn.close()
        total_inserted += len(insert_batch)
    except Exception as e:
        print(f"❌ 批量写入失败: {str(e)}")

# === 创建表（如不存在） ===
try:
    conn = psycopg2.connect(**DB_CONFIG)
    with conn:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
    conn.close()
except Exception as e:
    print(f"❌ 表创建失败: {str(e)}")

print(f"✅ 总共插入 {total_inserted} 条记录。")
