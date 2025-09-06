#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translate n8n workflow to Python:
- manualTrigger → main()
- postgres "query audio and video files" → sql_query_candidates
- splitInBatches/Loop Over Items → for item in rows
- postgres "filter out deleted files" → sql_filter_deleted
- IF (id notEmpty) OR (tl_id empty) OR (tl_status == 'error') → condition
- Execute Command (onError: continue) → subprocess call with try/except then continue
"""

import os
import sys
import argparse
import subprocess
from typing import Optional

import psycopg2
import psycopg2.extras

from global_config.logger_config import logger,get_logger

cur_logger = get_logger("transcribe_from_n8n")
perf_logger = get_logger("perf.transcribe_from_n8n")

SQL_QUERY_CANDIDATES = r"""
select 
  f.*
from file_inventory f
left outer join (
    select tl.status, tl.path, tl.id, tl.file_id, tl.ended_at, tl.file_md5
    from transcription_log tl
    where not exists (
        select t.id from transcription_log t
        where t.path = tl.path and t.id > tl.id
    )
) t on f.md5 = t.file_md5
where (f.mime_type ilike 'video/%%' or f.mime_type ilike 'audio/%%')
  and f.deleted = 0
  and (t.status != 'success' or t.id is null)
  and f.id between %(id_min)s and %(id_max)s
order by f.size desc, t.ended_at nulls last, f.id desc;
"""

SQL_FILTER_DELETED = r"""
select
  fi.id,
  fi.path,
  fi.md5,
  fi.mount_uuid,
  fi.relative_path,
  tl.id   as tl_id,
  tl.status as tl_status,
  tl.file_md5 as tl_md5
from file_inventory fi
left outer join transcription_log tl
  on fi.md5 = tl.file_md5
where fi.deleted = 0
  and fi.id in (%(file_id)s);
