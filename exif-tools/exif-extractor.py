import sys
from pathlib import Path
from pymediainfo import MediaInfo
import exifread
from mutagen import File as MutagenFile
from PIL import Image
import json
from tinytag import TinyTag

path = Path(sys.argv[1])
ext = path.suffix.lower()

def image_metadata(fp):
    with open(fp, 'rb') as f:
        tags = exifread.process_file(f)
    return {k: str(v) for k, v in tags.items()}

def video_audio_metadata(fp):
    info = MediaInfo.parse(fp)
    return {track.track_type: track.to_data() for track in info.tracks}

# def audio_id3_metadata(fp):
#     meta = MutagenFile(fp)
#     return {k: str(v) for k, v in meta.items()} if meta else {}

def audio_id3_metadata(fp,EXTRACT_APIC=False):
    if EXTRACT_APIC:
        '''
        错误来自 mutagen.File() 尝试解析一个 SMB 路径下的 .mp3 文件时失败，报错信息是：

    mutagen.id3._util.error: [Errno 22] Invalid argument
    � 根本原因

    这个报错通常发生在以下几种情况之一：

    SMB/GVFS路径文件不能被 mutagen 正常读取
    gvfs 提供的路径如：
    /run/user/1000/gvfs/smb-share:server=some_machine.local,...
    实际上是一个虚拟挂载系统，mutagen 尝试以普通 file-like 对象操作可能会失败。
    文件未按预期打开或不是标准文件对象
    mutagen.File() 默认尝试识别文件格式，但某些格式（尤其是 SMB 挂载下的）可能无法返回可读的 fileobj.read(10)。

    solution: 读取为 BytesIO 后再交给 mutagen 处理
        '''
        import io
        try:
            with open(fp, 'rb') as f:
                data = f.read()
            meta = MutagenFile(io.BytesIO(data))
            # print(f'audio_id3_metadata: keys: {",".join([k for k,v in meta.items()])}')
            return {k: str(v) for k, v in meta.items()} if meta else {}
        except Exception as e:
            return {'error': str(e)}
    else:
        tag = TinyTag.get(fp)
        # print(tag.title, tag.artist, tag.duration, tag.bitrate)
        return {key:getattr(tag, key)
                for key in dir(tag)
                  if key not in ['audio_offset','extra']
                    and not key.startswith('_') and not callable(getattr(tag,key))
            }

def safe_dict(obj):
    return {
        k: str(v) for k, v in obj.items()
        if isinstance(v, (str, int, float, bool, type(None)))
    }



def wrap_filepath(ret_json,file_path:str):
    ret_json['file_path'] = file_path
    return json.dumps(ret_json)

if ext in ['.jpg', '.jpeg', '.png', '.heic', '.webm','.svg']:
    return_json = image_metadata(path)
elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
    return_json = video_audio_metadata(path)
elif ext in ['.mp3', '.flac', '.wav']:
    return_json = audio_id3_metadata(path)
else:
    return_json = {'error': 'Unsupported file type'}

print(wrap_filepath(safe_dict(return_json), str(path)))