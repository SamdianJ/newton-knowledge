'use strict';

function solverRecord(id){
  for(const [key,c] of Object.entries(APP.solvers||{})){
    if(key==='vbd')continue;
    const r=[...c.parameters,...c.model_inputs,...c.claims,...c.mappings,...c.diagnostics,...c.papers].find(r=>r.id===id);
    if(r)return r;
  }
}
function solverNodeRoute(node){
  if(!node?.solver||node.solver==='vbd')return null;
  const base='#solver/'+node.solver,record=solverRecord(node.id);
  if(node.type==='parameter')return base+'/parameter/'+enc(record.name);
  if(node.type==='model_input')return base+'/model/'+enc(record.field);
  if(node.type==='paper')return base+'/papers';
  if(node.type==='solver')return base;
  return null;
}
function solverCards(){
  return `<div class="section-head"><h2>选择求解器</h2><span>固定 Newton 1.7.0 · 证据按 solver 区分</span></div><div class="grid-3">${Object.entries(APP.solvers||{}).map(([id,c])=>`<article class="card"><h3><a href="${id==='vbd'?'#home':'#solver/'+id}">${esc(c.name)}</a></h3><p>${id==='vbd'?'原理、参数、模型输入与 17 组实测 A/B。':id==='mujoco'?'广义坐标、模型转换、接触软化与 CPU/Warp 后端。':'最大坐标、闭环机械系统、PADMM/DVI 与分层配置。'}</p><a class="card-link" href="${id==='vbd'?'#home':'#solver/'+id}">${id==='vbd'?'查看 VBD':'进入知识库'} →</a></article>`).join('')}</div>`;
}
function renderSolverRoute(id,page='',name='',query=new URLSearchParams()){
  const c=APP.solvers[id];if(!c||id==='vbd'){location.hash='#home';return;}
  const base='#solver/'+id,head=(title,lead='')=>pageHead(title,lead,'NEWTON 1.7.0 / '+c.name);
  const nav=`<div class="segmented" style="margin-bottom:24px"><a href="${base}">总览</a><a href="${base}/parameters">参数与配置</a><a href="${base}/models">模型输入</a><a href="${base}/papers">论文</a><a href="${base}/diagnostics">实验计划</a></div>`;
  const docs=APP.documents.filter(d=>d.solver===id);
  const notice=`<div class="notice warm">本轮为静态源码核查、论文背景及待验证诊断设计，尚无 ${esc(c.name)} 参数 A/B 实测。VBD 实验不能直接作为本 solver 的验证。${id==='kamino'?'固定版本文档将 Kamino 标为 BETA 1 / experimental。':''}</div>`;
  if(!page){
    main.innerHTML=head(c.name+' 知识库',id==='mujoco'?'沿着模型转换、接触响应、数值求解与时间积分组织证据。':'按 Config 与子配置组织最大坐标机械系统、闭环约束和 PADMM/DVI 证据。')+nav+
    `<div class="stats"><div class="stat"><div class="value">${c.counts.constructor_optional}</div><span>可选构造参数</span></div><div class="stat"><div class="value">${c.counts.config_fields}</div><span>配置字段</span><small>另含 ${c.counts.reset_fields} 个 reset 字段</small></div><div class="stat"><div class="value">${c.counts.papers}</div><span>本地论文</span></div><div class="stat"><div class="value">0</div><span>新增实测实验</span><small>诊断方案均标为待验证</small></div></div>`+notice+
    `<div class="section-head"><h2>原理、实现与配置</h2></div><div class="grid-3">${docs.map(d=>`<article class="card"><h3><a href="${docLink(d.path)}">${esc(d.title)}</a></h3><p>${esc(d.path)}</p><a class="card-link" href="${docLink(d.path)}">阅读全文 →</a></article>`).join('')}</div>`+
    `<div class="section-head"><h2>关键源码结论</h2></div>${c.claims.map(r=>`<a class="related-item" href="#evidence/${enc(r.id)}">${esc(r.statement_zh)}<small>源码核查 · 查看对应参数与来源 →</small></a>`).join('')}`;
  }else if(page==='parameters'||page==='models'){
    const model=page==='models',rows=model?c.model_inputs:c.parameters;
    main.innerHTML=head(model?'重点模型输入':'参数与分层配置','声明默认值与给定 Model/后端的最终值分开解释。')+nav+
    `<div class="filters"><input id="solver-param-filter" type="search" aria-label="筛选 solver 参数" placeholder="按名称、作用或配置层筛选…"><span id="solver-param-count"></span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>参数 / 作用</th><th>所属层</th><th>声明默认 / 单位</th></tr></thead><tbody id="solver-param-rows"></tbody></table></div>`+notice;
    const filter=()=>{const q=$('#solver-param-filter').value.toLowerCase(),found=rows.filter(r=>JSON.stringify([r.name||r.field,r.summary_zh||r.description_zh,r.category]).toLowerCase().includes(q));$('#solver-param-count').textContent=found.length+' / '+rows.length;$('#solver-param-rows').innerHTML=found.map(r=>`<tr><td><a href="${base}/${model?'model':'parameter'}/${enc(r.name||r.field)}"><code>${esc(r.name||r.field)}</code></a><p class="summary">${esc(r.summary_zh||r.description_zh)}</p></td><td>${esc(r.layer||'model_input')}</td><td><code>${esc(model?r.units:r.required?'必填':r.declared_default_expression)}</code></td></tr>`).join('');};$('#solver-param-filter').addEventListener('input',filter);filter();
  }else if(page==='parameter'||page==='model'){
    const model=page==='model',r=(model?c.model_inputs:c.parameters).find(r=>(r.name||r.field)===name);if(!r)throw Error('未找到此 solver 中的参数。');
    const related=c.claims.filter(claim=>claim.parameter_ids.includes(r.id));
    main.innerHTML=head(`<code>${esc(name)}</code>`,esc(r.summary_zh||r.description_zh))+nav+
    `<div class="detail-grid"><div><div class="detail-panel"><h2>定义与默认解析</h2><div class="badges">${badge(c.name)}${badge(r.layer||'model_input')}${badge('源码核查')}</div><dl class="kv"><dt>所属位置</dt><dd>${esc(r.owner||'newton.Model / custom attributes')}</dd><dt>类型 / 单位</dt><dd><code>${esc(r.type||r.units)}</code></dd><dt>声明默认值</dt><dd><code>${esc(model?'读取实际 Model':r.required?'必填':r.declared_default_expression)}</code></dd><dt>最终默认策略</dt><dd>${esc(r.default_policy||r.resolved_default)}</dd></dl><pre class="raw-doc">${esc(r.documentation||r.description_zh)}</pre>${sourceLinks(r.definition||r.model_definition)}</div>${related.length?`<div class="detail-panel"><h2>关联结论</h2>${related.map(cl=>`<a class="related-item" href="#evidence/${enc(cl.id)}">${esc(cl.statement_zh)}</a>`).join('')}</div>`:''}</div><aside><div class="detail-panel"><h2>继续追溯</h2><a class="related-item" href="#evidence/${enc(r.id)}">证据关系 →</a><a class="related-item" href="${docLink('solvers/'+id+'/parameters.md')}">完整参数手册 →</a><a class="related-item" href="${base}/diagnostics">待验证实验计划 →</a></div></aside></div>`+notice;
  }else if(page==='papers'){
    main.innerHTML=head(c.name+' · 论文与实现')+nav+`<div class="grid-3">${c.papers.map(p=>`<article class="card paper-card"><div class="paper-id">${p.year}</div><h3>${esc(p.title)}</h3><p>${esc(p.role)}</p><div class="actions"><a class="btn primary" href="/files/${p.local_path}" target="_blank">本地 PDF · ${p.pages} 页 ↗</a><a class="btn" href="#evidence/${enc(p.id)}">证据关系</a></div></article>`).join('')}</div><div class="actions" style="margin-top:24px"><a class="btn" href="${docLink('solvers/'+id+'/paper-code-map.md')}">机制—源码对应 →</a><a class="btn" href="${docLink('solvers/'+id+'/papers.md')}">论文笔记 →</a></div>`+notice;
  }else if(page==='diagnostics'){
    main.innerHTML=head(c.name+' · 参数实验计划','以下方案尚未执行，后续实际运行后再补充 A/B 数据和物理结论。')+nav+notice+c.diagnostics.map(d=>`<article class="detail-panel"><div class="badges">${badge('待验证','proposed')}</div><h2>${esc(d.symptom)}</h2><ol>${d.plan.map(p=>`<li>${esc(p)}</li>`).join('')}</ol><p>${esc(d.caution)}</p><a href="#evidence/${enc(d.id)}">查看关联参数 →</a></article>`).join('');
  }else throw Error('页面不存在。');
}
