import asyncio, json, sys, time, os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(r'D:\RAG\Newton knowledge')
OUT=ROOT/'planning/review'
calls=[]
def add(label,tool,**arguments): calls.append(dict(label=label,tool=tool,arguments=arguments))
add('F1','get_source',path='newton/_src/sim/collide.py',start_line=1338,max_lines=15)
add('F2','search_knowledge',query='collision')
add('F3','search_knowledge',query='SolverXPBD',solver='all')
add('F4','search_knowledge',query='SolverXPBD',solver='xpbd')
add('F5','search_knowledge',query='requires_grad')
add('F6','search_knowledge',query='URDF',limit=5)
add('F7','get_relations',node_id='newton:1.7.0:SolverVBD:iterations',limit=1)
add('F8','get_relations',node_id='newton:1.7.0:SolverVBD:iterations',limit=1,offset=1)
add('F9','get_experiment',experiment_id='full_surface',detail='full',solver='vbd')
add('F10','get_parameter',name='body_f',solver='mujoco')
add('F11','get_parameter',name='use_mujoco_contacts',solver='mujoco')
add('F12','search_knowledge',query='Solver Observables',limit=5)
add('F13','search_knowledge',query='contact_f',solver='mujoco',limit=5)
add('F14','search_knowledge',query='节点不存在',limit=5)
add('F15','get_source',path='docs/concepts/sensors.rst',start_line=181,max_lines=30)
add('F16','get_parameter',name='config',solver='kamino')
async def main():
    config=StdioServerParameters(command=sys.executable,args=['-B','-X','utf8',str(ROOT/'mcp_service/server.py')],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'},cwd=str(OUT))
    results=[]
    with (OUT/'mcp-extra-stderr.log').open('w',encoding='utf8') as err:
      async with stdio_client(config,errlog=err) as (read,write):
        async with ClientSession(read,write,read_timeout_seconds=30) as session:
          init=await session.initialize()
          tools=await session.list_tools()
          (OUT/'mcp-extra-schema.json').write_text(tools.model_dump_json(by_alias=True,indent=2),encoding='utf8')
          for call in calls:
            t=time.perf_counter()
            result=(await session.call_tool(call['tool'],call['arguments'])).model_dump(by_alias=True,exclude_none=True)
            payload=json.dumps(result.get('structuredContent',result.get('content')),ensure_ascii=False)
            row={**call,'elapsed_ms':round((time.perf_counter()-t)*1000,2),'payload_chars':len(payload),'wire_chars':len(json.dumps(result,ensure_ascii=False)),'result':result}
            results.append(row)
            print(call['label'],call['tool'],'ERROR' if result.get('isError') else 'OK',len(payload),flush=True)
    (OUT/'mcp-extra-results.json').write_text(json.dumps({'initialized':init.model_dump(by_alias=True,exclude_none=True),'calls':results},ensure_ascii=False,indent=2),encoding='utf8')
asyncio.run(main())
