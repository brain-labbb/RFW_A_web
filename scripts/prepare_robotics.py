"""Encode all 30 supplied robotics recordings; verify sources and preserve full timelines."""
import concurrent.futures, hashlib, json, subprocess
from pathlib import Path
from robotics_roles import apply_roles
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path('/opt/isaacsim/end/real_sim_final_20261014')
OUT=ROOT/'public/media/robotics';OUT.mkdir(parents=True,exist_ok=True)
AUDIT=Path('/tmp/rfw-robotics');AUDIT.mkdir(exist_ok=True)
manifest=json.loads((SOURCE/'manifest.json').read_text())
TASKS=[('round_cabinet','Cabinet','Open the cabinet door with the left arm, then close it with the right arm.'),('folding_chair','Folding chair','Fold the chair to its closed configuration.'),('double_door','Double doors','Close both doors.'),('toaster','Toaster','Push down the toaster lever.'),('folding_ruler','Folding ruler','Straighten the articulated ruler.')]
def probe(path):
 return json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height:format=duration','-of','json',str(path)]))
def encode(entry):
 src=SOURCE/entry['file'];sha=hashlib.sha256(src.read_bytes()).hexdigest();assert sha==entry['sha256'],src
 folder=OUT/entry['family'];folder.mkdir(exist_ok=True);dst=folder/src.name
 info=probe(src);speed=4 if entry['domain']=='sim' else (1 if entry['family']=='folding_chair' else 2)
 vf=f'setpts=(PTS-STARTPTS)/{speed},fps=30,setsar=1'
 commands=[['-vf',vf,'-c:v','libx264','-preset','medium','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(dst)],['-vf',vf,'-c:v','libvpx-vp9','-deadline','good','-cpu-used','4','-row-mt','1','-crf','32','-b:v','0',str(dst.with_suffix('.webm'))]]
 for options in commands:
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(src),'-an','-threads','2',*options],check=True)
 subprocess.run(['ffmpeg','-v','error','-y','-ss','0.2','-i',str(src),'-frames:v','1','-vf','scale=640:-2','-quality','85',str(dst.with_suffix('.webp'))],check=True)
 result=probe(dst);duration=float(result['format']['duration']);original=float(info['format']['duration'])
 assert abs(duration-original/speed)<.15,(src,duration,original/speed)
 assert info['streams'][0]==result['streams'][0]
 assert hashlib.sha256(src.read_bytes()).hexdigest()==sha
 relative=dst.relative_to(ROOT/'public').as_posix()
 print('ENCODED',entry['file'],f'{original:.1f}s → {duration:.1f}s ({speed}×)',flush=True)
 return {'id':src.stem,'domain':entry['domain'],'src':relative,'poster':str(Path(relative).with_suffix('.webp')),'speed':speed,'duration':duration,'source_duration':original,'source_sha256':sha,'paper_representative':entry.get('paper_representative',False),'family':entry['family']}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: clips=list(pool.map(encode,manifest['files']))
tasks=[]
for key,label,description in TASKS:
 group=[v for v in clips if v['family']==key];group.sort(key=lambda v:(v['domain']=='real',not v['paper_representative'],v['id']))
 assert len(group)==6 and sum(v['domain']=='sim' for v in group)==5
 for i,v in enumerate(group):
  v['label']=f'Simulation {i+1:02}' if v['domain']=='sim' else 'Real world'
 tasks.append({'id':key,'label':label,'description':description,'videos':group})
data={'tasks':tasks,'results':[{'setting':'Retrieval','assets':1,'edits':0,'successes':[5,7,8,7,4],'average':62},{'setting':'Retrieval + 4 Edit','assets':5,'edits':4,'successes':[7,7,8,8,6],'average':72},{'setting':'Retrieval + 9 Edit','assets':10,'edits':9,'successes':[8,8,8,9,7],'average':80}],'demonstrations_per_task':500,'trials_per_task':10}
apply_roles(data)
(ROOT/'public/data/robotics.json').write_text(json.dumps(data,indent=2)+'\n')
(AUDIT/'media-audit.json').write_text(json.dumps({'source':str(SOURCE),'count':len(clips),'clips':clips},indent=2))
print('Verified all 30 sources and encoded full-length accelerated previews.',flush=True)
