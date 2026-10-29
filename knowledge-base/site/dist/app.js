'use strict';
const $=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const enc=encodeURIComponent,main=$('#main');let APP,GRAPH,navigation=0;
const kinds={parameter:'构造参数',model_input:'模型输入',claim:'源码结论',diagnostic:'诊断方案',mapping:'论文—代码映射',mechanism_mapping:'机制映射',document:'知识文档',paper:'论文',experiment:'CPU 探针',lab_experiment:'参数实验',code_symbol:'源码符号',solver:'求解器',pipeline_setting:'碰撞管线',process_setting:'时间步设置',capabilities:'功能边界'};
const docDesc={theory:'从隐式积分、顶点块更新，到 ALM 与 DAT 的分工。',implementation:'沿构造、碰撞、迭代和状态更新追踪源码。',papers:'核心论文及其在 Newton 中的实现边界。','paper-code-map':'让论文机制、源码符号、参数与验证相互对应。',parameters:'完整签名、默认值解析、有效范围及弃用状态。','model-inputs':'质量、材料、几何与控制层的关键输入。',diagnostics:'按穿透、滑落、振动等现象组织诊断顺序。','version-notes':'固定版本的默认值、模式变化和未验证边界。',WORKFLOW:'把检索、证据判断和实验反馈接入 agent 流程。'};
function pageHead(title,lead='',eyebrow='NEWTON 1.7.0'){return `<div class="page-head"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1>${lead?`<p class="lead">${lead}</p>`:''}</div><div class="head-note">PINNED SOURCE<br>7e75abe28b8d</div></div>`;}
function badge(label,type=''){return `<span class="badge ${type}">${esc(label)}</span>`;}
function expLink(id){return '#experiments?case='+enc(id);}
function docLink(path){return '#doc/'+path;}
function getExp(id){return APP.experiments.find(e=>e.id===id);}
function sourceLinks(ref){if(!ref?.path)return '';return `<a class="source-link" href="#source/${enc(ref.path)}?line=${ref.line||1}">${esc(ref.path)}:${ref.line||1} ↗</a>${ref.url?`<a class="btn" target="_blank" rel="noopener" href="${esc(ref.url)}">GitHub 固定版本 ↗</a>`:''}`;}
function nodeRoute(node){
  if(!node)return '#evidence';
  const extraRoute=solverNodeRoute(node);if(extraRoute)return extraRoute;
  if(node.type==='parameter')return '#parameter/'+enc(node.label);
  if(node.type==='model_input')return '#model/'+enc(node.id.replace('model:',''));
  if(node.type==='lab_experiment')return expLink(node.experiment_id);
  if(node.type==='code_symbol'&&node.source_ref)return '#source/'+enc(node.source_ref.path)+'?line='+node.source_ref.line;
  if(node.type==='paper')return '#papers';
  if(node.type==='pipeline_setting')return '#setting/full_surface';
  if(node.type==='process_setting')return '#setting/substeps';
  return '#evidence/'+enc(node.id);
}
function recordFor(id){return [...APP.parameters,...APP.model_inputs,...APP.claims,...APP.mappings,...APP.diagnostics,...APP.papers,...APP.experiments].find(r=>r.id===id||r.record_id===id)||solverRecord(id);}
function relatedExperiments(ids){return ids.length?ids.map(id=>{const e=getExp(id);return `<a class="related-item" href="${expLink(id)}">${esc(e.title)} ↗<small>${esc(e.parameter)} · ${esc(JSON.stringify(e.values))}</small></a>`;}).join(''):'<p class="muted">尚未为该输入单独建立 A/B 实验。</p>';}
function experimentCard(e){return `<article class="card experiment-card"><div class="badges">${badge(e.group)}${badge('实测 · A/B','measured')}</div><h3><a href="${expLink(e.id)}">${esc(e.title)}</a></h3><img class="mini-plot" src="/files/experiments/vbd_parameter_lab/plots/${e.id}.svg" alt="${esc(e.metric)}时间曲线"><p>${esc(e.question)}</p><a class="card-link" href="${expLink(e.id)}">查看三维对照与量测 →</a></article>`;}

