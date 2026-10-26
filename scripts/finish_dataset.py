"""Compress selected previews and validate published GLBs against the selection manifest."""
from pathlib import Path
import json,struct
from PIL import Image
root=Path(__file__).resolve().parents[1];data=json.loads((root/'public/data/dataset.json').read_text());out=root/'public/media/dataset';out.mkdir(parents=True,exist_ok=True)
report=[]
for a in data['assets']:
 src=Path('/tmp/rfw-dataset')/(a['id']+'.png');Image.open(src).convert('RGB').save(out/(a['id']+'.webp'),quality=88)
 b=(root/'public'/a['model']).read_bytes();size=struct.unpack_from('<I',b,12)[0];g=json.loads(b[20:20+size]);joint_names={n.get('extras',{}).get('rfw_joint') for n in g['nodes'] if n.get('extras',{}).get('rfw_joint')}
 assert joint_names=={j['name'] for j in a['joints']},a['id']
 exported={n['extras']['rfw_joint']:n['extras'] for n in g['nodes'] if n.get('extras',{}).get('rfw_joint')}
 for j in a['joints']:
  e=exported[j['name']]
  assert e['rfw_type']==j['type'] and e['rfw_axis']==j['axis'],(a['id'],j['name'])
  if j['type']!='continuous':
   assert abs(e['rfw_lower']-j['lower'])<1e-6 and abs(e['rfw_upper']-j['upper'])<1e-6,(a['id'],j['name'])
 assert not g.get('animations'), 'Do not imply simulated motion for static URDF exports'
 audit=json.loads((Path('/tmp/rfw-dataset')/(a['id']+'.audit.json')).read_text());assert not audit['missing_textures'],a['id']
 report.append({'id':a['id'],'joints':len(joint_names),'bytes':len(b),'thumbnailBytes':(out/(a['id']+'.webp')).stat().st_size,'meshObjects':audit['mesh_objects']})
Path('/tmp/rfw-dataset/export-validation.json').write_text(json.dumps(report,indent=2))
print(f'{len(report)} models preserve joint identities; no missing source textures; previews compressed.')
print('Total preview bytes:',sum(r['thumbnailBytes'] for r in report),'model bytes:',sum(r['bytes'] for r in report))
