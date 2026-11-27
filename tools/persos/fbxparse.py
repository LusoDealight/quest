import struct, zlib
def parse(path):
    d = open(path,'rb').read(); ver = struct.unpack('<I', d[23:27])[0]; big = ver >= 7500
    def rd_node(p):
        if big: end, nprop, plen = struct.unpack('<QQQ', d[p:p+24]); p += 24
        else: end, nprop, plen = struct.unpack('<III', d[p:p+12]); p += 12
        nl = d[p]; p += 1
        if end == 0: return None, p
        name = d[p:p+nl].decode('latin1'); p += nl
        props = []
        for _ in range(nprop):
            t = chr(d[p]); p += 1
            if t == 'Y': props.append(struct.unpack('<h', d[p:p+2])[0]); p += 2
            elif t == 'C': props.append(bool(d[p])); p += 1
            elif t == 'I': props.append(struct.unpack('<i', d[p:p+4])[0]); p += 4
            elif t == 'F': props.append(struct.unpack('<f', d[p:p+4])[0]); p += 4
            elif t == 'D': props.append(struct.unpack('<d', d[p:p+8])[0]); p += 8
            elif t == 'L': props.append(struct.unpack('<q', d[p:p+8])[0]); p += 8
            elif t in 'SR':
                n = struct.unpack('<I', d[p:p+4])[0]; p += 4; v = d[p:p+n]; p += n
                props.append(v.decode('latin1') if t == 'S' else v)
            elif t in 'fdlib':
                n, enc, cl = struct.unpack('<III', d[p:p+12]); p += 12; raw = d[p:p+cl]; p += cl
                if enc: raw = zlib.decompress(raw)
                fmt = {'f':'f','d':'d','l':'q','i':'i','b':'b'}[t]
                props.append(list(struct.unpack('<%d%s' % (n, fmt), raw)))
            else: raise Exception('type ' + t)
        kids = []
        while p < end:
            c, p = rd_node(p)
            if c is None: break
            kids.append(c)
        return (name, props, kids), end
    p = 27; nodes = []
    while p < len(d) - 13:
        n, p = rd_node(p)
        if n is None: break
        nodes.append(n)
    return ver, nodes
def find(n, name): return [k for k in n[2] if k[0] == name]
def one(n, name):
    r = find(n, name); return r[0] if r else None
def arr(n):
    if n is None: return None
    p = n[1]; return p[0] if (len(p)==1 and isinstance(p[0], list)) else p
def nm(s): return s.split('\x00')[0]
