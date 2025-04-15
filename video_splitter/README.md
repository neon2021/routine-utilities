# Video Splitter

一个跨平台的视频分割工具，支持多视频文件批量分割和压缩。

## 功能特点

- 支持多个视频文件同时处理
- 每个视频可以设置多个时间段进行分割
- 可调节视频压缩率（CRF值）
- 支持Windows、macOS和Linux系统
- 简单直观的图形界面

## 系统要求

- Python 3.6+
- FFmpeg
- PyQt6
- ffmpeg-python

## 安装说明

1. 首先确保系统已安装FFmpeg：

   - Windows: 下载FFmpeg并添加到系统PATH
   - macOS: `brew install ffmpeg`
   - Ubuntu: `sudo apt-get install ffmpeg`

2. 安装Python依赖：

```bash
pip install -r requirements.txt
```

## 使用方法

1. 运行程序：

```bash
python video_splitter.py
```

2. 点击"Select Videos"选择要处理的视频文件
3. 设置压缩率（CRF值，0-51，数值越小质量越高）
4. 为每个视频添加时间段（格式：HH:MM:SS）
5. 点击"Process Videos"开始处理

## 注意事项

- 时间格式必须为HH:MM:SS（例如：00:05:30表示5分30秒）
- CRF值范围为0-51，建议值：
  - 15-18：高质量
  - 19-23：中等质量
  - 24-28：低质量
- 输出文件将保存在原视频所在目录，文件名格式为：原文件名_segment_序号.mp4 