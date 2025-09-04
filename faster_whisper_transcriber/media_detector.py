#!/usr/bin/env python3
"""
视频文件音轨检测工具
支持 MKV、AVI 等常见格式的音频流检测
"""
import os
import subprocess
import json
import logging
from pathlib import Path
from global_config.logger_config import logger, get_logger

# 配置日志
cur_logger = get_logger(os.path.basename(__file__))

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

def check_audio_stream(file_path: str) -> dict:
    """
    检查视频文件是否有音频流
    
    Args:
        file_path (str): 视频文件路径
        
    Returns:
        dict: 包含检测结果的字典
            {
                'has_audio': bool,           # 是否有音频流
                'audio_streams': list,         # 音频流信息列表
                'error': str or None        # 错误信息（如果有）
            }
    """
    
    try:
        # 使用 ffprobe 检查音频流
        cmd = [
            "ffprobe",
            "-v", "error",                    # 只输出错误和数据
            "-show_entries", "stream=codec_type,codec_name,channels,sample_rate",
            "-select_streams", "a:0",           # 选择第一个音频流
            "-of", "json",
            file_path
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True,
            timeout=30  # 设置超时时间避免卡死
        )
        
        try:
            probe_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            return {
                'has_audio': False,
                'audio_streams': [],
                'error': f"ffprobe输出解析失败: {e}"
            }
            
        # 检查是否有音频流
        audio_streams = probe_data.get("streams", [])
        
        if not audio_streams:
            return {
                'has_audio': False,
                'audio_streams': [],
                'error': None
            }
            
        # 提取音频流信息
        audio_info_list = []
        
        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "audio":
                info = {
                    'index': stream.get('index', ''),
                    'codec': stream.get('codec_name', ''),
                    'channels': stream.get('channels', 0),
                    'sample_rate': stream.get('sample_rate', 0)
                }
                audio_info_list.append(info)
        
        return {
            'has_audio': True,
            'audio_streams': audio_info_list,
            'error': None
        }
        
    except subprocess.CalledProcessError as e:
        # ffprobe 执行失败
        cur_logger.error(f"ffprobe执行错误: {e}")
        return {
            'has_audio': False,
            'audio_streams': [],
            'error': f"ffprobe执行失败: {e.stderr}"
        }
    except subprocess.TimeoutExpired:
        # 超时
        cur_logger.error("ffprobe执行超时")
        return {
            'has_audio': False,
            'audio_streams': [],
            'error': "ffprobe执行超时"
        }
    except Exception as e:
        # 其他异常
        cur_logger.error(f"检测过程中发生错误: {e}")
        return {
            'has_audio': False,
            'audio_streams': [],
            'error': str(e)
        }

def check_audio_stream_alternative(file_path: str) -> dict:
    """
    非阻塞方式检查音频流 (可选的备用方法)
    
    Args:
        file_path (str): 视频文件路径
        
    Returns:
        dict: 检测结果
    """
    
    try:
        # 只获取基本的流信息而不解析音频元数据
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "stream=index,codec_type",
            "-select_streams", "a",  # 获取所有音频流
            "-of", "json",
            file_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            probe_data = json.loads(result.stdout)
            streams = probe_data.get("streams", [])
            
            # 检查是否包含音频流
            has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
            
            # 返回所有音频流的索引
            audio_indices = [stream["index"] for stream in streams 
                          if stream.get("codec_type") == "audio"]
            
            return {
                'has_audio': has_audio,
                'audio_streams': audio_indices if has_audio else [],
                'error': None
            }
        else:
            return {
                'has_audio': False,
                'audio_streams': [],
                'error': f"ffprobe检测失败: {result.stderr}"
            }
            
    except Exception as e:
        cur_logger.error(f"备用方法检测失败: {e}")
        return {
            'has_audio': False,
            'audio_streams': [],
            'error': str(e)
        }

def is_video_has_audio(file_path: str) -> bool:
    """
    简化版本：只返回是否有音频
    
    Args:
        file_path (str): 视频文件路径
        
    Returns:
        bool: True 表示有音频，False 表示无音频
    """
    
    result = check_audio_stream(file_path)
    return result.get('has_audio', False)

# def main():
#     """主函数测试"""
    
#     # 测试列表
#     test_files = [
#         "/path/to/test_video.mkv",
#         "/path/to/test_video.avi", 
#         "/path/to/test_video.mp4"
#     ]
    
#     for file_path in test_files:
#         if Path(file_path).exists():
#             try:
#                 result = check_audio_stream(file_path)
                
#                 print(f"\n=== 检测文件: {file_path} ===")
#                 print(f"有音频流: {'是' if result['has_audio'] else '否'}")
                
#                 if result['audio_streams']:
#                     print("音频流详情:")
#                     for idx, stream in enumerate(result['audio_streams']):
#                         print(f"  流 {idx}: 编解码器={stream['codec']}, "
#                               f"声道数={stream['channels']}, "
#                               f"采样率={stream['sample_rate']}Hz")
                
#                 if result['error']:
#                     print(f"错误信息: {result['error']}")
                    
#             except Exception as e:
#                 logger.error(f"处理文件 {file_path} 时出错: {e}")
#         else:
#             logger.warning(f"文件不存在: {file_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Transcribe audio or video files')
    parser.add_argument('files', metavar='FILE', nargs='+', help='File paths to transcribe')
    
    args = parser.parse_args()
    for test_file in args.files:
        # 示例用法
        print("=== 音频流检测示例 ===")
        
        # 检查测试文件
        result = check_audio_stream(test_file)
        print(f'result: {result}')
        
        if not Path(test_file).exists():
            print("⚠️ 测试文件不存在，请确认路径!")
        else:
            print(f"输入文件: {test_file}")
            print(f"检测结果:")
            print(f"  是否含有音频流: {'是' if result['has_audio'] else '否'}")
            
            if result['audio_streams']:
                print("  音频流详情:")
                for stream in result['audio_streams']:
                    print(f"    编解码器: {stream.get('codec', 'unknown')}")
                    print(f"    声道数: {stream.get('channels', 0)}")
                    print(f"    采样率: {stream.get('sample_rate', 0)}Hz")
            else:
                print("  检测到无音频流或无法获取流信息")
            
            if result['error']:
                print(f"  错误详情: {result['error']}")

        # 简化检查
        print("\n简化结果:")
        has_audio = is_video_has_audio(test_file)
        print(f"文件是否包含音频: {'是' if has_audio else '否'}")
