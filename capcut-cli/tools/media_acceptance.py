"""Read-only independent FFmpeg media decoding for acceptance."""
import os
from pathlib import Path
import re
import subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
FFMPEG=ROOT / ".native-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
RATE=48000
ENV=dict(os.environ,TEMP="D:/Caches/CapCutAgent/Temp",TMP="D:/Caches/CapCutAgent/Temp")

def run(arguments, *, check=True):
    result = subprocess.run([str(FFMPEG), '-hide_banner', *arguments],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
    if check and result.returncode:
        raise RuntimeError(result.stderr.decode('utf8', errors='replace'))
    return result


def metadata(path):
    result = run(['-i', str(path)], check=False)
    log = result.stderr.decode('utf8', errors='replace')
    streams = [line.strip() for line in log.splitlines() if 'Stream #' in line]
    duration = re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)', log)
    return {'streamDescriptions': streams,
            'containerDurationSeconds': (int(duration[1])*3600 + int(duration[2])*60
                                         + float(duration[3])) if duration else None}


def frames(path):
    result = run(['-v', 'error', '-xerror', '-i', str(path), '-map', '0:v:0',
                  '-vf', 'scale=320:180', '-fps_mode', 'passthrough',
                  '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'])
    return np.frombuffer(result.stdout, dtype=np.uint8).reshape(-1, 180, 320, 3)


def first_channel(path):
    # Select channel zero rather than downmixing stereo, to avoid adding an
    # implicit sqrt(2) coefficient in the verifier itself.
    result = run(['-v', 'error', '-xerror', '-i', str(path), '-map', '0:a:0',
                  '-af', 'pan=mono|c0=c0', '-ar', str(RATE), '-f', 'f32le', 'pipe:1'])
    return np.frombuffer(result.stdout, dtype='<f4')


def stereo(path):
    result = run(['-v', 'error', '-xerror', '-i', str(path), '-map', '0:a:0',
                  '-ar', str(RATE), '-ac', '2', '-f', 'f32le', 'pipe:1'])
    return np.frombuffer(result.stdout, dtype='<f4').reshape(-1, 2)