function home(){
  const c=APP.counts;
  main.innerHTML=pageHead('从原理，到可观察的参数效果。','将 Newton VBD、MuJoCo、Kamino 的论文、源码和参数连在一起，保留 VBD 的真实实验。以固定版本为基线，让每次解释和调参都有可核对的证据。','LOCAL KNOWLEDGE WORKSPACE')+
  solverCards()+`<div class="section-head"><h2>VBD 当前覆盖</h2></div><div class="stats"><div class="stat"><div class="value">${c.parameters}</div><span>可选构造参数</span><small>含默认值与源码定位</small></div><div class="stat"><div class="value">${c.papers}</div><span>核心论文</span><small>本地 PDF 与机制对应</small></div><div class="stat"><div class="value">${c.experiments}</div><span>参数实验组</span><small>${c.runs} 次运行 · 三维同步回放</small></div><div class="stat"><div class="value">${c.model_inputs}</div><span>重点模型输入</span><small>材料、几何、质量与控制</small></div></div>
  <div class="section-head"><h2>沿着证据理解 VBD</h2><a href="#docs">全部知识文档 →</a></div><div class="grid-3">
  <article class="card"><span class="step-num">01</span><div class="kicker">UNDERSTAND</div><h3>理解求解机制</h3><p>从变分形式和局部更新开始，区分 VBD、compliant ALM 与 DAT 各自解决的问题。</p><a class="card-link" href="#doc/solvers/vbd/theory.md">阅读原理与机制 →</a></article>
  <article class="card"><span class="step-num">02</span><div class="kicker">TRACE</div><h3>定位参数与实现</h3><p>查询参数的版本默认值、作用位置和关联证据，沿链接查看本地源码。</p><a class="card-link" href="#parameters">打开参数目录 →</a></article>
  <article class="card"><span class="step-num">03</span><div class="kicker">OBSERVE</div><h3>对照真实实验</h3><p>用相同场景下的 A/B 轨迹与量测，观察参数如何改变响应，再回到机制解释。</p><a class="card-link" href="#experiments">进入参数实验室 →</a></article></div>
  <div class="section-head"><h2>从这三个现象开始</h2><a href="#experiments">全部 17 组实验 →</a></div><div class="grid-3">${['full_surface','iterations','friction'].map(id=>experimentCard(getExp(id))).join('')}</div>
  <div class="home-bottom"><div class="list-links"><h3>连接知识与行动</h3><a href="#evidence/${enc('newton:1.7.0:SolverVBD:iterations')}">迭代数的证据关系<span>参数 / 源码 / 实验</span></a><a href="#doc/solvers/vbd/diagnostics.md">按现象组织诊断<span>8 组待验证方案</span></a><a href="#doc/agent/WORKFLOW.md">接入仿真重建 agent<span>检索与实验反馈</span></a></div><div class="list-links"><h3>版本与复现</h3><a href="#doc/solvers/vbd/version-notes.md">Newton 1.7.0 的适用边界<span>固定 commit</span></a><a href="#doc/experiments/vbd_parameter_lab/README.md">实验方法、数据与复现<span>CPU / 34 次运行</span></a><a href="#doc/evaluations/REPORT.md">知识库验证记录<span>结构与检索</span></a></div></div>
  <div class="notice warm">证据边界：本轮直接 A/B 覆盖 9 个可选构造参数，另含模型与流程参数。在线 latest 与 1.7.0 的默认值可能不同；实验结果只在保存的场景和条件内成立。</div><div class="footer-note">当前收录 VBD / MuJoCo / Kamino · 全站离线可用 · ${c.nodes} 个VBD 关系节点（另含 MuJoCo/Kamino 扩展） · 本地构建 ${esc(APP.built_at.slice(0,10))}</div>`;
}

