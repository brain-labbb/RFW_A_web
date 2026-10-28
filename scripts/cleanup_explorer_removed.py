"""Remove published explorer files that are not referenced by the current manifest."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEW = json.loads((ROOT / 'public/data/explorer.json').read_text())
keep_assets = {a['id'] for a in NEW['assets']}
keep_inputs = {i['image'].rsplit('/', 1)[-1] for f in NEW['families'] for i in f['inputs']}

targets = []
for folder, suffixes in [('data/explorer', ('.json', '.xml')), ('models/explorer', ('.glb',)), ('media/explorer', ('.webp',))]:
    for path in (ROOT / 'public' / folder).iterdir():
        if path.suffix in suffixes and path.stem not in keep_assets:
            targets.append(path)
for path in (ROOT / 'public/media/explorer/inputs').iterdir():
    if path.name not in keep_inputs:
        targets.append(path)

if '--apply' in sys.argv:
    for path in targets:
        path.unlink()
print(('removed' if '--apply' in sys.argv else 'would remove'), len(targets), 'files')
for path in sorted(targets):
    print(' ', path.relative_to(ROOT))
