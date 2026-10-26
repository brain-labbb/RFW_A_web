"""Add portable WebM versions without rerendering or changing the source media."""
from pathlib import Path
import subprocess,concurrent.futures
root=Path(__file__).resolve().parents[1]/'public/media'
def encode(p):
 out=p.with_suffix('.webm')
 if out.exists() and out.stat().st_size>1000:return
 subprocess.run(['ffmpeg','-y','-i',str(p),'-vf','scale=min(1280\\,iw):-2','-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','6','-row-mt','1','-threads','4','-crf','35','-b:v','0','-c:a','libopus','-b:a','96k',str(out)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
 print('ENCODED',p.name,round(out.stat().st_size/1e6,2),'MB',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(encode,[p for p in root.glob('*.mp4') if p.stem!='asset-wall']))
