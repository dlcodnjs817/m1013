#!/usr/bin/env python3
"""sim_out/scene3d/scene.json (+ turn/*.jpg) → 단일 HTML 3D 뷰어.
WebGL 이 있으면 three.js(r128, cdnjs) 실시간 뷰, 없으면 미리 렌더한 턴테이블로 대체."""
import json, sys, base64, glob, os
S = json.load(open('sim_out/scene3d/scene.json')); m = S['meta']
TURN = {os.path.basename(f)[:-4]: 'data:image/jpeg;base64,' + base64.b64encode(open(f, 'rb').read()).decode()
        for f in sorted(glob.glob('sim_out/scene3d/turn/*.jpg'))}
out = sys.argv[1] if len(sys.argv) > 1 else 'sim_out/scene3d/m1013_tool_assembly.html'
print('턴테이블 %d 장' % len(TURN))

HTML = r'''<title>M1013 툴 어셈블리</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{--ground:#ECEEF2;--panel:#FFFFFF;--ink:#1B1F27;--muted:#5C6370;--line:#D5D9E0;--accent:#E07A2E;--chip:#F3F4F7;--sky:#DCE1E8;--floor:#C9CED6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ground:#171A20;--panel:#1F232B;--ink:#E8EAEE;--muted:#9AA1AC;--line:#2E333C;--accent:#F08A3C;--chip:#262B34;--sky:#2A2F38;--floor:#1E222A}}
:root[data-theme="dark"]{--ground:#171A20;--panel:#1F232B;--ink:#E8EAEE;--muted:#9AA1AC;--line:#2E333C;--accent:#F08A3C;--chip:#262B34;--sky:#2A2F38;--floor:#1E222A}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font:14px/1.5 "IBM Plex Sans KR",-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;padding-inline:16px;padding-block:12px}
header{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 18px;margin-bottom:10px}
h1{font-size:18px;font-weight:600;margin:0;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:13px}
.views{display:flex;flex-wrap:wrap;gap:6px;margin-left:auto}
.views button{font:inherit;font-size:13px;padding:5px 11px;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:6px;cursor:pointer}
.views button:hover{border-color:var(--accent)}
.views button:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.views button.on{background:var(--accent);border-color:var(--accent);color:#fff}
.views button:disabled{opacity:.45;cursor:default}
main{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:12px;align-items:start}
#stage{position:relative;aspect-ratio:4/3;max-height:calc(100vh - 90px);width:100%;background:var(--sky);border:1px solid var(--line);border-radius:8px;overflow:hidden;touch-action:none}
#stage canvas,#stage img{display:block;width:100%!important;height:100%!important;object-fit:cover;user-select:none;-webkit-user-drag:none}
#hint{position:absolute;left:10px;bottom:8px;right:10px;font-size:12px;color:var(--muted);background:var(--panel);opacity:.9;padding:3px 8px;border-radius:5px;pointer-events:none;width:max-content;max-width:calc(100% - 20px)}
aside{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px;display:flex;flex-direction:column;gap:12px}
.grp{display:flex;flex-direction:column;gap:2px}
.grp h2{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 4px}
label.row{display:grid;grid-template-columns:16px 14px 1fr;gap:8px;align-items:start;padding:4px 4px;border-radius:5px;cursor:pointer}
label.row:hover{background:var(--chip)}
label.row input{margin:3px 0 0;accent-color:var(--accent)}
.sw{width:14px;height:14px;border-radius:3px;margin-top:3px;border:1px solid rgba(0,0,0,.15)}
.nm{font-weight:500}
.nt{display:block;color:var(--muted);font-size:12px;line-height:1.35}
dl{display:grid;grid-template-columns:auto 1fr;gap:3px 12px;margin:0;font-size:12.5px}
dt{color:var(--muted)}dd{margin:0;font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}
.foot{font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:10px}
@media (max-width:820px){main{grid-template-columns:1fr}#stage{max-height:none}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
<header>
  <h1>M1013 툴 어셈블리</h1>
  <span class="sub">ep__EP__ · 파지 프레임 __FRAME__ · 플랜지 로컬 설계 부품 전부</span>
  <div class="views" role="group" aria-label="시점">
    <button id="v-iso" class="on">전체</button><button id="v-tool">툴 정면</button><button id="v-side">브래킷 측면</button><button id="v-below">아래에서</button><button id="v-cam">손목캠 시점</button>
  </div>
</header>
<main>
  <div id="stage"><div id="hint">드래그 회전 · 휠 확대 · Shift+드래그 이동</div></div>
  <aside id="panel"></aside>
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
const SCENE = __DATA__;
const TURN = __TURN__;
const M = SCENE.meta;
const GROUPS = {robot:'로봇 M1013',tool:'그리퍼 · 어댑터 · 핑거',bracket:'브래킷 (PETG 출력)',camera:'손목캠',scene:'작업 환경'};
const stage = document.getElementById('stage');

function buildPanel(onToggle){
  const panel=document.getElementById('panel');const byGroup={};
  for(const p of SCENE.parts)(byGroup[p.group]=byGroup[p.group]||[]).push(p);
  for(const k of ['tool','bracket','camera','robot','scene']){
    if(!byGroup[k])continue;
    const d=document.createElement('div');d.className='grp';const h=document.createElement('h2');h.textContent=GROUPS[k];d.appendChild(h);
    const seen={};
    for(const p of byGroup[k]){
      const key=p.name.replace(/ 액센트$/,'').replace(/ \d$/,'');
      if(seen[key]){seen[key].push(p.name);continue}
      seen[key]=[p.name];
      const l=document.createElement('label');l.className='row';
      const c=document.createElement('input');c.type='checkbox';c.checked=true;c.id='pt-'+key.replace(/\W+/g,'_');
      c.addEventListener('change',()=>onToggle&&onToggle(seen[key],c.checked));
      const s=document.createElement('span');s.className='sw';s.style.background=p.color;
      const t=document.createElement('span');t.innerHTML='<span class="nm"></span><span class="nt"></span>';
      t.firstChild.textContent=key;if(p.note)t.lastChild.textContent=p.note;else t.lastChild.remove();
      l.append(c,s,t);d.appendChild(l);
    }
    panel.appendChild(d);
  }
  const dims=document.createElement('div');dims.className='grp';
  dims.innerHTML='<h2>치수 · 플랜지 로컬</h2><dl><dt>TCP (파지점)</dt><dd>Z = 72.5 mm</dd><dt>핑거 끝</dt><dd>Z = 83.0 mm</dd><dt>닫힘 갭</dt><dd>33.5 mm (큐브 35)</dd><dt>손목캠 광심</dt><dd>(0, −65, −10) mm</dd><dt>손목캠 틸트</dt><dd>23.4° · HFOV 85.6°</dd><dt>측면 M5</dt><dd>x = ±61, z = 32</dd></dl>';
  panel.appendChild(dims);
  const foot=document.createElement('div');foot.className='foot';
  foot.textContent='어댑터·핑거는 절삭 외주(AL6061), 브래킷 2개는 PETG 자체 출력. 손목캠 브래킷은 렌즈 스탠드오프 실측 후 출력.';panel.appendChild(foot);
}

function turntable(reason){
  // WebGL 이 없으면 Isaac 으로 미리 찍은 턴테이블(24 방위 × 2 고도 × 툴/전체)을 드래그로 돌린다
  stage.innerHTML='';
  const img=document.createElement('img');img.draggable=false;img.alt='M1013 툴 어셈블리 회전 뷰';stage.appendChild(img);
  const note=document.createElement('div');note.id='hint';note.textContent='미리 렌더한 회전 뷰 ('+reason+') · 좌우 드래그 회전 · 위로 드래그 높은 시점';stage.appendChild(note);
  let set='full',el=0,az=6;const N=24;
  const show=()=>{img.src=TURN[set+'_'+el+'_'+String(((az%N)+N)%N).padStart(2,'0')];};
  let d=null;
  stage.addEventListener('pointerdown',e=>{d={x:e.clientX,y:e.clientY};stage.setPointerCapture(e.pointerId)});
  stage.addEventListener('pointermove',e=>{if(!d)return;const dx=e.clientX-d.x,dy=e.clientY-d.y;
    if(Math.abs(dx)>16){az+=dx>0?-1:1;d.x=e.clientX;show()}
    if(Math.abs(dy)>50){el=dy<0?1:0;d.y=e.clientY;show()}});
  stage.addEventListener('pointerup',()=>d=null);
  const map={'v-iso':['full',0,6],'v-tool':['tool',0,6],'v-side':['tool',0,0],'v-below':['tool',0,12]};
  for(const id in map)document.getElementById(id).onclick=()=>{[set,el,az]=map[id];show();document.querySelectorAll('.views button').forEach(b=>b.classList.toggle('on',b.id===id));};
  const vc=document.getElementById('v-cam');vc.disabled=true;vc.title='실시간 3D(WebGL)에서만';
  document.querySelectorAll('#panel input').forEach(c=>{c.disabled=true;c.title='미리 렌더한 뷰에서는 부품을 끌 수 없습니다'});
  show();
}

let webgl=false;
try{const t=document.createElement('canvas');webgl=!!(t.getContext('webgl2')||t.getContext('webgl'));}catch(e){}
if(typeof THREE==='undefined'){buildPanel(null);turntable('three.js 로드 실패');}
else if(!webgl){buildPanel(null);turntable('이 화면엔 WebGL 없음');}
else{
  const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));stage.prepend(renderer.domElement);
  const scene=new THREE.Scene();const css=getComputedStyle(document.documentElement);const tok=n=>css.getPropertyValue(n).trim();
  scene.background=new THREE.Color(tok('--sky'));
  const camera=new THREE.PerspectiveCamera(40,4/3,0.01,50);
  scene.add(new THREE.HemisphereLight(0xffffff,0x8a8f99,0.9));
  const sun=new THREE.DirectionalLight(0xffffff,0.9);sun.position.set(1.5,-2,3);scene.add(sun);
  const fill=new THREE.DirectionalLight(0xffffff,0.35);fill.position.set(-2,1.5,1);scene.add(fill);
  scene.add(new THREE.Mesh(new THREE.PlaneGeometry(6,6),new THREE.MeshStandardMaterial({color:new THREE.Color(tok('--floor')),roughness:1})));
  const grid=new THREE.GridHelper(6,24,0x9aa1ac,0xb7bdc6);grid.rotation.x=Math.PI/2;grid.position.z=0.001;scene.add(grid);
  const b64=(s,T)=>{const b=atob(s),a=new Uint8Array(b.length);for(let i=0;i<b.length;i++)a[i]=b.charCodeAt(i);return new T(a.buffer)};
  for(const p of SCENE.parts){
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(b64(p.v,Float32Array),3));g.setIndex(new THREE.BufferAttribute(b64(p.f,Uint32Array),1));g.computeVertexNormals();
    const mat=new THREE.MeshStandardMaterial({color:new THREE.Color(p.color),roughness:0.5,metalness:p.group==='tool'?0.35:0.05,side:THREE.DoubleSide});
    const mesh=new THREE.Mesh(g,mat);mesh.name=p.name;scene.add(mesh);
  }
  buildPanel((names,on)=>{for(const n of names){const o=scene.getObjectByName(n);if(o)o.visible=on;}});
  // 손목캠 시야 프러스텀
  const cw=new THREE.Vector3(...M.cam_world),cf=new THREE.Vector3(...M.cam_fwd_world).normalize();
  const R=new THREE.Matrix3().set(...[].concat(...M.flange_R));const up0=new THREE.Vector3(-1,0,0).applyMatrix3(R);
  const right=new THREE.Vector3().crossVectors(cf,up0).normalize();const camUp=new THREE.Vector3().crossVectors(right,cf).normalize();
  {const th=Math.tan(M.hfov/2*Math.PI/180),tv=th*0.75,L=0.26;const c4=[[1,1],[1,-1],[-1,-1],[-1,1]].map(([a,b])=>cw.clone().add(cf.clone().multiplyScalar(L)).add(right.clone().multiplyScalar(a*th*L)).add(camUp.clone().multiplyScalar(b*tv*L)));
   const pts=[];for(const c of c4)pts.push(cw,c);for(let i=0;i<4;i++)pts.push(c4[i],c4[(i+1)%4]);
   scene.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color:0xE07A2E,transparent:true,opacity:0.7})));}
  // 궤도 컨트롤
  const ctl={target:new THREE.Vector3(...M.tcp_world),r:1.6,th:0.9,ph:1.05};let wristView=false;
  const apply=()=>{const t=ctl.target;camera.position.set(t.x+ctl.r*Math.sin(ctl.ph)*Math.cos(ctl.th),t.y+ctl.r*Math.sin(ctl.ph)*Math.sin(ctl.th),t.z+ctl.r*Math.cos(ctl.ph));camera.up.set(0,0,1);camera.lookAt(t);camera.fov=40;camera.updateProjectionMatrix();};
  const setView=(id,r,th,ph,target)=>{wristView=false;ctl.r=r;ctl.th=th;ctl.ph=ph;ctl.target.copy(target);apply();document.querySelectorAll('.views button').forEach(b=>b.classList.toggle('on',b.id===id));};
  const fl=new THREE.Vector3(...M.flange);
  document.getElementById('v-iso').onclick=()=>setView('v-iso',1.9,-0.9,1.15,new THREE.Vector3(0.45,-0.1,0.45));
  document.getElementById('v-tool').onclick=()=>setView('v-tool',0.42,-1.57,1.35,fl.clone().add(new THREE.Vector3(0,0,-0.03)));
  document.getElementById('v-side').onclick=()=>setView('v-side',0.38,-2.2,1.5,fl.clone().add(new THREE.Vector3(0,0,-0.02)));
  document.getElementById('v-below').onclick=()=>setView('v-below',0.45,-1.2,2.35,fl.clone().add(new THREE.Vector3(0,0,-0.02)));
  document.getElementById('v-cam').onclick=()=>{wristView=true;camera.position.copy(cw);camera.up.copy(camUp);camera.lookAt(cw.clone().add(cf));camera.fov=2*Math.atan(Math.tan(M.hfov/2*Math.PI/180)*0.75)*180/Math.PI;camera.updateProjectionMatrix();document.querySelectorAll('.views button').forEach(b=>b.classList.toggle('on',b.id==='v-cam'));};
  let drag=null;const el=renderer.domElement;
  el.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,pan:e.shiftKey||e.button===2};el.setPointerCapture(e.pointerId)});
  el.addEventListener('pointermove',e=>{if(!drag||wristView)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.x=e.clientX;drag.y=e.clientY;
    if(drag.pan){const s=ctl.r*0.0016;const rt=new THREE.Vector3().crossVectors(camera.getWorldDirection(new THREE.Vector3()),camera.up).normalize();ctl.target.addScaledVector(rt,-dx*s).addScaledVector(camera.up,dy*s);}
    else{ctl.th-=dx*0.006;ctl.ph=Math.min(3.0,Math.max(0.15,ctl.ph-dy*0.006));}apply();});
  el.addEventListener('pointerup',()=>drag=null);el.addEventListener('contextmenu',e=>e.preventDefault());
  el.addEventListener('wheel',e=>{e.preventDefault();if(wristView)return;ctl.r=Math.min(6,Math.max(0.12,ctl.r*Math.exp(e.deltaY*0.0012)));apply();},{passive:false});
  let pinch=null;el.addEventListener('touchstart',e=>{if(e.touches.length===2)pinch=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY)},{passive:true});
  el.addEventListener('touchmove',e=>{if(e.touches.length===2&&pinch&&!wristView){const d=Math.hypot(e.touches[0].clientX-e.touches[1].clientX,e.touches[0].clientY-e.touches[1].clientY);ctl.r=Math.min(6,Math.max(0.12,ctl.r*pinch/d));pinch=d;apply();}},{passive:true});
  const resize=()=>{const w=stage.clientWidth,h=stage.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();};
  new ResizeObserver(resize).observe(stage);resize();
  document.getElementById('v-iso').onclick();
  (function loop(){renderer.render(scene,camera);requestAnimationFrame(loop)})();
}
</script>'''
html = (HTML.replace('__DATA__', json.dumps(S, separators=(',', ':')))
            .replace('__TURN__', json.dumps(TURN, separators=(',', ':')))
            .replace('__EP__', m['ep']).replace('__FRAME__', str(m['frame'])))
open(out, 'w').write(html)
print('저장', out, '%.1f MB' % (os.path.getsize(out) / 1e6))