function docs(){
  main.innerHTML=pageHead('知识文档','按机制、配置与使用流程组织。公式、流程图、论文和源码引用均可在本地查看。')+
  [...new Set(APP.documents.map(d=>d.group))].map(group=>`<h2 class="doc-group-title">${esc(group)}</h2><div class="grid-3">${APP.documents.filter(d=>d.group===group).map(d=>`<article class="card doc-card"><h3><a href="${docLink(d.path)}">${esc(d.title)}</a></h3><p>${esc(d.solver&& !['vbd','shared'].includes(d.solver)?'查看 '+d.title+' 的固定版本证据、参数和适用边界。':docDesc[d.path.split('/').at(-1).replace('.md','')]||'查看原始说明、证据范围和可重复的工作流程。')}</p><a class="card-link" href="${docLink(d.path)}">阅读全文 →</a></article>`).join('')}</div>`).join('');
}
async function documentPage(path,query,token){
  const res=await fetch('/api/document?path='+enc(path));if(!res.ok)throw Error('未找到这篇文档。');const doc=await res.json();if(token!==navigation)return;
  main.innerHTML=`<div class="page-head"><div><div class="eyebrow">知识文档 / ${esc(doc.group)}</div><p class="muted" style="font-size:11px">Newton 1.7.0 · 固定源码证据</p></div><a class="btn" href="/files/${path}" target="_blank">查看 Markdown 原文 ↗</a></div><div class="doc-layout"><article class="doc-article">${doc.html}</article><aside class="doc-toc"><strong>本文目录</strong>${doc.toc.flatMap(t=>t.children?.length?t.children:[t]).map(t=>`<a href="${docLink(path)}?section=${enc(t.id)}" data-section="${esc(t.id)}">${esc(t.name)}</a>`).join('')}<div style="margin-top:24px"><a href="#parameters">参数目录 →</a><a href="#experiments">参数实验室 →</a></div></aside></div>`;
  main.querySelectorAll('.math-block').forEach(el=>katex.render(el.textContent,el,{displayMode:true,throwOnError:false,trust:false,strict:'ignore'}));
  const diagrams=main.querySelectorAll('.mermaid');if(diagrams.length)await mermaid.run({nodes:diagrams});
  if(token!==navigation)return;const section=query.get('section');if(section)document.getElementById(section)?.scrollIntoView({block:'start'});
}

function directory(query){
  const tab=query.get('tab')||'constructor';
  main.innerHTML=pageHead('参数目录','区分求解器构造参数、模型输入与流程设置。点击条目可查看默认值、源码，以及已完成的参数实验。')+
  `<div class="segmented"><a class="${tab==='constructor'?'active':''}" href="#parameters">构造参数 47</a><a class="${tab==='model'?'active':''}" href="#parameters?tab=model">模型输入 20</a><a class="${tab==='process'?'active':''}" href="#parameters?tab=process">流程设置 2</a></div><div class="filters"><input id="param-filter" type="search" placeholder="按名称或作用筛选…" aria-label="筛选参数"><select id="category-filter" aria-label="参数类别"><option value="">全部类别</option></select><label><input id="measured-filter" type="checkbox" style="width:auto"> 仅显示有关联实验</label><span class="count" id="param-count"></span></div><div class="table-wrap"><table class="data-table"><thead><tr><th style="width:45%">参数 / 作用</th><th>所属层级</th><th>默认值或单位</th><th>实验关联</th></tr></thead><tbody id="parameter-rows"></tbody></table></div><div class="notice">参数手册的基础条目来自源码核查。绿色标记表示已关联本轮实验；组干预只证明组合效果，不代表其中每项都已独立验证。</div>`;
  let rows;
  if(tab==='constructor')rows=APP.parameters.filter(p=>!p.required).map(p=>({...p,label:p.name,description:p.summary_zh,level:p.category,displayDefault:typeof p.resolved_default==='object'?JSON.stringify(p.resolved_default):p.resolved_default,route:'#parameter/'+enc(p.name)}));
  else if(tab==='model')rows=APP.model_inputs.map(p=>({...p,label:p.field,description:p.description_zh,level:'Model 输入',displayDefault:p.units,route:'#model/'+enc(p.field)}));
  else rows=['full_surface','substeps'].map(id=>{const e=getExp(id);return {label:e.parameter,description:e.question,level:e.group,displayDefault:'见具体场景配置',route:'#setting/'+id,experiments:[id]};});
  for(const cat of [...new Set(rows.map(p=>p.level))])$('#category-filter').insertAdjacentHTML('beforeend',`<option value="${esc(cat)}">${esc(cat)}</option>`);
  const filter=()=>{const q=$('#param-filter').value.toLowerCase(),cat=$('#category-filter').value,only=$('#measured-filter').checked;const visible=rows.filter(p=>(!q||(p.label+' '+p.description).toLowerCase().includes(q))&&(!cat||p.level===cat)&&(!only||p.experiments.length));
    $('#param-count').textContent=`${visible.length} / ${rows.length} 个条目`;
    $('#parameter-rows').innerHTML=visible.map(p=>`<tr><td><a href="${p.route}"><code>${esc(p.label)}</code></a><p class="summary">${esc(p.description)}</p></td><td>${esc(p.level)}</td><td class="default"><code>${esc(p.displayDefault??'None')}</code></td><td>${p.experiments.length?`<a href="${expLink(p.experiments[0])}">${badge(p.experiments.length+' 组实验','measured')}</a>`:badge('待探索','neutral')}</td></tr>`).join('')||'<tr><td colspan="4" class="empty">没有匹配条目。</td></tr>';
  };$('#param-filter').addEventListener('input',filter);$('#category-filter').addEventListener('change',filter);$('#measured-filter').addEventListener('change',filter);filter();
}

