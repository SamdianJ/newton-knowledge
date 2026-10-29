import asyncio, json, sys, time, os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(r'D:\RAG\Newton knowledge')
OUT=ROOT/'planning/review'
calls=[]
def add(label,tool,**arguments): calls.append(dict(label=label,tool=tool,arguments=arguments))
add('A1','search_knowledge',query='full_surface 穿模',solver='vbd',limit=5)
add('A2','get_parameter',name='enable_rigid_soft_full_surface_contact',solver='vbd')
add('A3','get_relations',node_id='pipeline:enable_rigid_soft_full_surface_contact')
add('A4','get_experiment',experiment_id='full_surface',solver='vbd')
add('A5','search_knowledge',query='CollisionPipeline full surface',solver='mujoco',limit=5)
add('A6','get_parameter',name='enable_rigid_soft_full_surface_contact',solver='mujoco')
add('A7','get_source',path='newton/_src/sim/collide.py',start_line=1275,max_lines=35)
add('B1','search_knowledge',query='ControllerDifferentialIK',limit=5)
add('B2','search_knowledge',query='ArticulationView',limit=5)
add('B3','search_knowledge',query='joint_target_q',solver='mujoco',limit=5)
add('B4','get_parameter',name='joint_target_q',solver='mujoco')
add('B5','search_knowledge',query='SensorContact',limit=5)
add('B6','get_source',path='newton/controllers.py',max_lines=50)
add('C1','search_knowledge',query='SolverCoupledADMM',limit=6)
add('C2','search_knowledge',query='coupling',limit=6)
add('C3','search_knowledge',query='integrate_with_external_rigid_solver',solver='vbd',limit=5)
add('C4','get_parameter',name='integrate_with_external_rigid_solver',solver='vbd')
add('C5','get_relations',node_id='newton:1.7.0:SolverVBD:integrate_with_external_rigid_solver')
add('C6','get_source',path='docs/concepts/coupling.rst',max_lines=85)
add('D1','get_parameter',name='iterations',solver='vbd')
add('D2','get_parameter',name='iterations',solver='mujoco')
add('D3','get_parameter',name='config.padmm.max_iterations',solver='kamino')
add('D4','get_experiment',experiment_id='iterations',solver='mujoco')
add('E1','search_knowledge',query='iterations',limit=2)
add('E2','search_knowledge',query='iterations',limit=20)
add('E3','search_knowledge',query='zzzz_no_such_module_88331')
add('E4','get_parameter',name='iterations')
add('E5','get_parameter',name='iterations',version='latest')
add('E6','get_document')
add('E7','search_knowledge',query='agent',solver='mujoco',kind='document')
add('E8','search_knowledge',query='agent',kind='document')
add('E9','search_knowledge',query='collision',stage='collision')
add('E10','get_document',path='solvers/mujoco/theory.md',max_lines=5)
add('E11','get_document',path='solvers/mujoco/theory.md',start_line=6,max_lines=5)
async def main():
    config=StdioServerParameters(command=sys.executable,args=['-B','-X','utf8',str(ROOT/'mcp_service/server.py')],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONIOENCODING':'utf-8'},cwd=str(OUT))
    results=[]
    with (OUT/'mcp-stderr.log').open('w',encoding='utf8') as err:
      async with stdio_client(config,errlog=err) as (read,write):
        async with ClientSession(read,write,read_timeout_seconds=30) as session:
          init=await session.initialize()
          tools=await session.list_tools()
          (OUT/'mcp-schema.json').write_text(tools.model_dump_json(by_alias=True,indent=2),encoding='utf8')
          for call in calls:
            t=time.perf_counter()
            result=(await session.call_tool(call['tool'],call['arguments'])).model_dump(by_alias=True,exclude_none=True)
            payload=json.dumps(result.get('structuredContent',result.get('content')),ensure_ascii=False)
            row={**call,'elapsed_ms':round((time.perf_counter()-t)*1000,2),'payload_chars':len(payload),'wire_chars':len(json.dumps(result,ensure_ascii=False)),'result':result}
            results.append(row)
            print(call['label'],call['tool'],'ERROR' if result.get('isError') else 'OK',len(payload),flush=True)
    (OUT/'mcp-call-results.json').write_text(json.dumps({'initialized':init.model_dump(by_alias=True,exclude_none=True),'calls':results},ensure_ascii=False,indent=2),encoding='utf8')
asyncio.run(main())
