"""Schedule native camera renders on eight GPUs, resuming complete frame sets."""
import subprocess,concurrent.futures,queue,os,json,sys
from pathlib import Path
p=Path('/tmp/rfw-scenes');p.mkdir(exist_ok=True);q=queue.Queue();mode=sys.argv[1]
assert mode in ['preview','final']
for sid,shots in json.loads((Path(__file__).parent/'scene_shots.json').read_text()).items():
 for i,a in enumerate(shots):
  if mode=='final' and all((p/'final-frames'/a['id']/f'{f:04d}.png').exists() for f in range(120)):continue
  q.put((sid,i))
def worker(gpu):
 while True:
  try:sid,i=q.get_nowait()
  except queue.Empty:return
  env=os.environ.copy();env['CUDA_VISIBLE_DEVICES']=str(gpu);logfile=p/f'{sid}-{i}-{mode}.log'
  with logfile.open('w') as log:
   r=subprocess.run(['/tmp/blender-5.2.2-linux-x64/blender','--background','--python',str(Path(__file__).parent/'render_scene_shots.py'),'--',sid,str(i),mode],env=env,stdout=log,stderr=subprocess.STDOUT)
  if r.returncode or 'RENDERED' not in logfile.read_text():raise RuntimeError(f'{sid}/{i} render failed; see {logfile}')
  print('GPU',gpu,sid,i,mode,'exit',r.returncode,flush=True);q.task_done()
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as e:list(e.map(worker,range(8)))
