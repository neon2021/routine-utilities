import sys
import os
import psycopg2
import datetime
from faster_transcribe import WhisperTranscriber
from langdetect import detect
from sentence_transformers import SentenceTransformer
from uuid import uuid4
import subprocess
import argparse
from types import SimpleNamespace

from global_config.logger_config import get_logger

cur_logger = get_logger(os.path.basename(__file__))

def log_transcription(conn, cur, file_id, file_md5, path, status, start_time, ollama_model, embedding_model_name,model_in_out,version, error_message=None):
    if status != 'success':
        cur_logger.info(f'error_message: {error_message}')

    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()
    cur.execute("""
        INSERT INTO transcription_log (
            file_id, file_md5, path, status, started_at, ended_at,
            duration_secs, error_message, model_used, embedding_model,model_in_out, version
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        file_id, file_md5, path, status, start_time, end_time,
        duration, error_message[:1000] if error_message else None,
        ollama_model, embedding_model_name, str(model_in_out), version
    ))
    conn.commit()


def get_transcription_log(cur, file_path):
    '''
    file_id, path, status FROM transcription_log
    '''
    try:
        cur.execute(f"SELECT file_id, path, status, started_at FROM transcription_log WHERE path = %s order by id desc;", (file_path,))
        row = cur.fetchone()
        cur_logger.info(f'row: {row}')
        return row
    except Exception as e:
        cur_logger.info(f"❌ 查询 transcription_log 记录失败: {str(e)}")
        return None

def old_logic(conn, cur, segments, ollamaModel, info, embedding_model,version):
    merged = []
    buffer, last_end = [], None
    
    seg_idx = 0
    for seg in segments:
        seg_idx += 1
        cur_logger.info(f'deal with seg_idx: {seg_idx}')
        start, end, text = seg.start, seg.end, seg.text.strip()
        if not text:
            continue
        if last_end and (start - last_end) > 1.5:
            merged.append(buffer)
            buffer = []
        buffer.append((start, end, text))
        last_end = end
    if buffer:
        merged.append(buffer)

    cur_logger.info(f'merged length: {len(merged)}')

    err_msg=[]
    # Step 2: 处理合并段落
    for group in merged:
        start = group[0][0]
        end = group[-1][1]
        full_text = " ".join([t[2] for t in group])
        lang = detect(full_text) if info is None or info.language is None else info.language

        # Step 3: 调用 Ollama 模型
        def run_ollama(prompt):
            start_time = datetime.datetime.now()
            cur_logger.info(f'begin to run_ollama with {prompt}')
            try:
                result = subprocess.run(
                    ["ollama", "run", ollamaModel],
                    input=prompt.encode("utf-8"),
                    stdout=subprocess.PIPE,
                    timeout=60
                )
                if result.stderr:
                    stderr_msg = result.stderr.decode()
                    if len(stderr_msg) > 0:
                        return {"err":stderr_msg,"errType":"stderr"}
                decoded_output = result.stdout.decode('utf-8', errors='replace')
                cur_logger.info(f'end to run_ollama with {prompt}\n\nresult: {decoded_output}')
                return {"out":decoded_output}
            except Exception as e:
                cur_logger.info(f'failed to run_ollama with {prompt}')
                return {"err":str(e),"errType":"exception"}
            finally:
                end_time = datetime.datetime.now()
                duration = (end_time - start_time).total_seconds()
                cur_logger.info(f'耗时: {duration:.2f} 秒')

        translated = ""
        summary_zh = ""
        
        if lang == 'zh':
            summary_zh_res = run_ollama(f"概括以下中文文本内容，不要做任何解释:\n\n{full_text}")
            if 'err' in summary_zh_res:
                summary_zh = None
                summary_zh_res['field']='summary_zh'
                err_msg.append(summary_zh_res)
            else:
                summary_zh = summary_zh_res['out']
            emotion_res = run_ollama(f"下面句子的整体情绪是什么?用一个词语描述，不要做任何解释:\n\n{full_text}")
            if 'err' in emotion_res:
                emotion = None
                emotion_res['field']='emotion'
                err_msg.append(emotion_res)
            else:
                emotion = emotion_res['out']
            topic_res = run_ollama(f"下面中文内容的主题?用一句简短的语句描述，不要做任何解释:\n\n{full_text}")
            if 'err' in topic_res:
                topic = None
                topic_res['field']='topic'
                err_msg.append(topic_res)
            else:
                topic = topic_res['out']
        else:
            summary_en_res = run_ollama(f"Summarize the following English text:\n\n{full_text}")
            if 'err' in summary_en_res:
                summary_en = None
                summary_en_res['field']='summary_en'
                err_msg.append(summary_en_res)
            else:
                summary_en = summary_en_res['out']
            emotion_res = run_ollama(f"What is the overall emotion in this sentence? Just return one word without any explanation:\n\n{full_text}")
            if 'err' in emotion_res:
                emotion = None
                emotion_res['field']='emotion'
                err_msg.append(emotion_res)
            else:
                emotion = emotion_res['out']
            topic_res = run_ollama(f"what is the topic for the following english text? Just return one brief sentence without any explanation:\n\n{full_text}")
            if 'err' in topic_res:
                topic = None
                topic_res['field']='topic'
                err_msg.append(topic_res)
            else:
                topic = topic_res['out']

            translated_res = run_ollama(f"Translate the following into fluent Chinese without any explanation:\n\n{full_text}")
            if 'err' in translated_res:
                translated = None
                translated_res['field']='translated'
                err_msg.append(translated_res)
            else:
                translated = translated_res['out']
            
            summary_zh_res = run_ollama(f"Translate the following English summary into Chinese without any explanation:\n\n{summary_en}")
            if 'err' in summary_zh_res:
                summary_zh = None
                summary_zh_res['field']='summary_zh'
                err_msg.append(summary_zh_res)
            else:
                summary_zh = summary_zh_res['out']

        # Step 4: 嵌入
        emb_vector = embedding_model.encode(full_text).tolist()

        # Step 5: 插入 PostgreSQL
        cur.execute("""
            INSERT INTO transcript_segment (
                file_id, start_time, end_time, speaker, text, text_language,
                translated_text, summary_en, summary_zh, emotion, topic, embedding, version
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            file_id,  # file_id: 建议先人工将文件入表获取 ID
            datetime.timedelta(seconds=start),
            datetime.timedelta(seconds=end),
            None,  # speaker 可选
            full_text,
            lang,
            translated,
            summary_en,
            summary_zh,
            emotion,
            topic,
            emb_vector,
            version,
        ))

    conn.commit()
    return err_msg

