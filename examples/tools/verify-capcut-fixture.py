"""Independent visibility/audio check for the two-second synthetic regression only."""
import argparse,json,math,struct,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from reverse_cli.config import ffmpeg
from reverse_cli.journal import write

def verify(path):
    decoder=str(ffmpeg());checks=[]
    # Six saturated color bars contain no bright neutral pixels in this caption
    # region. Both supplied white captions must add many such pixels. This is
    # a fixture assertion, not OCR or a validator for arbitrary source media.
    for label,at in [('English',.5),('Chinese',1.5)]:
        p=subprocess.run([decoder,'-v','error','-ss',str(at),'-i',str(path),'-frames:v','1','-vf','crop=iw:ih/4:0:3*ih/4','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,timeout=30)
        data=p.stdout;count=sum(min(data[i:i+3])>200 and max(data[i:i+3])-min(data[i:i+3])<35 for i in range(0,len(data),3))
        checks.append({'name':label+' caption pixels in saturated fixture','passed':p.returncode==0 and count>2500,'brightNeutralPixels':count})
    p=subprocess.run([decoder,'-v','error','-i',str(path),'-vn','-ac','1','-ar','48000','-f','f32le','-'],capture_output=True,timeout=30)
    samples=[x[0] for x in struct.iter_unpack('<f',p.stdout)];rms=math.sqrt(sum(x*x for x in samples)/len(samples)) if samples else 0
    checks.append({'name':'decoded audio has nonzero energy','passed':p.returncode==0 and rms>.001,'rms':rms})
    return {'passed':all(c['passed'] for c in checks),'checks':checks,'scope':'Only the generated two-second color-bar fixture with white English/Chinese captions. Pixel presence is not general OCR; RMS does not identify musical content.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    r=verify(a.input);write(a.report,r);print(json.dumps(r));raise SystemExit(0 if r['passed'] else 1)
