// A single shared WebGL renderer serves all panels, avoiding browser context limits.
// Geometry and animation use recorded XYZ positions; camera changes never alter simulation data.
const V3 = {
  add:(a,b)=>a.map((v,i)=>v+b[i]), sub:(a,b)=>a.map((v,i)=>v-b[i]),
  mul:(a,s)=>a.map(v=>v*s), dot:(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0),
  cross:(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],
  norm:a=>{const n=Math.hypot(...a)||1;return a.map(v=>v/n);}
};
function matrixMultiply(a,b){const out=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)out[c*4+r]+=a[k*4+r]*b[c*4+k];return out;}
function lookAt(eye,target){const z=V3.norm(V3.sub(eye,target)),x=V3.norm(V3.cross([0,0,1],z)),y=V3.cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-V3.dot(x,eye),-V3.dot(y,eye),-V3.dot(z,eye),1]);}
function perspective(fov,aspect,near,far){const f=1/Math.tan(fov/2);return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)/(near-far),-1,0,0,2*far*near/(near-far),0]);}
function ortho(h,aspect,near,far){return new Float32Array([1/(h*aspect),0,0,0,0,1/h,0,0,0,0,-2/(far-near),0,0,0,-(far+near)/(far-near),1]);}
function project3(p,m,w,h){const a=[...p.slice(0,3),1],q=[0,0,0,0];for(let r=0;r<4;r++)for(let k=0;k<4;k++)q[r]+=m[k*4+r]*a[k];return [(q[0]/q[3]+1)*w/2,(1-q[1]/q[3])*h/2,q[2]/q[3]];}
function roundedStep(v){const base=10**Math.floor(Math.log10(Math.max(v,1e-8)));return [1,2,5,10].map(k=>k*base).find(x=>x>=v);}
function bounds(row){
  const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
  function include(p,r=0){for(let k=0;k<3;k++){lo[k]=Math.min(lo[k],p[k]-r);hi[k]=Math.max(hi[k],p[k]+r);}}
  for(const v of row.variants){
    for(const frame of v.particle_q)frame.forEach((p,i)=>include(p,v.visual.particle_radii[i]||0));
    for(const frame of v.body_q)for(const shape of v.visual.body_shapes)include(frame[shape.body],shape.radius);
    if(v.visual.anchor)include(v.visual.anchor);
    if(v.visual.floor!==null)include([lo[0],0,v.visual.floor]);
    if(v.visual.slab){include([-.4,-.4,-.04]);include([.4,.4,0]);}
  }
  const span=hi.map((v,i)=>v-lo[i]),size=Math.max(...span,.12),center=hi.map((v,i)=>(v+lo[i])/2);
  const radius=Math.max(Math.hypot(...span)/2,size*.55),step=roundedStep(size/7);
  const floor=row.variants[0].visual.floor,slab=row.variants[0].visual.slab;
  const gridZ=floor!==null?floor:slab?0:lo[2]-size*.09;
  return {lo,hi,center,size,radius,step,gridZ};
}
function defaultCamera(){return {yaw:-1.04,pitch:.38,zoom:1,preset:'3d',pan:[0,0,0]};}
function cameraMatrix(s,aspect){
  const c=s.camera,b=s.bounds,target=V3.add(b.center,c.pan),narrow=Math.min(aspect,1);
  const distance=b.radius*3.65/(c.zoom*narrow),cp=Math.cos(c.pitch);
  const eye=V3.add(target,V3.mul([cp*Math.cos(c.yaw),cp*Math.sin(c.yaw),Math.sin(c.pitch)],distance));
  const view=lookAt(eye,target),near=Math.max(b.size*.001,distance-b.radius*8),far=distance+b.radius*15;
  const proj=c.preset==='3d'?perspective(.76,aspect,near,far):ortho(b.radius*1.22/(c.zoom*narrow),aspect,near,far);
  return {matrix:matrixMultiply(proj,view),view,target,eye};
}
const renderer3D=(()=>{
  const output=document.createElement('canvas');
  const gl=output.getContext('webgl',{alpha:false,antialias:true,preserveDrawingBuffer:true});
  if(!gl)return {error:'浏览器未能启用 WebGL，请开启硬件加速或使用原版视图。'};
  const vert='attribute vec3 aP;attribute vec3 aN;attribute vec3 aC;uniform mat4 uM;varying vec3 vN;varying vec3 vC;void main(){gl_Position=uM*vec4(aP,1.0);vN=aN;vC=aC;}';
  const frag='precision mediump float;varying vec3 vN;varying vec3 vC;void main(){float light=1.0;if(length(vN)>.1){light=.62+.38*abs(dot(normalize(vN),normalize(vec3(-.4,-.5,1.0))));}gl_FragColor=vec4(vC*light,1.0);}';
  function shader(type,src){const sh=gl.createShader(type);gl.shaderSource(sh,src);gl.compileShader(sh);if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(sh));return sh;}
  const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vert));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,frag));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
  gl.useProgram(program);const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
  ['aP','aN','aC'].forEach((name,i)=>{const loc=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,36,i*12);});
  const uniform=gl.getUniformLocation(program,'uM');gl.enable(gl.DEPTH_TEST);gl.depthFunc(gl.LEQUAL);
  gl.clearColor(.969,.98,.988,1);
  return {output,gl,draw(w,h,matrix,triangles,lines){
    if(output.width!==w||output.height!==h){output.width=w;output.height=h;}
    gl.viewport(0,0,w,h);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.uniformMatrix4fv(uniform,false,matrix);
    if(triangles.length){gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(1,1);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(triangles),gl.DYNAMIC_DRAW);gl.drawArrays(gl.TRIANGLES,0,triangles.length/9);gl.disable(gl.POLYGON_OFFSET_FILL);}
    if(lines.length){gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(lines),gl.DYNAMIC_DRAW);gl.drawArrays(gl.LINES,0,lines.length/9);}
  }};
})();
const unitSphere=[];
for(let j=0;j<12;j++)for(let i=0;i<18;i++){
  const p=(a,b)=>[Math.sin(a)*Math.cos(b),Math.sin(a)*Math.sin(b),Math.cos(a)];
  const a=j*Math.PI/12,b=(j+1)*Math.PI/12,u=i*Math.PI/9,v=(i+1)*Math.PI/9;
  unitSphere.push(p(a,u),p(b,u),p(b,v),p(a,u),p(b,v),p(a,v));
}
function geometry3D(s,v,progress,j){
  const b=s.bounds,now=sampled(v,progress*v.times.at(-1)),triangles=[],lines=[];
  const primary=j?[.84,.36,.12]:[.13,.36,.88],surface=j?[.97,.68,.43]:[.46,.67,.99],fixed=[.67,.77,.81];
  const addVertex=(out,p,n,c)=>out.push(...p.slice(0,3),...n,...c);
  function line(a,z,c=[.56,.65,.7]){addVertex(lines,a,[0,0,0],c);addVertex(lines,z,[0,0,0],c);}
  function triangle(a,z,c,color){const n=V3.norm(V3.cross(V3.sub(z,a),V3.sub(c,a)));for(const p of [a,z,c])addVertex(triangles,p,n,color);}
  function sphere(p,r,c){for(const n of unitSphere)addVertex(triangles,V3.add(p.slice(0,3),V3.mul(n,r)),n,c);}
  function cylinder(a,z,r,color){
    const d=V3.norm(V3.sub(z,a)),u=V3.norm(V3.cross(d,Math.abs(d[2])<.9?[0,0,1]:[1,0,0])),w=V3.cross(d,u);
    for(let i=0;i<8;i++){const radial=t=>V3.add(V3.mul(u,Math.cos(t)),V3.mul(w,Math.sin(t)));const n=radial(i*Math.PI/4),m=radial((i+1)*Math.PI/4);
      const pa=V3.add(a,V3.mul(n,r)),pb=V3.add(a,V3.mul(m,r)),pc=V3.add(z,V3.mul(n,r)),pd=V3.add(z,V3.mul(m,r));
      for(const [p,norm] of [[pa,n],[pc,n],[pd,m],[pa,n],[pd,m],[pb,m]])addVertex(triangles,p,norm,color);
    }
  }
  function quad(a,z,c,d,color){triangle(a,z,c,color);triangle(a,c,d,color);}
  // Reference grids are visual aids. Only an explicit floor/slab represents collision geometry.
  const hasFloor=v.visual.floor!==null,hasSlab=!!v.visual.slab;
  const minX=hasSlab?-.4:Math.floor((b.lo[0]-b.size*.18)/b.step)*b.step,maxX=hasSlab?.4:Math.ceil((b.hi[0]+b.size*.18)/b.step)*b.step;
  const halfY=hasSlab?.4:Math.max(b.size*.22,(b.hi[1]-b.lo[1])*.65),minY=hasSlab?-.4:b.center[1]-halfY,maxY=hasSlab?.4:b.center[1]+halfY;
  const z=b.gridZ;
  if(hasFloor||hasSlab){
    quad([minX,minY,z],[maxX,minY,z],[maxX,maxY,z],[minX,maxY,z],[.86,.9,.92]);
    if(hasSlab){const low=-.04;quad([minX,minY,low],[maxX,minY,low],[maxX,minY,0],[minX,minY,0],[.66,.73,.77]);quad([minX,maxY,low],[minX,minY,low],[minX,minY,0],[minX,maxY,0],[.72,.79,.82]);quad([maxX,minY,low],[maxX,maxY,low],[maxX,maxY,0],[maxX,minY,0],[.72,.79,.82]);quad([maxX,maxY,low],[minX,maxY,low],[minX,maxY,0],[maxX,maxY,0],[.72,.79,.82]);}
  }
  const gridColor=hasFloor||hasSlab?[.69,.77,.81]:[.85,.89,.92];
  for(let x=Math.ceil(minX/b.step)*b.step;x<=maxX+1e-8;x+=b.step)line([x,minY,z],[x,maxY,z],gridColor);
  for(let y=Math.ceil(minY/b.step)*b.step;y<=maxY+1e-8;y+=b.step)line([minX,y,z],[maxX,y,z],gridColor);
  // Initial outlines and point trails are displayed as reference lines, not simulated surfaces.
  for(const edge of v.visual.springs)line(v.particle_q[0][edge[0]],v.particle_q[0][edge[1]],[.76,.81,.85]);
  for(const face of v.visual.triangles)for(let k=0;k<3;k++)line(v.particle_q[0][face[k]],v.particle_q[0][face[(k+1)%3]],[.76,.81,.85]);
  if(v.particle_q[0].length===1){const until=Math.floor(progress*(v.particle_q.length-1));for(let i=1;i<=until;i++)line(v.particle_q[i-1][0],v.particle_q[i][0],j?[.88,.66,.49]:[.59,.72,.91]);}
  for(const face of v.visual.triangles){const f=face.every(i=>v.visual.fixed.includes(i));triangle(...face.map(i=>now.p[i]),f?fixed:surface);for(let k=0;k<3;k++)line(now.p[face[k]],now.p[face[(k+1)%3]],f?[.38,.52,.59]:primary);}
  for(const edge of v.visual.springs)cylinder(now.p[edge[0]],now.p[edge[1]],b.size*.003,primary);
  now.p.forEach((p,i)=>{const f=v.visual.fixed.includes(i),r=v.visual.particle_radii[i]||0;sphere(p,Math.max(r,b.size*.009),f?[.17,.29,.36]:primary);
    if(f){const d=b.size*.019;line(V3.add(p,[-d,0,-d]),V3.add(p,[d,0,d]),[.22,.36,.43]);line(V3.add(p,[-d,0,d]),V3.add(p,[d,0,-d]),[.22,.36,.43]);}
  });
  if(v.visual.anchor){const p=v.visual.anchor;sphere(p,b.size*.023,[.22,.34,.4]);line(p,now.b[0].slice(0,3),[.38,.5,.57]);}
  for(const shape of v.visual.body_shapes)sphere(now.b[shape.body],shape.radius,primary);
  return {triangles,lines};
}
function drawScene(canvas,row,v,progress,variant,b){
  const s=states.get(row.id);if(!s.camera)s.camera=defaultCamera();
  const rect=canvas.getBoundingClientRect();if(!rect.width||!rect.height)return;
  const dpr=Math.min(window.devicePixelRatio||1,2),w=rect.width,h=rect.height;
  const width=Math.round(w*dpr),height=Math.round(h*dpr);if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}
  const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  if(renderer3D.error){ctx.fillStyle='#874521';ctx.font='11px Microsoft YaHei';ctx.fillText('WebGL 未启用，请使用原版视图',10,35);canvas.dataset.renderer='unavailable';return;}
  const camera=cameraMatrix(s,w/h),g=geometry3D(s,v,progress,variant);
  renderer3D.draw(width,height,camera.matrix,g.triangles,g.lines);ctx.drawImage(renderer3D.output,0,0,w,h);
  canvas.dataset.renderer='webgl';canvas.dataset.camera=JSON.stringify(s.camera);canvas.dataset.time=String(progress*v.times.at(-1));
  // Orientation gizmo uses the same camera rotation as the world geometry.
  const origin=[29,h-32],axisLength=20,axes=[[1,0,0],[0,1,0],[0,0,1]],axisColors=['#b14d4a','#3b886a','#3872b8'];
  ctx.font='bold 10px Segoe UI';
  axes.forEach((a,i)=>{const x=origin[0]+axisLength*(camera.view[0]*a[0]+camera.view[4]*a[1]+camera.view[8]*a[2]),y=origin[1]-axisLength*(camera.view[1]*a[0]+camera.view[5]*a[1]+camera.view[9]*a[2]);ctx.beginPath();ctx.moveTo(...origin);ctx.lineTo(x,y);ctx.strokeStyle=axisColors[i];ctx.lineWidth=1.5;ctx.stroke();ctx.fillStyle=axisColors[i];ctx.fillText('XYZ'[i],x+3,y-2);});
  ctx.font='10px Segoe UI, Microsoft YaHei';ctx.fillStyle='#637d8c';ctx.textAlign='right';ctx.fillText(s.camera.preset==='3d'?'透视 3D':({'xz':'正视 XZ','xy':'俯视 XY','yz':'侧视 YZ'}[s.camera.preset]||'正交视图'),w-10,17);
  ctx.fillText('网格 '+num(b.step*1000)+' mm',w-9,h-9);ctx.textAlign='left';
}
function setCameraPreset(s,preset){
  s.camera=defaultCamera();s.camera.preset=preset;
  if(preset==='xz'){s.camera.yaw=-Math.PI/2;s.camera.pitch=0;}
  if(preset==='xy'){s.camera.yaw=-Math.PI/2;s.camera.pitch=Math.PI/2-.001;}
  if(preset==='yz'){s.camera.yaw=0;s.camera.pitch=0;}
  update(s);
}
function bindOrbit(canvas,s){
  canvas.tabIndex=0;canvas.title='拖动旋转；Shift + 拖动平移；滚轮缩放；双击复位。方向键旋转，+ / − 缩放。';
  let pointer=null;
  canvas.addEventListener('pointerdown',e=>{if(e.button!==0)return;pointer={id:e.pointerId,x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);canvas.classList.add('dragging');e.preventDefault();});
  canvas.addEventListener('pointermove',e=>{if(!pointer||pointer.id!==e.pointerId)return;const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;pointer.x=e.clientX;pointer.y=e.clientY;
    if(e.shiftKey){const cam=cameraMatrix(s,1),factor=s.bounds.size*.004/s.camera.zoom;const right=[cam.view[0],cam.view[4],cam.view[8]],up=[cam.view[1],cam.view[5],cam.view[9]];s.camera.pan=V3.add(s.camera.pan,V3.add(V3.mul(right,-dx*factor),V3.mul(up,dy*factor)));}
    else{s.camera.yaw-=dx*.009;s.camera.pitch=Math.max(-1.48,Math.min(1.48,s.camera.pitch+dy*.009));s.camera.preset='3d';}
    update(s);
  });
  const end=()=>{pointer=null;canvas.classList.remove('dragging');};canvas.addEventListener('pointerup',end);canvas.addEventListener('pointercancel',end);canvas.addEventListener('lostpointercapture',end);
  canvas.addEventListener('wheel',e=>{e.preventDefault();s.camera.zoom=Math.max(.3,Math.min(5,s.camera.zoom*Math.exp(-e.deltaY*.0015)));update(s);},{passive:false});
  canvas.addEventListener('dblclick',()=>setCameraPreset(s,'3d'));
  canvas.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();s.camera.preset='3d';s.camera.yaw+=e.key==='ArrowLeft'?.12:e.key==='ArrowRight'?-.12:0;s.camera.pitch=Math.max(-1.48,Math.min(1.48,s.camera.pitch+(e.key==='ArrowUp'?.1:e.key==='ArrowDown'?-.1:0)));}
    else if(['+','=','-'].includes(e.key)){e.preventDefault();s.camera.zoom=Math.max(.3,Math.min(5,s.camera.zoom*(e.key==='-'?.9:1.1)));}else if(e.key.toLowerCase()==='r'){setCameraPreset(s,'3d');return;}else return;update(s);
  });
}
function cameraTools(s,container,expand){
  const box=document.createElement('div');box.className='camera-tools';
  box.innerHTML='<select class="camera-preset" aria-label="相机视角"><option value="3d">3D · 斜视</option><option value="xz">正视 XZ</option><option value="xy">俯视 XY</option><option value="yz">侧视 YZ</option></select><button class="camera-reset" type="button">复位</button>'+(expand?'<button class="camera-expand" type="button">放大 A/B ↗</button>':'');
  box.querySelector('select').addEventListener('change',e=>setCameraPreset(s,e.target.value));box.querySelector('.camera-reset').addEventListener('click',()=>setCameraPreset(s,'3d'));
  if(expand)box.querySelector('.camera-expand').addEventListener('click',()=>openExpanded(s));container.appendChild(box);
}
function attachSceneControls(s){s.camera=defaultCamera();cameraTools(s,s.el.querySelector('.controls'),true);s.el.querySelectorAll('canvas.scene').forEach(c=>bindOrbit(c,s));}
let expandedView=null;
function openExpanded(s){
  if(expandedView)expandedView.dialog.close();
  const dialog=document.createElement('dialog');dialog.className='scene-dialog';
  dialog.innerHTML=`<div class="dialog-head"><div><div class="eyebrow">同步三维回放 · ${escapeHTML(s.row.parameter)}</div><h2>${escapeHTML(s.row.title)}</h2></div><button class="dialog-close" type="button" aria-label="关闭放大视图">关闭 ×</button></div><div class="dialog-pair">${s.row.variants.map((v,j)=>`<section class="${j?'b':'a'}"><div class="variant-head"><span class="letter">${v.variant}</span><strong>${escapeHTML(valueLabel(s.row,v.value))}</strong></div><canvas class="scene expanded-scene" data-variant="${j}" aria-label="${v.variant} 放大三维轨迹"></canvas><div class="metric"><strong>${num(metricLabel(s.row,v).number)}</strong><span>${metricLabel(s.row,v).unit} · ${escapeHTML(metricLabel(s.row,v).name)}</span></div></section>`).join('')}</div><div class="dialog-controls"><button class="dialog-play" type="button">回放</button><output class="dialog-clock"></output><input class="dialog-timeline" type="range" min="0" max="1000" aria-label="放大视图同步进度"></div><p class="orbit-hint">拖动旋转 · 滚轮缩放 · Shift 拖动平移 · A/B 相机联动 · Esc 关闭</p>`;
  document.body.appendChild(dialog);expandedView={dialog,s};cameraTools(s,dialog.querySelector('.dialog-controls'),false);
  dialog.querySelectorAll('canvas').forEach(c=>bindOrbit(c,s));dialog.querySelector('.dialog-close').addEventListener('click',()=>dialog.close());
  dialog.querySelector('.dialog-play').addEventListener('click',()=>{if(s.progress>=1)s.progress=0;s.playing=!s.playing;update(s);});
  dialog.querySelector('.dialog-timeline').addEventListener('input',e=>{s.progress=Number(e.target.value)/1000;s.playing=false;update(s);});
  dialog.addEventListener('close',()=>{if(expandedView?.dialog===dialog)expandedView=null;dialog.remove();});
  dialog.showModal();update(s);dialog.querySelector('canvas').focus();
}
function update3DExtras(s){
  s.el.querySelectorAll('.camera-preset').forEach(el=>el.value=s.camera.preset);
  if(expandedView?.s!==s)return;const dialog=expandedView.dialog;
  dialog.querySelectorAll('.camera-preset').forEach(el=>el.value=s.camera.preset);
  dialog.querySelectorAll('canvas').forEach((c,j)=>drawScene(c,s.row,s.row.variants[j],s.progress,j,s.bounds));
  dialog.querySelector('.dialog-timeline').value=Math.round(s.progress*1000);dialog.querySelector('.dialog-clock').value=(s.progress*s.row.duration).toFixed(3)+' / '+s.row.duration.toFixed(3)+' s';dialog.querySelector('.dialog-play').textContent=s.playing?'❚❚ 暂停':'▶ 回放';
}
window.addEventListener('resize',()=>{if(expandedView)update(expandedView.s);});
