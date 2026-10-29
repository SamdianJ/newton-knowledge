"""Persist verified phase progress and idempotent Feishu completion reports."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def render_progress(progress):
    names={'P0':'范围与契约冻结','P1':'数据与导航同步迁移','P2':'公共知识与 MCP 首版','P3':'任务深度与内容扩展','P4':'多 solver 参数实验','P5':'维护与版本扩展机制'}
    rows=['# Newton 知识库构建进度','',f"PRD：{progress['prd']}；最后更新：{progress.get('updated_at',progress['started_at'])}。",'',
          '| 阶段 | 状态 | 验收证据 | 飞书汇报 |','|---|---|---|---|']
    for phase in progress['phases']:
        evidence='、'.join('['+Path(p).name+'](../'+p+')' for p in phase['evidence']) or '待验收'
        rows.append(f"| {phase['id']} {names[phase['id']]} | {phase['status']} | {evidence} | {phase['notification']} |")
    (ROOT/'planning/PROGRESS.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')


def complete(phase_id,evidence_paths,summary,next_step):
    if not evidence_paths:raise ValueError('At least one phase-specific acceptance report is required')
    progress=load(ROOT/'planning/progress.json')
    phase=next(p for p in progress['phases'] if p['id']==phase_id)
    for relative in evidence_paths:
        path=(ROOT/relative).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():raise ValueError('Evidence not found: '+relative)
        data=load(path)
        if data.get('status')!='passed' or data.get('failed',0) or data.get('phase')!=phase_id:raise ValueError('Phase evidence is not passed or does not cover this phase: '+relative)
    if phase['status']=='complete' and phase['evidence']==evidence_paths:
        render_progress(progress)
        return
    phase.update(status='complete',completed_at=datetime.now(UTC).isoformat(),evidence=evidence_paths,summary=summary,next_step=next_step)
    progress['updated_at']=datetime.now(UTC).isoformat()
    following=next((p for p in progress['phases'] if p['id']==f'P{int(phase_id[1:])+1}'),None)
    if following and following['status']=='pending':following['status']='in_progress'
    save(ROOT/'planning/progress.json',progress);render_progress(progress)


def notify(phase_id):
    progress=load(ROOT/'planning/progress.json');phase=next(p for p in progress['phases'] if p['id']==phase_id)
    if phase['status']!='complete':raise ValueError('Only verified complete phases can be reported')
    directory=ROOT/'planning/notifications';config=load(directory/'config.json')
    key=hashlib.sha256((phase_id+phase['completed_at']+json.dumps(phase['evidence'])).encode()).hexdigest()[:32]
    receipt_path=directory/(phase_id+'-'+key+'.json')
    if receipt_path.exists() and load(receipt_path).get('sent'):
        print(json.dumps({'phase':phase_id,'sent':True,'already_sent':True}));return
    text=f"## Newton 知识库 {phase_id} 阶段完成\n\nPRD v{progress['prd']} · Newton 1.7.0\n\n{phase['summary']}\n\n"
    text+='验收资料：\n'+'\n'.join('- '+p for p in phase['evidence'])
    text+='\n\n下一步：'+phase['next_step']+'\n\n本地项目：D:\\RAG\\Newton knowledge'
    message=directory/(phase_id+'-'+key+'.md');message.write_text(text+'\n',encoding='utf-8')
    executable=shutil.which('lark-cli')
    if not executable:raise RuntimeError('lark-cli missing; message is prepared but not sent')
    command=[executable,'im','+messages-send','--as','bot','--chat-id',config['chat_id'],'--markdown','-',
             '--idempotency-key','newton-'+key,'--format','json']
    environment={**os.environ,'LARKSUITE_CLI_NO_UPDATE_NOTIFIER':'1','LARKSUITE_CLI_NO_SKILLS_NOTIFIER':'1'}
    try:
        result=subprocess.run(command,input=text,encoding='utf-8',capture_output=True,cwd=directory,env=environment,timeout=45)
        response=json.loads(result.stdout) if result.stdout.strip() else {}
        sent=result.returncode==0 and response.get('ok') is True
        record={'phase':phase_id,'sent':sent,'idempotency_key':'newton-'+key,'time':datetime.now(UTC).isoformat(),
                'exit_code':result.returncode,'response':response,'stderr':result.stderr}
        save(receipt_path,record)
        phase['notification']='sent' if sent else 'failed'
        phase['notification_receipt']=receipt_path.relative_to(ROOT).as_posix()
        save(ROOT/'planning/progress.json',progress);render_progress(progress)
        if not sent:
            print(json.dumps({'phase':phase_id,'sent':False,'exit_code':result.returncode,'error':result.stderr},ensure_ascii=False))
            raise SystemExit(1)
        data=response.get('data',{})
        print(json.dumps({'phase':phase_id,'sent':True,'message_id':data.get('message_id'),'message_app_link':data.get('message_app_link')},ensure_ascii=False))
    except subprocess.TimeoutExpired:
        save(receipt_path,{'phase':phase_id,'sent':False,'outcome':'unknown_timeout','idempotency_key':'newton-'+key})
        raise RuntimeError('Delivery outcome unknown; reuse the exact idempotency key before retrying') from None


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['complete','notify']);parser.add_argument('phase')
    parser.add_argument('--evidence',action='append',default=[]);parser.add_argument('--summary',default='');parser.add_argument('--next',default='')
    args=parser.parse_args()
    if args.action=='complete':complete(args.phase,args.evidence,args.summary,args.next)
    else:notify(args.phase)
