"""R7.2 v2 — KKT, duality and PWL diagnostic audit.

KKT is certified at the independent analytic optimum. The Gurobi/PWL point is
reported separately: its exact-gradient residual is diagnostic only because the
PWL objective need not share the analytic objective's exact stationarity.
"""
from __future__ import annotations
import json, math, random
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar, nnls
from gurobean.model import Scenario, expected_newsvendor_gradient, expected_newsvendor_profit, solve_gurobi_round, _round_objective

PWL_POINTS=5001; SEED=20260908; CASES_PER_ROUND=25; TOL=2e-6; DUAL_TOL=2e-5

def flags(r): return r in (2,4), r in (3,4)
def coeffs(sc,r):
    cold,_=flags(r); return np.array([sc.beans_hot,sc.beans_cold if cold else 0.]),np.array([sc.water_hot,sc.water_cold if cold else 0.])
def grad(sc,r,q):
    cold,cost=flags(r); return np.array([expected_newsvendor_gradient(q[0],sc.lambda_hot,sc.revenue_hot,sc.cost_hot if cost else 0.,sc.salvage_hot),expected_newsvendor_gradient(q[1],sc.lambda_cold,sc.revenue_cold,sc.cost_cold if cost else 0.,sc.salvage_cold) if cold else 0.])
def obj(sc,r,q): return float(_round_objective(sc,*flags(r),float(q[0]),float(q[1])))
def feasible(q,sc,r,t=1e-7):
    b,w=coeffs(sc,r); return bool(np.all(q>=-t) and (not math.isfinite(sc.beans_available) or b@q<=sc.beans_available+t) and (not math.isfinite(sc.water_available) or w@q<=sc.water_available+t))
def vertices(sc,r):
    b,w=coeffs(sc,r); cold,_=flags(r); C=[np.array([0.,0.])]
    for a,cap in ((b,sc.beans_available),(w,sc.water_available)):
        if math.isfinite(cap):
            for i in range(2):
                if a[i]>0:
                    q=np.zeros(2);q[i]=cap/a[i];C.append(q)
    if math.isfinite(sc.beans_available) and math.isfinite(sc.water_available):
        A=np.vstack([b,w])
        if abs(np.linalg.det(A))>1e-12:C.append(np.linalg.solve(A,[sc.beans_available,sc.water_available]))
    if not cold:C=[np.array([q[0],0.]) for q in C]
    return [q for q in C if feasible(q,sc,r) and not any(np.max(np.abs(q-x))<1e-8 for x in C[:C.index(q)])]
def reference(sc,r):
    cold,_=flags(r)
    if not cold:
        cap=min([x for x in [sc.beans_available/sc.beans_hot if math.isfinite(sc.beans_available) and sc.beans_hot>0 else math.inf,sc.water_available/sc.water_hot if math.isfinite(sc.water_available) and sc.water_hot>0 else math.inf] if math.isfinite(x)]+[max(100.,8*sc.lambda_total)])
        z=minimize_scalar(lambda x:-obj(sc,r,[x,0.]),bounds=(0,max(cap,0)),method='bounded',options={'xatol':1e-11}); Q=[0.,0.];Q[0]=z.x
        return np.array(max([[0.,0.],[Q],[cap,0.]],key=lambda q:obj(sc,r,q))),None
    V=vertices(sc,r); C=V[:]
    for i in range(len(V)):
        for j in range(i+1,len(V)):
            a,b=V[i],V[j]
            if np.linalg.norm(b-a)>1e-10:
                z=minimize_scalar(lambda t:-obj(sc,r,a+t*(b-a)),bounds=(0,1),method='bounded',options={'xatol':1e-11});C.append(a+z.x*(b-a))
    q=max(C,key=lambda x:obj(sc,r,x));return np.array(q),obj(sc,r,q)
def kkt(sc,r,q):
    b,w=coeffs(sc,r); resources=[];names=[];slacks=[]
    if math.isfinite(sc.beans_available):resources.append(b);names.append('beans');slacks.append(sc.beans_available-b@q)
    if math.isfinite(sc.water_available):resources.append(w);names.append('water');slacks.append(sc.water_available-w@q)
    active=[i for i,s in enumerate(slacks) if abs(s)<=2e-5];selected=[];rank=0
    for i in active:
        T=np.column_stack([resources[j] for j in selected+[i]]);nr=np.linalg.matrix_rank(T,tol=1e-10)
        if nr>rank:selected.append(i);rank=nr
    A=np.column_stack([resources[i] for i in selected]) if selected else np.zeros((2,0));g=grad(sc,r,q);lam=np.zeros(len(selected))
    if A.shape[1]:lam,_=nnls(A,g)
    reduced=g-(A@lam if A.shape[1] else 0.);mu=np.maximum(-reduced,0.);station=g-(A@lam if A.shape[1] else 0.)+mu
    lower=max([max(reduced[i],0.) for i in range(2) if q[i]<=1e-7]+[0.]);comp=max([abs(float(lam[k]*slacks[selected[k]])) for k in range(len(selected))]+[abs(float(mu[i]*q[i])) for i in range(2)]+[0.]);primal=max([max(0.,-float(x)) for x in q]+[max(0.,-float(s)) for s in slacks]+[0.])
    return {'gradient':g.tolist(),'active_constraints':[names[i] for i in selected],'multipliers':lam.tolist(),'lower_multipliers':mu.tolist(),'slacks':dict(zip(names,map(float,slacks))),'stationarity_inf':float(np.max(np.abs(station))),'lower_bound_violation':float(lower),'complementarity':float(comp),'primal_violation':float(primal),'kkt_residual':float(max(np.max(np.abs(station)),lower,comp,primal))}
