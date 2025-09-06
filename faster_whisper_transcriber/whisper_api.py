# ~/whisper_api.py
from fastapi import FastAPI, UploadFile, File, Form
import tempfile
import os
from faster_transcribe import WhisperTranscriber

from global_config.logger_config import get_logger

cur_logger = get_logger(os.path.basename(__file__))

app = FastAPI()

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...),
                     whisper_model_alias: str = Form(...),  whisper_beam_size:int=Form(1)
                    ):
    try:
        # 保存上传的文件
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(file.filename)[1], delete=False) as tmp:
            content = await file.read()
            with open(tmp.name, "wb") as f:
                f.write(content)
            
            # 转录
            # 初始化模型
            cur_logger.info(f'begin to init {whisper_model_alias}')
            transcriber = WhisperTranscriber(whisper_model_alias, num_workers=1)
            cur_logger.info(f'end to init {whisper_model_alias}, transcriber.id: {id(transcriber)}')

            # Step 1: 转录
            cur_logger.info(f'begin to transcribe by {whisper_model_alias}, file: {tmp.name}')
            segments, info = transcriber.transcribe(tmp.name, beam_size=whisper_beam_size, language=None, vad_filter=True)
            cur_logger.info(f'end to transcribe by {whisper_model_alias}, info:{info}')
            
            cur_logger.info(f'in whisper_api: type(segments): {type(segments)}, type(segments[0]):{type(segments[0] if segments else "No segments")}, segments[0]:{segments[0] if segments else "No segments data"}, info: {info}, type(info): {type(info)}')
            
            # 清理临时文件
            os.unlink(tmp.name)
            
            return {
                "segments": segments,
                "info": info
            }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)