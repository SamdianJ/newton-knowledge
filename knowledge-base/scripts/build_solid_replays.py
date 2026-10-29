"""Describe saved scene geometry without changing or rerunning any experiment."""
import hashlib
import json
from pathlib import Path

from replay_geometry_kamino import geometry_for_case, _rotor_glyph, _hinge

ROOT = Path(__file__).resolve().parents[1]
LABS = ('solver_parameter_lab', 'kamino_mechanism_lab', 'kamino_pd_lab', 'mujoco_joint_contact_lab')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def source(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def mujoco_scene(case, variant):
    run = (ROOT / variant['result_file']).parent
    protocol = load(run / 'protocol.json')
    cid = case['id']
    spec = dict(shapes=[], joints=[], floor=None, notes=[], sources=[source(run / x) for x in ('protocol.json', 'runner.py', 'resolved-config.json')])
    if cid.startswith('mujoco_joint_'):
        spec.update(shapes=_rotor_glyph([0., 0., 0.]), joints=[_hinge()], notes=['此单关节实验没有碰撞形状；转盘与指针仅用于显示真实转角，示意尺寸不参与动力学。'])
    else:
        if cid.startswith('native_'):
            shape = dict(type='sphere', radius=protocol['scene']['radius_m'])
        else:
            design = next(x for x in protocol['cases'] if x['id'] == cid)
            shape = dict(type=design['shape'])
            if shape['type'] == 'box':
                shape['half_extents'] = design['half_extents_m']
            else:
                shape['radius'] = design['radius_m']
        shape.update(body=0, position=[0, 0, 0], quaternion=[0, 0, 0, 1], evidence_role='physical')
        spec.update(shapes=[shape], floor=0., notes=['物体尺寸来自冻结场景，位置与旋转来自保存的 body_q。表面色带只帮助看清转动。'])
    return spec


def main():
    cases, hashes = {}, {}
    for lab in LABS:
        path = ROOT / 'experiments' / lab / 'report-data.json'
        hashes[source(path)['path']] = source(path)['sha256']
        for case in load(path)['cases']:
            variants = geometry_for_case(case, ROOT)
            if not variants:
                variants = {}
                for i, v in enumerate(case['variants']):
                    replay = case['replay'][i]
                    if replay.get('visual'):
                        visual = replay['visual']
                        shapes = [dict(s, position=[0, 0, 0], quaternion=[0, 0, 0, 1], evidence_role='physical') for s in visual['body_shapes']]
                        variants[v['variant']] = dict(shapes=shapes, floor=visual.get('floor'), joints=[], notes=['原实验记录中的真实球体/方块尺寸；使用保存的完整位姿。'], sources=[source(path), source(ROOT / case['protocol_file'])])
                    else:
                        variants[v['variant']] = mujoco_scene(case, v)
            for i, v in enumerate(case['variants']):
                spec = variants[v['variant']]
                count = len(case['replay'][i]['body_q'][0])
                assert spec['shapes'] and all(-1 <= s['body'] < count for s in spec['shapes'])
                for s in spec['sources']:
                    assert source(ROOT / s['path'])['sha256'] == s['sha256']
                    hashes[s['path']] = s['sha256']
            cases[lab + '/' + case['id']] = dict(variants=variants, solver=case['solver'])
    output = ROOT / 'experiments/solid_replay/geometry.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(dict(schema_version=1, cases=cases, source_hashes=hashes), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(solid_replay_cases=len(cases), variants=sum(len(c['variants']) for c in cases.values()))))


if __name__ == '__main__':
    main()
