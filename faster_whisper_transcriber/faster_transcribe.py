import os
from datetime import datetime
from dataclasses import dataclass

import torch
from faster_whisper import WhisperModel

import argparse

import subprocess, tempfile
from pathlib import Path
import json
    
from global_config.logger_config import logger

from types import SimpleNamespace


logger.name = os.path.basename(__file__)

# nice method to convert seconds to the format as "hour:minute:second"
# sourced from "Python Convert Seconds to HH:MM:SS (hours, minutes, seconds)" https://pynative.com/python-convert-seconds-to-hhmmss/
def conver_to_hms(sec:float)->str:
    mm,ss=divmod(sec,60)
    hh,mm=divmod(mm,60)
    return '%02d:%02d:%02d'%(hh,mm,ss)

class WhisperTranscriber:
    def __init__(self, model:str, cpu_threads:int=4, num_workers:int=1) -> None:
        import platform
        self.system = platform.system()
        
        logger.name = os.path.basename(__file__)
        same_folder=os.path.expanduser("~/Downloads/huggingface_downloads/")
        model_dict={
            'distil-large-v3-ct2':same_folder+"/distil-whisper/distil-large-v3-ct2",
            # 'faster-distil-whisper-large-v2':os.path.join(same_folder,"/Systran/faster-distil-whisper-large-v2"),
            'faster-whisper-large-v3-turbo-ct2':same_folder+"/deepdml/faster-whisper-large-v3-turbo-ct2",
            # 'faster-whisper-large-v3':same_folder+"/Systran/faster-whisper-large-v3",
            "faster-whisper-medium":same_folder+"Systran/faster-whisper-medium"
            }

        if self.is_macos():
            if model == 'large':
                self.selected_model_path = os.path.expanduser("~/Downloads/huggingface_downloads/mlx-community/whisper-large-v3-mlx")
            else:
                self.selected_model_path = os.path.expanduser("~/Downloads/huggingface_downloads/mlx-community/whisper-medium-mlx-8bit")
        else:
            self.selected_model_path = model_dict[model]
        logger.info('model=%s, selected_model_path=%s'%(model, self.selected_model_path))


        # define our torch configuration
        # device = "cuda:0" if torch.cuda.is_available() else "cpu" # bug: ValueError: unsupported device cuda:0
        if not self.is_macos():
            device = "cuda" if torch.cuda.is_available() else "cpu" # fix bug: ValueError: unsupported device cuda:0
            compute_type = "float16" if self.system == "Darwin" or torch.cuda.is_available() else "float32"
            logger.info('device=%s, compute_type=%s'%(device, compute_type))

            # load model on GPU if available, else cpu
            # model = WhisperModel(os.path.expanduser("~/Downloads/huggingface_downloads/distil-whisper/distil-large-v3-ct2"), device=device, compute_type=compute_type,local_files_only=True)
            self.model = WhisperModel(self.selected_model_path, device=device, compute_type=compute_type,local_files_only=True,
                                    cpu_threads=cpu_threads, num_workers=num_workers)

    def is_macos(self)->bool:
        return self.system == "Darwin"
    
    def transcribe(self, file_path:str, beam_size:int=5, language:str=None, vad_filter:bool=True):
        '''
            language: "zh", "en" or None
        '''
        
        logger.info('transcribe: pid=%s, ppid=%s, file_path=%s'%(os.getpid(), os.getppid(), file_path))
        
        if self.is_macos():
            import mlx_whisper
            # NOTE: beam_size, vad_filter are omitted, not yet implemented
            # RETURNS:
            #   text
            #   segments
            #   language
            res = mlx_whisper.transcribe(file_path, path_or_hf_repo=self.selected_model_path, language=language)
            segments = res['segments']
            info = {'language': res['language'], 'selected_model_path': self.selected_model_path, 'tech':'mlx_whisper'}
        else:
            segments, info = self.model.transcribe(file_path
                                , beam_size=beam_size
                                , language=language
                                , vad_filter=vad_filter)
        # if delete_after_transcribing:
        #     os.remove(file_path)
        #     logger.info(f'after removing, file_path is there: {os.path.exists(file_path)}')
        return segments, info

    def start_transcribe(self, file_path:str, file_format:str="srt", not_write_file:bool=True, multilingual=True, language:str=None, temperature=(0.0, 0.2, 0.4)):
        '''
            language: "zh", "en" or None
        '''
        
        logger.info('file_path=%s'%(file_path))
        
        if self.is_macos():
            import mlx_whisper
            # NOTE: beam_size, vad_filter are omitted, not yet implemented
            # RETURNS:
            #   text
            #   segments
            #   language
            res = mlx_whisper.transcribe(file_path, path_or_hf_repo=self.selected_model_path,language=language)
            segments = res['segments']
            info = {'language': res['language']}
        else:
            segments, info = self.model.transcribe(file_path
                                , beam_size=5
                                , multilingual=multilingual
                                , language=language
                                , vad_filter=True
                                , temperature=temperature)

        start = datetime.now()
        if not_write_file:
            lines=[]
            row_num=1
            for segment in segments:
                if file_format=='txt':
                    line = self.create_txt_line(row_num, segment)
                    
                if file_format=='srt':
                    line = self.create_srt_line(row_num, segment)
                    
                lines.append(line)
                # if row_num % 50 ==0:
                #     srt_out.flush()
                logger.info(line)
                row_num+=1

                ending = datetime.now()
                elapse_seconds = (ending-start).seconds
                # srt_out.write("selected_model_path: %s"%(selected_model_path),ending='\n')
                lines.append("\n\n\n")
                lines.append("selected_model_path: %s\n"%(self.selected_model_path))
                lines.append("start: %s, end: %s\n"%(start, ending))
                lines.append("elapse_seconds: %s\n"%elapse_seconds)
            return ''.join(lines)
        else:
            only_file_name = os.path.splitext(os.path.basename(file_path))[0]

            file_name_suffix= "_srt.txt" if file_format=='txt' else ".srt"

            output_srt_file_path= os.path.join( os.path.dirname(file_path),only_file_name+"_"+start.strftime("%H_%M_%S")+file_name_suffix)
            logger.info('output_srt_file_path: %s'%(output_srt_file_path))
            with open(output_srt_file_path,'w') as srt_out:
                row_num=1
                for segment in segments:
                    if file_format=='txt':
                        line = self.create_txt_line(row_num, segment)
                        
                    if file_format=='srt':
                        line = self.create_srt_line(row_num, segment)
                        
                    srt_out.write(line)
                    # if row_num % 50 ==0:
                    #     srt_out.flush()
                    logger.info(line)
                    row_num+=1

                ending = datetime.now()
                elapse_seconds = (ending-start).seconds
                # srt_out.write("selected_model_path: %s"%(selected_model_path),ending='\n')
                srt_out.write("\n\n\n")
                srt_out.write("selected_model_path: %s\n"%(self.selected_model_path))
                srt_out.write("start: %s, end: %s\n"%(start, ending))
                srt_out.write("elapse_seconds: %s\n"%elapse_seconds)
        
            return output_srt_file_path


    def create_txt_line(self, row_num:int, segment)->str:
        if row_num<=2:
            logger.info('row_num=%s, segment=%s, type(segment)=%s'%(row_num, segment, type(segment)))
            
        if isinstance(segment, dict):
            segment = SimpleNamespace(**segment)
            
        ''' for txt format, line:
        [00:56:06 -> 00:56:06] Yeah.
        '''
        return """[%s -> %s] %s\n""" % (
                conver_to_hms(segment.start), conver_to_hms(segment.end)
                    , segment.text
            )

    def create_srt_line(self, row_num:int, segment)->str:
        if row_num<=2:
            logger.info('row_num=%s, segment=%s, type(segment)=%s'%(row_num, segment, type(segment)))
            
        ''' for srt format, line:
        1
        00:56:06,001 --> 00:56:06,901
        Yeah.
        '''
        if isinstance(segment, dict):
            segment = SimpleNamespace(**segment)
        
        return """%s
%s,000 --> %s,000
%s\n\n""" % (row_num
                , conver_to_hms(segment.start), conver_to_hms(segment.end)
                , segment.text
            )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Transcribe audio or video files')
    parser.add_argument('files', metavar='FILE', nargs='+', help='File paths to transcribe')
    
    args = parser.parse_args()

    # Unable to load any of {libcudnn_ops.so.9.1.0, libcudnn_ops.so.9.1, libcudnn_ops.so.9, libcudnn_ops.so}
    # Invalid handle. Cannot load symbol cudnnCreateTensorDescriptor
    # [1]    65130 IOT instruction (core dumped)  python faster-transcribe.py
    # transcriber = WhisperTranscriber('faster-whisper-large-v3-turbo-ct2')
    transcriber = None
    for file_path in args.files:
        if not os.path.exists(file_path):
            logger.info(f"File not found: {file_path}")
            continue

        parts = os.path.splitext(file_path)
        srt_file_path=parts[0]+'.srt'
        logger.info(f"\ncheckpoint: file_path: {file_path}, srt_file_path: {srt_file_path}\n")

        if transcriber is None:
            transcriber = WhisperTranscriber('distil-large-v3-ct2')
        srt = transcriber.start_transcribe(file_path=file_path)

        with open(srt_file_path,'w') as srt_file:
            srt_file.write(srt)
