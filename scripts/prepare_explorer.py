"""Curate image-grounded generator families directly from PV_A_vlm (read-only).

Input lineage is checked against source maps and the exact generator hash; source
maps may cite the picture library under its historical picture/, pictureX/ or
pictureY/ roots, and some categories are filed under a different lineage slug
(LINEAGE_KEYS). Record-derived categories documented by a modular spec use the
matching picture subclass folder with the spec recorded as evidence (SPEC_LINEAGE).
All temporary metadata and source copies live in /tmp/rfw-explorer, never the release.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import re
import shutil
import xml.etree.ElementTree as ET
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/data/oss_bucket_0/yuanbo/PV_A_vlm/assets')
ART = Path('/home/lyuyuanbo.lyb/PVA/articraft_data')
TEMPLATES = Path('/home/lyuyuanbo.lyb/PVA/arti-template')
WORK = Path('/tmp/rfw-explorer')
CACHE = WORK / 'source'
EXCLUSIONS = json.loads((ROOT / 'scripts/explorer_exclusions.json').read_text())
SELECTION = [
    ('Handtools_Clamp', 'Screw clamps', 'Tools'),
    ('Handtools_dial_caliper', 'Calipers', 'Tools'),
    ('pictureX_0611_Air_blower', 'Air blowers', 'Tools'),
    ('sewing_machine', 'Sewing machines', 'Home'),
    ('watch', 'Watches', 'Everyday'),
    ('pictureX_0611_compass', 'Compasses', 'Outdoor'),
    ('Parts_quick_release_clamp', 'Quick-release clamps', 'Tools'),
    ('Music_Headphone', 'Headphones', 'Electronics'),
    ('Music_Amplifier', 'Amplifiers', 'Electronics'),
    ('Technology_Audio_Device', 'Audio devices', 'Electronics'),
    ('Music_keyboard', 'Keyboards', 'Electronics'),
    ('universal_joint', 'Universal joints', 'Tools'),
    ('Technology_Flashlight', 'Flashlights', 'Electronics'),
    ('Astronomy_Astronaut_helmet', 'Astronaut helmets', 'Outdoor'),
    ('Accessories_glasses', 'Glasses', 'Everyday'),
    ('Bag_Suitcase_Suitcase', 'Suitcases', 'Everyday'),
    ('Astronomy_Return_capsule', 'Return capsules', 'Outdoor'),
    ('Container_Lipstick', 'Lipsticks', 'Everyday'),
    ('Container_Dispenser', 'Dispensers', 'Everyday'),
    ('Other_Tripod_Turnstile', 'Tripod turnstiles', 'Everyday'),
    ('Sports_Carabiner', 'Carabiners', 'Outdoor'),
    ('Sports_Roller_scates', 'Roller skates', 'Outdoor'),
    ('Sports_Skateboard', 'Skateboards', 'Outdoor'),
    ('pictureX_0611_full_height_turnstile', 'Full-height turnstiles', 'Everyday'),
    ('Equipment_Lock', 'Locks', 'Everyday'),
    ('Equipment_LED_work_light', 'Work lights', 'Tools'),
    ('Others_Binocular', 'Binoculars', 'Outdoor'),
    ('Other_Folding_screen', 'Folding screens', 'Home'),
    ('Military_helicopter', 'Helicopters', 'Outdoor'),
    ('Light_Latern', 'Lanterns', 'Outdoor'),
    ('Urban_Environment_Tilt_Truck', 'Tilt trucks', 'Tools'),
    ('Kitchen_Corkscrew', 'Corkscrews', 'Tools'),
    ('Handtools_clothes_peg', 'Clothes pegs', 'Everyday'),
    ('Equipment_Power_switch', 'Power switches', 'Electronics'),
    ('Container_Gas_cylinder', 'Gas cylinders', 'Tools'),
    ('Container_Locker', 'Lockers', 'Home'),
    ('Other_Scale', 'Scales', 'Everyday'),
    ('Bag_Suitcase_Box', 'Storage boxes', 'Home'),
    ('Container_Cosmetic', 'Cosmetic cases', 'Everyday'),
    ('Others_Safe', 'Safes', 'Home'),
    ('Equipment_Control_panel', 'Control panels', 'Electronics'),
    ('Sports_Scooter_Racer', 'Scooters', 'Outdoor'),
]

# Combined families: one published family drawing a fixed quota of seeds from
# several source categories (asset ids keep their source category prefix).
MERGED = {'Urban_Environment_Tilt_Truck': [('Urban_Environment_Tilt_Truck1', 2), ('Urban_Environment_Tilt_Truck2', 4)]}
# Categories whose picture-library folder and source-map docs are filed under a
# different slug than the PV_A_vlm category (pictureX/pictureY expansions and
# record-derived categories).
LINEAGE_KEYS = {
    'pictureX_0611_Air_blower': '0611airblower',
    'pictureX_0611_compass': '0611compass',
    'pictureX_0611_full_height_turnstile': '0611fullheightturnstile',
    'watch': '0611watch',
    'sewing_machine': 'textilesfabricsewingmachine',
    'universal_joint': '0611universaljoint',
}
# Record-derived categories documented by a modular spec instead of a source
# map; the input image comes from the picture subclass folder of the same name
# and the spec is recorded as the lineage evidence.
SPEC_LINEAGE = {'Astronomy_Astronaut_helmet', 'Astronomy_Return_capsule', 'Military_helicopter', 'universal_joint'}
# Seeds are filtered by exact generator hash before the 24-sample spread when
# only a minority of on-disk seeds still match the current template.
FILTER_FIRST = {'pictureX_0611_compass'}
# Source maps cite the same picture library under its historical roots.
PICTURE_ROOTS = ['picture/', 'pictureX/', 'pictureY/']


def norm(value):
    return re.sub('[^a-z0-9]', '', value.lower())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def numbers(value, default='0 0 0'):
    return list(map(float, (value or default).split()))


def read_metadata(job):
    category, seed = job
    dest = CACHE / category / seed
    dest.mkdir(parents=True, exist_ok=True)
    for name in ['model.urdf', 'appearance.json', 'part_physics.json', 'affordance/affordance_annot.json']:
        target = dest / name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copyfile(SOURCE / category / seed / name, target)
            except FileNotFoundError:
                print('SKIP incomplete source',category,seed,name,flush=True)
                return None
    xml = ET.parse(dest / 'model.urdf').getroot()
    appearance = json.loads((dest / 'appearance.json').read_text())
    links = xml.findall('link')
    joints = [j for j in xml.findall('joint') if j.get('type') != 'fixed']
    surfaces = [(l.get('name'), v.get('name')) for l in links for v in l.findall('visual')]
    signature = set('p:' + l.get('name') for l in links)
    signature.update('v:' + str(v) for _, v in surfaces)
    signature.update('j:' + j.get('name') + ':' + j.get('type') for j in joints)
    signature.update('m:' + str(b.get('material_class_id')) for b in appearance['bindings'])
    return dict(category=category, seed=int(seed.removeprefix('seed_')), directory=dest,
                xml=xml, appearance=appearance, signature=signature, surfaces=surfaces,
                links=len(links), jointCount=len(joints))


def distance(a, b):
    union = a['signature'] | b['signature']
    return 1 - len(a['signature'] & b['signature']) / max(1, len(union)) + abs(a['jointCount'] - b['jointCount']) * .05


def publish_sample(row, name, domain):
    directory, xml, appearance = row['directory'], row['xml'], row['appearance']
    category, seed = row['category'], row['seed']
    asset_id = f'{category}__{seed:04d}'
    physics = json.loads((directory / 'part_physics.json').read_text())
    affordances = json.loads((directory / 'affordance/affordance_annot.json').read_text())['affordances']
    annotations = {}
    for entry in affordances:
        annotations.setdefault(norm(entry['part_name']), []).append(entry)
    bindings = {b['surface_key']: b for b in appearance['bindings']}
    joints = []
    for joint in xml.findall('joint'):
        limit, axis, dynamics, mimic = (joint.find(t) for t in ['limit', 'axis', 'dynamics', 'mimic'])
        if joint.get('type') == 'fixed':
            continue
        item = dict(name=joint.get('name'), type=joint.get('type'),
                    parent=joint.find('parent').get('link'), child=joint.find('child').get('link'),
                    axis=numbers(axis.get('xyz') if axis is not None else '1 0 0'))
        for field in ['lower', 'upper', 'effort', 'velocity']:
            item[field] = float(limit.get(field)) if limit is not None and limit.get(field) is not None else None
        for field in ['damping', 'friction']:
            item[field] = float(dynamics.get(field)) if dynamics is not None and dynamics.get(field) is not None else None
        if mimic is not None:
            item['mimic'] = dict(joint=mimic.get('joint'), multiplier=float(mimic.get('multiplier', 1)), offset=float(mimic.get('offset', 0)))
        joints.append(item)
    parts, links = [], []
    for link in xml.findall('link'):
        inertial = link.find('inertial')
        mass = inertial.find('mass') if inertial is not None else None
        tensor = inertial.find('inertia') if inertial is not None else None
        origin = inertial.find('origin') if inertial is not None else None
        links.append(dict(name=link.get('name'), massKg=float(mass.get('value')) if mass is not None else None,
                          inertia={k:float(v) for k,v in tensor.attrib.items()} if tensor is not None else None,
                          centerOfMass=numbers(origin.get('xyz')) if origin is not None else None,
                          inertialRotation=numbers(origin.get('rpy')) if origin is not None else None))
        for visual in link.findall('visual'):
            vname = visual.get('name', '')
            matches = annotations.get(norm(vname), [])
            annotation = matches[0] if len(matches) == 1 else None
            record = physics['parts'].get(str(annotation['id'])) if annotation else None
            key = link.get('name') + '::' + vname
            binding = bindings.get(key, {})
            parts.append(dict(id=key, name=vname.replace('_', ' '), link=link.get('name'),
                              annotationId=annotation['id'] if annotation else None, materialClass=binding.get('material_class_id'),
                              physics=record, description=annotation.get('Basic_description', '') if annotation else '',
                              function=annotation.get('Functional_description', '') if annotation else ''))
    details = dict(id=asset_id, parts=parts, links=links, joints=joints,
                   sourceAnnotations=affordances,
                   massSummary={k:physics.get(k) for k in ['total_mass','composed_mass','mass_ratio','mass_check','mass_policy','mass_source']},
                   sources=['model.urdf', 'appearance.json', 'part_physics.json', 'affordance/affordance_annot.json'])
    target = ROOT / 'public/data/explorer' / f'{asset_id}.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(details, separators=(',', ':')))
    # Copy only referenced assets to temporary storage for offline exports.
    paths = {m.get('filename') for m in xml.findall('.//mesh')}
    for binding in appearance['bindings']:
        channels = (binding.get('appearance') or {}).get('channels') or {}
        paths.update(c['path'] for c in channels.values() if isinstance(c, dict) and c.get('kind') == 'texture' and c.get('path'))
    def copy(relative):
        target = directory / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / category / directory.name / relative, target)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(copy, sorted(paths)))
    return dict(id=asset_id, category=category, name=name, domain=domain, seed=seed,
                templateHash=appearance['template_sha256'], urdfHash=digest((directory/'model.urdf').read_bytes()),
                links=row['links'], surfaces=len(parts), joints=joints,
                materialClasses=sorted({b.get('material_class_id') for b in appearance['bindings'] if b.get('material_class_id')}),
                sourceBindings=len(appearance['bindings']), sourceRelative=f'{category}/{directory.name}',
                model=f'models/explorer/{asset_id}.glb', image=f'media/explorer/{asset_id}.webp',
                details=f'data/explorer/{asset_id}.json', simulation=f'data/explorer/{asset_id}.xml')


def main():
    WORK.mkdir(exist_ok=True)
    docs = {}
    for folder in [ART/'picture_expansion/template_source_maps', TEMPLATES/'articraft_template_authoring/picture_source_maps', TEMPLATES/'articraft_template_authoring/specs_modular_v1']:
        for path in folder.glob('*.md'):
            docs.setdefault(norm(path.stem), []).append(path)
    picture_groups = {}
    for path in (ART/'picture').rglob('*'):
        if path.suffix.lower() in ['.png','.jpg','.jpeg','.webp']:
            picture_groups.setdefault(norm(str(path.parent.relative_to(ART/'picture'))), []).append(path)

    def lineage_images(category):
        key = LINEAGE_KEYS.get(category, norm(category))
        doc_paths = docs.get(norm(category), []) + ([] if key == norm(category) else docs.get(key, []))
        texts = [(p, p.read_text()) for p in doc_paths]
        images = []
        for picture in sorted(picture_groups.get(key, [])):
            relative = picture.relative_to(ART).as_posix()
            evidence = [str(p) for p, text in texts
                        if any(relative.replace('picture/', root, 1) in text for root in PICTURE_ROOTS)]
            basis = 'source map cites the image path'
            if not evidence and category in SPEC_LINEAGE:
                evidence = [str(p) for p, _ in texts]
                basis = 'record-derived category; input from the matching picture subclass folder, lineage recorded in the modular spec'
            if not evidence:
                continue
            out = f'media/explorer/inputs/{category}-{picture.stem}.webp'
            target = ROOT / 'public' / out
            target.parent.mkdir(parents=True, exist_ok=True)
            im = ImageOps.exif_transpose(Image.open(picture)).convert('RGB')
            im.thumbnail((800, 800)); im.save(target, quality=90)
            images.append(dict(image=out, source=relative))
            audit.append(dict(category=category, input=relative, inputSha256=digest(picture.read_bytes()),
                              evidence=evidence, basis=basis))
        return images

    def candidates_for(category):
        seeds = sorted(s for s in os.listdir(SOURCE/category) if s.startswith('seed_'))
        local_hash = digest((TEMPLATES/'agent/templates'/f'{category}.py').read_bytes())
        if category in FILTER_FIRST:
            def current(seed):
                try:
                    return json.loads((SOURCE/category/seed/'appearance.json').read_text()).get('template_sha256') == local_hash
                except (FileNotFoundError, json.JSONDecodeError):
                    return False
            seeds = [s for s in seeds if current(s)]
        sample_indices = sorted({round(i*(len(seeds)-1)/23) for i in range(24)})
        jobs = [(category, seeds[i]) for i in sample_indices]
        with ThreadPoolExecutor(max_workers=12) as pool:
            candidates = list(pool.map(read_metadata, jobs))
        candidates = [c for c in candidates if c and c['appearance']['template_sha256'] == local_hash]
        # Withdrawn samples leave the pool before diversity selection so quotas stay filled.
        candidates = [c for c in candidates if f"{c['category']}__{c['seed']:04d}" not in EXCLUSIONS['samples']]
        return seeds, local_hash, candidates

    def select_diverse(candidates, count):
        selected = [candidates[0]]
        while len(selected) < count:
            remaining = [c for c in candidates if c not in selected]
            selected.append(max(remaining, key=lambda c: min(distance(c, s) for s in selected)))
        return selected

    families, assets, audit = [], [], []
    for category, name, domain in SELECTION:
        if len(families) == 30:
            break
        if category in EXCLUSIONS['categories']:
            continue
        if category in MERGED:
            members, images, hashes, available = [], [], {}, {}
            for source, quota in MERGED[category]:
                images.extend(lineage_images(source))
                seeds, local_hash, candidates = candidates_for(source)
                if len(candidates) < quota:
                    raise ValueError(f'{source}: fewer than {quota} exact generator matches')
                with ThreadPoolExecutor(max_workers=3) as pool:
                    members.extend(pool.map(lambda c: publish_sample(c, name, domain), select_diverse(candidates, quota)))
                hashes[source] = local_hash
                available[source] = len(seeds)
            if not images:
                raise ValueError('No verified input for '+category)
            assets.extend(members)
            families.append(dict(id=category, name=name, domain=domain, inputs=images,
                                 templateHash=hashes[MERGED[category][0][0]], templateHashes=hashes,
                                 samples=[a['id'] for a in members], availableSeeds=available))
            print('READY', category, [a['id'] for a in members], flush=True)
            (WORK/'selection-progress.json').write_text(json.dumps(dict(families=families, assets=assets)))
            continue
        images = lineage_images(category)
        if not images:
            raise ValueError('No verified input for '+category)
        seeds, local_hash, candidates = candidates_for(category)
        if len(candidates) < 6:
            print('SKIP',category,'fewer than six exact generator matches',flush=True)
            continue
        selected = select_diverse(candidates, 6)
        with ThreadPoolExecutor(max_workers=3) as pool:
            members = list(pool.map(lambda c:publish_sample(c,name,domain), selected))
        assets.extend(members)
        families.append(dict(id=category, name=name, domain=domain, inputs=images,
                             templateHash=local_hash, samples=[a['id'] for a in members],
                             availableSeeds=len(seeds)))
        print('READY', category, [a['seed'] for a in members], flush=True)
        (WORK/'selection-progress.json').write_text(json.dumps(dict(families=families, assets=assets)))
    expected = {'Handtools_Clamp', 'Handtools_dial_caliper', 'pictureX_0611_Air_blower',
                'sewing_machine', 'watch', 'pictureX_0611_compass', 'Music_Headphone', 'Music_Amplifier',
                'Technology_Audio_Device', 'Music_keyboard', 'universal_joint', 'Technology_Flashlight',
                'Astronomy_Astronaut_helmet', 'Accessories_glasses', 'Bag_Suitcase_Suitcase',
                'Astronomy_Return_capsule', 'Container_Lipstick', 'Container_Dispenser', 'Other_Tripod_Turnstile',
                'Sports_Carabiner', 'Sports_Roller_scates', 'Sports_Skateboard', 'pictureX_0611_full_height_turnstile',
                'Equipment_Lock', 'Equipment_LED_work_light', 'Others_Binocular', 'Other_Folding_screen',
                'Military_helicopter', 'Light_Latern', 'Urban_Environment_Tilt_Truck'}
    chosen = {f['id'] for f in families}
    if len(families) != 30 or chosen != expected:
        raise SystemExit(f'Unexpected selection: {len(families)} families, missing {sorted(expected - chosen)}, extra {sorted(chosen - expected)}')
    manifest = dict(release=dict(assets=402410,categories=531), families=families, assets=assets,
                    source='PV_A_vlm/assets', scope='Curated image-grounded generator families')
    (ROOT/'public/data/explorer.json').write_text(json.dumps(manifest, indent=2))
    (WORK/'input-lineage.json').write_text(json.dumps(audit, indent=2))
    print('Selected', len(families), 'families /', len(assets), 'samples', flush=True)


if __name__ == '__main__':
    main()
