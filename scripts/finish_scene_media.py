"""Publish only reviewed scene-map images, projected hotspots and compressed clips."""
import json,subprocess,concurrent.futures,time
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];TMP=Path('/tmp/rfw-scenes');PUB=ROOT/'public';OUT=PUB/'media/scenes';OUT.mkdir(parents=True,exist_ok=True)
shots=json.loads((ROOT/'scripts/scene_shots.json').read_text());catalog={a['id']:a for a in json.loads((PUB/'data/catalog.json').read_text())}
names={'asset_90_hero_toaster_6664610a':'Toaster','cabinet_rig_three_drawer_2fce3abe':'Drawer cabinet','asset_25_piano_7c8af708':'Piano','ferris_wheel_594ea2e6':'Ferris wheel','swing_0970_placement_504d4cae':'Swing','tower_crane_ccb3c33d':'Tower crane','v03_satellite_articulated_508d3d52':'Satellite','urdf_08_antenna_dish_001_8494e9b1':'Antenna dish','urdf_12_rotating_observatory_dome_4c3d10d5':'Observatory dome','robot_dog_placement_b3ab1056':'Robot dog','robot_dexterous_placement_150223ae':'Dexterous robot','desk_microscope_placement_162ffbd1':'Microscope'}
names.update({
 'asset_13_refrigerator_with_hinged_doors_35af1266':'Refrigerator',
 'asset_15_dishwasher_with_dropdown_door_and_sliding_racks_cfd7dc9f':'Dishwasher',
 'asset_21_washmachine_2e9d4f84':'Washing machine',
 'asset_27_vocal_mic_bcb8d220':'Microphone',
 'asset_56_laundry_clothes_drying_rack_c40fe128':'Drying rack',
 'cabinet_rig_sink_double_door_758afe8d':'Sink cabinet',
 'ceiling_light_five_arm_03e9eaf1':'Ceiling light',
 'room_cabinet_e7872afb':'Sideboard',
 'urdf_11_astronomical_telescope_on_tripod_348a2d1a':'Telescope',
 'urdf_09_pressurised_module_door_36a2cbb7':'Module hatch',
 'cabinet_left_placement_71522c75':'Left cabinet',
 'cabinet_right_placement_50b14ef9':'Right cabinet',
 'desk_left_front_placement_050bd932':'Left workbench',
 'desk_right_front_placement_58bf4247':'Right workbench',
 'door_zigzag_placement_a35b6b82':'Sliding door',
 'robot_clamp_placement_c10e95ae':'Robot arm',
 'wall_air_conditioner_placement_3b771f9e':'Air conditioner',
})
def encode(a):
 aid=a['id'];folder=TMP/'final-frames'/aid
 if all((OUT/(aid+'.'+ext)).exists() for ext in ['mp4','webm','webp']):return aid
 deadline=time.monotonic()+600
 while not all((folder/f'{i:04d}.png').is_file() for i in range(120)):
  if time.monotonic()>deadline:raise RuntimeError('Incomplete render: '+aid)
  time.sleep(2)
 Image.open(folder/'0042.png').convert('RGB').save(OUT/(aid+'.webp'),quality=89)
 for suffix,args in [('mp4',['-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart']),('webm',['-c:v','libvpx-vp9','-b:v','0','-crf','33','-cpu-used','4','-pix_fmt','yuv420p'])]:
  subprocess.run(['ffmpeg','-y','-v','error','-framerate','24','-i',str(folder/'%04d.png'),'-frames:v','120','-threads','2',*args,str(OUT/(aid+'.'+suffix))],check=True)
 return aid
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for aid in pool.map(encode,[a for group in shots.values() for a in group]):print('ENCODED',aid,flush=True)
result=[]
for sid,group in shots.items():
 Image.open(TMP/(sid+'-map.png')).convert('RGB').save(OUT/(sid+'.webp'),quality=90)
 projections={a['id']:a for a in json.loads((TMP/(sid+'-map.json')).read_text())};objects=[]
 for a in group:
  aid=a['id'];objects.append({**projections[aid],'name':names.get(aid,catalog[aid]['name']),'video':f'media/scenes/{aid}.mp4','poster':f'media/scenes/{aid}.webp','duration':5})
 result.append({'id':sid,'label':sid.capitalize(),'image':f'media/scenes/{sid}.webp','objects':objects})
(PUB/'data/scenes.json').write_text(json.dumps(result,indent=2))
print(f'Published {len(result)} scene maps and {sum(len(g) for g in shots.values())} native-scene camera clips.')
