# Audio/Video Transcriber

This script transcribes audio and video files to text using OpenAI's Whisper speech recognition model.

## Requirements

- Python 3.6+
- ffmpeg
- openai-whisper

The script will attempt to install missing dependencies automatically.

## Usage

### Command Line

```bash
cd transcriber
./run_transcriber.sh /path/to/your/audio_or_video_file.mp4
```

### Installation

Run the installation script to set up the integration with your file manager:

```bash
cd transcriber
./install_transcriber.sh
```

### Integration with Thunar File Manager

1. The installation script will automatically set up Thunar integration if Thunar is installed.

2. Alternatively, you can manually set up Thunar custom action:
   - Open Thunar
   - Go to Edit > Configure custom actions...
   - Click the "+" button to add a new action
   - Fill in the following details:
     - Name: Transcribe Audio/Video
     - Description: Transcribe audio or video to text
     - Command: /home/YOUR_USERNAME/Documents/code-projects/routine-utilities/transcriber/run_transcriber.sh %f
   - In the "Appearance Conditions" tab, select:
     - Audio files
     - Video files
   - Click "OK" to save

3. Now you can right-click on any audio or video file in Thunar and select "Transcribe Audio/Video" from the context menu.

### Integration with Nautilus (Ubuntu Files)

1. Install the nautilus-python package:

```bash
sudo apt install python3-nautilus
```

2. The installation script will automatically set up Nautilus integration if the requirements are installed.

3. Alternatively, you can manually set up the Nautilus extension:
   - Copy the transcriber_extension.py file to the Nautilus extensions directory:
   ```bash
   mkdir -p ~/.local/share/nautilus-python/extensions/
   cp transcriber_extension.py ~/.local/share/nautilus-python/extensions/
   ```
   - Edit the script path in the extension if needed
   - Restart Nautilus:
   ```bash
   nautilus -q
   ```

4. Now you can right-click on audio/video files in Nautilus and select "Transcribe Audio/Video" from the context menu. 