function parameterPage(name,model=false){
  const p=(model?APP.model_inputs:APP.parameters).find(p=>(model?p.field:p.name)===name);if(!p)throw Error('未找到该参数。');
  const refs=model?[p.model_definition,p.consumer]:[p.definition];const claims=APP.claims.filter(c=>c.parameter_ids?.includes(p.id));
  main.innerHTML=pageHead(`<code>${esc(name)}</code>`,esc(model?p.description_zh:p.summary_zh),(model?'MODEL INPUT':'SOLVER PARAMETER')+' / NEWTON 1.7.0')+
  `<div class="detail-grid"><div><div class="detail-panel"><h2>参数解释</h2><div class="badges">${badge(model?'Model 输入':p.category)}${badge('源码核查')}${p.experiments.length?badge('有关联实测','measured'):badge('尚无独立 A/B','neutral')}</div><dl class="kv"><dt>所属位置</dt><dd>${esc(model?'newton.Model':p.owner)}</dd><dt>类型 / 单位</dt><dd><code>${esc(model?p.units:p.type+' / '+p.units)}</code></dd><dt>声明默认值</dt><dd><code>${esc(model?'由 ModelBuilder / 场景设置决定':p.declared_default_expression??'必填')}</code></dd><dt>解析后默认值</dt><dd><code>${esc(model?p.default_policy:typeof p.resolved_default==='object'?JSON.stringify(p.resolved_default):p.resolved_default)}</code></dd></dl>${!model?`<div class="small-title">官方源码说明</div><pre class="raw-doc">${esc(p.documentation)}</pre>`:''}<div class="notice">${esc(model?'这里没有声明跨场景通用默认值；应读取实际构建的 Model。':'尚未建立通用经验调参区间。实验中使用的两个值用于展示作用，不能直接视为推荐范围。')}</div></div>
  <div class="detail-panel"><h2>实现位置</h2>${refs.map(sourceLinks).join('<hr style="border:0;border-top:1px solid #edf1f4;margin:18px 0">')}</div>
  ${claims.length?`<div class="detail-panel"><h2>关联源码结论</h2>${claims.map(c=>`<a class="related-item" href="#evidence/${enc(c.id)}">${esc(c.statement_zh)}</a>`).join('')}</div>`:''}</div>
  <aside><div class="detail-panel"><h2>对应实验</h2>${relatedExperiments(p.experiments)}</div><div class="detail-panel"><h2>继续追溯</h2><a class="related-item" href="#evidence/${enc(p.id)}">查看一跳证据关系 →</a><a class="related-item" href="#doc/solvers/vbd/${model?'model-inputs':'parameters'}.md">阅读完整手册 →</a><a class="related-item" href="#doc/solvers/vbd/diagnostics.md">按现象排查 →</a></div></aside></div>`;
}
function settingPage(id){const e=getExp(id);if(!e)throw Error('未找到流程设置。');main.innerHTML=pageHead(`<code>${esc(e.parameter)}</code>`,esc(e.question),'PROCESS / PIPELINE SETTING')+`<div class="detail-grid"><div class="detail-panel"><h2>作用与所属层级</h2><p>${esc(e.expectation)}</p><div class="notice">${id==='full_surface'?'这是 CollisionPipeline 的接触覆盖开关，不属于 SolverVBD 的 47 个可选构造参数。':'子步数属于仿真调用流程。它改变每次 step 的 dt，不是增加一次 step 内的迭代数。'}</div><h2>本轮测量</h2><p>${esc(e.observation)}</p><div class="actions" style="margin-top:18px"><a class="btn primary" href="${expLink(id)}">打开三维 A/B 实验</a><a class="btn" href="#evidence/${enc(e.record_id)}">查看证据关系</a></div></div><aside class="detail-panel"><h2>源码依据</h2>${sourceLinks(e.source)}<a class="related-item" href="${e.guide_url}" target="_blank" rel="noopener">官方指南 ↗</a></aside></div>`;}

