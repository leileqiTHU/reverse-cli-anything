"""Create the small synthetic integration fixtures; never overwrite user media."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from capcut_media import DECODER
from PIL import Image, ImageDraw, ImageFont

def main():
    target = ROOT / 'capcut-test-media'
    target.mkdir(exist_ok=True)
    paths = [target / f'card-{c}.png' for c in 'ABC'] + [target / 'live-edit-test.mp4']
    if all(p.exists() for p in paths):
        print(json.dumps({'created':False,'reason':'All fixtures already exist','directory':str(target)}))
        return
    if any(p.exists() for p in paths):
        raise RuntimeError('Partial fixtures exist; inspect them before generating replacements')
    if not DECODER.is_file():
        raise RuntimeError('Install .native-tools dependencies before generating fixtures')
    try:
        font = ImageFont.truetype('arial.ttf',220)
    except OSError:
        font = ImageFont.load_default(size=220)
    for label,color,path in zip('ABC',('#176b78','#7449a3','#b86828'),paths):
        img=Image.new('RGB',(1280,720),color)
        ImageDraw.Draw(img).text((640,360),label,fill='white',font=font,anchor='mm')
        img.save(path)
    temp=ROOT/'.runtime/fixture-generation'
    temp.mkdir(parents=True,exist_ok=True)
    argv=[str(DECODER),'-hide_banner','-v','error','-n']
    for path in paths[:3]:argv+=['-loop','1','-t','3','-i',str(path)]
    argv+=['-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0,fps=30[v]',
           '-map','[v]','-c:v','libx264','-pix_fmt','yuv420p','-t','9',str(paths[3])]
    subprocess.run(argv,check=True,env=dict(os.environ,TEMP=str(temp),TMP=str(temp)))
    print(json.dumps({'created':True,'directory':str(target)}))

if __name__=='__main__':main()
