"""Validate freshly authored bilingual cues and emit native import JSON + SRT.

Translation is authored by the current agent after reading the current ASR.
This tool validates/formats that translation; it does not claim to translate.
"""
import argparse
import json
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args()
    rows=json.loads(a.input.read_text(encoding='utf8'))
    cues=[]
    for i,row in enumerate(rows):
        start=round(round(row['startSeconds']*30)*1000000/30)
        end=min(33700000,round(round(row['endSeconds']*30)*1000000/30))
        if not (0<=start<end<=33700000) or cues and cues[-1]['endUs']>start:
            raise ValueError(f'Invalid caption interval {i}')
        if not row['chinese'].strip() or not row['english'].strip(): raise ValueError('Empty caption')
        cues.append({'id':f'fresh-{i+1:02}','startUs':start,'endUs':end,
                     'text':row['chinese']+'\n'+row['english']})
    if a.output.exists(): raise FileExistsError(a.output)
    a.output.write_text(json.dumps({'timebase':'timeline_us','cues':cues},ensure_ascii=False,indent=2),encoding='utf8')
    def stamp(us):
        ms=round(us/1000); s,ms=divmod(ms,1000); m,s=divmod(s,60); h,m=divmod(m,60)
        return f'{h:02}:{m:02}:{s:02},{ms:03}'
    a.output.with_suffix('.srt').write_text('\n\n'.join(f"{i+1}\n{stamp(c['startUs'])} --> {stamp(c['endUs'])}\n{c['text']}" for i,c in enumerate(cues))+'\n',encoding='utf8')
    print(json.dumps({'ok':True,'freshBilingualCues':len(cues),'output':str(a.output)}))

if __name__ == '__main__': main()
