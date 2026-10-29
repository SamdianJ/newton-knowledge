"""Download original primary-source papers, preserve hashes and page-text locators."""
from pathlib import Path
import hashlib, json, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pypdf import PdfReader
ROOT = Path(__file__).resolve().parents[1]
PAPERS = [
    dict(id='paper:vbd2024', title='Vertex Block Descent', year=2024, doi='10.1145/3658179', url='https://graphics.cs.utah.edu/research/projects/vbd/vbd-siggraph2024.pdf', file='vbd2024.pdf', role='particle variational block descent foundation'),
    dict(id='paper:avbd2025', title='Augmented Vertex Block Descent', year=2025, doi='10.1145/3731195', url='https://graphics.cs.utah.edu/research/projects/avbd/Augmented_VBD-SIGGRAPH25.pdf', file='avbd2025.pdf', role='legacy rigid AVBD foundation; not identical to compliant ALM extension'),
    dict(id='paper:dat2026', title='Divide and Truncate: A Penetration and Inversion Free Framework for Coupled Multi-physics Systems', year=2026, doi='10.1145/3799902.3811143', arxiv='2604.15513v1', url='https://arxiv.org/pdf/2604.15513v1', file='dat2026.pdf', role='collision-bound and motion truncation foundation'),
]
def fetch(p):
    dest = ROOT/'sources/papers'/p['file']; dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        with urllib.request.urlopen(p['url'], timeout=120) as r: dest.write_bytes(r.read())
    reader=PdfReader(dest)
    pages=[{'page':i+1,'text':page.extract_text() or ''} for i,page in enumerate(reader.pages)]
    (dest.with_suffix('.pages.json')).write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
    (dest.with_suffix('.txt')).write_text('\n\n'.join(f"--- PDF PAGE {x['page']} ---\n{x['text']}" for x in pages),encoding='utf-8')
    return {**p,'local_path':dest.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'pages':len(pages),'downloaded_date':'2026-10-27','extraction_note':'Plain text may lose formula layout; check original PDF. Page numbers are PDF pages starting at 1.','license':'Original authors/publisher license; not relicensed by this knowledge base.'}
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as ex: records=list(ex.map(fetch,PAPERS))
    (ROOT/'manifests/papers.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{'id':r['id'],'pages':r['pages'],'sha256':r['sha256']} for r in records]))
