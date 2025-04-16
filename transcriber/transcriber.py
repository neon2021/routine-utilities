#!/usr/bin/env python3

import os
import sys
import subprocess
import tempfile
import argparse
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        # Check for ffmpeg
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        
        # Check for whisper
        subprocess.run(["pip3", "show", "openai-whisper"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def install_dependencies():
    """Install required dependencies."""
    print("Installing required dependencies...")
    try:
        # Install ffmpeg if not available
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            subprocess.run(["sudo", "apt", "install", "-y", "ffmpeg"], check=True)
        
        # Install whisper
        subprocess.run(["pip3", "install", "openai-whisper"], check=True)
        
        return True
    except subprocess.SubprocessError:
        print("Failed to install dependencies.")
        return False

def extract_audio(file_path):
    """Extract audio from video file to a temporary WAV file."""
    temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_audio.close()
    
    cmd = [
        "ffmpeg", "-i", file_path, 
        "-vn", "-acodec", "pcm_s16le", 
        "-ar", "16000", "-ac", "1", 
        temp_audio.name
    ]
    
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return temp_audio.name

def transcribe_audio(audio_path, output_path):
    """Transcribe audio using Whisper."""
    try:
        import whisper
        model = whisper.load_model("base")
        print(f"Transcribing {os.path.basename(audio_path)}...")
        result = model.transcribe(audio_path)
        
        with open(output_path, 'w') as f:
            f.write(result["text"])
        
        return True
    except Exception as e:
        print(f"Error during transcription: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Transcribe audio or video files')
    parser.add_argument('files', metavar='FILE', nargs='+', help='File paths to transcribe')
    
    args = parser.parse_args()
    
    # Check and install dependencies
    if not check_dependencies():
        if not install_dependencies():
            print("Unable to install required dependencies. Please install ffmpeg and whisper manually.")
            sys.exit(1)
    
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
        
        output_path = f"{os.path.splitext(file_path)[0]}.txt"
        print(f"Processing {os.path.basename(file_path)}...")
        
        try:
            # Extract audio if it's a video file
            if os.path.splitext(file_path)[1].lower() in ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm']:
                temp_audio = extract_audio(file_path)
                transcribe_audio(temp_audio, output_path)
                os.unlink(temp_audio)
            else:
                # Assume it's already an audio file
                transcribe_audio(file_path, output_path)
            
            print(f"Transcription saved to {output_path}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    main() 