function experiments(query){
  const id=query.get('case')||'',view=query.get('view')==='2d'?'2d':'3d',selected=getExp(id),file=view==='3d'?'index-3d.html':'index.html';
  const url='/files/experiments/vbd_parameter_lab/'+file+'?embed=1'+(selected?'&case='+enc(id):'');
  main.innerHTML=pageHead('参数实验室','同一场景、两组设置。用真实轨迹、完整曲线和源码说明对照参数作用。')+
  `<div class="lab-toolbar"><div class="segmented"><a class="${view==='3d'?'active':''}" href="#experiments?view=3d${id?'&case='+enc(id):''}">交互三维版</a><a class="${view==='2d'?'active':''}" href="#experiments?view=2d${id?'&case='+enc(id):''}">原版视图</a></div><select id="case-select" aria-label="选择实验"><option value="">全部 17 组实验</option>${APP.experiments.map((e,i)=>`<option value="${e.id}" ${e.id===id?'selected':''}>${String(i+1).padStart(2,'0')} · ${esc(e.title)}</option>`).join('')}</select><a class="btn" target="_blank" href="${url.replace('embed=1','embed=0')}">独立窗口 ↗</a><a class="btn" href="#doc/experiments/vbd_parameter_lab/README.md">实验说明</a></div>
  ${selected?`<div class="lab-related"><span>关联知识：</span>${selected.associations.map(nid=>{const n=GRAPH.nodes.find(n=>n.id===nid);return `<a href="${nodeRoute(n)}">${esc(n?.label||nid)} →</a>`;}).join('')}<a href="#evidence/${enc(selected.record_id)}">证据关系 →</a></div>`:''}
  <iframe class="lab-frame" title="VBD 参数实验 A/B 对照" src="${url}"></iframe>`;
  $('#case-select').addEventListener('change',e=>location.hash='#experiments?view='+view+(e.target.value?'&case='+e.target.value:''));
}

function papers(){
  main.innerHTML=pageHead('论文与源码','保存原始论文、本地源码快照及两者的机制对应。所有源码定位固定在 Newton 1.7.0。')+
  `<div class="grid-3">${APP.papers.map(p=>`<article class="card paper-card"><div class="paper-id">${p.year} / ${esc(p.id.replace('paper:','').toUpperCase())}</div><h3>${esc(p.title)}</h3><div class="badges">${badge(p.pages+' 页 PDF')}${badge('方法背景')}</div><p>${esc(p.role)}</p><div class="actions"><a class="btn primary" href="/files/${p.local_path}" target="_blank">阅读本地 PDF ↗</a><a class="btn" href="#evidence/${enc(p.id)}">查看关系</a></div><small>DOI ${esc(p.doi)}<br>原作者 / 出版方权利保留</small></article>`).join('')}</div><div class="section-head"><h2>沿实现阅读</h2><a href="#doc/solvers/vbd/implementation.md">完整源码导读 →</a></div><div class="grid-3">${[['solver_vbd.py','求解器组织','构造参数、碰撞检测、迭代和状态更新。'],['particle_vbd_kernels.py','粒子与材料核','弹簧、膜、弯曲、摩擦和局部系统。'],['rigid_vbd_kernels.py','刚体与约束核','刚体块、接触、关节和 compliant ALM。']].map(([f,title,desc])=>`<article class="card"><h3>${title}</h3><p>${desc}</p><a class="card-link" href="#source/${enc('newton/_src/solvers/vbd/'+f)}?line=1"><code>${f}</code> →</a></article>`).join('')}</div><div class="notice">论文给出方法背景；当前实现的扩展、默认值与适用前提需单独核对。<a href="#doc/solvers/vbd/paper-code-map.md">阅读论文—源码对应说明 →</a></div>`;
}

