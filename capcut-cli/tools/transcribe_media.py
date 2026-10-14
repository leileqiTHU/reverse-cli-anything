"""Fresh local English speech recognition; caches and model stay on D:."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

CACHE = Path('D:/Caches/CapCutAgentSpeech')
for key, value in {'HF_HOME':CACHE/'huggingface', 'HF_HUB_CACHE':CACHE/'huggingface/hub',
                   'XDG_CACHE_HOME':CACHE, 'TEMP':CACHE/'temp', 'TMP':CACHE/'temp'}.items():
    os.environ[key] = str(value)
import numpy as np
from faster_whisper import WhisperModel

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): raise FileExistsError(a.output)
    root = Path(__file__).resolve().parents[1]
    ffmpeg = root/'.native-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
    model_dir = CACHE/'models/models--Systran--faster-whisper-base.en/snapshots/3d3d5dee26484f91867d81cb899cfcf72b96be6c'
    began = time.monotonic()
    pcm = subprocess.run([str(ffmpeg),'-hide_banner','-v','error','-xerror','-i',str(a.input),
        '-map','0:a:0','-ar','16000','-ac','1','-f','f32le','pipe:1'],capture_output=True,check=True).stdout
    model = WhisperModel(str(model_dir),device='cpu',compute_type='int8',cpu_threads=6)
    segments, info = model.transcribe(np.frombuffer(pcm,dtype='<f4').copy(),language='en',
        beam_size=5,word_timestamps=True,vad_filter=False,condition_on_previous_text=False)
    result = {'input':str(a.input.resolve()),'model':str(model_dir),'initialPromptUsed':False,'segments':[]}
    for s in segments:
        result['segments'].append({'start':s.start,'end':s.end,'text':s.text,
            'words':[{'start':w.start,'end':w.end,'word':w.word,'probability':w.probability} for w in s.words or []]})
        print(f'{s.start:.2f} - {s.end:.2f}: {s.text}',flush=True)
    result['elapsedSeconds'] = time.monotonic()-began
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'ok':True,'segments':len(result['segments']),'output':str(a.output)}),flush=True)

if __name__ == '__main__': main()
