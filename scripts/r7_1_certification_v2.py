"""R7.1 v2 — independent exact-reference certification.

The reference is built from the separable strictly-concave analytic objective and
its linear feasible polygon, independently of Gurobi/PWL.  This avoids using the
production SLSQP result as a KKT oracle.
"""
from __future__ import annotations
import json, math, random
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from scipy.optimize import minimize_scalar, nnls, brentq
from gurobean.model import Scenario, _feasible, _round_objective, expected_newsvendor_gradient, expected_newsvendor_profit, solve_gurobi_round

PWL_POINTS=5001; SEED=20260908; CASES=80
OBJ_TOL=2e-2; Q_TOL=.75; KKT_TOL=2e-6; FEAS_TOL=2e-6

def flags(r): return r in (2,4), r in (3,4)
def coeffs(sc,r):
    cold,cost=flags(r)
    return np.array([sc.beans_hot, sc.beans_cold if cold else 0.]), np.array([sc.water_hot, sc.water_cold if cold else 0.])
def grad(sc,r,q):
    cold,cost=flags(r)
    return np.array([expected_newsvendor_gradient(q[0],sc.lambda_hot,sc.revenue_hot,sc.cost_hot if cost else 0.,sc.salvage_hot), expected_newsvendor_gradient(q[1],sc.lambda_cold,sc.revenue_cold,sc.cost_cold if cost else 0.,sc.salvage_cold) if cold else 0.])
def obj(sc,r,q): return float(_round_objective(sc,*flags(r),float(q[0]),float(q[1])))

def _upper(sc,r):
    # Conservative finite bounds for vertex construction.
    b,w=coeffs(sc,r); vals=[]
    if math.isfinite(sc.beans_available):
        vals += [sc.beans_available/b[i] for i in range(2) if b[i]>0]
    if math.isfinite(sc.water_available):
        vals += [sc.water_available/w[i] for i in range(2) if w[i]>0]
    return max(vals+[max(sc.lambda_total*8.,100.)])

def _feasible_vec(q,sc,r,tol=1e-7):
    b,w=coeffs(sc,r)
    return bool(np.all(q>=-tol) and (not math.isfinite(sc.beans_available) or b@q<=sc.beans_available+tol) and (not math.isfinite(sc.water_available) or w@q<=sc.water_available+tol))

def polygon_vertices(sc,r):
    b,w=coeffs(sc,r); cold,_=flags(r); cand=[np.array([0.,0.])]
    if math.isfinite(sc.beans_available):
        for i in range(2):
            if b[i]>0:
                q=np.zeros(2); q[i]=sc.beans_available/b[i]; cand.append(q)
    if math.isfinite(sc.water_available):
        for i in range(2):
            if w[i]>0:
                q=np.zeros(2); q[i]=sc.water_available/w[i]; cand.append(q)
    if math.isfinite(sc.beans_available) and math.isfinite(sc.water_available):
        A=np.vstack([b,w])
        if abs(np.linalg.det(A))>1e-12:
            q=np.linalg.solve(A,[sc.beans_available,sc.water_available]); cand.append(q)
    # In rounds without cold, force cold=0.
    if not cold: cand=[np.array([float(q[0]),0.]) for q in cand]
    out=[]
    for q in cand:
        if _feasible_vec(q,sc,r):
            if not any(np.max(np.abs(q-x))<1e-8 for x in out): out.append(q)
    return out

def exact_reference(sc,r):
    cold,_=flags(r)
    if not cold:
        cap=_upper(sc,r)
        if math.isfinite(sc.beans_available): cap=min(cap,sc.beans_available/max(sc.beans_hot,1e-15))
        if math.isfinite(sc.water_available): cap=min(cap,sc.water_available/max(sc.water_hot,1e-15))
        f=lambda x: -obj(sc,r,np.array([x,0.]))
        z=minimize_scalar(f,bounds=(0.,max(cap,0.)),method='bounded',options={'xatol':1e-11})
        candidates=[(0.,0.),(float(z.x),0.),(cap,0.)]
        q=max(candidates,key=lambda x:obj(sc,r,np.array(x)))
        return np.array(q,dtype=float),obj(sc,r,np.array(q))
    V=polygon_vertices(sc,r)
    candidates=V[:]
    # Every boundary edge of a 2D convex polygon is represented by a pair of vertices.
    for i in range(len(V)):
        for j in range(i+1,len(V)):
            a,b=V[i],V[j]; d=b-a
            if np.linalg.norm(d)<=1e-10: continue
            f=lambda t:-obj(sc,r,a+t*d)
            z=minimize_scalar(f,bounds=(0.,1.),method='bounded',options={'xatol':1e-11})
            candidates.append(a+float(z.x)*d)
    q=max(candidates,key=lambda x:obj(sc,r,x))
    return np.array(q,dtype=float),obj(sc,r,q)

