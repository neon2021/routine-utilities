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

### Ubuntu 详细安装指南

在Ubuntu系统上，您可以按照以下步骤安装和运行Video Splitter：

1. 安装所需的系统依赖：

```bash
# 安装FFmpeg
sudo apt-get update
sudo apt-get install ffmpeg

# 安装Python3和pip
sudo apt-get install python3 python3-pip

# 安装PyQt6所需的系统库
sudo apt-get install libxcb-cursor0
```

2. 创建并进入项目目录：

```bash
mkdir -p ~/video-splitter
cd ~/video-splitter
```

3. 下载或克隆项目：

```bash
# 如果使用git
git clone https://github.com/your-username/video-splitter.git .
# 或者手动下载并解压项目文件到该目录
```

4. 创建requirements.txt文件（如果项目中没有）：

```bash
echo "PyQt6>=6.0.0" > requirements.txt
echo "ffmpeg-python>=0.2.0" >> requirements.txt
```

5. 安装Python依赖：

```bash
pip3 install -r requirements.txt
```

6. 创建启动脚本：

```bash
echo '#!/bin/bash' > run_video_splitter.sh
echo 'python3 "$(dirname "$0")"/video_splitter/video_splitter.py' >> run_video_splitter.sh
chmod +x run_video_splitter.sh
```

7. 创建桌面快捷方式（可选）：

```bash
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/video-splitter.desktop << EOF
[Desktop Entry]
Name=Video Splitter
Comment=Split video files into segments
Exec=bash -c 'cd $HOME/video-splitter && ./run_video_splitter.sh'
Terminal=false
Type=Application
Categories=Utility;Video;
Icon=ffmpeg
EOF
```

## 使用方法

1. 运行程序：

```bash
python video_splitter.py
```

或在Ubuntu上，使用以下方法之一：

```bash
# 使用启动脚本
./run_video_splitter.sh

# 或直接运行Python脚本
python3 video_splitter/video_splitter.py
```

也可以从应用程序菜单中找到并启动"Video Splitter"（如果创建了桌面快捷方式）。

2. 点击"Select Videos"选择要处理的视频文件
3. 设置压缩率（CRF值，0-51，数值越小质量越高）
4. 为每个视频添加时间段（格式：HH:MM:SS）
5. 点击"Process Videos"开始处理

## 常见问题解决

在Ubuntu上使用时，可能会遇到以下问题：

1. **找不到PyQt6模块**：
   ```
   ModuleNotFoundError: No module named 'PyQt6'
   ```
   解决方案：确保使用`pip3 install PyQt6`安装了PyQt6，并且使用的是安装了该模块的Python版本。

2. **Qt xcb插件错误**：
   ```
   qt.qpa.plugin: Could not load the Qt platform plugin "xcb"
   ```
   解决方案：安装所需的xcb库：`sudo apt-get install libxcb-cursor0`

3. **ffmpeg命令未找到**：
   确保已正确安装ffmpeg：`sudo apt-get install ffmpeg`

## 注意事项

- 时间格式必须为HH:MM:SS（例如：00:05:30表示5分30秒）
- CRF值范围为0-51，建议值：
  - 15-18：高质量
  - 19-23：中等质量
  - 24-28：低质量
- 输出文件将保存在原视频所在目录，文件名格式为：原文件名_segment_序号.mp4 