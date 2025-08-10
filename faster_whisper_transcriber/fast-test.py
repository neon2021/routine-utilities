from faster_whisper import WhisperModel
import os

model_path = os.path.expanduser("~/Downloads/huggingface_downloads/") \
            + "/Systran/faster-whisper-large-v3"
media_fp="/home/caesar/Videos/martin-english/compress_mov-italki-2023_11_17-Martin_English-Screen Recording 2023-11-17 at 21.34.11_hardwareHevcNvenc.mp4"
model = WhisperModel(model_path, device="cuda", compute_type="float16")
segments, _ = model.transcribe(media_fp, beam_size=5)
print(segments[0].text)