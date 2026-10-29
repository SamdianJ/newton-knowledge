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
function qrotate(q,v){const n=Math.hypot(...q)||1,[x,y,z,w]=q.map(a=>a/n),t=V3.mul(V3.cross([x,y,z],v),2);return V3.add(v,V3.add(V3.mul(t,w),V3.cross([x,y,z],t)));}
function bodyPoint(poses,body,p){return body<0?p:V3.add(poses[body].slice(0,3),qrotate(poses[body].slice(3),p));}
function solidMesh(scene,poses,index){
 const triangles=[],lines=[],lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
 const primary=index?[.88,.36,.13]:[.10,.48,.66],edge=index?[.43,.18,.07]:[.04,.22,.31];
 const vertex=(out,p,n,c)=>out.push(...p,...n,...c);
 function line(a,b,color=edge){vertex(lines,a,[0,0,0],color);vertex(lines,b,[0,0,0],color);}
 function triangle(a,b,c,color=primary){const n=V3.norm(V3.cross(V3.sub(b,a),V3.sub(c,a)));for(const p of [a,b,c])vertex(triangles,p,n,color);}
 for(const [si,s] of scene.shapes.entries()){
  const color=s.label?.includes('指针')||s.label?.includes('标记')?[.97,.77,.25]:primary;
  const point=p=>bodyPoint(poses,s.body,V3.add(s.position||[0,0,0],qrotate(s.quaternion||[0,0,0,1],p)));
  const world=p=>{const v=point(p);for(let i=0;i<3;i++){lo[i]=Math.min(lo[i],v[i]);hi[i]=Math.max(hi[i],v[i]);}return v;};
  if(s.type==='box'){
   const v=[];for(const x of [-1,1])for(const y of [-1,1])for(const z of [-1,1])v.push(world([x*s.half_extents[0],y*s.half_extents[1],z*s.half_extents[2]]));
   for(const f of [[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]]){triangle(v[f[0]],v[f[1]],v[f[2]],color);triangle(v[f[0]],v[f[2]],v[f[3]],color);for(let j=0;j<4;j++)line(v[f[j]],v[f[(j+1)%4]]);}
  }else if(s.type==='sphere'){
   for(let j=0;j<unitSphere.length;j+=3){const points=unitSphere.slice(j,j+3).map(p=>world(V3.mul(p,s.radius)));const stripe=Math.atan2(unitSphere[j][1],unitSphere[j][0]);triangle(...points,stripe>0&&stripe<.45?[.97,.78,.3]:color);}
   for(const plane of [0,1])for(let j=0;j<48;j++){const p=t=>point(plane===0?[s.radius*Math.cos(t),s.radius*Math.sin(t),0]:[s.radius*Math.cos(t),0,s.radius*Math.sin(t)]);line(p(j*Math.PI/24),p((j+1)*Math.PI/24));}
  }else if(s.type==='cylinder'){
   const axis=s.axis||'z';const p=(r,t,h)=>world(axis==='y'?[r*Math.cos(t),h,r*Math.sin(t)]:axis==='x'?[h,r*Math.cos(t),r*Math.sin(t)]:[r*Math.cos(t),r*Math.sin(t),h]);
   for(let j=0;j<48;j++){const a=j*Math.PI/24,b=(j+1)*Math.PI/24,h=s.half_height,aa=p(s.radius,a,-h),ab=p(s.radius,b,-h),ba=p(s.radius,a,h),bb=p(s.radius,b,h);triangle(aa,ba,bb,color);triangle(aa,bb,ab,color);triangle(p(0,0,-h),ab,aa,color);triangle(p(0,0,h),ba,bb,color);line(aa,ab);line(ba,bb);if(j%12===0)line(aa,ba);}
  }else throw Error('Unsupported saved shape '+s.type);
 }
 return {triangles,lines,worldBounds:{lo,hi},shapeTriangles:triangles.length/27,line,triangle};
}
function replayBounds(item,scenes,all){
 const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
 item.replay.forEach((r,k)=>{const frames=all?r.body_q:[r.body_q[0]];for(const poses of frames)for(const s of scenes[k].shapes){const p=bodyPoint(poses,s.body,s.position||[0,0,0]);const radius=s.type==='box'?Math.hypot(...s.half_extents):s.type==='cylinder'?Math.hypot(s.radius,s.half_height):s.radius;for(let i=0;i<3;i++){lo[i]=Math.min(lo[i],p[i]-radius);hi[i]=Math.max(hi[i],p[i]+radius);}}if(scenes[k].floor!==null&&scenes[k].floor!==undefined)lo[2]=Math.min(lo[2],scenes[k].floor);});
 const span=hi.map((x,i)=>x-lo[i]),size=Math.max(...span,.06);return {lo,hi,size,center:hi.map((x,i)=>(x+lo[i])/2),radius:Math.max(Math.hypot(...span)/2,size*.55),step:roundedStep(size/7),gridZ:scenes[0].floor??lo[2]-size*.12};
}
function drawSolid(canvas,state,replay,scene,frame,variant){
 const width=canvas.clientWidth,height=canvas.clientHeight;if(!width||!height)return;
 const dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);
 if(renderer3D.error){ctx.fillText(renderer3D.error,15,30);canvas.dataset.renderer='unavailable';return;}
 const poses=replay.body_q[Math.min(frame,replay.body_q.length-1)],g=solidMesh(scene,poses,variant),b=state.bounds,cam=cameraMatrix(state,width/height);
 const range=b.size*.7,minX=b.center[0]-range,maxX=b.center[0]+range,minY=b.center[1]-range,maxY=b.center[1]+range,z=b.gridZ;
 if(scene.floor!==null&&scene.floor!==undefined){const a=[minX,minY,z],c=[maxX,maxY,z];g.triangle(a,[maxX,minY,z],c,[.85,.89,.9]);g.triangle(a,c,[minX,maxY,z],[.85,.89,.9]);}
 for(let x=Math.ceil(minX/b.step)*b.step;x<=maxX;x+=b.step)g.line([x,minY,z],[x,maxY,z],[.77,.82,.85]);
 for(let y=Math.ceil(minY/b.step)*b.step;y<=maxY;y+=b.step)g.line([minX,y,z],[maxX,y,z],[.77,.82,.85]);
 // Real joint anchors are shown independently: separated markers expose closure error.
 for(const j of scene.joints||[]){const p=bodyPoint(poses,j.parent,j.parent_position),c=bodyPoint(poses,j.child,j.child_position),axis=j.axis||[0,1,0];const d=V3.mul(j.parent<0?axis:qrotate(poses[j.parent].slice(3),axis),b.size*.025);g.line(V3.sub(p,d),V3.add(p,d),[.13,.17,.21]);g.line(p,c,[.8,.15,.22]);}
 renderer3D.draw(canvas.width,canvas.height,cam.matrix,g.triangles,g.lines);ctx.drawImage(renderer3D.output,0,0,width,height);
 canvas.dataset.renderer='webgl';canvas.dataset.shapeCount=scene.shapes.length;canvas.dataset.triangleCount=g.shapeTriangles;canvas.dataset.frameIndex=Math.min(frame,replay.body_q.length-1);canvas.dataset.worldBounds=JSON.stringify(g.worldBounds);canvas.dataset.poses=JSON.stringify(poses);canvas.dataset.camera=JSON.stringify(state.camera);
 ctx.font='12px system-ui';ctx.fillStyle='#456070';ctx.fillText('A/B 同相机、同尺度 · m',12,20);ctx.textAlign='right';ctx.fillText(({xz:'正视 XZ',xy:'俯视 XY',yz:'侧视 YZ'})[state.camera.preset]||'透视 3D',width-12,20);ctx.textAlign='left';
 const off=poses.filter(p=>{const q=project3(p,cam.matrix,width,height);return q[0]<0||q[0]>width||q[1]<0||q[1]>height;}).length;
 ctx.fillStyle=off?'#a7452b':'#456070';ctx.fillText(off?`${off} 个中心超出场景范围，可选“全轨迹”查看`:`网格 ${Number(b.step.toPrecision(3))} m · 拖动旋转 / 滚轮缩放`,12,height-12);
 const o=[30,height-42],axes=[[1,0,0],[0,1,0],[0,0,1]],colors=['#b14d4a','#3b886a','#3872b8'];axes.forEach((a,i)=>{const x=o[0]+20*(cam.view[0]*a[0]+cam.view[4]*a[1]+cam.view[8]*a[2]),y=o[1]-20*(cam.view[1]*a[0]+cam.view[5]*a[1]+cam.view[9]*a[2]);ctx.strokeStyle=ctx.fillStyle=colors[i];ctx.beginPath();ctx.moveTo(...o);ctx.lineTo(x,y);ctx.stroke();ctx.fillText('XYZ'[i],x+2,y);});
}
function preset(state,name){state.camera=defaultCamera();state.camera.preset=name;if(name==='xz'){state.camera.yaw=-Math.PI/2;state.camera.pitch=0;}if(name==='xy'){state.camera.yaw=-Math.PI/2;state.camera.pitch=Math.PI/2-.001;}if(name==='yz'){state.camera.yaw=0;state.camera.pitch=0;}}
function orbit(canvas,state,paint){let drag=null;canvas.tabIndex=0;canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId);};canvas.onpointerup=canvas.onpointercancel=()=>drag=null;canvas.onpointermove=e=>{if(!drag)return;const dx=e.clientX-drag[0],dy=e.clientY-drag[1];if(e.shiftKey){const c=cameraMatrix(state,1),f=state.bounds.size*.003/state.camera.zoom;state.camera.pan=V3.add(state.camera.pan,[(-dx*c.view[0]+dy*c.view[1])*f,(-dx*c.view[4]+dy*c.view[5])*f,(-dx*c.view[8]+dy*c.view[9])*f]);}else{state.camera.yaw-=dx*.009;state.camera.pitch=Math.max(-1.48,Math.min(1.48,state.camera.pitch+dy*.009));state.camera.preset='3d';}drag=[e.clientX,e.clientY];paint();};canvas.addEventListener('wheel',e=>{e.preventDefault();state.camera.zoom=Math.max(.2,Math.min(12,state.camera.zoom*Math.exp(-e.deltaY*.0015)));paint();},{passive:false});canvas.ondblclick=()=>{preset(state,'3d');paint();};}
window.SolidReplay={draw:drawSolid,bounds:replayBounds,preset,orbit,defaultCamera,mesh:solidMesh};
