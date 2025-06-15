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

# === 获取本机主机名 ===
machine_name = socket.gethostname()

# === 工具函数：计算文件的 MD5 ===
def calculate_md5(filepath, block_size=65536):
    md5 = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(block_size), b''):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception:
        return None

# === 工具函数：获取 MIME 类型（读取内容） ===
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

# === 插入语句（避免重复） ===
insert_sql = f"""
INSERT INTO {TABLE_NAME} (machine, path, mime_type, md5, size, scanned_at, gmt_create, scan_duration_secs, deleted)
VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, 0)
ON CONFLICT (path) DO NOTHING;
"""

# === 更新旧记录为已删除并记录新状态 ===
update_deleted_sql = f"""
UPDATE {TABLE_NAME}
SET deleted = 1, scanned_at = CURRENT_TIMESTAMP,
    md5 = %s, size = %s, mime_type = %s, scan_duration_secs = %s
WHERE path = %s AND (md5 IS DISTINCT FROM %s OR size IS DISTINCT FROM %s);
"""

# === 执行插入 ===
def insert_records(records):
    if not records:
        return
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn:
            with conn.cursor() as cur:
                execute_batch(cur, insert_sql, records)
        conn.close()
    except Exception as e:
        print(f"❌ 批量写入失败: {str(e)}")

# === 执行标记旧记录已删除并更新字段 ===
def mark_old_versions(update_tuples):
    if not update_tuples:
        return
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn:
            with conn.cursor() as cur:
                execute_batch(cur, update_deleted_sql, update_tuples)
        conn.close()
    except Exception as e:
        print(f"❌ 批量更新失败: {str(e)}")

# === 扫描并处理文件 ===
batch_insert = []
batch_update = []
total_inserted = 0

for root_dir in ROOT_DIRS:
    print(f"� 正在扫描目录: {root_dir}")
    for root, _, files in os.walk(root_dir):
        for name in files:
            full_path = os.path.join(root, name)
            print(f"full_path: {full_path}")
            try:
                if os.path.isfile(full_path):
                    start_time = time.time()
                    mime_type = get_mime_type(full_path)
                    md5_hash = calculate_md5(full_path)
                    file_size = os.path.getsize(full_path)
                    duration = round(time.time() - start_time, 4)
                    if md5_hash:
                        # for insert
                        batch_insert.append((machine_name, full_path, mime_type, md5_hash, file_size, duration))
                        # for update
                        batch_update.append((md5_hash, file_size, mime_type, duration, full_path, md5_hash, file_size))
                        if len(batch_insert) >= BATCH_SIZE:
                            mark_old_versions(batch_update)
                            insert_records(batch_insert)
                            total_inserted += len(batch_insert)
                            batch_insert.clear()
                            batch_update.clear()
            except Exception:
                continue

# === 写入剩余数据 ===
if batch_insert:
    mark_old_versions(batch_update)
    insert_records(batch_insert)
    total_inserted += len(batch_insert)

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
