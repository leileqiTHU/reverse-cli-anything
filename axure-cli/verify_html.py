"""Render the native export in installed Chrome with a disposable D: profile."""
import functools,hashlib,http.server,json,os,subprocess,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parent
report=ROOT/'evidence'/'native-text-acceptance.json'
data=json.loads(report.read_text(encoding='utf-8'))
page=Path(data['htmlPage']);out=page.parent.parent
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(page.parent)))
threading.Thread(target=server.serve_forever,daemon=True).start()
profile=Path(r'D:\Caches\Axure\HtmlQA')/out.name
shot=out/'native-html.png'
url=f'http://127.0.0.1:{server.server_port}/{page.name}'
args=[r'C:\Program Files\Google\Chrome\Application\chrome.exe','--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',f'--user-data-dir={profile}',f'--disk-cache-dir={profile / "Cache"}','--window-size=1280,800','--virtual-time-budget=3000','--dump-dom',f'--screenshot={shot}',url]
try:
 p=subprocess.run(args,capture_output=True,timeout=45,env=dict(os.environ,TEMP=r'D:\Caches\Axure\Temp',TMP=r'D:\Caches\Axure\Temp'))
 dom=p.stdout.decode('utf-8',errors='replace');(out/'rendered-dom.html').write_text(dom,encoding='utf-8')
 checks={'browserExitZero':p.returncode==0,'exactTextInRenderedDom':data['expectedText'] in dom,'screenshotCreated':shot.exists() and shot.stat().st_size>1000}
 result={'passed':all(checks.values()),'checks':checks,'screenshot':str(shot),'profile':str(profile),'mouseClicks':0,'sha256':hashlib.sha256(shot.read_bytes()).hexdigest() if shot.exists() else None}
 (ROOT/'evidence'/'native-html-render.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result))
finally:server.shutdown()
raise SystemExit(0 if result['passed'] else 1)
