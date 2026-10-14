"""Optional real-window capture for acceptance_login.py; no editing or mouse input."""
import ctypes,json,os,subprocess,sys,time,textwrap
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from reverse_cli.config import ffmpeg
FFMPEG=ffmpeg('axure')
class Recorder:
 def __init__(self,out):
  self.out=out;self.proc=None;self.parts=[];self.steps=[];self.caption=out/'current-command.txt'
 def window(self,pid):
  u=ctypes.windll.user32;found=[]
  callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
  def visit(hwnd,unused):
   owner=wintypes.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
   if owner.value==pid and u.IsWindowVisible(hwnd) and u.GetWindowTextLengthW(hwnd)>0:found.append(hwnd)
   return True
  u.EnumWindows(callback(visit),0)
  if len(found)!=1:raise RuntimeError(f'Expected one visible Axure recording window; got {len(found)}')
  return found[0]
 def start(self,pid):
  hwnd=self.window(pid)
  # Window presentation only. Project content and edits remain public CLI calls.
  u=ctypes.windll.user32;u.SetThreadDpiAwarenessContext.argtypes=[wintypes.HANDLE];u.SetThreadDpiAwarenessContext.restype=wintypes.HANDLE
  prior=u.SetThreadDpiAwarenessContext(wintypes.HANDLE(-4))
  u.MoveWindow(wintypes.HWND(hwnd),0,0,2800,1700,True);u.SetForegroundWindow(wintypes.HWND(hwnd));u.SetThreadDpiAwarenessContext(prior)
  time.sleep(.8)
  self.update('Axure native editor | actual CLI replay | no mouse input')
  name=f'native-part-{len(self.parts)+1}.mp4';output=self.out/name
  self.log=(self.out/(name+'.log')).open('wb')
  vf="scale=1920:1166,pad=1920:1280:0:0:color=0x111827,drawtext=fontfile='C\\:/Windows/Fonts/consola.ttf':textfile=current-command.txt:reload=1:fontcolor=white:fontsize=26:x=26:y=1184"
  self.proc=subprocess.Popen([str(FFMPEG),'-hide_banner','-loglevel','warning','-n','-f','gdigrab','-framerate','15','-draw_mouse','0','-i',f'hwnd={hwnd}','-vf',vf,'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],cwd=self.out,stdin=subprocess.PIPE,stdout=self.log,stderr=self.log,creationflags=subprocess.CREATE_NO_WINDOW,env=dict(os.environ,TEMP=r'D:\Caches\Axure\Temp',TMP=r'D:\Caches\Axure\Temp'))
  self.started=time.monotonic();self.parts.append(str(output));time.sleep(1)
  if self.proc.poll() is not None:raise RuntimeError('Recorder failed; inspect '+str(self.out/(name+'.log')))
 def update(self,caption):
  text='\n'.join(textwrap.wrap(caption,130)[:3])
  temp=self.caption.with_suffix('.tmp');temp.write_text(text,encoding='utf-8')
  # FFmpeg briefly opens this file on Windows at each frame. Retry only the
  # caption-file rename, never a software-editing CLI operation.
  for attempt in range(100):
   try:temp.replace(self.caption);break
   except PermissionError:
    if attempt==99:raise
    time.sleep(.02)
  if self.proc:self.steps.append({'part':len(self.parts),'seconds':round(time.monotonic()-self.started,3),'caption':caption})
 def before(self,args):
  if self.proc:self.update('> axure-cli '+subprocess.list2cmdline(list(map(str,args))))
 def after(self,args):
  if self.proc:time.sleep(1.5 if (args[0] in ('undo','redo') or len(args)>1 and args[1] in ('create','bounds','set','save','open','new','html')) else .08)
 def stop(self):
  if not self.proc:return
  self.proc.stdin.write(b'q\n');self.proc.stdin.flush();self.proc.wait(timeout=30);self.log.close()
  if self.proc.returncode:raise RuntimeError('Recording did not finalize successfully')
  self.proc=None
  (self.out/'recording-timeline.json').write_text(json.dumps({'parts':self.parts,'steps':self.steps,'mouseEvents':0,'capture':'FFmpeg GDI window capture at 15 fps; captions are actual CLI commands'},indent=2),encoding='utf-8')
