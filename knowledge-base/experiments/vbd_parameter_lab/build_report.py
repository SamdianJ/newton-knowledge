"""Produce a self-contained HTML report from measured JSON and Matplotlib SVG plots."""
from pathlib import Path
import json,re
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
data=json.loads((HERE/'report-data.json').read_text(encoding='utf-8'))
for row in data['experiments']:
    svg=(HERE/row['plot']).read_text(encoding='utf-8');svg=svg[svg.index('<svg'):]
    # Unique SVG IDs prevent cross-figure clipping/reference collisions when embedded inline.
    prefix=row['id']+'-';ids=re.findall(r'\bid="([^"]+)"',svg)
    for id in ids:
        svg=svg.replace('id="'+id+'"','id="'+prefix+id+'"').replace('#'+id+'"','#'+prefix+id+'"').replace('#'+id+')','#'+prefix+id+')')
    row['plot_svg']=svg
params=json.loads((ROOT/'solvers/vbd/parameters.json').read_text(encoding='utf-8'))['records']
varied={r['parameter'] for r in data['experiments']}
data['coverage']=[{'name':p['name'],'status':p['status'],'varied':p['name'] in varied} for p in params if not p['required']]
encoded=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
template=(HERE/'report.template.html').read_text(encoding='utf-8')
base=template.replace('__DATA__',encoded)
nav_style='.view-nav{display:flex;gap:7px;margin-top:15px;font-size:12px}.view-nav a,.view-nav span{padding:4px 11px;border:1px solid #cbd8e1;border-radius:5px;text-decoration:none;background:#fff}.view-nav .active{background:#e2edf4;color:#234e69;font-weight:650}'
original=base.replace('</style>',nav_style+'\n</style>').replace('</header>','<nav class="view-nav" aria-label="回放版本"><span class="active">原版视图</span><a href="index-3d.html">交互三维版 ↗</a></nav>\n</header>')
(HERE/'index.html').write_text(original,encoding='utf-8')

# Both pages embed the same frozen evidence. Only the renderer and its controls differ.
three=base
start=three.index('function projection(');end=three.index('function sampled(',start)
three=three[:start]+(HERE/'viewer-3d.js').read_text(encoding='utf-8')+'\n'+three[end:]
# Remove the legacy fixed-projection canvas renderer (the last drawScene definition).
start=three.rindex('function drawScene(');end=three.index('function update(s)',start)
three=three[:start]+three[end:]
def replace_once(old,new):
    global three
    assert three.count(old)==1, '3D integration anchor must be unique: '+old[:70]
    three=three.replace(old,new,1)
replace_once('});return el;}','});attachSceneControls(s);return el;}')
replace_once('s.bounds));}','s.bounds));update3DExtras(s);}')
replace_once('</style>',(HERE/'viewer-3d.css').read_text(encoding='utf-8')+'\n</style>')
replace_once('<title>VBD 参数实验对照 · Newton 1.7.0</title>','<title>VBD 参数实验对照 · 交互三维版 · Newton 1.7.0</title>')
replace_once('<h1>VBD 参数实验对照</h1>','<h1>VBD 参数实验对照 <span style="font-size:16px;color:#517a94;font-weight:500">/ 交互三维版</span></h1>')
replace_once('</header>','<nav class="view-nav" aria-label="回放版本"><a href="index.html">原版视图</a><span class="active">交互三维版</span></nav><p class="orbit-hint">拖动任一画面旋转 · 滚轮缩放 · Shift 拖动平移 · 每行 A/B 相机联动 · 点击“放大 A/B”查看细节</p>\n</header>')
replace_once('画面回放的是保存的粒子位置和刚体位姿；','三维画面使用保存的完整 XYZ 坐标、网格拓扑和球体位置，支持任意方向观察。参考网格仅为视觉辅助；只有实验明确配置的平面/薄板是碰撞面。很小的粒子与固定点作适度放大标记；关节实验的球体是刚体位置示意。画面回放的是保存的粒子位置和刚体位姿；')
replace_once('2026-10-27 · 原始轨迹','三维视图更新 2026-10-28 · 实验数据 2026-10-27 · 原始轨迹')
replace_once('<a href="validation.json">验证报告</a>','<a href="validation.json">数据验证报告</a><a href="validation-3d.json">三维交互验证</a>')
(HERE/'index-3d.html').write_text(three,encoding='utf-8')
print(json.dumps({'html':[str(HERE/'index.html'),str(HERE/'index-3d.html')],'rows':len(data['experiments']),'constructor_options_varied':sum(p['varied'] for p in data['coverage'])}))
