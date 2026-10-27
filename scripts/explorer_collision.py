"""Keep adjacent rigid groups out of self-contact, including a fixed base.

MuJoCo normally filters parent/child contacts, except when the parent is welded
to world. Explicit pairs extend the same policy to the fixed-base inspector.
Nonadjacent bodies retain their original contact geometry and masks.
"""
import xml.etree.ElementTree as ET
import mujoco

VERSION = 'adjacent-rigid-groups-v1'
DESCRIPTION = 'Self-contact excluded between directly connected rigid groups, including the fixed base; nonadjacent contacts retained'


def add_adjacent_exclusions(root, model):
    contact = root.find('contact')
    if contact is None:
        contact = ET.SubElement(root, 'contact')
    existing = {frozenset((e.get('body1'), e.get('body2'))) for e in contact.findall('exclude')}
    bodies = sorted(set(int(b) for b in model.geom_bodyid))
    pairs = []
    for i, first in enumerate(bodies):
        for second in bodies[i+1:]:
            a, b = int(model.body_weldid[first]), int(model.body_weldid[second])
            if a == b:
                continue
            adjacent = ((a and int(model.body_weldid[model.body_parentid[a]]) == b)
                        or (b and int(model.body_weldid[model.body_parentid[b]]) == a))
            if not adjacent:
                continue
            names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, n) for n in (first, second)]
            pairs.append(names)
            if frozenset(names) not in existing:
                ET.SubElement(contact, 'exclude', body1=names[0], body2=names[1])
                existing.add(frozenset(names))
    return dict(version=VERSION, description=DESCRIPTION, excludedPairs=pairs)
