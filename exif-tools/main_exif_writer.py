import os
from pathlib import Path
import json
import subprocess
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

from global_config.logger_config import logger

# lib to read meta data from files
from pymediainfo import MediaInfo
import exifread
from mutagen import File as MutagenFile
from tinytag import TinyTag

# ================= Configuration Area =================
from global_config.config import yaml_config_boxed

CONFIG_FILE = os.path.expanduser("~/exif_extractor_config.json")
logger.name = os.path.basename(__file__)

# ================ Utility Functions ================
import re
from psycopg2.extras import Json

# Remove both actual NUL characters and escaped \u0000 in text
_CTRL_NUL_RE = re.compile(r'\x00')
_ESCAPED_NUL_RE = re.compile(r'\\u0000')

def _strip_nuls_from_str(s: str) -> str:
    s = _CTRL_NUL_RE.sub('', s)
    s = _ESCAPED_NUL_RE.sub('', s)
    return s

def _deep_strip_nuls(obj):
    """Recursively remove NUL characters from dicts, lists, and strings"""
    if isinstance(obj, dict):
        return {_deep_strip_nuls(k): _deep_strip_nuls(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_strip_nuls(x) for x in obj]
    if isinstance(obj, str):
        return _strip_nuls_from_str(s=obj)
    return obj

def prepare_metadata_for_db(metadata_raw):
    """
    Input can be a dict or JSON string; output is psycopg2.extras.Json(dict)
    and all NUL characters are recursively removed.
    """
    if isinstance(metadata_raw, str):
        # First remove NULs, then try to deserialize
        cleaned = _strip_nuls_from_str(metadata_raw)
        try:
            data = json.loads(cleaned)
        except Exception:
            data = {"raw": cleaned}
    elif isinstance(metadata_raw, dict):
        data = metadata_raw
    else:
        data = {"raw": metadata_raw}

    data = _deep_strip_nuls(data)
    return Json(data)


def image_metadata(fp):
    with open(fp, 'rb') as f:
        tags = exifread.process_file(f)
    return {k: str(v) for k, v in tags.items()}


def video_audio_metadata(fp):
    metadata = {}

    # -------- Extract using pymediainfo --------
    try:
        info = MediaInfo.parse(fp)
        mediainfo_data = {}
        for track in info.tracks:
            t_type = track.track_type or "Unknown"
            t_data = track.to_data()
            if t_type not in mediainfo_data:
                mediainfo_data[t_type] = []
            mediainfo_data[t_type].append(t_data)
        metadata["mediainfo"] = mediainfo_data
    except Exception as e:
        metadata["mediainfo_error"] = str(e)

    # The following commented block was for hachoir extraction
    # but it caused "InputPipe object has no attribute 'close'" errors
    #
    # # -------- Extract using hachoir (manual method) --------
    # try:
    #     parser = createParser(fp)
    #     if not parser:
    #         metadata["hachoir_error"] = "Could not parse file"
    #     else:
    #         extractor = MetadataExtractor(parser)
    #         if extractor.hasMetadata():
    #             extractor.extractMetadata()
    #             hachoir_data = {}
    #             for item in extractor.getMetadata().exportPlaintext():
    #                 if ": " in item:
    #                     key, value = item.strip("- ").split(": ", 1)
    #                     hachoir_data[key.strip()] = value.strip()
    #             metadata["hachoir"] = hachoir_data
    #         else:
    #             metadata["hachoir_error"] = "No metadata found"
    # except Exception as e:
    #     metadata["hachoir_error"] = str(e)

    logger.info(f'metadata: {metadata}')
    # ---------------- Merge & Simplify (example) ----------------
    # You can further clean the results: e.g., extract only duration, width, height, codec_name, etc.
    errors = []
    for key in ["hachoir_error", "mediainfo_error"]:
        if key in metadata:
            errors.append(f'{key}:{metadata[key]}')
    if errors:
        metadata['error'] = ';'.join(errors)
    return metadata


def audio_id3_metadata(fp, EXTRACT_APIC=False):
    if EXTRACT_APIC:
        '''
        Error occurs when mutagen.File() tries to parse an .mp3 file over SMB path and fails with:

        mutagen.id3._util.error: [Errno 22] Invalid argument

        Root causes:
        - SMB/GVFS paths cannot be read normally by mutagen
        - Paths like /run/user/1000/gvfs/smb-share:server=some_machine.local,... are virtual mount points,
          mutagen may fail when trying to open them as normal file objects.
        - The file is not opened as a standard file object or is in an unexpected format.

        Solution: Read into BytesIO before passing to mutagen.
        '''
        import io
        try:
            with open(fp, 'rb') as f:
                data = f.read()
            meta = MutagenFile(io.BytesIO(data))
            return {k: str(v) for k, v in meta.items()} if meta else {}
        except Exception as e:
            return {'error': str(e)}
    else:
        tag = TinyTag.get(fp)
        return {key: getattr(tag, key)
                for key in dir(tag)
                if key not in ['audio_offset', 'extra']
                and not key.startswith('_') and not callable(getattr(tag, key))
                }

def db_connect():
    return psycopg2.connect(yaml_config_boxed.transcribe.db_conn)

def execute_sql(sql, params=None, fetch=False, commit=False, dry_run=False, debug_mode=False):
    """Execute SQL, supports dry_run mode"""
    if dry_run:
        logger.info("[DRY-RUN SQL]", sql, params)
        return []
    if debug_mode:
        logger.info(f"debug info: sql={sql}, params={params}")
    with db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if commit:
                conn.commit()
            if fetch:
                return cur.fetchall()
    return None

def clean_json_str(raw):
    """Clean JSON string from stdout, remove \\u0000"""
    try:
        obj = json.loads(raw)
        clean = json.dumps(obj)
        clean = clean.replace("\u0000", "").replace("\\u0000", "")
        return clean
    except Exception:
        return raw.replace("\u0000", "").replace("\\u0000", "")

def deep_equal(a, b):
    """Recursively compare two JSON objects for equality"""
    if a == b:
        return True
    if type(a) != type(b):
        return False
    if isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            return False
        return all(deep_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        return all(deep_equal(x, y) for x, y in zip(a, b))
    return False

# ================ Core Process Functions ================

def log_scan_operation(config, dry_run=False, debug_mode=False):
    """Log one scan operation"""
    sql = """
        INSERT INTO scan_operation(machine, operation_type, tool_language, libraries, file_count)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING scan_id;
    """
    params = (
        config.get("machine", os.uname().nodename),
        "scan_exif",
        config.get("language_tool", "python"),
        config.get("libraries", "exiftool"),
        0
    )
    result = execute_sql(sql, params, fetch=True, commit=True, dry_run=dry_run, debug_mode=debug_mode)
    return result[0]["scan_id"] if result else "DRY-RUN"

def fetch_files(limit=100, dry_run=False, run_mode=None, debug_mode=False):
    """Fetch non-deleted audio/video/image files from file_inventory"""
    if run_mode == 'fix':
        sql = """
            select fi.* from file_inventory fi
            left outer join file_metadata fm on fi.id = fm.file_id
            where fi.deleted = 0 and fm.status ='failed' and fm.id is not null
                 AND (fi.mime_type LIKE 'video%%' OR fi.mime_type LIKE 'audio%%' OR fi.mime_type LIKE 'image%%')
             order by fi.id
            limit %s
        """
    else:
        sql = """
            SELECT * FROM file_inventory
            WHERE deleted = 0 AND (mime_type LIKE 'video%%' OR mime_type LIKE 'audio%%' OR mime_type LIKE 'image%%')
            LIMIT %s
        """
    return execute_sql(sql, (limit,), fetch=True, dry_run=dry_run, debug_mode=debug_mode)

def replace_path(file_path, old_prefix, new_prefix):
    """Replace path prefix"""
    if old_prefix.startswith("/"):
        old_prefix = old_prefix[1:]
    if old_prefix.endswith("/"):
        old_prefix = old_prefix[:-1]
    return file_path.replace(old_prefix, new_prefix, 1)

def safe_dict(obj):
    """Return a dict with only serializable primitive types"""
    return {
        k: str(v) for k, v in obj.items()
        if isinstance(v, (str, int, float, bool, type(None)))
    }

def wrap_filepath(ret_json, file_path: str):
    """Attach file_path to JSON dict"""
    ret_json['file_path'] = file_path
    return json.dumps(ret_json)

def run_exif(file_path, mime_type, debug_mode=None):
    clean_stdout = None
    try:
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if debug_mode:
            logger.info(f"debug: path={path}, ext={ext}, mime_type={mime_type}")

        not_match_by_mime_type = False
        return_json = None
        if mime_type:
            if mime_type.startswith('image/'):
                not_match_by_mime_type = True
                return_json = image_metadata(path)
            elif mime_type.startswith('video/'):
                not_match_by_mime_type = True
                return_json = video_audio_metadata(path)
            elif mime_type.startswith('audio/'):
                not_match_by_mime_type = True
                return_json = audio_id3_metadata(path)

        if not_match_by_mime_type:
            if ext in ['.jpg', '.jpeg', '.png', '.heic', '.webm', '.svg']:
                return_json = image_metadata(path)
            elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
                return_json = video_audio_metadata(path)
            elif ext in ['.mp3', '.flac', '.wav']:
                return_json = audio_id3_metadata(path, True)
            else:
                return_json = {'error': 'Unsupported file type'}

        status = "successful"
        error_message = None
        
        # Merge file_path and ensure all values are serializable
        meta_obj = safe_dict(return_json)
        meta_obj["file_path"] = str(path)

        # Recursively remove NULs to avoid \u0000 in JSON
        meta_obj = _deep_strip_nuls(meta_obj)

        clean_stdout = meta_obj   # dict, not string

        logger.info(f'clean_stdout: {clean_stdout}')
        
        if return_json and "error" in return_json and return_json["error"]:
            status = 'failed'
            error_message = return_json["error"]
    except Exception as e:
        status = "failed"
        error_message = str(e)
        logger.warning(f'some errors happened, path={path}', e)
        
    return file_path, status, error_message, clean_stdout

def query_file_metadata(file_id, dry_run=False):
    """Query file_metadata table for existing version info"""
    sql = """
        SELECT 
            EXISTS (SELECT 1 FROM file_metadata m WHERE m.file_id = %s) AS exists_flag,
            (SELECT id FROM file_metadata m WHERE m.file_id = %s ORDER BY version DESC LIMIT 1) AS existing_id,
            (SELECT max(version) FROM file_metadata m WHERE m.file_id = %s) AS existing_version,
            (SELECT metadata FROM file_metadata m WHERE m.file_id = %s ORDER BY version DESC LIMIT 1) AS existing_metadata
    """
    result = execute_sql(sql, (file_id, file_id, file_id, file_id), fetch=True, dry_run=dry_run)
    return result[0] if result else None

def save_metadata(file_id, scan_id, metadata, status, error_message, existing=None, dry_run=False, debug_mode=False):
    """Insert or update file_metadata and record in history"""
    now = datetime.now()
    
    # Data to insert: Json(dict) with NULs removed
    meta_for_db = prepare_metadata_for_db(metadata)
    
    if existing and existing["exists_flag"]:
        if debug_mode:
            logger.info('existing ... ')
        # Compare metadata
        old_meta = existing["existing_metadata"]
        
        # Remove NULs from old metadata
        try:
            old_json = old_meta if isinstance(old_meta, dict) else json.loads(old_meta)
        except Exception:
            old_json = None
        old_json = _deep_strip_nuls(old_json) if isinstance(old_json, (dict, list)) else old_json

        # Clean new metadata before comparison
        if isinstance(metadata, dict):
            new_json = _deep_strip_nuls(metadata)
        else:
            try:
                new_json = json.loads(_strip_nuls_from_str(metadata))
            except Exception:
                new_json = None
            if isinstance(new_json, (dict, list)):
                new_json = _deep_strip_nuls(new_json)
            
        if debug_mode:
            logger.info(f'old_json: {old_json}, new_json: {new_json}')
        
        if deep_equal(old_json, new_json):
            # No change → only record in history
            version = existing["existing_version"]
        else:
            # Update file_metadata
            version = (existing["existing_version"] or 0) + 1
            sql = """
                UPDATE file_metadata
                SET version=%s, scan_id=%s, metadata=%s, status=%s, error_message=%s, scanned_at=%s
                WHERE id=%s
            """
            execute_sql(sql, (version, scan_id, Json(metadata), status, error_message, now, existing["existing_id"]), commit=True, dry_run=dry_run, debug_mode=debug_mode)
    else:
        if debug_mode:
            logger.info('new ... ')
        # New file → insert record
        version = 1
        sql = """
            INSERT INTO file_metadata(file_id, version, scan_id, metadata, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        execute_sql(sql, (file_id, version, scan_id, Json(metadata), status, error_message), commit=True, dry_run=dry_run)

    # Insert into history table
    sql_history = """
        INSERT INTO file_metadata_history(file_id, version, scan_id, metadata, status, error_message, scanned_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    execute_sql(sql_history, (file_id, version, scan_id, Json(metadata), status, error_message, now), commit=True, dry_run=dry_run)

def delete_file_rows_not_existed(file_id, orig_path, dry_run=False):
    logger.info(f'delete file rows, file_id:{file_id}, orig_path:{orig_path}')
    execute_sql("""update file_inventory set deleted=1, scanned_at = CURRENT_TIMESTAMP where id = %s
                """, (file_id, ), commit=True, dry_run=dry_run)

# ================ Main Execution Logic ================

def main(limit=100, dry_run=False, workers=1, run_mode=None, debug_mode=None):
    # 1. Read config file
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    # scan_id = log_scan_operation(config, dry_run=dry_run)
    scan_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Started scan operation: {scan_id}")

    # 2. Fetch file list
    files = fetch_files(limit=limit, dry_run=dry_run, run_mode=run_mode, debug_mode=debug_mode)
    logger.info(f"Fetched {len(files)} files")

    # 3. Replace path prefix
    old_prefix = config.get("path_replacement", {}).get("old_path", "")
    new_prefix = config.get("path_replacement", {}).get("new_path", "")
    file_tasks = [(file["id"], replace_path(file["path"], old_prefix, new_prefix), file["path"], file["mime_type"]) for file in files]

    # 4. Run EXIF extraction
    # 5. Save to database
    for task in file_tasks:
        file_id, real_path, orig_path, mime_type = task
        existed = os.path.exists(real_path)
        logger.info(f'path: {real_path}, existed: {existed}')
        if not existed:
            delete_file_rows_not_existed(file_id, orig_path)
            continue
        
        file_path, status, error_message, clean_stdout = run_exif(real_path, mime_type, debug_mode=debug_mode)

        logger.info(f"[{file_path}] status={status}, error={error_message}")
        existing = query_file_metadata(file_id, dry_run=dry_run)
        if debug_mode:
            logger.info(f'debug info: {file_id}, {scan_id}, {clean_stdout}, {status}, {error_message}, {existing}')
        save_metadata(file_id, scan_id, clean_stdout or "{}", status, error_message, existing, dry_run=dry_run, debug_mode=debug_mode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="File EXIF Scanner with PostgreSQL and Multi-processing")
    parser.add_argument("--limit", type=int, default=100, help="Max number of files to process")
    parser.add_argument("--dry-run", action="store_true", help="Print SQL without executing")
    parser.add_argument("--workers", type=int, default=max(1, multiprocessing.cpu_count() // 2), help="Number of parallel workers for EXIF extraction")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--run-mode", choices=['normal', 'fix'], default='normal', help="Run mode: normal or fix")
    args = parser.parse_args()
    
    main(limit=args.limit, dry_run=args.dry_run, workers=args.workers, run_mode=args.run_mode, debug_mode=args.debug)