def new_logic(conn, cur, file_id, segments, version):
    cur_logger.info(f'begin to deal with segments')
    
    err_msg=[]
    
    seg_idx = 0
    for seg in segments:
        if seg_idx <= 2:
            cur_logger.info(f'seg_idx: {seg_idx}, segment: {seg}, type(segment): {type(seg)}')

        if isinstance(seg, dict):
            seg = SimpleNamespace(**seg)
            
        seg_idx += 1
        cur_logger.info(f'deal with file_id: {file_id} seg_idx: {seg_idx}')
        start, end, text = seg.start, seg.end, seg.text.strip()
        if not text:
            continue

        '''
        all columns:
        
            file_id, start_time, end_time, speaker, text, text_language,
            translated_text, summary_en, summary_zh, emotion, topic, embedding
        
        using columns:
        
            file_id, start_time, end_time, text
        '''
        cur.execute("""
            INSERT INTO transcript_segment (
                file_id, start_time, end_time, text, version
            ) VALUES (
                %s, %s, %s, %s, %s
            )
        """, (
            file_id,  # file_id: 建议先人工将文件入表获取 ID
            datetime.timedelta(seconds=start),
            datetime.timedelta(seconds=end),
            text,
            version,
        ))

        conn.commit()
    return err_msg

def exist_same_md5_transcript_log(cur, file_md5:str)->bool:
    '''
    file_id, path, status, started_at FROM transcription_log
    '''
    try:
        cur.execute(f"SELECT file_id, path, status, started_at FROM transcription_log WHERE file_md5 = %s and status='success';", (file_md5,))
        rows = cur.fetchall()
        cur_logger.info(f'exist_same_md5_transcript_log: rows: {rows}')
        return rows and len(rows)>0
    except Exception as e:
        cur_logger.info(f"❌ failed to query transcription_log with same md5: {str(e)}")
        return None

from functools import lru_cache

NUM_WORKERS=1

