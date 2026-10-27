"""Render prepared category batches using the existing Blender installation."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
WORK=Path('/tmp/rfw-explorer')
BLENDER='/tmp/blender-5.2.2-linux-x64/blender'
(WORK/'renders').mkdir(exist_ok=True)
running={};completed=set();failed=[]
deadline=time.monotonic()+7200
while time.monotonic()<deadline:
    for category,(process,log,gpu) in list(running.items()):
        if process.poll() is not None:
            log.close();del running[category];completed.add(category)
            if process.returncode:failed.append(category)
            print('FINISHED',category,process.returncode,flush=True)
    try:manifest=json.loads((WORK/'selection-progress.json').read_text())
    except (FileNotFoundError,json.JSONDecodeError):time.sleep(2);continue
    for family in manifest['families']:
        if len(running)>=8:break
        cat=family['id']
        if cat in completed or cat in running:continue
        if all((WORK/'renders'/f'{aid}.audit.json').exists() for aid in family['samples']):
            completed.add(cat);continue
        occupied={v[2] for v in running.values()};gpu=next(i for i in range(8) if i not in occupied)
        env={**os.environ,'CUDA_VISIBLE_DEVICES':str(gpu)}
        log=(WORK/f'render-{cat}.log').open('w')
        process=subprocess.Popen([BLENDER,'-b','-t','4','--python',str(ROOT/'scripts/export_explorer.py'),'--',*family['samples']],env=env,stdout=log,stderr=subprocess.STDOUT)
        running[cat]=(process,log,gpu);print('START',cat,'GPU',gpu,flush=True)
    final=ROOT/'public/data/explorer.json'
    if final.exists() and len(completed)>=len(json.loads(final.read_text())['families']) and not running:break
    time.sleep(3)
if failed:raise RuntimeError('Rendering failed: '+', '.join(failed))
print('Rendered',len(completed),'families',flush=True)
