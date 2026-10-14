"""Record actual Windows application pixels and an executed-command journal.

Windows Graphics Capture follows the largest visible window for one PID,
including the home/editor HWND change. No mouse, keyboard, or document writes.
"""
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import threading
import time

from PIL import Image, ImageDraw, ImageFont, ImageOps
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/".native-tools"))
from windows_capture import WindowsCapture


class WindowRecorder:
    def __init__(self, pid, output, ffmpeg, env):
        self.pid, self.output, self.ffmpeg, self.env = pid, Path(output), ffmpeg, env
        self.events, self.command, self.status = [], '', 'Starting actual CapCut window capture'
        self.stop_event, self.error = threading.Event(), None
        self.started = time.monotonic()
        self.frames = 0
        self.handles = set()
        self.last_window = None
        self.next_snapshot = 0

    def update(self, command, status='RUNNING'):
        self.command, self.status = command, status
        self.events.append({'seconds': round(time.monotonic()-self.started, 3),
                            'command': command, 'status': status})

    def check(self):
        if self.error:
            raise RuntimeError('Recorder failed; stopping further edits') from self.error

    def start(self):
        self.log = self.output.with_suffix('.ffmpeg.log').open('wb')
        self.process = subprocess.Popen([str(self.ffmpeg), '-hide_banner', '-loglevel', 'warning',
            '-n', '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', '1920x1440',
            '-framerate', '15', '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'veryfast',
            '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(self.output)],
            stdin=subprocess.PIPE, stdout=self.log, stderr=self.log, env=self.env,
            creationflags=subprocess.CREATE_NO_WINDOW)
        self.started = time.monotonic()
        self.thread = threading.Thread(target=self._record, daemon=True)
        self.thread.start()
        time.sleep(2)
        self.check()

    def _record(self):
        u, g = C.windll.user32, C.windll.gdi32
        u.SetThreadDpiAwarenessContext.argtypes = [W.HANDLE]
        u.SetThreadDpiAwarenessContext.restype = W.HANDLE
        prior = u.SetThreadDpiAwarenessContext(W.HANDLE(-4))
        control = None
        capture = None
        latest = [None]
        callback = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
        font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 23)
        title_font = ImageFont.truetype('C:/Windows/Fonts/consolab.ttf', 26)
        try:
            while not self.stop_event.is_set():
                candidates = []
                def visit(hwnd, _):
                    p = W.DWORD(); u.GetWindowThreadProcessId(hwnd, C.byref(p))
                    if p.value == self.pid and u.IsWindowVisible(hwnd) and not u.IsIconic(hwnd) and u.GetWindowTextLengthW(hwnd):
                        rect = W.RECT(); u.GetWindowRect(hwnd, C.byref(rect))
                        w, h = rect.right-rect.left, rect.bottom-rect.top
                        if w > 400 and h > 250: candidates.append((w*h, hwnd, w, h))
                    return True
                u.EnumWindows(callback(visit), 0)
                canvas = Image.new('RGB', (1920, 1440), '#111827')
                draw = ImageDraw.Draw(canvas)
                if candidates:
                    _, hwnd, w, h = max(candidates)
                    self.handles.add(int(hwnd))
                    if self.last_window != int(hwnd):
                        self.events.append({'seconds':round(time.monotonic()-self.started,3), 'windowHandle':int(hwnd), 'size':[w,h]})
                        self.last_window = int(hwnd)
                    if capture is None or getattr(capture, 'bound_hwnd', None) != int(hwnd):
                        if control is not None and not control.is_finished(): control.stop()
                        latest[0] = None
                        capture = WindowsCapture(cursor_capture=False, window_hwnd=int(hwnd),
                                                 secondary_window=True, minimum_update_interval=66)
                        capture.bound_hwnd = int(hwnd)
                        @capture.event
                        def on_frame_arrived(frame, capture_control):
                            latest[0] = Image.fromarray(frame.frame_buffer[:, :, [2,1,0]].copy())
                        @capture.event
                        def on_closed():
                            pass
                        control = capture.start_free_threaded()
                    if latest[0] is not None:
                        pixels = ImageOps.contain(latest[0], (1920,1134), Image.Resampling.BILINEAR)
                        canvas.paste(pixels, ((1920-pixels.width)//2,(1134-pixels.height)//2))
                    else:
                        draw.text((50,520),'Waiting for the first native window frame...',font=title_font,fill='white')
                else:
                    draw.text((50, 520), 'CapCut is switching between home and editor windows...', font=title_font, fill='white')
                elapsed = time.monotonic()-self.started
                draw.rectangle((0,1134,1920,1440), fill='#111827')
                draw.text((24,1150), f'REVERSE-CLI  |  CapCut native editing  |  {elapsed:06.1f}s  |  No mouse input', font=title_font, fill='#67E8F9')
                lines = textwrap.wrap(self.command, 135, replace_whitespace=False)
                if len(lines)>7: raise RuntimeError('Command does not fit recording footer')
                for i,line in enumerate(lines):
                    draw.text((24,1190+i*27), line, font=font, fill='white')
                draw.text((24,1404), self.status[:130], font=font, fill='#86EFAC' if self.status.startswith('OK') else '#FDE68A')
                if elapsed >= self.next_snapshot:
                    snapshot=self.output.parent/f'capture-{int(elapsed):04}s.png'
                    canvas.save(snapshot)
                    self.events.append({'seconds':round(elapsed,3),'snapshot':str(snapshot),'command':self.command,'status':self.status})
                    self.next_snapshot=elapsed+15
                # Duplicate real samples when needed to retain wall-clock duration,
                # rather than silently speeding up slow capture/encoding.
                target = max(self.frames+1, round((time.monotonic()-self.started)*15))
                raw = canvas.tobytes()
                while self.frames < target:
                    self.process.stdin.write(raw); self.frames += 1
                self.stop_event.wait(max(0, self.frames/15-(time.monotonic()-self.started)))
        except BaseException as exc:
            self.error = exc
        finally:
            if control is not None and not control.is_finished(): control.stop()
            u.SetThreadDpiAwarenessContext(prior)

    def stop(self):
        self.stop_event.set(); self.thread.join(timeout=30)
        if self.thread.is_alive(): raise RuntimeError('Recorder thread did not stop')
        self.process.stdin.close(); self.process.wait(timeout=60); self.log.close()
        journal = {'capture':'Windows Graphics Capture; occlusion-independent PID-bound home/editor pixels; live command footer',
                   'frames':self.frames, 'fps':15, 'durationSeconds':self.frames/15,
                   'windowHandles':sorted(self.handles), 'mouseEventsSent':0, 'keyboardEventsSent':0,
                   'events':self.events, 'recorderError':str(self.error) if self.error else None}
        self.output.with_suffix('.timeline.json').write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding='utf8')
        self.check()
        if self.process.returncode: raise RuntimeError('Recording encoder failed')
