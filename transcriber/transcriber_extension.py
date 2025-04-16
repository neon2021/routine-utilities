#!/usr/bin/env python3
import os
import subprocess
from urllib.parse import unquote
from gi.repository import Nautilus, GObject

class AudioVideoTranscriberExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        pass
        
    def get_file_items(self, window, files):
        # Only show for audio and video files
        audio_video_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm']
        
        for file_info in files:
            filename = unquote(file_info.get_uri()[7:])  # Remove 'file://' prefix
            ext = os.path.splitext(filename)[1].lower()
            
            if ext in audio_video_extensions:
                item = Nautilus.MenuItem(
                    name='Nautilus::transcribe',
                    label='Transcribe Audio/Video',
                    tip='Transcribe this audio/video file to text'
                )
                item.connect('activate', self.transcribe_file, file_info)
                return [item]
                
        return []
        
    def transcribe_file(self, menu, file_info):
        filename = unquote(file_info.get_uri()[7:])  # Remove 'file://' prefix
        script_path = os.path.expanduser('~/Documents/code-projects/routine-utilities/transcriber/run_transcriber.sh')
        
        # Run the script in a terminal
        cmd = ['gnome-terminal', '--', 'bash', '-c', f'"{script_path}" "{filename}"; read -p "Press Enter to close..."']
        subprocess.Popen(cmd) 