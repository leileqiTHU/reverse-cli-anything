"""Create and verify a native login prototype using only the public Axure CLI."""
import hashlib,json,os,subprocess,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'/('login-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
OUT.mkdir(parents=True)
records=[];checks=[];widgets={};pages={};snapshots={}
recorder=None
if os.environ.get('AXURE_RECORD_DEMO')=='1':
 from record_demo import Recorder
 recorder=Recorder(OUT)
env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',TEMP=r'D:\Caches\Axure\Temp',TMP=r'D:\Caches\Axure\Temp')
def run(*args,expected=True):
 if recorder:
  recorder.before(args)
  if args==('project','close'):recorder.stop()
 argv=[sys.executable,str(ROOT/'axure_cli.py'),*map(str,args)]
 gateway=os.environ.get('REVERSE_CLI_ACCEPTANCE_GATEWAY')=='1' and expected
 if gateway:argv=[sys.executable,str(ROOT.parent/'reverse-cli.py'),'run','axure','--operation-id','axure-regression-'+uuid.uuid4().hex,'--',*map(str,args)]
 p=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',env=env,timeout=120)
 envelope=json.loads(p.stdout);result=envelope.get('response',envelope) if gateway else envelope
 records.append({'command':list(map(str,args)),'response':result,'exitCode':p.returncode,'commonReceipt':envelope.get('receipt')})
 assert result['ok']==expected,(args,result,p.stderr)
 if recorder:
  if args==('project','new') and not recorder.parts:recorder.start(status['pid'])
  if args[0]=='launch':recorder.start(result['result']['pid'])
  recorder.after(args)
 return result.get('result',result)
def check(name,value):
 checks.append({'name':name,'passed':bool(value)});assert value,name
def create(name,kind,text,x,y,width,height,*extra):
 w=run('widget','create','--kind',kind,'--name',name,'--text',text,'--x',x,'--y',y,'--width',width,'--height',height,*extra)
 widgets[name]=w['id'];return w
def install(name,spec):
 path=OUT/(name+'-click.json');path.write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
 return run('interaction','set','--id',widgets[name],'--spec',path)
def settext(name,text):return {'type':'setText','target':widgets[name],'text':text}
def snapshot():
 state=run('inspect')
 return {'widgets':state['widgets'],'interactions':{w['id']:run('interaction','get','--id',w['id']) for w in state['widgets']}}
