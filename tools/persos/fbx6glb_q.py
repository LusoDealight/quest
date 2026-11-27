import numpy as np
def mat2q(R):
    tr = R[0,0]+R[1,1]+R[2,2]
    if tr > 0: s_ = np.sqrt(tr+1)*2; q = [(R[2,1]-R[1,2])/s_, (R[0,2]-R[2,0])/s_, (R[1,0]-R[0,1])/s_, s_/4]
    elif R[0,0] > R[1,1] and R[0,0] > R[2,2]: s_ = np.sqrt(1+R[0,0]-R[1,1]-R[2,2])*2; q = [s_/4, (R[0,1]+R[1,0])/s_, (R[0,2]+R[2,0])/s_, (R[2,1]-R[1,2])/s_]
    elif R[1,1] > R[2,2]: s_ = np.sqrt(1+R[1,1]-R[0,0]-R[2,2])*2; q = [(R[0,1]+R[1,0])/s_, s_/4, (R[1,2]+R[2,1])/s_, (R[0,2]-R[2,0])/s_]
    else: s_ = np.sqrt(1+R[2,2]-R[0,0]-R[1,1])*2; q = [(R[0,2]+R[2,0])/s_, (R[1,2]+R[2,1])/s_, s_/4, (R[1,0]-R[0,1])/s_]
    q = np.array(q); return q / np.linalg.norm(q)
