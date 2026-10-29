"""Check the new renderer, data equivalence, orbit coupling and enlarged playback."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent
checks=[]
def check(ok,label):
    checks.append({'check':label,'passed':bool(ok)})
    if not ok: print('FAILED:',label)

def main():
    shots=HERE/'screenshots-3d';shots.mkdir(exist_ok=True)
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1120},device_scale_factor=1)
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.goto((HERE/'index.html').as_uri(),wait_until='load')
        original_data=page.locator('#lab-data').text_content()
        original_metrics=page.locator('.metric').all_text_contents()
        page.goto((HERE/'index-3d.html').as_uri(),wait_until='load');page.wait_for_timeout(700)
        check(page.locator('#lab-data').text_content()==original_data,'3D page embeds byte-identical simulation data to original')
        check(page.locator('.metric').all_text_contents()==original_metrics,'all original numerical results preserved')
        check(page.locator('#experiments tr').count()==17,'all 17 comparison rows present')
        check(page.locator('canvas.scene[data-renderer="webgl"]').count()==34,'all 34 panels rendered with shared WebGL renderer')
        check(page.locator('.plot svg').count()==17,'all 17 scientific curves preserved')
        from urllib.parse import unquote
        links=page.locator('a[href]').evaluate_all('(els)=>els.map(e=>e.getAttribute("href")).filter(h=>!/^https?:/.test(h))')
        check(all((HERE/unquote(h.split('#')[0])).is_file() for h in links),'all local 3D report links resolve')
        check(page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'desktop no horizontal overflow')
        page.screenshot(path=str(shots/'desktop.png'))
        page.locator('#search').fill('full_surface')
        row=page.locator('#experiments tr:visible');a=row.locator('canvas').nth(0);b=row.locator('canvas').nth(1)
        before_a=a.evaluate('(el)=>el.toDataURL()');before_b=b.evaluate('(el)=>el.toDataURL()')
        box=a.bounding_box();x=box['x']+box['width']*.5;y=box['y']+box['height']*.5
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+45,y+24,steps=8);page.mouse.up()
        check(before_a!=a.evaluate('(el)=>el.toDataURL()'),'drag rotates panel A geometry')
        check(before_b!=b.evaluate('(el)=>el.toDataURL()'),'dragging A updates B camera')
        check(a.get_attribute('data-camera')==b.get_attribute('data-camera'),'A/B share identical orbit state')
        camera_before=json.loads(a.get_attribute('data-camera'))
        page.mouse.wheel(0,-180);page.wait_for_timeout(100)
        camera_after=json.loads(a.get_attribute('data-camera'))
        check(camera_after['zoom']>camera_before['zoom'],'wheel zoom works')
        check(a.get_attribute('data-camera')==b.get_attribute('data-camera'),'A/B zoom stays linked')
        page.keyboard.down('Shift');page.mouse.down();page.mouse.move(x+20,y+10,steps=3);page.mouse.up();page.keyboard.up('Shift')
        check(any(abs(v)>1e-9 for v in json.loads(a.get_attribute('data-camera'))['pan']),'Shift drag pans the shared camera')
        row.locator('.camera-preset').select_option('xy')
        check(json.loads(a.get_attribute('data-camera'))['preset']=='xy','top XY preset works')
        row.locator('.camera-preset').select_option('xz')
        check(json.loads(a.get_attribute('data-camera'))['preset']=='xz','front XZ preset works')
        row.locator('.camera-reset').click()
        check(json.loads(a.get_attribute('data-camera'))['preset']=='3d','reset restores 3D orbit')
        row.locator('.camera-expand').click();dialog=page.locator('dialog[open]')
        check(dialog.count()==1 and dialog.locator('canvas[data-renderer="webgl"]').count()==2,'expanded paired 3D view renders')
        dialog.locator('.dialog-timeline').evaluate('(el)=>{el.value=300;el.dispatchEvent(new Event("input",{bubbles:true}));}')
        check(row.locator('.timeline').input_value()=='300','expanded timeline updates inline playback')
        check(dialog.locator('canvas').nth(0).get_attribute('data-time')==dialog.locator('canvas').nth(1).get_attribute('data-time'),'expanded A/B use identical physical time')
        dialog.locator('.dialog-play').click();page.wait_for_timeout(300)
        check(float(dialog.locator('.dialog-timeline').input_value())>300,'expanded playback advances')
        dialog.locator('.dialog-play').click()
        dialog.locator('.dialog-timeline').evaluate('(el)=>{el.value=1000;el.dispatchEvent(new Event("input",{bubbles:true}));}')
        page.screenshot(path=str(shots/'expanded.png'))
        page.keyboard.press('Escape');check(page.locator('dialog').count()==0,'Escape closes and removes expanded view')
        page.locator('#search').fill('');page.locator('#group').select_option('薄膜材料');page.wait_for_timeout(120)
        page.screenshot(path=str(shots/'cloth.png'))
        page.locator('#group').select_option('');page.locator('#search').fill('摩擦');page.wait_for_timeout(120)
        page.screenshot(path=str(shots/'friction.png'))
        page.locator('#search').fill('');page.set_viewport_size({'width':390,'height':1000});page.wait_for_timeout(150)
        check(page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'mobile no horizontal overflow')
        page.screenshot(path=str(shots/'mobile.png'))
        first=page.locator('#experiments tr').first;first.locator('.camera-expand').click()
        check(page.locator('dialog[open]').evaluate('(el)=>el.scrollWidth<=el.clientWidth+1'),'mobile expanded view no horizontal overflow')
        page.screenshot(path=str(shots/'mobile-expanded.png'))
        check(not errors,'no JavaScript errors: '+str(errors))
        browser.close()
    status='passed' if all(c['passed'] for c in checks) else 'failed'
    result={'status':status,'date':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'checks':checks,'errors':errors,'browser':'Microsoft Edge headless, isolated profile','data_source':'same recorded Newton 1.7.0 trajectories; no new simulation','screenshots':[p.relative_to(HERE).as_posix() for p in sorted(shots.glob('*.png'))]}
    (HERE/'validation-3d.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':status,'passed':sum(c['passed'] for c in checks),'total':len(checks),'errors':errors}))
    if status!='passed':raise SystemExit(1)

if __name__=='__main__':main()
