"""R7.2 v5 — forensic audit of the analytic reference and Gurobi/PWL adapter.

Purpose: isolate whether R7.2 v4 failures originate in the independent
reference geometry or in the Gurobi PWL adapter. The model implementation is
not modified. For every case this audit computes three points:
  1) polygon/edge analytic reference,
  2) existing independent SciPy reference,
  3) Gurobi PWL solution.
The SciPy result is diagnostic only; it is never used to certify the model.
"""
from __future__ import annotations
import json, math, random
from pathlib import Path
import numpy as np
from scipy.optimize import brentq, minimize_scalar, nnls
from gurobean.model import Scenario, expected_newsvendor_gradient, solve_gurobi_round, solve_round_scipy, _round_objective

SEED=20260908
CASES_PER_ROUND=25
PWL_POINTS=5001


def setup(sc,r):
    cold=r in (2,4); cost=r in (3,4)
    A=[]; caps=[]; names=[]
    if math.isfinite(sc.beans_available): A.append([sc.beans_hot, sc.beans_cold if cold else 0.]); caps.append(sc.beans_available); names.append('beans')
    if math.isfinite(sc.water_available): A.append([sc.water_hot, sc.water_cold if cold else 0.]); caps.append(sc.water_available); names.append('water')
    return cold,cost,np.asarray(A,float),np.asarray(caps,float),names

def obj(sc,r,x):
    cold,cost,_,_,_=setup(sc,r)
    return float(_round_objective(sc,cold,cost,float(x[0]),float(x[1])))

def grad(sc,r,x):
    cold,cost,_,_,_=setup(sc,r)
    return np.array([
        expected_newsvendor_gradient(float(x[0]),sc.lambda_hot,sc.revenue_hot,sc.cost_hot if cost else 0.,sc.salvage_hot),
        expected_newsvendor_gradient(float(x[1]),sc.lambda_cold,sc.revenue_cold,sc.cost_cold if cost else 0.,sc.salvage_cold) if cold else 0.],float)

def feasible(sc,r,x,t=1e-7):
    _,_,A,caps,_=setup(sc,r)
    return bool(np.all(np.asarray(x)>=-t) and all(A[i]@x<=caps[i]+t for i in range(len(caps))))

def bounds(sc,r):
    cold,_,A,caps,_=setup(sc,r)
    out=[]
    for j,lam in enumerate((sc.lambda_hot,sc.lambda_cold)):
        vals=[caps[i]/A[i,j] for i in range(len(caps)) if A[i,j]>1e-14]
        vals.append(20.*max(lam,1.)+100.)
        out.append((0.,float(min(vals))))
    return out

def polygon(sc,r):
    cold,_,A,caps,_=setup(sc,r)
    if not cold: return [np.array([0.,0.])]
    b=bounds(sc,r)
    lines=[(np.array([1.,0.]),0.),(np.array([0.,1.]),0.)]
    for a,c in zip(A,caps): lines.append((np.asarray(a,float),float(c)))
    lines += [(np.array([1.,0.]),b[0][1]),(np.array([0.,1.]),b[1][1])]
    pts=[]
    for i in range(len(lines)):
        for j in range(i+1,len(lines)):
            M=np.vstack([lines[i][0],lines[j][0]])
            if abs(np.linalg.det(M))<1e-12: continue
            p=np.linalg.solve(M,np.array([lines[i][1],lines[j][1]]))
            if feasible(sc,r,p,1e-6): pts.append(p)
    u=[]
    for p in pts:
        if not any(np.linalg.norm(p-q)<=1e-8 for q in u): u.append(p)
    return u

def edge_reference(sc,r,vertices):
    cold,_,A,caps,_=setup(sc,r)
    if not cold: return None
    constraints=[(np.array([1.,0.]),0.),(np.array([0.,1.]),0.)]
    constraints += [(np.asarray(a,float),float(c)) for a,c in zip(A,caps)]
    best=None
    for a,cap in constraints:
        pts=[p for p in vertices if abs(float(a@p-cap))<=2e-6]
        for i in range(len(pts)):
            for j in range(i+1,len(pts)):
                p0,p1=pts[i],pts[j]; d=p1-p0
                if d@d<=1e-18: continue
                fun=lambda t:-obj(sc,r,p0+t*d)
                z=minimize_scalar(fun,bounds=(0.,1.),method='bounded',options={'xatol':1e-11,'maxiter':1000})
                for t in (float(z.x),0.,1.):
                    p=p0+t*d
                    if feasible(sc,r,p,1e-5):
                        if best is None or obj(sc,r,p)>obj(sc,r,best): best=p
    return best

