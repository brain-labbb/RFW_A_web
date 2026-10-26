import subprocess,concurrent.futures,queue,os,json,sys
from pathlib import Path
p=Path('/tmp/rfw-scenes');q=queue.Queue();mode=sys.argv[1]
for s in ['indoor','outdoor','space','laboratory']:
 for i in range(3):q.put((s,i))
def worker(gpu):
 while True:
  try:s,i=q.get_nowait()
  except queue.Empty:return
  env=os.environ.copy();env['CUDA_VISIBLE_DEVICES']=str(gpu)
  with (p/f'{s}-{i}-{mode}.log').open('w') as log:
   r=subprocess.run(['/tmp/blender-5.2.2-linux-x64/blender','--background','--python',str(Path(__file__).parent/'render_scene_shots.py'),'--',s,str(i),mode],env=env,stdout=log,stderr=subprocess.STDOUT)
  if r.returncode or 'RENDERED' not in (p/f'{s}-{i}-{mode}.log').read_text():raise RuntimeError(f'{s}/{i} render failed')
  print('GPU',gpu,s,i,mode,'exit',r.returncode,flush=True);q.task_done()
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as e:list(e.map(worker,range(8)))