try:
 status=run('status');check('starts from a saved project',not status['project']['dirty'])
 run('project','new')
 login=run('page','create','--name','Login')['page'];pages['Login']=login['Id']
 check('new page uses exact requested name',login['Name']=='Login')
 run('undo');check('one native undo removes created page',all(p['Id']!=login['Id'] for p in run('page','list')['pages']))
 run('redo');check('native redo restores page and stable ID',any(p['Id']==login['Id'] and p['Name']=='Login' for p in run('page','list')['pages']))
 run('page','create','--name','Login',expected=False);check('duplicate page names rejected',len(run('page','list')['pages'])==2)
 pages['Success']=run('page','create','--name','Success')['page']['Id']
 run('page','open','--id',pages['Success'])
 create('success_heading','paragraph','Signed in successfully',180,100,450,40)
 create('success_note','paragraph','Native Axure interaction completed.\nThis is a local prototype, with no account or network authentication.',180,160,520,70)
 create('back','button','Back to login',180,260,320,44)
 install('back',{'cases':[{'name':'Return to Login','actions':[{'type':'navigate','page':pages['Login']}]}]})
 snapshots['Success']=snapshot()
 run('page','open','--id',pages['Login'])
 create('heading','paragraph','Sign in to reverse-cli',180,80,420,40)
 create('subtitle','paragraph','Created and wired through the native Axure CLI.',180,126,460,30)
 create('username_label','paragraph','Username',180,180,320,24)
 create('username','input','',180,210,320,42,'--placeholder','Enter username')
 create('password_label','paragraph','Password',180,270,320,24)
 password=create('password','input','',180,300,320,42,'--password','--placeholder','Enter password')
 check('native input retains password type',password['inputType']=='Password')
 submit=create('submit','button','Sign in',170,365,300,46)
 change=run('widget','bounds','--id',submit['id'],'--x',180,'--width',320)
 check('native bounds transaction returns actual geometry',change['after']['bounds']==dict(x=180,y=365,width=320,height=46))
 undo=run('undo');check('bounds undo restores original rectangle',next(w for w in undo['widgets'] if w['id']==submit['id'])['bounds']==submit['bounds'])
 redo=run('redo');check('bounds redo restores changed rectangle',next(w for w in redo['widgets'] if w['id']==submit['id'])['bounds']==change['after']['bounds'])
 before=run('inspect')['widgets'];run('widget','bounds','--id',submit['id'],'--width',0,expected=False)
 check('invalid dimensions leave widgets unchanged',run('inspect')['widgets']==before)
 create('reset','button','Clear form',180,427,320,40)
 create('feedback','paragraph','Enter the demo credentials to continue.',180,490,460,45)
 create('demo_note','paragraph','Demo credentials: demo / cli123\nLocal prototype only. Do not enter a real password.',180,550,480,55)
 invalid={'cases':[{'actions':[{'type':'setText','target':'00000000-0000-0000-0000-000000000000','text':'invalid'}]}]}
 bad=OUT/'invalid-spec.json';bad.write_text(json.dumps(invalid),encoding='utf-8')
 run('interaction','set','--id',submit['id'],'--spec',bad,expected=False)
 check('invalid action target leaves native interaction map empty',not run('interaction','get','--id',submit['id'])['events'])
 spec={'event':'click','cases':[
  {'name':'Missing fields','when':{'any':[{'widget':widgets['username'],'equals':''},{'widget':widgets['password'],'equals':''}]},'actions':[settext('feedback','Please enter both username and password.')]},
  {'name':'Demo credentials accepted','when':{'all':[{'widget':widgets['username'],'equals':'demo'},{'widget':widgets['password'],'equals':'cli123'}]},'actions':[{'type':'navigate','page':pages['Success']}]},
  {'name':'Invalid credentials','actions':[settext('feedback','Those demo credentials are incorrect. Try demo / cli123.')]}
 ]}
 attached=install('submit',spec)['interaction'];check('native click has three conditional cases',len(attached['events'][0]['cases'])==3)
 run('undo');check('native undo removes installed interaction',not run('interaction','get','--id',submit['id'])['events'])
 run('redo');check('native redo restores exact interaction tree',run('interaction','get','--id',submit['id'])==attached)
 run('interaction','set','--id',submit['id'],'--spec',OUT/'submit-click.json',expected=False)
 check('existing interaction protected',run('interaction','get','--id',submit['id'])==attached)
 install('reset',{'cases':[{'name':'Clear inputs and feedback','actions':[settext('username',''),settext('password',''),settext('feedback','Enter the demo credentials to continue.')]}]})
 snapshots['Login']=snapshot();page_state=run('page','list')['pages']
 rp=OUT/'login-form.rp';save=run('project','save','--path',rp)
 check('native save creates a clean nonempty project',rp.stat().st_size>0 and not save['dirty'])
 run('project','new');run('project','open','--path',rp)
 check('save/reopen retains all page IDs and names',run('page','list')['pages']==page_state)
 for name in ('Success','Login'):
  run('page','open','--id',pages[name]);check(name+' save/reopen retains widgets, geometry and native interactions',snapshot()==snapshots[name])
 oldpid=run('status')['pid'];run('project','close')
 from axure_cli import alive
 for _ in range(100):
  if not alive(oldpid):break
  time.sleep(.1)
 check('old native process exits',not alive(oldpid))
 launched=run('launch','--project',rp);check('cold reopen starts a different PID',launched['pid']!=oldpid)
 check('native cache and process TEMP are on D',launched['temp'].lower().startswith('d:') and launched['configuredCache'].lower().startswith('d:'))
 check('cold reopen retains page IDs and names',run('page','list')['pages']==page_state)
 for name in ('Success','Login'):
  run('page','open','--id',pages[name]);check(name+' cold reopen retains widgets, geometry and native interactions',snapshot()==snapshots[name])
 html=OUT/'html';export=run('export','html','--output',html)
 check('native HTML exporter reports success',export['nativeSuccess'])
 check('Login and Success HTML pages exported',(html/'login.html').exists() and (html/'success.html').exists())
 check('native interaction runtime emitted',(html/'resources/scripts/axure/expr.js').exists())
 check('native export includes click branches','Missing fields' in (html/'files/login/data.js').read_text(encoding='utf-8'))
 run('project','save')
 result={'passed':True,'version':'11.0.0.4150','utc':datetime.now(timezone.utc).isoformat(),'mouseClicks':0,'keyboardAutomation':0,'outputDirectory':str(OUT),'project':str(rp),'htmlPage':str(html/'login.html'),'pages':pages,'widgets':widgets,'checks':checks,'commands':records,'snapshots':snapshots,'oldPid':oldpid,'reopenedPid':launched['pid'],'artifacts':[{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (rp,html/'login.html',html/'files/login/data.js')]}
except Exception as e:
 result={'passed':False,'error':str(e),'checks':checks,'commands':records,'outputDirectory':str(OUT)}
if recorder:
 recorder.update('Native editor acceptance: '+('PASS' if result['passed'] else 'FAILED'))
 time.sleep(2);recorder.stop();result['recordingParts']=recorder.parts
(OUT/'acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
Path(os.environ.get('AXURE_EVIDENCE_OUTPUT',ROOT/'evidence/native-login-acceptance.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':result['passed'],'checks':len(checks),'output':str(OUT),'error':result.get('error')},ensure_ascii=False))
raise SystemExit(0 if result['passed'] else 1)