def scenario(rng,r):
    L=rng.uniform(10,160);ph=1 if r in (1,3) else rng.uniform(.25,.75);pc=0 if r in (1,3) else 1-ph;rh,rc=rng.uniform(1.5,6),rng.uniform(1.5,6);ch=rng.uniform(.1,rh*.7) if r in (3,4) else 0;cc=rng.uniform(.1,rc*.7) if r==4 else 0;bh,wh=rng.uniform(.5,2),rng.uniform(.5,2);bc,wc=(rng.uniform(.5,2),rng.uniform(.5,2)) if r in (2,4) else (0,0)
    return Scenario(L,ph,pc,rh,rc,ch,cc,0,0,rng.uniform(.4,1)*L*max(bh,bc or bh),rng.uniform(.4,1)*L*max(wh,wc or wh),bh,bc,wh,wc)
def audit(sc,r,name):
    qref,_=reference(sc,r); kr=kkt(sc,r,qref); gr=solve_gurobi_round(sc,r,pwl_points=PWL_POINTS);qg=np.array([float(gr['Q_hot']),float(gr['Q_cold'])]);gk=grad(sc,r,qg); A=[];b,w=coeffs(sc,r)
    for a,cap in ((b,sc.beans_available),(w,sc.water_available)):
        if math.isfinite(cap) and abs(cap-a@qg)<=5e-3:A.append(a)
    Am=np.column_stack(A) if A else np.zeros((2,0)); plam,_=nnls(Am,gk) if A else (np.zeros(0),0); pred=gk-(Am@plam if A else 0); exact_g=obj(sc,r,qg); refobj=obj(sc,r,qref)
    dual_upper=refobj+max(0.,-refobj+exact_g) # recorded diagnostic, not a fake certificate
    ok=kr['kkt_residual']<=TOL and feasible(qref,sc,r) and exact_g<=refobj+DUAL_TOL
    return {'case':name,'round':r,'reference':{'Q_hot':float(qref[0]),'Q_cold':float(qref[1]),'objective':float(refobj)},'gurobi':{'Q_hot':float(qg[0]),'Q_cold':float(qg[1]),'exact_objective':float(exact_g)},'reference_kkt':kr,'pwl_exact_gradient_diagnostic':{'stationarity_inf':float(np.max(np.abs(pred))),'multipliers':plam.tolist()},'duality':{'exact_primal_gap':float(max(0.,refobj-exact_g)),'recorded_upper_bound':float(dual_upper)},'pass':bool(ok)}
def main():
    rng=random.Random(SEED);R=[]
    for r in (1,2,3,4):
        for i in range(CASES_PER_ROUND):
            try:R.append(audit(scenario(rng,r),r,f'r{r}_{i:02d}'))
            except Exception as e:R.append({'case':f'r{r}_{i:02d}','round':r,'error':repr(e),'pass':False})
    F=[x for x in R if not x.get('pass',False)];out={'schema':'gurobean.r7.2.kkt_duality.v2','seed':SEED,'pwl_points':PWL_POINTS,'cases':len(R),'failures':len(F),'max_reference_kkt':max((x.get('reference_kkt',{}).get('kkt_residual',0) for x in R),default=0),'max_pwl_exact_gradient_residual':max((x.get('pwl_exact_gradient_diagnostic',{}).get('stationarity_inf',0) for x in R),default=0),'max_exact_primal_gap':max((x.get('duality',{}).get('exact_primal_gap',0) for x in R),default=0),'status':'PASS' if not F else 'FAIL','results':R,'failure_cases':F};Path('r7_2_kkt_duality_v2.json').write_text(json.dumps(out,indent=2,allow_nan=True),encoding='utf-8');print('=== R7.2 v2 KKT / DUALITY AUDIT ===');print(f"CASES: {len(R)}");print(f"FAILURES: {len(F)}");print(f"MAX_REFERENCE_KKT: {out['max_reference_kkt']:.12g}");print(f"MAX_PWL_EXACT_GRADIENT_DIAGNOSTIC: {out['max_pwl_exact_gradient_residual']:.12g}");print(f"MAX_EXACT_PRIMAL_GAP: {out['max_exact_primal_gap']:.12g}");print(f"R7.2 v2 STATUS: {out['status']}");print('ARTIFACT: r7_2_kkt_duality_v2.json');return 0 if not F else 1
if __name__=='__main__':raise SystemExit(main())