"""


def getenv_or(arg: Optional[str], env_key: str, default: Optional[str] = None) -> Optional[str]:
    if arg:
        return arg
    val = os.getenv(env_key, default)
    return val


def get_conn(dsn: Optional[str], host: Optional[str]=None, port: Optional[int]=None,
             db: str=None, user: str=None, password: Optional[str]=None):
    if dsn:
        return psycopg2.connect(dsn)
    return psycopg2.connect(
        host=host, port=port, dbname=db, user=user, password=password
    )


def handle_result(fut, ctx):
    try:
        res = fut.result()
        cur_logger.info("[id=%s] done: %s", ctx["file_id"], res)
    except Exception as e:
        cur_logger.exception("[id=%s] failed: %r", ctx["file_id"], e)

from global_config.config import yaml_config_boxed
import traceback

max_parallel_workers = yaml_config_boxed.transcribe.max_parallel_workers
def transcribe_files(filtered_rows):
    from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED, as_completed
    from concurrent.futures.process import BrokenProcessPool
    
    import multiprocessing as mp
    import time
    
    processed = 0
    MAX_WORKERS = max_parallel_workers # 3 workers causes OOM in CUDA at 2025-08-25 00:30:38
    # MAX_WORKERS = 3 # 2025-08-25 00:30:38 | INFO | faster_transcribe.py:17 | error_message: CUDA failed with error out of memory
    # 使用 spawn，避免 fork + CUDA
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass
    ctx = mp.get_context("spawn")

    try:
        with ProcessPoolExecutor(max_workers=MAX_WORKERS, mp_context=ctx) as pool:
            pending = set()
            ctx_map = {}
            perf_logger.info("start to transcribe audio stream for files")
            for r in filtered_rows:
                file_id = r["id"]
                path = r["path"]
                md5 = r["md5"]
                cur_logger.info("[id=%s] Processing file: %s", file_id, path)

                submit_path = path
                is_tmp_wav = False
                # # —— 串行转换：MKV 先转 WAV，再交给子进程只做转录 ——
                # if path.lower().endswith(".mkv"):
                #     wait_for_free_ram(min_free_gb=2.0)  # 转换前守内存
                #     submit_path = to_wav16k_mono(path)
                #     is_tmp_wav = True
                #     logger.info("[id=%s] mkv→wav done: %s", file_id, submit_path)

                from transcribe_insert import main_func
                cur_logger.info("[id=%s] Submitting to pool: %s", file_id, submit_path)
                fut = pool.submit(main_func, file_id, submit_path, md5)
                pending.add(fut)
                ctx_map[fut] = {"file_id": file_id, "path": submit_path, "is_tmp_wav": is_tmp_wav}
                processed += 1

                # 达并发上限就消费一个完成的
                if len(pending) >= MAX_WORKERS:
                    done, pending = wait(pending, return_when=FIRST_COMPLETED)
                    for f in done:
                        try:
                            res = f.result()
                            cur_logger.info("[id=%s] done: %s", ctx_map[f]["file_id"], res)
                        except BrokenProcessPool as e:
                            # 池已破碎：取消剩余任务并显式关闭
                            cur_logger.error("ProcessPool broken while getting result: %r", e)
                            for pf in list(pending):
                                pf.cancel()
                            pending.clear()
                            # 让 with 块退出后 __exit__ 正常触发 shutdown
                            raise
                        except Exception as e:
                            # 记录详细错误信息
                            logger.error(f"[id={file_id}] failed: {e}")
                            logger.debug(f"[id={file_id}] Full traceback:\n{traceback.format_exc()}")
                            # old code
                            logger.exception("[id=%s] failed: %r", ctx_map[f]["file_id"], e)
                        finally:
                            # 清理临时 WAV
                            if ctx_map[f]["is_tmp_wav"]:
                                try:
                                    os.remove(ctx_map[f]["path"])
                                except Exception:
                                    pass
                            ctx_map.pop(f, None)
                    time.sleep(0.3)  # 轻微错峰
            perf_logger.info("finish to transcribe audio stream for files")

            # 收尾：把剩余的都处理掉
            for f in as_completed(pending):
                try:
                    res = f.result()
                    cur_logger.info("[id=%s] done: %s", ctx_map[f]["file_id"], res)
                except BrokenProcessPool as e:
                    cur_logger.error("ProcessPool broken in tail consume: %r", e)
                    for pf in list(pending):
                        pf.cancel()
                    pending.clear()
                    raise
                except Exception as e:
                    cur_logger.exception("[id=%s] failed: %r", ctx_map[f]["file_id"], e)
                finally:
                    if ctx_map[f]["is_tmp_wav"]:
                        try:
                            os.remove(ctx_map[f]["path"])
                        except Exception:
                            pass
                    ctx_map.pop(f, None)
    except BrokenProcessPool:
        # 到这里时 with 已经离开；再做一层保险清理
        for f in list(pending):
            f.cancel()
        pending.clear()
        ctx_map.clear()
        # 可视需要这里选择：重建池重试 / 直接返回 / 抛出
        logger.error("Process pool broken; cancelled pending and cleaned up.")
    finally:
        logger.info("Done. processed=%d", processed)

def main():
    parser = argparse.ArgumentParser(description="Run media transcribe loop translated from n8n.")
    # id 范围与批处理
    parser.add_argument("--id-min", type=int, default=0, help="Lower bound (inclusive) for file_inventory.id (BETWEEN).")
    parser.add_argument("--id-max", type=int, default=100000000, help="Upper bound (inclusive) for file_inventory.id (BETWEEN).")
    parser.add_argument("--limit", type=int, default=None, help="Optional hard cap on number of candidates processed.")

    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase log verbosity.")
    args = parser.parse_args()

    # DB 连接参数
    DB_CONN = yaml_config_boxed.transcribe.db_conn

    conn = get_conn(DB_CONN)
    conn.autocommit = False
    
    # path converter
    from file_scanner.mount_path_utils import MountPathUtil
    mountPathUtil = MountPathUtil.from_system()

    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # === node: query audio and video files ===
            cur_logger.info("Querying candidate media files in id range [%s, %s] ...", args.id_min, args.id_max)
            cur.execute(SQL_QUERY_CANDIDATES, {"id_min": args.id_min, "id_max": args.id_max})
            rows = cur.fetchall()
            rows_count = len(rows)
            cur_logger.info("Fetched %d candidate rows.", rows_count)


            idx = 0
            filtered_rows = []
            count_sum = {}
            perf_logger.info("Start filtering rows ... rows_count: %s", rows_count)
            for r in rows:
                idx += 1
                if idx % 200 == 0:
                    perf_logger.info("filtered rows_count: %s/%s (%.2f%%)", idx, rows_count, (idx/rows_count)*100)
                    
                    # 2025-09-04 11:18:28 | INFO | media_detector.py:175 | filtered_rows length: 152, count_sum for skipping files: {'no_audio': 125, 'non_existing': 248}
                    perf_logger.info("-" * 120)
                    perf_logger.info("filtered_rows length: %s, count_sum for skipping files: %s", len(filtered_rows), count_sum)
                    perf_logger.info("-" * 120)
                    
                    transcribe_files(filtered_rows)
                    
                    filtered_rows.clear()

                file_id = r["id"]
                if args.limit and idx >= args.limit:
                    break
                
                # === node: filter out deleted files ===
                cur.execute(SQL_FILTER_DELETED, {"file_id": file_id})
                filtered = cur.fetchall()
                if not filtered:
                    cur_logger.info("[id=%s] no rows after filter; continue.", file_id)
                    continue

                row = filtered[0]
                # logger.info("[id=%s] row after filter: %s", file_id, row)
                
                tl_id = row.get("tl_id")
                tl_status = row.get("tl_status")
                path = row.get("path")
                md5 = row.get("md5")
                mount_uuid = row.get("mount_uuid")
                relative_path = row.get("relative_path")
                cur_logger.info("[id=%s] tl_id: %s, tl_status: %s, path: %s, md5: %s, mount_uuid: %s, relative_path: %s", file_id, tl_id, tl_status, path, md5, mount_uuid, relative_path)

                cond = (file_id is not None) and ((tl_id is None) or (tl_status == "error"))
                if not cond:
                    cur_logger.debug("[id=%s] IF condition false; skip.", file_id)
                    continue
                if not path:
                    cur_logger.debug("[id=%s] Empty path; skip.", file_id)
                    continue
                
                if mount_uuid and relative_path:
                    abs_path_from_uuid_and_rel_path = mountPathUtil.logical_path_2_real(mount_uuid, relative_path)
                    if abs_path_from_uuid_and_rel_path and os.path.exists(abs_path_from_uuid_and_rel_path):
                        cur_logger.info("[id=%s] path[%s] updated to %s", file_id, path, abs_path_from_uuid_and_rel_path)
                        path = abs_path_from_uuid_and_rel_path
                        row["path"] = path
                        r["path"] = path
                    
                if not os.path.exists(path) or not os.path.isfile(path):
                    # 文件不存在，跳过
                    cur_logger.info("[id=%s][path=%s] Non-existing or irregular file detected; skip.", file_id, path)
                    count_sum["non_existing"] = count_sum.get("non_existing", 0) + 1
                    continue

                from media_detector import is_video_has_audio
                if not is_video_has_audio(path):
                    # 无音频流，跳过
                    cur_logger.info("[id=%s][path=%s] No audio stream detected; skip.", file_id, path)
                    count_sum["no_audio"] = count_sum.get("no_audio", 0) + 1
                    continue
                
                filtered_rows.append(r)
                
                # sys.exit(0)


    finally:
        conn.close()

import subprocess, tempfile
from pathlib import Path

def wait_for_free_ram(min_free_gb=3.0, interval=0.5):
    try:
        import psutil
    except ImportError:
        return
    need = int(min_free_gb * (1024**3))
    import time
    while psutil.virtual_memory().available < need:
        time.sleep(interval)

def to_wav16k_mono(src_path: str) -> str:
    dst = Path(tempfile.gettempdir()) / (Path(src_path).stem + ".16k.mono.wav")
    cmd = [
        "ffmpeg", "-hide_banner", "-nostdin", "-y",
        "-i", src_path,
        "-vn", "-sn", "-dn",
        "-map", "a:0",
        "-ac", "1", "-ar", "16000",
        "-acodec", "pcm_s16le",
        "-threads", "1",          # 限制 ffmpeg 内部并行，降低内存峰值
        str(dst),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return str(dst)

import time
def fake_main_func(path:str):
    sleep_seconds = 10
    print(f"开始阻塞...{path}")
    time.sleep(sleep_seconds)   # 阻塞当前线程 {sleep_seconds} 秒
    print(f"{sleep_seconds} 秒结束，继续执行...{path}")

if __name__ == "__main__":
    main()
