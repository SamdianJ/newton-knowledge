"""Archive official mutable guide pages for this experimental comparison.

Run deliberately: refreshing these files changes the documentation evidence date.
Source code evidence remains fixed to the official Newton 1.7.0 commit.
"""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
import hashlib
import json

HERE = Path(__file__).resolve().parent
PAGES = [
    'solvers/index.html',
    'solvers/vbd.html',
    'concepts/simulation_tuning.html',
    'concepts/simulation_tuning_vbd.html',
    'concepts/simulation_tuning_solvers.html',
    'concepts/collisions.html',
]

def fetch(relative):
    url = 'https://newton-physics.github.io/newton/latest/' + relative
    request = Request(url, headers={'User-Agent': 'Newton-Knowledge-Experiment-Archive/1.0'})
    with urlopen(request, timeout=60) as response:
        data = response.read()
        final_url = response.url
    path = HERE / 'official-docs' / relative.replace('/', '_')
    path.write_bytes(data)
    return {'url': url, 'resolved_url': final_url,
            'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
            'path': path.relative_to(HERE).as_posix(),
            'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

if __name__ == '__main__':
    (HERE / 'official-docs').mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        pages = list(pool.map(fetch, PAGES))
    manifest = {'purpose': 'Frozen copies of mutable latest guides; not Newton 1.7.0 documentation.',
                'source_commit': '7e75abe28b8d69522bc0b34837aaed2c303dff5a',
                'attribution': 'Newton developers; original document rights retained. See original pages for license.',
                'pages': pages}
    (HERE / 'official-sources.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'archived': len(pages), 'bytes': sum(p['bytes'] for p in pages)}))
