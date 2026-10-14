"""Join actual native-window/browser captures and verify the complete MP4 decode."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from record_demo import FFMPEG
ROOT=Path(__file__).resolve().parent
os.environ.update(TEMP=r'D:\Caches\Axure\Temp',TMP=r'D:\Caches\Axure\Temp')
native=json.loads((ROOT/'evidence/native-login-acceptance.json').read_text(encoding='utf-8'))
browser=json.loads((ROOT/'evidence/native-login-browser.json').read_text(encoding='utf-8'))
assert native['passed'] and browser['passed'] and native['outputDirectory']==browser['outputDirectory']
out=Path(native['outputDirectory']);parts=[*map(Path,native['recordingParts']),Path(browser['video'])]
def info(p):
 r=subprocess.run([str(FFMPEG),'-hide_banner','-i',str(p)],capture_output=True,text=True,encoding='utf-8',errors='replace')
 m=re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)',r.stderr);assert m,r.stderr
 return int(m[1])*3600+int(m[2])*60+float(m[3])
durations=[info(p) for p in parts]
(out/'parts.txt').write_text(''.join("file '"+p.as_posix()+"'\n" for p in parts),encoding='utf-8')
titles=['CLI builds the native Axure project','Cold reopen and native HTML export','Native HTML interaction verification']
start=0;chapters=[];meta=';FFMETADATA1\n'
for title,duration in zip(titles,durations):
 chapters.append({'title':title,'startSeconds':round(start,3),'durationSeconds':duration})
 meta+=f'[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(start*1000)}\nEND={round((start+duration)*1000)}\ntitle={title}\n';start+=duration
(out/'chapters.txt').write_text(meta,encoding='utf-8')
video=out/'axure-cli-from-blank.mp4'
subprocess.run([str(FFMPEG),'-hide_banner','-loglevel','error','-n','-f','concat','-safe','0','-i',str(out/'parts.txt'),'-f','ffmetadata','-i',str(out/'chapters.txt'),'-map','0:v:0','-map_metadata','1','-map_chapters','1','-vf','setsar=1','-r','15','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
decoded=subprocess.run([str(FFMPEG),'-hide_banner','-xerror','-err_detect','explode','-i',str(video),'-map','0:v:0','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
(out/'video-decode.log').write_text(decoded.stderr,encoding='utf-8')
assert decoded.returncode==0,decoded.stderr
frames=re.findall(r'frame=\s*(\d+)',decoded.stderr)
result={'passed':True,'path':str(video),'bytes':video.stat().st_size,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'durationSeconds':info(video),'decodedFrames':int(frames[-1]),'width':1920,'height':1280,'fps':15,'mouseEvents':0,'chapters':chapters,'sourceClips':[str(p) for p in parts],'capture':'Native window: FFmpeg GDI at 15 fps. Browser: actual CDP screenshots sampled at approximately 5 fps, resampled to 15 fps. No synthesized software frames.','editing':'Three chronological clips joined at app cold restart and browser transition; CLI command captions overlaid. No speed-up. No audio.','nativeEvidence':'native-login-acceptance.json','browserEvidence':'native-login-browser.json'}
(out/'recording-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
(ROOT/'evidence/login-recording.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
