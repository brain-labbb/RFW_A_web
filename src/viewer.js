import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

export class AssetViewer {
 constructor(container, onProgress) {
  this.THREE=THREE;this.container=container;this.onProgress=onProgress;this.playing=false;this.token=0;this.duration=0;
  this.scene=new THREE.Scene();this.scene.background=new THREE.Color('#f4f4f4');
  this.camera=new THREE.PerspectiveCamera(35,1,0.01,10000);
  this.renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
  this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=.85;this.renderer.shadowMap.enabled=true;this.renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  container.appendChild(this.renderer.domElement);
  const pmrem=new THREE.PMREMGenerator(this.renderer);const room=new RoomEnvironment();
  this.environment=pmrem.fromScene(room,0.04);this.scene.environment=this.environment.texture;this.scene.environmentIntensity=.45;room.dispose();pmrem.dispose();
  this.scene.add(new THREE.HemisphereLight(0xffffff,0x8c987d,.4));
  const light=new THREE.DirectionalLight(0xffffff,2.2);light.position.set(4,7,5);light.castShadow=true;light.shadow.mapSize.set(1024,1024);this.scene.add(light);this.light=light;
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.dampingFactor=.08;
  this.loader=new GLTFLoader();this.clock=new THREE.Clock();
  this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(container);this.resize();
  this.visible=true;this.intersection=new IntersectionObserver(([e])=>{this.visible=e.isIntersecting;});this.intersection.observe(container);
  this.renderer.setAnimationLoop(()=>{
   const delta=Math.min(this.clock.getDelta(),.05);
   if(!this.visible||document.hidden)return;
   if(this.mixer&&this.playing){this.time=(this.time+delta)%this.duration;this.mixer.setTime(this.time);this.onProgress?.(this.time/this.duration,this.time);}
   this.controls.update();this.renderer.render(this.scene,this.camera);
  });
 }
 resize(){const w=this.container.clientWidth,h=this.container.clientHeight;if(!w||!h)return;this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.renderer.setSize(w,h);}
 disposeModel(model){model?.traverse(o=>{o.geometry?.dispose();if(o.material){for(const m of [].concat(o.material)){for(const v of Object.values(m))if(v?.isTexture)v.dispose();m.dispose();}}});}
 async load(url){
  const token=++this.token;this.playing=false;
  const gltf=await this.loader.loadAsync(url);
  if(token!==this.token){this.disposeModel(gltf.scene);return false;}
  if(this.mixer){this.mixer.stopAllAction();this.mixer.uncacheRoot(this.model);}
  if(this.root){this.scene.remove(this.root);this.disposeModel(this.model);}
  this.model=gltf.scene;this.model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});this.root=new THREE.Group();this.root.add(this.model);this.scene.add(this.root);
  this.mixer=new THREE.AnimationMixer(this.model);
  this.clips=gltf.animations;for(const clip of this.clips)this.mixer.clipAction(clip).play();
  this.duration=Math.max(0,...this.clips.map(c=>c.duration));this.time=0;this.mixer.setTime(0);
  this.model.updateMatrixWorld(true);
  const box=new THREE.Box3().setFromObject(this.model);const size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());
  this.root.position.copy(center).negate();this.size=size;this.radius=Math.max(size.x,size.y,size.z,.01);
  if(this.ground){this.scene.remove(this.ground);this.ground.geometry.dispose();this.ground.material.dispose();}
  const r=this.radius;this.ground=new THREE.Mesh(new THREE.PlaneGeometry(r*15,r*15),new THREE.ShadowMaterial({opacity:.16}));this.ground.rotation.x=-Math.PI/2;this.ground.position.y=-size.y/2-r*.005;this.ground.receiveShadow=true;this.scene.add(this.ground);
  this.light.position.set(r*2,r*4,r*2);Object.assign(this.light.shadow.camera,{left:-r*2,right:r*2,top:r*2,bottom:-r*2,near:r*.01,far:r*15});this.light.shadow.camera.updateProjectionMatrix();this.light.shadow.bias=-.0003;this.light.shadow.normalBias=r*.005;
  this.reset();this.onProgress?.(0,0);this.renderer.render(this.scene,this.camera);return true;
 }
 reset(){if(!this.radius)return;const r=this.radius;this.camera.position.set(r*1.45,r*.95,r*1.7);this.camera.near=r/1000;this.camera.far=r*100;this.camera.updateProjectionMatrix();this.controls.target.set(0,0,0);this.controls.minDistance=r*.3;this.controls.maxDistance=r*7;this.controls.update();this.seek(0);}
 seek(fraction){this.time=Math.max(0,Math.min(1,fraction))*this.duration;this.mixer?.setTime(this.time);this.onProgress?.(fraction,this.time);this.renderer.render(this.scene,this.camera);}
 setPlaying(value){this.playing=Boolean(value&&this.duration>0);return this.playing;}
 highlightMaterial(name){this.model?.traverse(o=>{if(!o.isMesh)return;for(const m of [].concat(o.material||[])){if(!m.userData.originalEmissive&&m.emissive)m.userData.originalEmissive=m.emissive.clone();if(m.emissive){m.emissive.copy(m.userData.originalEmissive);if(name&&m.name===name)m.emissive.setHex(0x3b1607);}}});}
}
