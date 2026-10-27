"""Lay out native Blender renders, short headings and arrows for the web.
Run after render_robotics_workflow.py has produced all four /tmp panels.
"""
import json
import hashlib
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TMP = Path('/tmp/rfw-workflow')
MEDIA = ROOT / 'public/media'
FONT = '/usr/share/fonts/dejavu/DejaVuSans.ttf'
PANELS = ['retrieve', 'edit', 'train', 'deploy']
TITLES = ['Retrieve from 400K+', 'Edit', 'Simulation training', 'Real-world deployment']
SIZE = 640
GAP = 90
MARGIN = 12
FRAME_Y = 90
WIDTH = MARGIN * 2 + SIZE * 4 + GAP * 3
INK = '#20272b'
ARROW = '#647075'


def arrow(draw, points):
    draw.line(points, fill=ARROW, width=4, joint='curve')
    x, y = points[-1]
    dx, dy = x - points[-2][0], y - points[-2][1]
    if abs(dx) > abs(dy):
        sign = 1 if dx > 0 else -1
        head = [(x-sign*12, y-9), (x, y), (x-sign*12, y+9)]
    else:
        sign = 1 if dy > 0 else -1
        head = [(x-9, y-sign*12), (x, y), (x+9, y-sign*12)]
    draw.line(head, fill=ARROW, width=4, joint='curve')


def frame(canvas, i, x, y, mobile=False):
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT, 46 if mobile else 42)
    draw.text((x+SIZE/2, y-54), TITLES[i], font=font, fill=INK, anchor='mm')
    draw.rounded_rectangle((x, y, x+SIZE, y+SIZE), radius=7, fill='#f3f5f6')
    source = Image.open(TMP / (PANELS[i] + '.png')).convert('RGBA')
    if source.size != (1280, 1280):
        raise ValueError('Final-quality 1280px render required: ' + PANELS[i])
    source.thumbnail((SIZE-24, SIZE-24), Image.Resampling.LANCZOS)
    canvas.paste(source, (x+12, y+12), source)
    draw.rounded_rectangle((x, y, x+SIZE, y+SIZE), radius=7, outline='#e0e4e6', width=2)


def compose():
    desktop = Image.new('RGB', (WIDTH, FRAME_Y+SIZE+12), 'white')
    for i in range(4):
        x = MARGIN + i*(SIZE+GAP)
        frame(desktop, i, x, FRAME_Y)
        if i < 3:
            arrow(ImageDraw.Draw(desktop), [(x+SIZE+18, FRAME_Y+SIZE/2), (x+SIZE+GAP-18, FRAME_Y+SIZE/2)])
    desktop.save(MEDIA / 'robotics-flow.webp', quality=93, method=6)
    desktop.save(TMP / 'robotics-flow.png')
    # Reading order stays left-to-right on both rows; the return arrow connects
    # Edit to Train rather than changing the order of the two lower panels.
    mobile_width = MARGIN*2+SIZE*2+GAP
    second_y = 960
    mobile = Image.new('RGB', (mobile_width, second_y+SIZE+12), 'white')
    for i in range(4):
        x = MARGIN + (i%2)*(SIZE+GAP)
        y = FRAME_Y if i < 2 else second_y
        frame(mobile, i, x, y, mobile=True)
        if i in (0, 2):
            arrow(ImageDraw.Draw(mobile), [(x+SIZE+18, y+SIZE/2), (x+SIZE+GAP-18, y+SIZE/2)])
    x1 = MARGIN+SIZE/2
    x2 = MARGIN+SIZE+GAP+SIZE/2
    arrow(ImageDraw.Draw(mobile), [(x2, FRAME_Y+SIZE+14), (x2, 812), (x1, 812), (x1, second_y-102)])
    mobile.save(MEDIA / 'robotics-flow-mobile.webp', quality=93, method=6)
    mobile.save(TMP / 'robotics-flow-mobile.png')
    # GitHub Pages can cache unchanged asset URLs between quick revisions.
    # Content versions keep the inline image and its lightbox in sync.
    html_path = ROOT / 'index.html'
    html = html_path.read_text()
    for name in ('robotics-flow.webp', 'robotics-flow-mobile.webp'):
        version = hashlib.sha256((MEDIA / name).read_bytes()).hexdigest()[:12]
        html = re.sub(r'(media/' + re.escape(name) + r')(?:\?v=[a-zA-Z0-9-]+)?', lambda m: m[1] + '?v=' + version, html)
    html_path.write_text(html)
    audits = [json.loads((TMP / (p+'.json')).read_text()) for p in PANELS]
    checks = [v for a in audits for arm in a['robot_pose_checks'].values() for v in arm.values()]
    if not checks or max(checks) > 1e-5:
        raise ValueError('Native URDF / recorded pose agreement failed')
    out = ROOT / 'output/robotics-workflow'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'render-audit.json').write_text(json.dumps({'panels': audits, 'max_fk_position_error_m': max(checks), 'desktop_dimensions': desktop.size, 'mobile_dimensions': mobile.size}, indent=2))
    print('Desktop:', desktop.size, 'Mobile:', mobile.size, 'Max FK error:', max(checks))


if __name__ == '__main__':
    compose()
