# Cuit des animations Mixamo FBX 7.x en un seul GLB de clips partagés (squelette nu + animations).
import sys, json, struct, numpy as np
sys.path.insert(0, '.'); from fbxparse import *
from fbx6glb_q import mat2q
TICK = 46186158000
def euler(r):
    x, y, z = np.radians(r); cx, sx, cy, sy, cz, sz = np.cos(x), np.sin(x), np.cos(y), np.sin(y), np.cos(z), np.sin(z)
    return np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]]) @ np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]]) @ np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
def load(path):
    ver, nodes = parse(path); objs = [n for n in nodes if n[0] == 'Objects'][0][2]; cons = [c[1] for c in [n for n in nodes if n[0] == 'Connections'][0][2]]
    byid = {k[1][0]: k for k in objs}
    P70 = lambda k: {p[1][0]: p[1][4:] for p in (one(k, 'Properties70') or ('', [], []))[2]}
    models = {k[1][0]: nm(k[1][1]) for k in objs if k[0] == 'Model'}
    parent = {}; cn_of = {}; curves = {}
    for c in cons:
        if c[0] == 'OO' and c[1] in models and c[2] in models: parent[c[1]] = c[2]
        if c[0] == 'OP' and c[2] in models and byid.get(c[1], ('',))[0] == 'AnimationCurveNode': cn_of[(c[2], c[3])] = c[1]
        if c[0] == 'OP' and byid.get(c[1], ('',))[0] == 'AnimationCurve': curves[(c[2], c[3])] = byid[c[1]]
    props = {i: P70(byid[i]) for i in models}
    for k, v in props.items():
        ro = v.get('RotationOrder', [0])[0]
        if ro: print('ordre de rotation non géré', models[k], ro)
    def chan(mid, prop, default):
        cn = cn_of.get((mid, prop)); out = []
        for ax, d in zip('XYZ', default):
            cv = curves.get((cn, 'd|' + ax)) if cn else None
            if cv is None: out.append((None, d)); continue
            out.append((np.array(arr(one(cv, 'KeyTime')), dtype=float) / TICK, np.array(arr(one(cv, 'KeyValueFloat')), dtype=float)))
        return out
    return models, parent, props, chan
def ev(ch, t): return np.array([v if k is None else np.interp(t, k, v) for k, v in ch])
clips_in = [a.split('=', 1) for a in sys.argv[2:]]; out = sys.argv[1]; FPS = 20
bin_ = bytearray(); views = []; accs = []
def add(a, typ, minmax=False):
    while len(bin_) % 4: bin_.append(0)
    a = np.ascontiguousarray(a, dtype='<f4'); views.append({'buffer': 0, 'byteOffset': len(bin_), 'byteLength': a.nbytes}); bin_.extend(a.tobytes())
    acc = {'bufferView': len(views) - 1, 'componentType': 5126, 'count': len(a), 'type': typ}
    if minmax: acc['min'] = [float(a.min())]; acc['max'] = [float(a.max())]
    accs.append(acc); return len(accs) - 1
gnodes = None; idx = {}; anims = []
for name, path in clips_in:
    models, parent, props, chan = load(path)
    if gnodes is None:
        ids = [i for i in models if models[i].startswith('mixamorig')]; idx = {models[i]: n for n, i in enumerate(ids)}; gnodes = []
        for i in ids:
            P = props[i]; R = euler(P.get('PreRotation', [0,0,0])) @ euler(P.get('Lcl Rotation', [0,0,0]))
            nd = {'name': models[i], 'translation': list(map(float, P.get('Lcl Translation', [0,0,0]))), 'rotation': mat2q(R).tolist()}
            ch = [idx[models[c]] for c in ids if parent.get(c) == i]
            if ch: nd['children'] = ch
            gnodes.append(nd)
        roots = [idx[models[i]] for i in ids if parent.get(i) not in ids]
    dur = 0
    for i in models:
        for prop in ('Lcl Rotation', 'Lcl Translation'):
            for k, v in chan(i, prop, [0,0,0]):
                if k is not None: dur = max(dur, k[-1])
    n = max(2, int(round(dur * FPS)) + 1); T = np.linspace(0, dur, n)
    tin = add(T, 'SCALAR', True); chs = []; smp = []
    for i in models:
        mn = models[i]
        if mn not in idx: continue
        P = props[i]; pre = euler(P.get('PreRotation', [0,0,0]))
        rc = chan(i, 'Lcl Rotation', P.get('Lcl Rotation', [0,0,0]))
        if any(k is not None for k, v in rc):
            Q = np.array([mat2q(pre @ euler(ev(rc, t))) for t in T])
            for j in range(1, n):
                if np.dot(Q[j], Q[j-1]) < 0: Q[j] = -Q[j]
            smp.append({'input': tin, 'output': add(Q, 'VEC4'), 'interpolation': 'LINEAR'}); chs.append({'sampler': len(smp) - 1, 'target': {'node': idx[mn], 'path': 'rotation'}})
        tc = chan(i, 'Lcl Translation', P.get('Lcl Translation', [0,0,0]))
        if mn == 'mixamorig:Hips' and any(k is not None for k, v in tc):
            Tr = np.array([ev(tc, t) for t in T])
            smp.append({'input': tin, 'output': add(Tr, 'VEC3'), 'interpolation': 'LINEAR'}); chs.append({'sampler': len(smp) - 1, 'target': {'node': idx[mn], 'path': 'translation'}})
            print(name, 'dur', round(dur, 2), 'hanches y0', round(Tr[0, 1], 1), 'dérive z', round(Tr[-1, 2] - Tr[0, 2], 1), 'x', round(Tr[-1, 0] - Tr[0, 0], 1))
    anims.append({'name': name, 'channels': chs, 'samplers': smp})
while len(bin_) % 4: bin_.append(0)
gnodes.append({'name': 'Clips', 'children': roots})
gl = {'asset': {'version': '2.0', 'generator': 'quest anim7'}, 'scene': 0, 'scenes': [{'nodes': [len(gnodes) - 1]}], 'nodes': gnodes,
      'animations': anims, 'accessors': accs, 'bufferViews': views, 'buffers': [{'byteLength': len(bin_)}]}
js = json.dumps(gl, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
with open(out, 'wb') as f:
    f.write(struct.pack('<III', 0x46546C67, 2, 28 + len(js) + len(bin_))); f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
    f.write(struct.pack('<II', len(bin_), 0x004E4942)); f.write(bin_)
print('écrit', out, 28 + len(js) + len(bin_))