def polygon_reference(sc,r):
    cold,_,_,_,_=setup(sc,r)
    if not cold:
        # exact 1-D optimizer through the existing closed-form/scipy reference
        s=solve_round_scipy(sc,r)
        return np.array([s['Q_hot'],0.])
    v=polygon(sc,r); candidates=list(v)
    # Unconstrained stationary point: solve each scalar derivative exactly.
    q=[]
    for j in (0,1):
        lo,hi=bounds(sc,r)[j]
        def gj(x): return grad(sc,r,[x,0.] if j==0 else [0.,x])[j]
        g0,gh=gj(lo),gj(hi)
        q.append(lo if g0<=0 else hi if gh>=0 else brentq(gj,lo,hi,xtol=1e-12,rtol=1e-12))
    q=np.asarray(q,float)
    if feasible(sc,r,q,1e-6): candidates.append(q)
    e=edge_reference(sc,r,v)
    if e is not None: candidates.append(e)
    for j in (0,1):
        lo,hi=bounds(sc,r)[j]
        def gj(x): return grad(sc,r,[x,0.] if j==0 else [0.,x])[j]
        g0,gh=gj(lo),gj(hi)
        qj=lo if g0<=0 else hi if gh>=0 else brentq(gj,lo,hi,xtol=1e-12,rtol=1e-12)
        p=np.array([qj,0.]) if j==0 else np.array([0.,qj])
        if feasible(sc,r,p,1e-6): candidates.append(p)
    return max(candidates,key=lambda p:obj(sc,r,p))

def scenario(rng,r):
    L=rng.uniform(10,160); ph=1. if r in (1,3) else rng.uniform(.25,.75); pc=0. if r in (1,3) else 1-ph
    rh,rc=rng.uniform(1.5,6),rng.uniform(1.5,6); ch=rng.uniform(.1,rh*.7) if r in (3,4) else 0.; cc=rng.uniform(.1,rc*.7) if r==4 else 0.
    bh,wh=rng.uniform(.5,2),rng.uniform(.5,2); bc,wc=(rng.uniform(.5,2),rng.uniform(.5,2)) if r in (2,4) else (0.,0.)
    return Scenario(L,ph,pc,rh,rc,ch,cc,0.,0.,rng.uniform(.4,1.)*L*max(bh,bc or bh),rng.uniform(.4,1.)*L*max(wh,wc or wh),bh,bc,wh,wc)

def main():
    rng=random.Random(SEED); rows=[]
    for r in (1,2,3,4):
        for i in range(CASES_PER_ROUND):
            name=f'r{r}_{i:02d}'
            try:
                sc=scenario(rng,r); qp=polygon_reference(sc,r); ss=solve_round_scipy(sc,r); qs=np.array([ss['Q_hot'],ss['Q_cold']]); gg=solve_gurobi_round(sc,r,pwl_points=PWL_POINTS); qg=np.array([gg['Q_hot'],gg['Q_cold']])
                rows.append({'case':name,'round':r,'scenario':sc.__dict__,'polygon':{'q':qp.tolist(),'objective':obj(sc,r,qp)},'scipy':{'q':qs.tolist(),'objective':obj(sc,r,qs),'solver_reported_objective':float(ss['objective'])},'gurobi':{'q':qg.tolist(),'objective_exact':obj(sc,r,qg),'solver_objective':float(gg['objective'])},'delta_polygon_scipy':float(np.max(np.abs(qp-qs))),'delta_polygon_scipy_obj':float(abs(obj(sc,r,qp)-obj(sc,r,qs))),'delta_gurobi_scipy':float(np.max(np.abs(qg-qs))),'delta_gurobi_scipy_obj':float(abs(obj(sc,r,qg)-obj(sc,r,qs)))})
            except Exception as e: rows.append({'case':name,'round':r,'error':repr(e)})
    bad_ref=[x for x in rows if x.get('delta_polygon_scipy',0)>1e-3 or x.get('delta_polygon_scipy_obj',0)>1e-3]
    bad_g=[x for x in rows if x.get('delta_gurobi_scipy',0)>1.0 or x.get('delta_gurobi_scipy_obj',0)>2e-2]
    rows_sorted=sorted(rows,key=lambda x:max(x.get('delta_polygon_scipy_obj',0),x.get('delta_gurobi_scipy_obj',0)),reverse=True)
    out={'schema':'gurobean.r7.2.kkt_duality.v5.forensic','seed':SEED,'cases':len(rows),'reference_disagreements':len(bad_ref),'gurobi_disagreements':len(bad_g),'worst':rows_sorted[:12],'results':rows}
    Path('r7_2_kkt_duality_v5.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print('=== R7.2 v5 FORENSIC AUDIT ==='); print(f'CASES: {len(rows)}'); print(f'REFERENCE DISAGREEMENTS: {len(bad_ref)}'); print(f'GUROBI DISAGREEMENTS VS SCIPY: {len(bad_g)}');
    for x in rows_sorted[:8]: print(x['case'], 'poly-vs-scipy-Q=',f"{x.get('delta_polygon_scipy',0):.6g}",'gurobi-vs-scipy-Q=',f"{x.get('delta_gurobi_scipy',0):.6g}",'gurobi-vs-scipy-OBJ=',f"{x.get('delta_gurobi_scipy_obj',0):.6g}")
    print('ARTIFACT: r7_2_kkt_duality_v5.json')
    return 0
if __name__=='__main__': raise SystemExit(main())
