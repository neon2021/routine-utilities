import sys
import os
import socket
import psycopg2
import yaml
import time
from psycopg2.extras import execute_batch, execute_values
from datetime import datetime
import argparse

from global_config.logger_config import logger
from file_scanner.device_utils import list_mounted_devices
from file_scanner.mount_path_utils import MountPathUtil
from file_scanner.device_utils import calculate_md5, get_mime_type

logger.name = os.path.basename(__file__)

# === read parameters from yaml configuration file ===
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
logger.info("✅ Loaded config:")
logger.info(config)

parser = argparse.ArgumentParser(description="File Scanner")
parser.add_argument("root_dirs", metavar='FILE', nargs='+', help='scanning dirs')
parser.add_argument("--run_mode", choices=['scan', 'list_disks', 'list_mount_path'], default='scan', help='show all external disks or scan files in particular dirs')
args = parser.parse_args()

logger.info("✅ Loaded args:")
logger.info(args)

mountPathUtil = MountPathUtil.from_system()
mount_points = mountPathUtil.mount_points

if args.run_mode == 'list_disks':
    for m in mount_points:
        logger.info(f'mounted: {m}')
    sys.exit(0)
elif args.run_mode == 'list_mount_path':
    mount_path_str = ' '.join([m.mount_path for m in mount_points])
    logger.info(f'all mount paths: {mount_path_str}')
    sys.exit(0)
else:
    root_dirs = args.root_dirs

    ROOT_DIRS = [os.path.expanduser(p) for p in root_dirs] if root_dirs else [os.path.expanduser(p) for p in config.get('scan_dirs', ['/tmp'])]
    DB_CONFIG = config.get('db', {})
    TABLE_NAME = config.get('table_name', 'file_inventory')
    BATCH_SIZE = config.get('batch_size', 100)
    FORCE_UPDATE = config.get('force_update', False)

    # === 获取本机主机名 ===
    machine_name = socket.gethostname()


    UPSERT_SQL = """
    INSERT INTO mount_info (uuid, mount_path, device, filesystem_type, label, is_external, partition_uuid, mounted_at)
    VALUES %s
    ON CONFLICT (uuid, mount_path, device, filesystem_type,partition_uuid)
    DO UPDATE SET
    mounted_at = CURRENT_TIMESTAMP,
    label = COALESCE(EXCLUDED.label, mount_info.label),
    is_external = COALESCE(EXCLUDED.is_external, mount_info.is_external);
    """

    def insert_disk_mount_info():
        mountInfoList= [(mountInfo.uuid, # 1
                        mountInfo.mount_path,
                        mountInfo.device,
                        mountInfo.fs_type,
                        mountInfo.label, # 5
                        mountInfo.is_external, #6
                        mountInfo.partition_uuid, #7
                        ) for mountInfo in mount_points]
        logger.info(f'mountInfoList: {mountInfoList}')
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            with conn, conn.cursor() as cur:
                execute_values(cur, sql=UPSERT_SQL,argslist=mountInfoList,template="(%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)")
        except Exception as e:
            logger.info(f"❌ failed to write disk mount info: {str(e)}")

    insert_disk_mount_info()



    insert_sql = f"""
    INSERT INTO {TABLE_NAME} (machine, path, mime_type, md5, size, scanned_at, gmt_create, scan_duration_secs, deleted, mount_uuid, relative_path)
    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, 0, %s, %s);
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
                    cur.execute(f"SELECT md5, size, id FROM {TABLE_NAME} WHERE path = %s AND deleted = 0;", (path,))
                    row = cur.fetchone()
            conn.close()
            return row
        except Exception as e:
            logger.info(f"❌ 查询旧记录失败: {str(e)}")
            return None

    def mark_old_record(path):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            with conn:
                with conn.cursor() as cur:
                    cur.execute(mark_old_sql, (path,))
            conn.close()
        except Exception as e:
            logger.info(f"❌ 标记旧记录失败: {str(e)}")

    insert_batch = []
    total_inserted = 0
    MIN_FILE_COUNT=10

    scanning_count = 0
    for root_dir in ROOT_DIRS:
        logger.info(f"> 正在扫描目录: {root_dir}")
        for root, _, files in os.walk(root_dir):
            files_count = len(files)
            if files_count>MIN_FILE_COUNT:
                logger.info(f"> 正在扫描目录: {root_dir} 中的(文件数量大于{MIN_FILE_COUNT})子目录: {root}, 其中文件数量: {files_count}")
            for name in files:
                scanning_count += 1
                if scanning_count % 1000 == 0:
                    logger.info(f"> 累计扫描文件数量: {scanning_count}")
                    
                full_path = os.path.join(root, name)
                mount_conversion = mountPathUtil.real_path_2_logical(full_path)
                disk_uuid, relative_path = None, None
                if mount_conversion:
                    disk_uuid, relative_path = mount_conversion
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
                            insert_batch.append((machine_name, full_path, mime_type, md5_hash, file_size, duration, disk_uuid, relative_path))
                        else:
                            old_record = get_existing_record(full_path)
                            if old_record is None:
                                insert_batch.append((machine_name, full_path, mime_type, md5_hash, file_size, duration, disk_uuid, relative_path))
                            else:
                                old_md5, old_size, old_id = old_record
                                if md5_hash != old_md5 or file_size != old_size:
                                    mark_old_record(full_path)
                                    insert_batch.append((machine_name, full_path, mime_type, md5_hash, file_size, duration, disk_uuid, relative_path))

                        if len(insert_batch) >= BATCH_SIZE:
                            insert_records = insert_batch[:]
                            insert_batch.clear()
                            try:
                                conn = psycopg2.connect(**DB_CONFIG)
                                with conn, conn.cursor() as cur:
                                    execute_batch(cur, insert_sql, insert_records)
                                total_inserted += len(insert_records)
                                logger.info(f"> 累计写入文件数量: {total_inserted}")
                            except Exception as e:
                                logger.info(f"❌ 批量写入失败: {str(e)}")
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
            logger.info(f"❌ 批量写入失败: {str(e)}")

    logger.info(f"✅ 总共插入 {total_inserted} 条记录。")
