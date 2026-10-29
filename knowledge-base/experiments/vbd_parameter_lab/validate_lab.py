"""Validate experimental records and the report UI in an isolated headless browser."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np

HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--skip-browser',action='store_true');args=parser.parse_args()
    data=read(HERE/'report-data.json');checks=[]
    def check(ok,label):
        checks.append({'check':label,'passed':bool(ok)})
        if not ok:print('FAILED: '+label)
    digest=hashlib.sha256((HERE/'run_lab.py').read_bytes()).hexdigest()
    check(data['environment']['solver_file_matches_snapshot'],'loaded solver matches official v1.7.0 snapshot')
    check(not data['environment']['failures'],'final run has no failed variants')
    check(len(data['experiments'])==17,'17 experiments available')
    manifest=json.loads((HERE/'official-sources.json').read_text(encoding='utf-8'))
    for doc in manifest['pages']:
        check(hashlib.sha256((HERE/doc['path']).read_bytes()).hexdigest()==doc['sha256'],'official document snapshot hash: '+doc['path'])
    for r in data['experiments']:
        a,b=r['variants'];ra=np.load(HERE/a['raw_file']);rb=np.load(HERE/b['raw_file'])
        check(a['value']==r['values'][0] and b['value']==r['values'][1],r['id']+': A/B treatments match declared values')
        check(a['config']['common']==b['config']['common']==r['common'],r['id']+': common settings identical')
        check(np.array_equal(ra['particle_q'][0],rb['particle_q'][0]) and np.array_equal(ra['body_q'][0],rb['body_q'][0]),r['id']+': initial poses identical')
        check(np.isclose(ra['time'][-1],rb['time'][-1]) and np.isclose(ra['time'][-1],r['duration']),r['id']+': identical physical horizon')
        for v,raw in [(a,ra),(b,rb)]:
            check(v['program_sha256']==digest,r['id']+' '+v['variant']+': final frozen runner hash')
            check(all(np.isfinite(raw[k]).all() for k in raw.files),r['id']+' '+v['variant']+': finite raw arrays')
            check(all(not raw[k].size or abs(raw[k]).max()<5 for k in ['particle_q','body_q']),r['id']+' '+v['variant']+': bounded scene state (<5 m, quaternion components <5)')
            check(np.allclose(raw['series'],v['curve']['value'],atol=1e-4),r['id']+' '+v['variant']+': displayed curve matches raw trajectory metric')
            check(np.isclose(float(raw['series'][-1]),v['metrics']['final'],atol=1e-4),r['id']+' '+v['variant']+': displayed final metric matches raw')
    lookup={r['id']:r for r in data['experiments']}
    a,b=[v['metrics'] for v in lookup['full_surface']['variants']]
    check(a['max_soft_contact_records']==0 and b['max_edge_face_records']>0,'full surface changes feature coverage')
    check(a['final']<-100 and b['final']>-1,'full surface supports sphere in this scene')
    a,b=[v['metrics'] for v in lookup['iterations']['variants']]
    check(b['reference_rmse_mm']<.01 and a['reference_rmse_mm']>10,'iterations compared against exact discrete linear reference')
    for v in lookup['stiffness']['variants']:
        check(abs(v['metrics']['tail_mean']-v['metrics']['static_prediction_mm'])/v['metrics']['static_prediction_mm']<.01,'spring static deflection agrees with mg/k '+v['variant'])
    check(lookup['dat']['variants'][1]['metrics']['min']>=-1e-3,'DAT point stays above plane in the tested setup')
    for v in lookup['self_margin']['variants']:
        check(abs(v['metrics']['tail_mean']-v['value']*1000)<.1,'self-contact equilibrium tracks margin '+v['variant'])
    ui={'status':'not_run'}
    if not args.skip_browser:
        from playwright.sync_api import sync_playwright
        shots=HERE/'screenshots';shots.mkdir(exist_ok=True)
        errors=[]
        ui_start=len(checks)
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1050},device_scale_factor=1)
            page.on('pageerror',lambda err:errors.append(str(err)))
            page.goto((HERE/'index.html').as_uri(),wait_until='load');page.wait_for_timeout(300)
            check(page.locator('#experiments tr').count()==17,'browser renders 17 experiment rows')
            check(page.locator('canvas.scene').count()==34,'browser renders both measured panels for every row')
            check(page.locator('.plot svg').count()==17,'browser renders all scientific time curves')
            from urllib.parse import unquote
            local_links=page.locator('a[href]').evaluate_all('(els)=>els.map(e=>e.getAttribute("href")).filter(h=>!/^https?:/.test(h))')
            missing_links=[h for h in local_links if not (HERE/unquote(h.split('#')[0])).is_file()]
            check(not missing_links,'all local report links resolve: '+str(missing_links))
            check(page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'desktop has no page-wide horizontal overflow')
            page.screenshot(path=str(shots/'desktop.png'),full_page=False)
            page.locator('#search').fill('full_surface');check(page.locator('#experiments tr:visible').count()==1,'parameter search filters to full surface')
            row=page.locator('#experiments tr:visible');before=row.locator('canvas').first.evaluate('(el)=>el.toDataURL()')
            row.locator('.timeline').evaluate('(el)=>{el.value=400;el.dispatchEvent(new Event("input",{bubbles:true}));}')
            after=row.locator('canvas').first.evaluate('(el)=>el.toDataURL()')
            check(before!=after,'timeline redraws measured positions')
            row.locator('.row-play').click();page.wait_for_timeout(350)
            check(float(row.locator('.timeline').input_value())>400,'playback advances shared time')
            page.locator('#pause-all').click();row.locator('.timeline').evaluate('(el)=>{el.value=1000;el.dispatchEvent(new Event("input",{bubbles:true}));}')
            page.locator('#search').fill('');page.locator('#group').select_option('薄膜材料')
            check(page.locator('#experiments tr:visible').count()==2,'group filter isolates two cloth material examples')
            page.screenshot(path=str(shots/'cloth.png'),full_page=False)
            page.locator('#group').select_option('');page.locator('#search').fill('摩擦')
            page.screenshot(path=str(shots/'friction.png'),full_page=False)
            page.locator('#search').fill('no-such-experiment')
            check(page.locator('#empty').is_visible(),'empty query state is visible')
            page.locator('#search').fill('');page.set_viewport_size({'width':390,'height':1000});page.wait_for_timeout(100)
            check(page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'mobile has no page-wide horizontal overflow')
            page.screenshot(path=str(shots/'mobile.png'),full_page=False)
            check(not errors,'no browser JavaScript errors: '+str(errors))
            browser.close()
        ui={'status':'passed' if all(c['passed'] for c in checks[ui_start:]) else 'failed','browser':'Microsoft Edge headless, fresh isolated profile','viewports':[[1440,1050],[390,1000]],'errors':errors,'screenshots':['screenshots/desktop.png','screenshots/cloth.png','screenshots/friction.png','screenshots/mobile.png']}
    report={'status':'passed' if all(c['passed'] for c in checks) else 'failed','date':'2026-10-27','experiments':17,'variants':34,'checks':checks,'browser':ui,'limits':'One exploratory pair per scene; no independent replication, broad physical proof, hardware performance benchmark or validation of untested constructor options.'}
    (HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':report['status'],'passed':sum(c['passed'] for c in checks),'total':len(checks),'failed':[c['check'] for c in checks if not c['passed']]},ensure_ascii=False))
    if report['status']!='passed':raise SystemExit(1)

if __name__=='__main__':main()