function evidence(id='newton:1.7.0:SolverVBD:iterations'){
  const node=GRAPH.nodes.find(n=>n.id===id);if(!node)throw Error('该记录不在关系图中。');
  const allEdges=GRAPH.edges.filter(e=>e.source===id||e.target===id),neighbors=[...new Set(allEdges.map(e=>e.source===id?e.target:e.source))].filter(n=>n!==id);
  const priority=n=>({lab_experiment:0,claim:1,mechanism_mapping:2,paper:3,parameter:4,model_input:5,code_symbol:6,solver:8}[n.type]??7);
  const ordered=neighbors.map(id=>GRAPH.nodes.find(n=>n.id===id)).sort((a,b)=>priority(a)-priority(b)),shown=ordered.slice(0,16),height=Math.max(370,Math.ceil(shown.length/2)*70+60),center=[430,height/2];
  const color=t=>t==='lab_experiment'?'#e4f1e9':t==='paper'?'#f6eddd':t==='code_symbol'?'#eef1f5':t==='claim'?'#eee9f5':'#e4eef5';
  const shortLabel=(text,max=31)=>{let size=0,out='';for(const c of text){size+=c.charCodeAt(0)>255?2:1;if(size>max)return out+'…';out+=c;}return out;};
  let lines='',nodes='';
  shown.forEach((n,i)=>{const side=i%2,x=side?670:190,y=45+Math.floor(i/2)*70;const edge=allEdges.find(e=>e.source===n.id||e.target===n.id);const left=side?center[0]+85:x+98,right=side?x-98:center[0]-85;
    lines+=`<path d="M${left},${side?center[1]:y} C${(left+right)/2},${side?center[1]:y} ${(left+right)/2},${side?y:center[1]} ${right},${side?y:center[1]}" fill="none" stroke="#d6e3eb" stroke-width="1.3"/>`;
    const label=shortLabel(n.label);
    nodes+=`<a href="#evidence/${enc(n.id)}"><title>${esc(n.label)} · ${esc(edge.relation)}</title><rect x="${x-98}" y="${y-23}" width="196" height="46" rx="5" fill="${color(n.type)}" stroke="#d7e3eb"/><text x="${x}" y="${y-3}" text-anchor="middle" font-size="10" fill="#41677d">${esc(label)}</text><text x="${x}" y="${y+13}" text-anchor="middle" font-size="8" fill="#8fa3ae">${esc(kinds[n.type]||n.type)}</text></a>`;
  });
  const rec=recordFor(id),description=rec?.summary_zh||rec?.description_zh||rec?.statement_zh||rec?.observation||rec?.correspondence||rec?.symptom||'查看此节点连接的来源与适用范围。';
  const refs=rec?.source_refs||(node.source_ref?[node.source_ref]:rec?.definition?[rec.definition]:rec?.source?[rec.source]:[]);
  main.innerHTML=pageHead('证据关系','选择一个节点，查看它与参数、论文、源码和实验的一跳关联。关系方向与名称列在右侧，实验关联仅在对应场景中成立。')+
  `<div class="filters"><input id="node-search" type="search" list="node-options" placeholder="输入节点名称…" aria-label="查找关系节点"><datalist id="node-options">${GRAPH.nodes.map(n=>`<option value="${esc(n.label)}">${esc(kinds[n.type]||n.type)}</option>`).join('')}</datalist><button id="node-go">查看关系</button><span class="count">${APP.total_counts.nodes} 个节点 · 当前 ${neighbors.length} 个邻居${neighbors.length>16?'（图中显示前 16 个）':''}</span></div><div class="graph-layout"><div><div class="graph-canvas"><svg viewBox="0 0 860 ${height}" role="img" aria-label="${esc(node.label)}一跳证据关系">${lines}<rect x="345" y="${center[1]-34}" width="170" height="68" rx="7" fill="#315e78"/><text x="430" y="${center[1]-5}" text-anchor="middle" fill="white" font-size="11">${esc(node.label.length>23?node.label.slice(0,22)+'…':node.label)}</text><text x="430" y="${center[1]+16}" text-anchor="middle" fill="#c2d8e4" font-size="9">${esc(kinds[node.type]||node.type)}</text>${nodes}</svg></div><div class="graph-legend"><span><i></i>参数 / 机制</span><span><i style="background:#8fb39a"></i>参数实验</span><span><i style="background:#c0ac82"></i>论文</span><span><i style="background:#a5adbb"></i>源码</span></div><div class="notice">网站在原有关系图上补充了 17 个实验节点及显式参数关联，原始知识库图文件保持独立。这里不根据相邻节点推断新的因果关系。</div></div><aside class="detail-panel graph-detail"><div class="small-title">当前节点</div><h3>${esc(node.label)}</h3>${badge(kinds[node.type]||node.type)}<p style="margin-top:12px;font-size:12px">${esc(description)}</p><div class="actions">${nodeRoute(node)!=='#evidence/'+enc(id)?`<a class="btn" href="${nodeRoute(node)}">打开对应内容 →</a>`:''}</div>${refs.slice(0,2).map(sourceLinks).join('')}<div class="small-title" style="margin-top:22px">关系明细</div><ul class="edge-list">${allEdges.map(e=>{const other=GRAPH.nodes.find(n=>n.id===(e.source===id?e.target:e.source));return `<li><a href="#evidence/${enc(other.id)}">${esc(other.label)}</a><code>${e.source===id?'→':'←'} ${esc(e.relation)}</code></li>`;}).join('')||'<li>没有直接关联。</li>'}</ul></aside></div>`;
  const go=()=>{const q=$('#node-search').value.toLowerCase(),n=GRAPH.nodes.find(n=>n.label.toLowerCase()===q)||GRAPH.nodes.find(n=>n.label.toLowerCase().includes(q));if(n)location.hash='#evidence/'+enc(n.id);else toast('没有匹配节点。');};$('#node-go').addEventListener('click',go);$('#node-search').addEventListener('keydown',e=>{if(e.key==='Enter')go();});
}

