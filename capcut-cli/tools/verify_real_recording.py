"""Independent output/source acceptance; only reads project and media files."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--run-dir', type=Path, required=True)
HERE = parser.parse_args().run_dir.resolve()
OUTPUT = HERE / 'water-science-final.mp4'
sources = json.loads((HERE / 'sources.json').read_text(encoding='utf8'))
SOURCE = Path(sources['video'])
MUSIC = Path(sources['music'])
sys.path.insert(0, str(ROOT))
from capcut_export import export_content_signature
from capcut_extensions import caption_timing_matches
spec = importlib.util.spec_from_file_location('media_helpers', ROOT / 'tools/media_acceptance.py')
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)
media.ENV.update(TEMP=str(HERE/'temp'), TMP=str(HERE/'temp'))
SR = 48000

def read(name):
    return json.loads((HERE / name).read_text(encoding='utf8'))

def audio(path, start, duration):
    p = media.run(['-v','error','-xerror','-ss',str(start),'-i',str(path),'-t',str(duration),
                   '-map','0:a:0','-ar',str(SR),'-ac','2','-f','f32le','pipe:1'])
    return np.frombuffer(p.stdout,dtype='<f4').reshape(-1,2).astype(np.float64)

def frame(path, second, scale=1):
    # Native scaleX/Y is centered and expressed relative to the canvas.
    vf = 'scale=960:540' if scale == 1 else f'scale={round(1920*scale/2)*2}:{round(1080*scale/2)*2},crop=1920:1080,scale=960:540'
    p=media.run(['-v','error','-xerror','-ss',str(second),'-i',str(path),'-frames:v','1','-vf',vf,'-f','rawvideo','-pix_fmt','rgb24','pipe:1'])
    return np.frombuffer(p.stdout,dtype=np.uint8).reshape(540,960,3)

def lag(x,y):
    n=1<<((len(x)+len(y)-1).bit_length())
    cross=np.fft.irfft(np.fft.rfft(y,n)*np.conj(np.fft.rfft(x,n)),n)
    candidates=np.arange(-2048,2049)
    return int(candidates[np.argmax(cross[candidates % n])])

def words(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)?",text.lower().replace('’',"'"))

def distance(a,b):
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        row=[i]
        for j,y in enumerate(b,1):
            row.append(min(previous[j]+1,row[j-1]+1,previous[j-1]+(x!=y)))
        previous=row
    return previous[-1]

def main():
    plan,state=read('edit-plan.json'),read('project-state.json')
    tid=state['timelineId']
    after=read('28-edited.json')['result']['items']
    reopened=read('43-reopened.json')['result']['items']
    before_docs,after_docs=read('original-project-before.json'),read('original-project-after.json')
    doc=read('reopened-drafts.json')[tid]
    videos=sorted([x for x in reopened if x['type']=='video'],key=lambda x:x['targetUs']['start'])
    audios=[x for x in reopened if x['type']=='audio']
    texts=[x for x in reopened if x['type']=='text']
    expected_cues=read('captions.json')['cues']+read('credits.json')['cues']
    target_cues=sorted((x['targetUs']['start'],x['targetUs']['start']+x['targetUs']['duration'],x['properties']['text']) for x in texts)
    expected_cues=sorted((x['startUs'],x['endUs'],x['text']) for x in expected_cues)
    checks={'timelineIdentity':doc['id']==tid,
            'duration33_7Seconds':doc['duration']==plan['durationUs'],
            'threeNativeVideoClips':len(videos)==3,
            'oneNativeMusicClip':len(audios)==1,
            'freshBilingualCaptionsAndSourceCredit':len(target_cues)==len(expected_cues) and all(a[2]==b[2] and caption_timing_matches({'start':a[0],'duration':a[1]-a[0]},{'startUs':b[0],'endUs':b[1]}) for a,b in zip(target_cues,expected_cues)),
            'editableItemsSurviveCloseAndReopen':after==reopened,
            'originalUserProjectUnchanged':all(export_content_signature(d)==export_content_signature(after_docs[k]) for k,d in before_docs.items())}
    pos=0
    for i,(item,segment) in enumerate(zip(videos,plan['segments'])):
        length=segment['sourceOutUs']-segment['sourceInUs']
        checks[f'clip{i+1}NativeSourceAndTarget']=(item['sourceUs']=={'start':segment['sourceInUs'],'duration':length} and item['targetUs']=={'start':pos,'duration':length})
        pos+=length
    patch=plan['transform']['patch']['transform']
    checks['middleClipNative108PercentScale']=all(abs(videos[1]['properties']['transform'][k]-v)<1e-6 for k,v in patch.items())
    music=audios[0]
    checks['musicNativeGainSourceAndFades']=(music['targetUs']=={'start':0,'duration':plan['durationUs']}
        and music['sourceUs']=={'start':plan['music']['sourceInUs'],'duration':plan['durationUs']}
        and abs(music['properties']['volumeLinear']-10**(-22/20))<1e-8
        and music['properties']['fadeInUs']==1200000 and music['properties']['fadeOutUs']==1600000)
    rgb=media.frames(OUTPUT)
    output=media.stereo(OUTPUT).astype(np.float64)
    meta=media.metadata(OUTPUT)
    checks['newProjectStartedEmpty'] = read('03-empty.json')['result']['items'] == []
    checks['freshAsrAndChineseTranslation'] = (read('sources.json')['oldChineseCaptionsRead'] is False and read('source-asr.json')['input'] == str((HERE/'rough-cut.mp4').resolve()) and len(read('fresh-translations.json')) > 0)
    checks['1011FramesFullyDecoded']=len(rgb)==1011
    checks['1080p30H264AAC']=(any('1920x1080' in x and '30 fps' in x and 'h264' in x for x in meta['streamDescriptions']) and any('aac' in x for x in meta['streamDescriptions']))
    checks['finiteAudioNoClipping']=bool(np.isfinite(output).all() and np.max(np.abs(output))<1)
    checks['audioDurationWithinAACPadding']=abs(len(output)/SR-33.7)<.05
    checks['noBlankFrames']=bool(np.min(rgb.std(axis=(1,2,3)))>10)
    report={'checks':checks,'file':{'path':str(OUTPUT),'bytes':OUTPUT.stat().st_size,'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),**meta},
        'decode':{'frames':len(rgb),'audioSeconds':len(output)/SR,'audioPeak':float(np.max(np.abs(output))),'stateItemCount':len(reopened)}}

    source_audio=np.concatenate([audio(SOURCE,s['sourceInUs']/1e6,(s['sourceOutUs']-s['sourceInUs'])/1e6) for s in plan['segments']])
    music_audio=audio(MUSIC,20,33.7)
    mixes=[]
    # Mid-shot windows avoid the deliberate hard cuts and music fades.
    for start,end in [(1.5,7.5),(9.5,19.5),(21.5,31.5)]:
        i,j=round(start*SR),round(end*SR)
        delay=lag(source_audio[i:j,0],output[i:j,0])
        out=output[i+delay:j+delay]
        spoken=source_audio[i:j]
        # Recover music delay independently after subtracting the speech fit.
        voice_gain=np.sum(spoken*out,axis=0)/np.sum(spoken**2,axis=0)
        residual=out-spoken*voice_gain
        music_delay=lag(music_audio[i:j,0],residual[:,0])
        m=music_audio[i-music_delay:j-music_delay]
        gains=[]
        corrs=[]
        snrs=[]
        balances=[]
        for c in range(2):
            model=np.column_stack([spoken[:,c],m[:,c]])
            coeff=np.linalg.lstsq(model,out[:,c],rcond=None)[0]
            predicted=model@coeff
            gains.append(coeff.tolist())
            corrs.append(float(np.corrcoef(predicted,out[:,c])[0,1]))
            snrs.append(float(10*np.log10(np.mean(predicted**2)/np.mean((out[:,c]-predicted)**2))))
            balances.append(float(20*np.log10(np.std(spoken[:,c]*coeff[0])/np.std(m[:,c]*coeff[1]))))
        gain_db=(20*np.log10(np.abs(gains))).tolist()
        mixes.append({'windowSeconds':[start,end],'speechDelaySamples':delay,'musicRelativeDelaySamples':music_delay,
                      'gainDbPerChannelSpeechMusic':gain_db,'reconstructionCorrelation':corrs,'reconstructionSnrDb':snrs,'speechOverMusicDb':balances})
    report['audioMixMeasurements']=mixes
    checks['renderedSpeechPreserved']=all(abs(g[0])<.5 for w in mixes for g in w['gainDbPerChannelSpeechMusic'])
    checks['renderedMusicMinus22dB']=all(abs(g[1]+22)<1 for w in mixes for g in w['gainDbPerChannelSpeechMusic'])
    checks['renderedAudioMatchesRealSources']=min(c for w in mixes for c in w['reconstructionCorrelation'])>.98
    checks['speechClearlyAboveAddedMusic']=min(c for w in mixes for c in w['speechOverMusicDb'])>14

    refs=read('captions-reference.json')
    reference=' '.join(x['english'] for x in refs)
    recognized=' '.join(x['text'] for x in read('final-asr.json')['segments'])
    errors=distance(words(reference),words(recognized))
    wer=errors/len(words(reference))
    report['independentFinalSpeechRecognition']={'model':'local base.en CPU/int8','referenceWords':len(words(reference)),
        'editDistance':errors,'wordErrorRate':wer,'reference':reference,'recognized':recognized,'initialPromptUsed':False}
    checks['independentRecognitionRetainsSpeech']=wer<.10

    comparisons=[]
    for k,t in enumerate(plan['previewSeconds']):
        pos=0
        for index,s in enumerate(plan['segments']):
            duration=(s['sourceOutUs']-s['sourceInUs'])/1e6
            if pos<=t<pos+duration:
                source_time=s['sourceInUs']/1e6+t-pos
                scale=1.08 if index==1 else 1
                break
            pos+=duration
        rendered=frame(OUTPUT,t)
        expected=frame(SOURCE,round(source_time*30)/30,scale)
        # Bottom captions and top credits are intentionally different.
        a,b=rendered[55:410].astype(np.float32),expected[55:410].astype(np.float32)
        mae=float(np.mean(np.abs(a-b)))
        corr=float(np.corrcoef(a.ravel(),b.ravel())[0,1])
        native=np.asarray(Image.open(HERE/f'native-{t}s.png').convert('RGB').resize((960,540)))
        native_mae=float(np.mean(np.abs(native.astype(np.float32)-rendered.astype(np.float32))))
        comparisons.append({'outputSeconds':t,'sourceSeconds':source_time,'scale':scale,'contentMae':mae,'contentCorrelation':corr,'nativeFrameVsExportMae':native_mae})
    canvas=Image.new('RGB',(1920,1740),'#151515')
    draw=ImageDraw.Draw(canvas)
    for k,t in enumerate(plan['previewSeconds']):
        img=Image.fromarray(frame(OUTPUT,t))
        x,y=(k%2)*960,(k//2)*580
        canvas.paste(img,(x,y+36))
        draw.text((x+14,y+10),f'CapCut native MP4: {t}s',fill='white')
    canvas.save(HERE/'final-contact-sheet.jpg',quality=95)
    report['frameCorrespondence']=comparisons
    checks['sampledFramesMatchSelectedSourceAndTransform']=all(x['contentMae']<12 and x['contentCorrelation']>.97 for x in comparisons)
    checks['nativeTimelineFramesMatchExport']=all(x['nativeFrameVsExportMae']<10 for x in comparisons)
    report['limitations']=['ASR comparison is evidence of speech preservation, not a human listening claim.', 'Visual correspondence and subtitle legibility are sampled; full video and audio were decoded.', 'Encoder and renderer resampling may introduce small PCM or pixel differences.', 'No source JSON rewriting or UI click/key events were used for editing; CapCut remained the native editor and renderer.']
    report['passed']=all(checks.values())
    (HERE/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps({'passed':report['passed'],'checks':checks,'mixes':mixes,'wer':wer,'frames':comparisons},ensure_ascii=False),flush=True)
    if not report['passed']:
        raise SystemExit(1)

if __name__=='__main__':
    main()
