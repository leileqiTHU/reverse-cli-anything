"""Run real native acceptance via the public CLI; creates its own isolated project."""
import hashlib,json,os,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'/('acceptance-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
OUT.mkdir(parents=True)
records=[];checks=[]
env=dict(os.environ,PYTHONIOENCODING='utf-8')
def run(*args,expected=True):
 p=subprocess.run([sys.executable,str(ROOT/'axure_cli.py'),*args],capture_output=True,text=True,encoding='utf-8',env=env,timeout=120)
 result=json.loads(p.stdout);records.append({'command':list(args),'response':result,'exitCode':p.returncode})
 assert result['ok']==expected,(args,result,p.stderr)
 return result.get('result',result)
def check(name,value):
 checks.append({'name':name,'passed':bool(value)});assert value,name
def text(state):return next(w['text'] for w in state['widgets'] if w['id']==wid)
try:
 status=run('status');check('initial project is clean',not status['project']['dirty'])
 cache=run('settings','cache','--path',r'D:\Caches\Axure\Application');check('native configurable cache points to D',cache['configuredCache']==r'D:\Caches\Axure\Application')
 run('project','new');widget=run('widget','create','--text','Original text','--name','CLI acceptance paragraph');wid=widget['id']
 check('native widget creation',widget['text']=='Original text')
 updated='Hello from reverse-cli — 原生文字编辑'
 change=run('widget','text','--id',wid,'--text',updated)
 check('native text transaction',change['before']=='Original text' and change['after']['text']==updated and change['dirty'])
 rejected=run('project','new',expected=False);check('dirty-project guard','UNSAVED_CHANGES' in rejected['error'])
 check('guard leaves document intact',text(run('inspect'))==updated)
 check('native undo restores original text',text(run('undo'))=='Original text')
 check('native redo restores changed text',text(run('redo'))==updated)
 rp=OUT/'text-proof.rp';save=run('project','save','--path',str(rp));check('native save persisted clean file',rp.stat().st_size>0 and not save['dirty'])
 check('native new removes previous page widgets',not run('project','new')['widgets'])
 reopened=run('project','open','--path',str(rp));check('save/reopen retains stable ID and Unicode text',text(reopened)==updated and not reopened['dirty'])
 sitemap=run('project','sitemap');check('official read service remains usable',bool(sitemap))
 html=OUT/'html';export=run('export','html','--output',str(html));check('native exporter reports success',export['nativeSuccess'])
 pages=[p for p in html.glob('*.html') if updated in p.read_text(encoding='utf-8-sig')]
 check('exported HTML contains exact edited text',bool(pages))
 check('native JavaScript runtime emitted',(html/'resources'/'scripts'/'axure'/'axQuery.js').exists())
 check('native CSS emitted',any(html.rglob('*.css')))
 run('export','html','--output',str(html),expected=False);check('nonempty export directory protected',True)
 oldpid=run('status')['pid'];run('project','close')
 from axure_cli import alive
 for _ in range(100):
  if not alive(oldpid):break
  time.sleep(.1)
 check('native close exits old process',not alive(oldpid))
 launched=run('launch','--project',str(rp));check('cold start uses a new PID',launched['pid']!=oldpid)
 check('cold-start reopen retains stable ID and Unicode text',text(launched['project'])==updated)
 check('cold-start process uses D temp and cache',launched['temp'].lower().startswith('d:') and launched['configuredCache'].lower().startswith('d:'))
 # Demonstrate that the reopened widget remains editable, then restore it via native undo.
 run('widget','text','--id',wid,'--text','Cold reopen editable')
 check('reopened widget remains editable',text(run('inspect'))=='Cold reopen editable')
 check('native undo works after cold reopen',text(run('undo'))==updated)
 run('project','save');check('final saved state is clean',not run('inspect')['dirty'])
 result={'passed':True,'application':'Axure RP','version':'11.0.0.4150','utc':datetime.now(timezone.utc).isoformat(),'mouseClicks':0,'keyboardAutomation':0,'outputDirectory':str(OUT),'project':str(rp),'widgetId':wid,'expectedText':updated,'htmlPage':str(pages[0]),'oldPid':oldpid,'reopenedPid':launched['pid'],'checks':checks,'commands':records,'artifacts':[{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [rp,pages[0]]]}
except Exception as e:
 result={'passed':False,'error':str(e),'checks':checks,'commands':records,'outputDirectory':str(OUT)}
(OUT/'acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'evidence'/'native-text-acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':result['passed'],'checks':len(checks),'output':str(OUT),'error':result.get('error')},ensure_ascii=False))
raise SystemExit(0 if result['passed'] else 1)