async function searchPage(query,token){
  const q=query.get('q')||'';$('#query').value=q;main.innerHTML=pageHead('搜索知识库',`正在检索 ${esc(q)}…`);
  const res=await fetch('/api/search?q='+enc(q));if(!res.ok)throw Error('本地检索失败。');const result=await res.json();if(token!==navigation)return;
  main.innerHTML=pageHead('搜索结果',`“${esc(q)}” · 找到 ${result.hits.length} 条相关记录。覆盖知识文档、参数、源码结论与本轮实验。`)+
  (result.hits.map(h=>`<a class="search-result" href="${esc(h.route)}">${badge(h.solver==='shared'?'共享':h.solver||'vbd')}${badge(kinds[h.kind]||h.kind,h.kind==='lab_experiment'?'measured':h.kind==='diagnostic'?'proposed':'')}<h3>${esc(h.title)}</h3><p>${esc(h.summary.slice(0,260))}${h.summary.length>260?'…':''}</p></a>`).join('')||'<div class="empty">没有匹配结果。可以尝试参数全名，或“摩擦”“自接触”“默认值”等关键词。</div>')+'<div class="footer-note">本地词项检索与标识符匹配 · Newton 1.7.0 · 搜索结果不是模型生成的回答</div>';
}
async function sourcePage(path,query,token){
  const res=await fetch('/api/source?path='+enc(path)+'&line='+(query.get('line')||1));if(!res.ok)throw Error('未找到这段本地源码。');const source=await res.json();if(token!==navigation)return;
  main.innerHTML=pageHead('源码定位',`<code>${esc(path)}</code>`,'PINNED SOURCE / NEWTON 1.7.0')+`<div class="actions"><a class="btn" href="#source/${enc(path)}?line=${Math.max(1,source.start-130)}">← 上一段</a><a class="btn" href="#source/${enc(path)}?line=${Math.min(source.total_lines,source.end+31)}">下一段 →</a><a class="btn" href="/files/sources/newton-v1.7.0/${path}" target="_blank">查看完整文件 ↗</a><a class="btn" href="https://github.com/newton-physics/newton/blob/${APP.commit}/${path}#L${source.line}" target="_blank" rel="noopener">GitHub 固定版本 ↗</a></div><div class="source-meta">显示 ${source.start}–${source.end} / ${source.total_lines} 行 · 定位 L${source.line}</div><pre class="source-code">${source.lines.map((text,i)=>`<span class="line ${source.start+i===source.line?'highlight':''}" id="L${source.start+i}"><span class="ln">${source.start+i}</span><span class="src">${esc(text)||' '}</span></span>`).join('')}</pre>`;
}
function toast(text){$('#toast').textContent=text;$('#toast').style.display='block';setTimeout(()=>$('#toast').style.display='none',2500);}
async function route(){
  const token=++navigation,raw=location.hash.slice(1)||'home',split=raw.indexOf('?'),path=split<0?raw:raw.slice(0,split),query=new URLSearchParams(split<0?'':raw.slice(split+1));const [type,...parts]=path.split('/'),name=decodeURIComponent(parts.join('/'));
  const navType=({solver:'home',doc:'docs',parameter:'parameters',model:'parameters',setting:'parameters',source:'papers'}[type]||type),labels={home:'总览',docs:'知识文档',parameters:'参数目录',experiments:'参数实验室',evidence:'证据关系',papers:'论文与源码',search:'搜索'};
  $('#crumb').textContent=labels[navType]||'知识库';document.title=($('#crumb').textContent)+' · Newton Knowledge';document.querySelectorAll('[data-nav]').forEach(a=>a.classList.toggle('active',a.dataset.nav===navType));document.body.classList.remove('menu-open');window.scrollTo(0,0);
  main.innerHTML='<div class="loading">正在读取本地内容…</div>';
  try{
    const selected=type==='solver'?parts[0]:type==='doc'?(parts[1]||'vbd'):type==='evidence'?(GRAPH.nodes.find(n=>n.id===name)?.solver||'vbd'):'vbd';document.querySelectorAll('[data-solver]').forEach(a=>a.classList.toggle('active',a.dataset.solver===selected));
    if(type==='solver')renderSolverRoute(parts[0],parts[1]||'',decodeURIComponent(parts.slice(2).join('/')),query);
    else if(type==='home')home();else if(type==='docs')docs();else if(type==='doc')await documentPage(name,query,token);
    else if(type==='parameters')directory(query);else if(type==='parameter')parameterPage(name);else if(type==='model')parameterPage(name,true);else if(type==='setting')settingPage(name);
    else if(type==='experiments')experiments(query);else if(type==='papers')papers();else if(type==='evidence')evidence(name||undefined);
    else if(type==='search')await searchPage(query,token);else if(type==='source')await sourcePage(name,query,token);else throw Error('页面不存在。');
  }catch(err){if(token===navigation)main.innerHTML=pageHead('无法显示这项内容',esc(err.message))+'<a class="btn" href="#home">返回总览</a>';console.error(err);}
}
$('#global-search').addEventListener('submit',e=>{e.preventDefault();const q=$('#query').value.trim();if(q)location.hash='#search?q='+enc(q);});
$('#menu').addEventListener('click',()=>document.body.classList.toggle('menu-open'));
$('.skip').addEventListener('click',e=>{e.preventDefault();main.focus();});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('#query').focus();$('#query').select();}if(e.key==='Escape')document.body.classList.remove('menu-open');});
window.addEventListener('hashchange',()=>{if(APP)route();});
(async()=>{try{[APP,GRAPH]=await Promise.all([fetch('/catalog.json').then(r=>r.json()),fetch('/graph.json').then(r=>r.json())]);mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'neutral',fontFamily:'Segoe UI, Microsoft YaHei',flowchart:{useMaxWidth:true}});await route();}catch(err){main.innerHTML='<div class="empty">本地站点未能完成加载，请重新启动服务。<br>'+esc(err.message)+'</div>';console.error(err);}})();