def kkt(sc,r,q):
    b,w=coeffs(sc,r); Aall=[]; names=[]; slacks=[]
    rb=sc.beans_available-b@q; rw=sc.water_available-w@q
    if math.isfinite(sc.beans_available): slacks.append(rb); Aall.append(b); names.append('beans')
    if math.isfinite(sc.water_available): slacks.append(rw); Aall.append(w); names.append('water')
    A=np.array(Aall,dtype=float).T if Aall else np.zeros((2,0)); active=[]
    for i,s in enumerate(slacks):
        if abs(s)<=2e-5: active.append(i)
    # Select a linearly independent active subset.
    selected=[]; rank=0
    for i in active:
        trial=np.column_stack([A[:,j] for j in selected+[i]])
        nr=np.linalg.matrix_rank(trial,tol=1e-10)
        if nr>rank: selected.append(i); rank=nr
    As=A[:,selected] if selected else np.zeros((2,0))
    g=grad(sc,r,q)
    lam=np.zeros(len(selected))
    if As.shape[1]: lam,_=nnls(As,g)
    reduced=g-(As@lam if As.shape[1] else 0.)
    mu=np.maximum(-reduced,0.)
    station=g-(As@lam if As.shape[1] else 0.)+mu
    # At q>0, mu must be zero; at q=0, reduced gradient must be <=0.
    lb=float(max([max(reduced[i],0.) for i in range(2) if q[i]<=1e-7]+[0.]))
    comp=max([abs(float(lam[k]*slacks[selected[k]])) for k in range(len(selected))]+[abs(float(mu[i]*q[i])) for i in range(2)])
    primal=max([max(0.,-float(q[i])) for i in range(2)]+[max(0.,-float(s)) for s in slacks]+[0.])
    return {'gradient':g.tolist(),'active_constraints':[names[i] for i in selected],'multipliers':lam.tolist(),'slacks':{'beans':float(rb),'water':float(rw)},'stationarity_inf':float(np.max(np.abs(station))),'lower_bound_violation':lb,'complementarity':float(comp),'primal_violation':float(primal),'kkt_residual':float(max(np.max(np.abs(station)),lb,comp,primal))}

def random_scenario(rng,r):
    lam=rng.uniform(5,180); ph=1. if r in (1,3) else rng.uniform(.2,.8); pc=0. if r in (1,3) else 1-ph
    rh,rc=rng.uniform(1,6),rng.uniform(1,6); ch=rng.uniform(.05,min(2,rh*.85)) if r in (3,4) else 0.; cc=rng.uniform(.05,min(2,rc*.85)) if r==4 else 0.
    sh=rng.uniform(0,.25); sc=rng.uniform(0,.25) if r in (2,4) else 0.; bh=rng.uniform(.3,2); bc=rng.uniform(.3,2) if r in (2,4) else 0.; wh=rng.uniform(.3,2); wc=rng.uniform(.3,2) if r in (2,4) else 0.
    return Scenario(lam,ph,pc,rh,rc,ch,cc,sh,sc,rng.uniform(.35,1.15)*lam*max(bh,bc or bh),rng.uniform(.35,1.15)*lam*max(wh,wc or wh),bh,bc,wh,wc)

def certify(sc,r,name):
    qref,refobj=exact_reference(sc,r); kr=kkt(sc,r,qref); gr=solve_gurobi_round(sc,r,pwl_points=PWL_POINTS); qg=np.array([float(gr['Q_hot']),float(gr['Q_cold'])]); eg=obj(sc,r,qg); oe=abs(eg-refobj); qe=float(np.max(np.abs(qg-qref))); feasible=_feasible_vec(qg,sc,r,FEAS_TOL)
    passed=feasible and kr['kkt_residual']<=KKT_TOL and oe<=OBJ_TOL and qe<=Q_TOL
    return {'case':name,'round':r,'reference':{'Q_hot':float(qref[0]),'Q_cold':float(qref[1]),'objective':float(refobj)},'gurobi':{'Q_hot':float(qg[0]),'Q_cold':float(qg[1]),'exact_objective':float(eg)},'errors':{'objective_abs':float(oe),'q_inf':qe,'exact_regret':float(max(0.,refobj-eg))},'feasible':feasible,'kkt':kr,'pass':bool(passed)}

def main():
    rng=random.Random(SEED); results=[]
    deterministic=[('r1_base',1,Scenario(100,1,0,2,1,0,0,0,0,120,120,1,0,1,0)),('r2_balanced',2,Scenario(100,.6,.4,3,4,0,0,0,0,100,100,1,1,1,1)),('r3_cost',3,Scenario(100,1,0,4,1,.7,0,0,0,80,80,1,0,1,0)),('r4_shared',4,Scenario(120,.55,.45,4,5,.8,1,0,0,90,90,1.2,.8,.9,1.1))]
    for n,r,sc in deterministic+[(f'random_r{r}_{i:02d}',r,random_scenario(rng,r)) for r in (1,2,3,4) for i in range(CASES//4)]:
        try: results.append(certify(sc,r,n))
        except Exception as e: results.append({'case':n,'round':r,'error':repr(e),'pass':False})
    fails=[x for x in results if not x.get('pass',False)]; out={'schema':'gurobean.r7.1.certification.v2','seed':SEED,'pwl_points':PWL_POINTS,'total_cases':len(results),'failures':len(fails),'max_objective_error':max((x.get('errors',{}).get('objective_abs',0) for x in results),default=0),'max_q_inf_error':max((x.get('errors',{}).get('q_inf',0) for x in results),default=0),'max_kkt_residual':max((x.get('kkt',{}).get('kkt_residual',0) for x in results),default=0),'status':'PASS' if not fails else 'FAIL','results':results,'failure_cases':fails}
    Path('r7_1_certification_v2.json').write_text(json.dumps(out,indent=2,allow_nan=True),encoding='utf-8')
    print('=== R7.1 v2 INDEPENDENT MATHEMATICAL CERTIFICATION ==='); print(f"CASES: {len(results)}"); print(f"FAILURES: {len(fails)}"); print(f"MAX_OBJECTIVE_ERROR: {out['max_objective_error']:.12g}"); print(f"MAX_Q_INF_ERROR: {out['max_q_inf_error']:.12g}"); print(f"MAX_KKT_RESIDUAL: {out['max_kkt_residual']:.12g}"); print(f"R7.1 v2 STATUS: {out['status']}"); print('ARTIFACT: r7_1_certification_v2.json'); return 0 if not fails else 1
if __name__=='__main__': raise SystemExit(main())
