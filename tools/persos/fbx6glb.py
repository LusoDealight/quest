# Convertit un FBX 6.1 Mixamo (mesh + squelette + skin) en GLB (diffuse seule, réduite).
import sys, io, json, struct, numpy as np
sys.path.insert(0, '.'); from fbxparse import *
from PIL import Image
src, out, texsize = sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1024
ver, nodes = parse(src)
objs = [n for n in nodes if n[0] == 'Objects'][0][2]; cons = [c[1] for c in [n for n in nodes if n[0] == 'Connections'][0][2]]
def M16(p): return np.array(p, dtype=float).reshape(4, 4).T
byname = {nm(k[1][0]): k for k in objs if k[1]}
parent = {}; kids = {}
for c in cons:
    if c[0] == 'OO' and c[2].endswith('\x00\x01Model') and c[1].endswith('\x00\x01Model'): parent[nm(c[1])] = nm(c[2]); kids.setdefault(nm(c[2]), []).append(nm(c[1]))
G = {}
for k in objs:
    if k[0] == 'Pose':
        for pn in find(k, 'PoseNode'): G[nm(one(pn, 'Node')[1][0])] = M16(arr(one(pn, 'Matrix')))
limbs = [nm(k[1][0]) for k in objs if k[0] == 'Model' and k[1][1] == 'LimbNode']
meshes = [nm(k[1][0]) for k in objs if k[0] == 'Model' and k[1][1] == 'Mesh']
def props60(k):
    P = {}
    for p in (one(k, 'Properties60') or ('', [], []))[2]: P[p[1][0]] = p[1][3:]
    return P
def euler(r):  # XYZ en degrés -> matrice (ordre FBX eEulerXYZ : R = Rz*Ry*Rx)
    x, y, z = np.radians(r); cx, sx, cy, sy, cz, sz = np.cos(x), np.sin(x), np.cos(y), np.sin(y), np.cos(z), np.sin(z)
    Rx = np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]]); Ry = np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]]); Rz = np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
    return Rz @ Ry @ Rx
def lcl(name):
    P = props60(byname[name]); M = np.eye(4)
    R = euler(P.get('PreRotation', [0,0,0])) @ euler(P.get('Lcl Rotation', [0,0,0]))
    M[:3, :3] = R * np.array(P.get('Lcl Scaling', [1,1,1])); M[:3, 3] = P.get('Lcl Translation', [0,0,0]); return M
# globals des os : pose de liaison si connue, sinon parent * local
def glob(n):
    if n in G: return G[n]
    p = parent.get(n); g = (glob(p) if p in byname and p in limbs else np.eye(4)) @ lcl(n); G[n] = g; return g
for n in limbs: glob(n)
# skin
cl_bone = {}; cl_of_mesh = {}
for c in cons:
    if c[0] != 'OO': continue
    a, b = nm(c[1]), nm(c[2])
    if a in limbs and b in byname and byname[b][0] == 'Deformer': cl_bone[b] = a
    if a in byname and byname[a][0] == 'Deformer' and b in byname and byname[b][0] == 'Deformer': cl_of_mesh.setdefault(b, []).append(a)  # cluster -> skin
    if a in byname and byname[a][0] == 'Deformer' and b in meshes: cl_of_mesh.setdefault('mesh:' + b, []).append(a)  # skin -> mesh
