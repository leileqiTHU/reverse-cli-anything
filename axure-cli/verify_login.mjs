// Real native HTML runtime verification. Node 22+ built-in WebSocket; no packages.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const root=path.dirname(fileURLToPath(import.meta.url));
const native=JSON.parse(fs.readFileSync(process.env.AXURE_NATIVE_EVIDENCE||path.join(root,'evidence/native-login-acceptance.json'),'utf8'));
if(!native.passed)throw new Error('Native acceptance must pass first');
const out=native.outputDirectory, html=path.dirname(native.htmlPage);
const profile=path.join('D:/Caches/Axure/HtmlQA',path.basename(out)+'-'+Date.now());
fs.mkdirSync(profile,{recursive:true});
const checks=[],exceptions=[],captureErrors=[],screenshots=[];
const recording=process.env.AXURE_RECORD_DEMO==='1',frames=[],captions=[];
let capturing=false,captureLoop,captureStarted;
const frameDir=path.join('D:/Caches/Axure/Recordings',path.basename(out)+'-'+Date.now());
const label=text=>{if(recording&&captureStarted)captions.push({seconds:(performance.now()-captureStarted)/1000,text});};
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const check=(name,passed,detail)=>{checks.push({name,passed:!!passed,...(detail===undefined?{}:{detail})});label((passed?'PASS: ':'FAIL: ')+name);if(!passed)throw new Error(name);};
const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.gif':'image/gif','.svg':'image/svg+xml','.json':'application/json'};
const server=http.createServer((req,res)=>{
 try{
  const p=path.resolve(html,'.'+decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname));
  if(!p.startsWith(path.resolve(html)+path.sep)){res.writeHead(403).end();return;}
  const body=fs.readFileSync(p);res.writeHead(200,{'Content-Type':mime[path.extname(p)]||'application/octet-stream'});res.end(body);
 }catch{res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=`http://127.0.0.1:${server.address().port}`;
const log=fs.openSync(path.join(out,'browser.log'),'a');
const browser=spawn(process.env.REVERSE_CLI_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe',[
 '--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
 '--remote-debugging-port=0','--remote-debugging-address=127.0.0.1',`--user-data-dir=${profile}`,`--disk-cache-dir=${path.join(profile,'Cache')}`,
 '--window-size=1280,900','about:blank'
],{windowsHide:true,stdio:['ignore',log,log],env:{...process.env,TEMP:'D:/Caches/Axure/Temp',TMP:'D:/Caches/Axure/Temp'}});
let socket,send,result;
try{
 let port;
 for(let i=0;i<120;i++){try{port=Number(fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0]);break;}catch{await pause(100);}}
 if(!port)throw new Error('Chrome did not open a debugging endpoint');
 const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
 socket=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
 let sequence=0;const pending=new Map();
 socket.addEventListener('message',ev=>{const m=JSON.parse(ev.data);if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params.exceptionDetails);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result);}});
 send=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence;const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout: '+method));},15000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
 // Chrome serializes screenshots internally; keep stills and recording frames
 // on one queue to avoid overlapping capture requests during navigation.
 let screenshotTail=Promise.resolve();
 const capture=options=>{const request=screenshotTail.catch(()=>{}).then(()=>send('Page.captureScreenshot',options));screenshotTail=request;return request;};
 await send('Page.enable');await send('Runtime.enable');await send('Network.enable');
 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 if(recording){
  fs.mkdirSync(frameDir,{recursive:true});captureStarted=performance.now();capturing=true;
  label('Native Axure HTML | real browser interaction | keyboard activation only');
  captureLoop=(async()=>{while(capturing){const started=performance.now();try{const r=await capture({format:'jpeg',quality:85,captureBeyondViewport:false});const file=path.join(frameDir,String(frames.length).padStart(6,'0')+'.jpg');fs.writeFileSync(file,Buffer.from(r.data,'base64'));frames.push({file,seconds:(started-captureStarted)/1000});}catch(e){if(capturing)captureErrors.push(String(e));}await pause(Math.max(5,200-(performance.now()-started)));}})();
 }
 // Axure exports a Google Fonts link by default. Test local prototype offline.
 await send('Network.setBlockedURLs',{urls:['https://*','http://fonts.*']});
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const until=async(expression)=>{for(let i=0;i<80;i++){if(await evaluate(expression))return true;await pause(100);}return false;};
 const select=name=>`document.querySelector('[data-label="${name}"] input')`;
 const feedback=`document.querySelector('[data-label="feedback"]')?.innerText`;
 const fill=async(name,value)=>{label('Enter dummy '+name+': '+value);const r=await evaluate(`(()=>{const e=${select(name)};if(!e)throw new Error('Missing input');e.focus();e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return e.value;})()`);if(recording)await pause(1100);return r;};
 const activate=async(name)=>{
  label('Focus '+name+' and press Enter (no mouse event)');
  await evaluate(`${select(name)}.focus()`);
  await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
  await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
  if(recording)await pause(1200);
 };
 const shot=async(name)=>{if(recording)await pause(2200);const p=path.join(out,name+'.png');const data=await capture({format:'png',captureBeyondViewport:false});fs.writeFileSync(p,Buffer.from(data.data,'base64'));screenshots.push({path:p,sha256:createHash('sha256').update(fs.readFileSync(p)).digest('hex')});};
 await send('Page.navigate',{url:base+'/login.html'});
 check('native Login page initializes',await until(`document.title==='Login' && !!${select('username')} && typeof $axure!=='undefined'`));
 await pause(700);
 check('username hint survives native export',await evaluate(`${select('username')}.value==='Enter username'`));
 check('native exported submit geometry matches CLI bounds',await evaluate(`(()=>{const r=document.querySelector('[data-label="submit"]').getBoundingClientRect();return r.width===320 && r.height===46;})()`));
 await shot('login-initial');
 await activate('submit');
 check('empty fields trigger native validation',await until(`${feedback}==='Please enter both username and password.'`));
 check('validation does not navigate',await evaluate(`document.title==='Login'`));
 await shot('login-validation');
 await fill('username','demo');await activate('submit');
 check('partial credentials remain on validation branch',await until(`${feedback}==='Please enter both username and password.' && document.title==='Login'`));
 await fill('password','wrong-demo-password');await activate('submit');
 check('native password input is masked when it contains a value',await evaluate(`${select('password')}.type==='password'`));
 check('incorrect credentials trigger native else branch',await until(`${feedback}==='Those demo credentials are incorrect. Try demo / cli123.'`));
 await shot('login-invalid');
 await activate('reset');
 check('clear button restores empty input hints through native actions',await until(`${select('username')}.value==='Enter username' && ${select('password')}.value==='Enter password'`));
 check('clear button restores feedback',await until(`${feedback}==='Enter the demo credentials to continue.'`));
 await fill('username','demo');await fill('password','cli123');await activate('submit');
 check('valid demo credentials navigate through native link action',await until(`document.title==='Success' && location.pathname.endsWith('/success.html')`));
 check('native destination page renders',await until(`document.body?.innerText.includes('Signed in successfully') && !!${select('back')}`));
 await shot('login-success');
 await activate('back');
 check('native return action reaches Login',await until(`document.title==='Login' && !!${select('submit')}`));
 check('no JavaScript exceptions or capture failures',exceptions.length===0&&captureErrors.length===0,{exceptions,captureErrors});
 const dom=await evaluate('document.documentElement.outerHTML');fs.writeFileSync(path.join(out,'rendered-login.html'),dom);
 result={passed:true,checks,mouseEvents:0,activation:'CDP keyboard Enter; no mouse events or DOM click calls',input:'dummy values assigned to native exported form controls with input/change events',htmlModified:false,network:'local HTTP only; external URLs blocked in test',profile,outputDirectory:out,screenshots,exceptions};
}catch(e){result={passed:false,error:String(e),checks,profile,outputDirectory:out,screenshots,exceptions};}
finally{
 if(recording){await pause(1500);capturing=false;await captureLoop;}
 if(send){try{await send('Browser.close');}catch{browser.kill();}}
 else browser.kill();
 socket?.close();server.close();fs.closeSync(log);
}
if(recording&&frames.length){
 const list=frames.map((f,i)=>`file '${f.file.replaceAll('\\','/')}'\nduration ${Math.max(.01,(frames[i+1]?.seconds??f.seconds+.2)-f.seconds).toFixed(3)}`).join('\n')+`\nfile '${frames.at(-1).file.replaceAll('\\','/')}'\n`;
 fs.writeFileSync(path.join(frameDir,'frames.txt'),list);
 const stamp=s=>{const ms=Math.round(s*1000);return `${String(Math.floor(ms/3600000)).padStart(2,'0')}:${String(Math.floor(ms/60000)%60).padStart(2,'0')}:${String(Math.floor(ms/1000)%60).padStart(2,'0')},${String(ms%1000).padStart(3,'0')}`;};
 const last=frames.at(-1).seconds+.2;
 const cues=captions.filter((c,i)=>!captions[i+1]||captions[i+1].seconds-c.seconds>.15);
 fs.writeFileSync(path.join(out,'browser-captions.srt'),cues.map((c,i)=>`${i+1}\n${stamp(c.seconds)} --> ${stamp(cues[i+1]?.seconds??last)}\n${c.text}\n`).join('\n'));
 const ffmpeg=process.env.REVERSE_CLI_FFMPEG||path.resolve(root,'../capcut-cli/.native-tools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe');
 const video=path.join(out,'browser-interaction-'+Date.now()+'.mp4');
 const vf="scale=1920:1166:force_original_aspect_ratio=decrease,pad=1920:1280:(ow-iw)/2:0:color=0x111827,subtitles=browser-captions.srt:force_style='FontName=Consolas,FontSize=16,PrimaryColour=&HFFFFFF,Alignment=2,MarginV=15'";
 const encoder=spawn(ffmpeg,['-hide_banner','-loglevel','warning','-n','-f','concat','-safe','0','-i',path.join(frameDir,'frames.txt'),'-vf',vf,'-r','15','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',video],{cwd:out,windowsHide:true,stdio:['ignore','ignore','pipe'],env:{...process.env,TEMP:'D:/Caches/Axure/Temp',TMP:'D:/Caches/Axure/Temp'}});
 let errors='';encoder.stderr.on('data',b=>errors+=b.toString());const code=await new Promise(resolve=>encoder.on('exit',resolve));
 if(code!==0){result.passed=false;result.recordingError=errors;}else result.video=video;
 result.captureFrames=frames.length;result.captions=captions;result.frameCache=frameDir;
}
fs.writeFileSync(path.join(out,'browser-acceptance.json'),JSON.stringify(result,null,2));
fs.writeFileSync(process.env.AXURE_BROWSER_EVIDENCE||path.join(root,'evidence/native-login-browser.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify({passed:result.passed,checks:checks.length,error:result.error,screenshots}));
process.exitCode=result.passed?0:1;