def transcribe_all(conn, cur, file_id:str, file_path:str,start_time:str,llm_model_name:str,file_md5:str,whisper_model_alias:str,whisper_beam_size:str,model_384d:str):
    version_ymd_hms_ppid_pid = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S') + '-' + str(os.getppid()) + '-' + str(os.getpid())
    embedding_model_name = model_384d
    model_in_out = None
    try:
        # 配置项
        SRT_SOURCE = file_path
        OLLAMA_MODEL = llm_model_name  # 你在本地 Ollama 中配置的模型名
        
        # if a file with the same md5 had been transcribed, the current file will be ignored.
        if exist_same_md5_transcript_log(cur, file_md5):
            return

        # 初始化模型
        cur_logger.info(f'begin to init {whisper_model_alias}')
        transcriber = WhisperTranscriber(whisper_model_alias, num_workers=NUM_WORKERS)
        cur_logger.info(f'end to init {whisper_model_alias}, transcriber.id: {id(transcriber)}')

        # Step 1: 转录
        cur_logger.info(f'begin to transcribe by {whisper_model_alias}')
        segments, info = transcriber.transcribe(SRT_SOURCE, beam_size=whisper_beam_size, language=None, vad_filter=True)
        cur_logger.info(f'end to transcribe by {whisper_model_alias}, info:{info}')
        
        if info is None or (isinstance(info, dict) and info['tech'] == 'mlx_whisper'):
            model_in_out = {'model':'mlx_whisper'}
            model_in_out = {**model_in_out, **info}
        else:    
            model_in_out = {
                "args": str(getattr(info, "transcription_options", "")),
                "info":{"language":info.language,"language_probability":info.language_probability, "duration":info.duration, "duration_after_vad":info.duration_after_vad}
            }
        cur_logger.info(f'model_in_out:{model_in_out}')

        # err_msg = old_logic(segments,OLLAMA_MODEL,info,embedding_model)
        err_msg = new_logic(conn, cur, file_id, segments, version_ymd_hms_ppid_pid)

        if len(err_msg)>0:
            log_transcription(conn, cur, file_id, file_md5, file_path, "partial_success", start_time, whisper_model_alias, embedding_model_name,model_in_out,version_ymd_hms_ppid_pid, str(err_msg))
        else:
            log_transcription(conn, cur, file_id, file_md5, file_path, "success", start_time, whisper_model_alias, embedding_model_name,model_in_out,version_ymd_hms_ppid_pid)

    except Exception as e:
        log_transcription(conn, cur, file_id, file_md5, file_path, "error", start_time, whisper_model_alias, embedding_model_name,model_in_out if model_in_out else 'None',version_ymd_hms_ppid_pid, str(e))
    finally:
        # cur.close()
        # conn.close()
        conn.commit()


from global_config.config import yaml_config_boxed
def main_func(whisper_model_alias:str, file_id:str, file_path:str,file_md5:str, start_time=datetime.datetime.now()):
    DB_CONN = yaml_config_boxed.transcribe.db_conn
    llm_model_name = yaml_config_boxed.transcribe.llm.ollama_model
    whisper_beam_size = yaml_config_boxed.transcribe.whisper.beam_size
    model_384d = yaml_config_boxed.transcribe.embedding.model_384d

    # PostgreSQL 连接
    with psycopg2.connect(DB_CONN) as conn, conn.cursor() as cur:
        conn.autocommit = False
        # 15 seconds timeout for each statement
        cur.execute("SET statement_timeout = %s", (15 * 1000,))
        # using 'for update' lock to prevent multiple processes from transcribing the same file
        cur.execute("""
            SELECT * FROM file_inventory 
            WHERE id = %s FOR UPDATE SKIP LOCKED
        """, (file_id,))
        
        record = cur.fetchone()
        
        if not record:
            cur_logger.warning(f"[file_id={file_id}] locked by other processes; skip.")
            return
                    
        old_row = get_transcription_log(cur, file_path)
        started_at = datetime.datetime.now()
        if old_row:
            file_id, path, status, started_at = old_row
            cur_logger.info(f'get_transcription_log, file_id:{file_id}, path:{path}, status:{status}, started_at:{started_at}')
        time_gap_in_days = (datetime.datetime.now() - started_at).days
        if old_row is None or status != 'success' or time_gap_in_days>1:
            transcribe_all(conn, cur, file_id, file_path, start_time, llm_model_name, file_md5, whisper_model_alias, whisper_beam_size, model_384d)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transcribe audio or video files')
    parser.add_argument('-fp','--filepath', help='File path to transcribe')
    parser.add_argument('-fid','--fileid', help='File id from file_inventory to transcribe')
    parser.add_argument('-fmd5','--file_md5', help='File md5 from file_inventory to transcribe')

    args = parser.parse_args()

    start_time = datetime.datetime.now()
    file_id = args.fileid
    file_path = args.filepath
    file_md5 = args.file_md5

    if not os.path.exists(file_path):
        cur_logger.info(f"file not exists, ignored, file_path:{file_path}")
        sys.exit(0)
        
    main_func(file_id, file_path, file_md5, start_time)