J = {n: i for i, n in enumerate(limbs)}
TL = {}
P_all, N_all, UV_all, JI_all, JW_all, I_all = [], [], [], [], [], []
base = 0
for mname in meshes:
    k = byname[mname]
    V = np.array(arr(one(k, 'Vertices'))).reshape(-1, 3); PI = np.array(arr(one(k, 'PolygonVertexIndex')))
    nv = len(V); W = np.zeros((nv, 4)); Jx = np.zeros((nv, 4), dtype=int)
    skins = cl_of_mesh.get('mesh:' + mname, [])
    for sk in skins:
        for cl in cl_of_mesh.get(sk, []):
            ck = byname[cl]; bone = cl_bone.get(cl)
            if bone is None or one(ck, 'Indexes') is None: continue
            TL[bone] = M16(arr(one(ck, 'TransformLink'))); MT = M16(arr(one(ck, 'Transform')))
            for vi, w in zip(arr(one(ck, 'Indexes')), arr(one(ck, 'Weights'))):
                j = np.argmin(W[vi])
                if w > W[vi, j]: W[vi, j] = w; Jx[vi, j] = J[bone]
    s = W.sum(1, keepdims=True); s[s == 0] = 1; W /= s
    Mg = G.get(mname, np.eye(4))
    # polygones -> triangles (éventail), attributs par coin
    corners = []; polys = []; cur = []
    for ci, v in enumerate(PI):
        cur.append(ci)
        if v < 0: polys.append(cur); cur = []
    vidx = np.where(PI < 0, ~PI, PI)
    def layer(name, key, idxkey):
        L = one(k, name)
        if L is None: return None
        mp = one(L, 'MappingInformationType')[1][0]; rf = one(L, 'ReferenceInformationType')[1][0]
        data = np.array(arr(one(L, key))); dim = 3 if key == 'Normals' else 2; data = data.reshape(-1, dim)
        if rf == 'IndexToDirect': data = data[np.array(arr(one(L, idxkey)))]
        return data if mp == 'ByPolygonVertex' else data[vidx]
    Nc = layer('LayerElementNormal', 'Normals', 'NormalsIndex'); UVc = layer('LayerElementUV', 'UV', 'UVIndex')
    tri = []
    for p in polys:
        for t in range(1, len(p) - 1): tri += [p[0], p[t], p[t + 1]]
    tri = np.array(tri)
    pos = (np.c_[V[vidx], np.ones(len(vidx))] @ Mg.T)[:, :3]
    nrm = Nc @ Mg[:3, :3].T; nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
    uv = UVc.copy(); uv[:, 1] = 1 - uv[:, 1]
    # déduplication des coins
    key = np.c_[vidx, np.round(nrm, 4), np.round(uv, 5)]
    u, inv = np.unique(key, axis=0, return_inverse=True); first = np.zeros(len(u), dtype=int); first[inv[::-1]] = np.arange(len(inv))[::-1]
    P_all.append(pos[first]); N_all.append(nrm[first]); UV_all.append(uv[first]); JI_all.append(Jx[vidx[first]]); JW_all.append(W[vidx[first]])
    I_all.append(inv.ravel()[tri] + base); base += len(u)
    print('mesh', mname, 'verts', len(u), 'tris', len(tri) // 3, 'skins', len(skins))
P = np.vstack(P_all).astype('<f4'); N = np.vstack(N_all).astype('<f4'); UV = np.vstack(UV_all).astype('<f4')
JI = np.vstack(JI_all).astype('<u2'); JW = np.vstack(JW_all).astype('<f4'); I = np.concatenate(I_all).astype('<u4')
for n in limbs:
    if n not in TL: TL[n] = G[n]
# texture diffuse
tex = None
for c in cons:
    if c[0] == 'OP' and len(c) > 3 and c[3] == 'DiffuseColor':
        t = nm(c[1])
        for c2 in cons:
            if c2[0] == 'OO' and nm(c2[2]) == t and byname[nm(c2[1])][0] == 'Video':
                img = Image.open(io.BytesIO(one(byname[nm(c2[1])], 'Content')[1][0]))
                alpha = img.mode in ('RGBA', 'LA') and np.array(img.getchannel('A')).min() < 250
                img = img.convert('RGBA' if alpha else 'RGB'); img.thumbnail((texsize, texsize), Image.LANCZOS)
                b = io.BytesIO()
                if alpha: img.save(b, 'PNG', optimize=True); mime = 'image/png'
                else: img.save(b, 'JPEG', quality=85); mime = 'image/jpeg'
                tex = (b.getvalue(), mime, alpha); print('texture', img.size, mime, len(tex[0]))
        break
# --- écriture glTF
bin_ = bytearray(); views = []; accs = []
def add(a, target=None, comp=5126, typ='VEC3', minmax=False):
    while len(bin_) % 4: bin_.append(0)
    off = len(bin_); bin_.extend(a.tobytes()); v = {'buffer': 0, 'byteOffset': off, 'byteLength': a.nbytes}
    if target: v['target'] = target
    views.append(v); acc = {'bufferView': len(views) - 1, 'componentType': comp, 'count': len(a), 'type': typ}
    if minmax: acc['min'] = a.min(0).tolist(); acc['max'] = a.max(0).tolist()
    accs.append(acc); return len(accs) - 1
attrs = {'POSITION': add(P, 34962, minmax=True), 'NORMAL': add(N, 34962), 'TEXCOORD_0': add(UV, 34962, typ='VEC2'),
         'JOINTS_0': add(JI, 34962, 5123, 'VEC4'), 'WEIGHTS_0': add(JW, 34962, typ='VEC4')}
ind = add(I, 34963, 5125, 'SCALAR')
IBM = np.array([np.linalg.inv(TL[n]).T.ravel() for n in limbs]).astype('<f4'); ibm = add(IBM, None, 5126, 'MAT4')
def trs(M):
    t = M[:3, 3]; S = np.linalg.norm(M[:3, :3], axis=0); R = M[:3, :3] / S
    tr = R[0,0]+R[1,1]+R[2,2]
    if tr > 0: s_ = np.sqrt(tr+1)*2; q = [(R[2,1]-R[1,2])/s_, (R[0,2]-R[2,0])/s_, (R[1,0]-R[0,1])/s_, s_/4]
    elif R[0,0] > R[1,1] and R[0,0] > R[2,2]: s_ = np.sqrt(1+R[0,0]-R[1,1]-R[2,2])*2; q = [s_/4, (R[0,1]+R[1,0])/s_, (R[0,2]+R[2,0])/s_, (R[2,1]-R[1,2])/s_]
    elif R[1,1] > R[2,2]: s_ = np.sqrt(1+R[1,1]-R[0,0]-R[2,2])*2; q = [(R[0,1]+R[1,0])/s_, s_/4, (R[1,2]+R[2,1])/s_, (R[0,2]-R[2,0])/s_]
    else: s_ = np.sqrt(1+R[2,2]-R[0,0]-R[1,1])*2; q = [(R[0,2]+R[2,0])/s_, (R[1,2]+R[2,1])/s_, s_/4, (R[1,0]-R[0,1])/s_]
    q = np.array(q); q /= np.linalg.norm(q)
    return {'translation': t.tolist(), 'rotation': q.tolist(), 'scale': S.tolist()}
gnodes = []
for n in limbs:
    p = parent.get(n); L = (np.linalg.inv(TL[p]) @ TL[n]) if p in J else TL[n]
    nd = {'name': n, **trs(L)}; ch = [J[c] for c in kids.get(n, []) if c in J]
    if ch: nd['children'] = ch
    gnodes.append(nd)
roots = [J[n] for n in limbs if parent.get(n) not in J]
mesh_i = len(gnodes); gnodes.append({'name': 'Corps', 'mesh': 0, 'skin': 0})
gnodes.append({'name': 'Personnage', 'children': roots + [mesh_i], 'scale': [0.01, 0.01, 0.01]})
mat = {'name': 'peau', 'pbrMetallicRoughness': {'metallicFactor': 0, 'roughnessFactor': 0.85}}
gl = {'asset': {'version': '2.0', 'generator': 'quest fbx6glb'}, 'scene': 0, 'scenes': [{'nodes': [len(gnodes) - 1]}], 'nodes': gnodes,
      'meshes': [{'name': 'Corps', 'primitives': [{'attributes': attrs, 'indices': ind, 'material': 0}]}],
      'skins': [{'joints': list(range(len(limbs))), 'inverseBindMatrices': ibm, 'skeleton': roots[0]}], 'materials': [mat], 'accessors': accs, 'bufferViews': views}
if tex:
    while len(bin_) % 4: bin_.append(0)
    views.append({'buffer': 0, 'byteOffset': len(bin_), 'byteLength': len(tex[0])}); bin_.extend(tex[0])
    gl['images'] = [{'bufferView': len(views) - 1, 'mimeType': tex[1]}]; gl['textures'] = [{'source': 0, 'sampler': 0}]
    gl['samplers'] = [{'magFilter': 9729, 'minFilter': 9987}]; mat['pbrMetallicRoughness']['baseColorTexture'] = {'index': 0}
    if tex[2]: mat['alphaMode'] = 'MASK'; mat['alphaCutoff'] = 0.5
    mat['doubleSided'] = True
while len(bin_) % 4: bin_.append(0)
gl['buffers'] = [{'byteLength': len(bin_)}]
js = json.dumps(gl, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
with open(out, 'wb') as f:
    f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_)))
    f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js); f.write(struct.pack('<II', len(bin_), 0x004E4942)); f.write(bin_)
hy = TL['mixamorig:Hips'][1, 3] if 'mixamorig:Hips' in TL else 0
print('écrit', out, len(js) + len(bin_), 'os', len(limbs), 'hanches', round(hy, 1))
