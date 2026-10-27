"""Apply the user's chosen display roles without changing video order.

The owner requested the current first clip per task to be Retrieved and the
remaining four to be Edited. This is a user-designated mapping, not a retrieval
lineage inferred from the original manifest's paper_representative field.
"""
import json
from pathlib import Path

ROLES = {
    'round_cabinet': ('sim_crown_molding', ['sim_seed0000', 'sim_seed0001', 'sim_strap_loop', 'sim_t_bar']),
    'folding_chair': ('sim_caret_fabric', ['sim_bistro', 'sim_garden_cafe', 'sim_kids_plastic', 'sim_sling_camping']),
    'double_door': ('sim_seed2228', ['sim_seed0002', 'sim_seed0004', 'sim_seed0049', 'sim_seed0159']),
    'toaster': ('sim_capsule_pill', ['sim_faceted_hex', 'sim_seed0000', 'sim_seed0002', 'sim_taper_trapezoid']),
    'folding_ruler': ('sim_seed0000', ['sim_seed0005', 'sim_seed0020', 'sim_seed0123', 'sim_seed0143']),
}

def apply_roles(data):
    for task in data['tasks']:
        retrieved, edited = ROLES[task['id']]
        clips = [c for c in task['videos'] if c['domain'] == 'sim']
        assert {c['id'] for c in clips} == {retrieved, *edited}, task['id']
        for clip in task['videos']:
            if clip['domain'] == 'real':
                clip['role'], clip['label'] = 'real', 'Real world'
            elif clip['id'] == retrieved:
                clip['role'], clip['label'] = 'retrieved', 'Retrieved'
            else:
                clip['role'] = 'edited'
                clip['edit_index'] = edited.index(clip['id']) + 1
                clip['label'] = f"Edited {clip['edit_index']}"
    data['display_role_source'] = 'User-designated current ordering, 2026-10-27; not inferred from paper_representative.'
    return data

if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'public/data/robotics.json'
    data = apply_roles(json.loads(path.read_text()))
    path.write_text(json.dumps(data, indent=2) + '\n')
    print('Labeled five Retrieved clips and twenty Edited clips; video order preserved.')
