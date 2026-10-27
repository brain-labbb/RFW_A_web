"""Update published MJCF contact filters without rebuilding meshes or annotations."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import mujoco
from explorer_collision import add_adjacent_exclusions

root = Path(__file__).resolve().parents[1] / 'public'
manifest = json.loads((root / 'data/explorer.json').read_text())
for asset in manifest['assets']:
    path = root / asset['simulation']
    tree = ET.parse(path)
    model = mujoco.MjModel.from_xml_path(str(path))
    record = add_adjacent_exclusions(tree.getroot(), model)
    xml = ET.tostring(tree.getroot(), encoding='unicode')
    mujoco.MjModel.from_xml_string(xml)
    path.write_text(xml)
    path = root / asset['details']
    details = json.loads(path.read_text())
    details['simulation']['collisionFilter'] = record
    path.write_text(json.dumps(details, separators=(',', ':')))
print('Applied adjacent-group filtering to', len(manifest['assets']), 'models')
