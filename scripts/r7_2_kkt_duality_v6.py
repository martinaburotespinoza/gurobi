"""R7.2 v6 — definitive KKT + Lagrangian dual certificate.

The PWL optimizer is an approximation of the exact concave objective, so its
point is not required to satisfy the exact analytic KKT equations. This audit
therefore certifies the exact continuous problem independently, then measures
Gurobi/PWL feasibility, exact-objective regret, and Q displacement.

The dual is the actual Lagrangian dual for shared resource constraints:
  g(mu) = mu'b + sum_i sup_{q_i >= 0} [f_i(q_i) - (A'mu)_i q_i].
For a concave primal, weak duality gives g(mu) >= p*, and equality at KKT.
"""
from __future__ import annotations
import json, math, random
from pathlib import Path
import numpy as np
from scipy.optimize import brentq, minimize_scalar, nnls
from gurobean.model import Scenario, expected_newsvendor_gradient, expected_newsvendor_profit, solve_gurobi_round, _round_objective

SEED=20260908
PWL_POINTS=5001
CASES_PER_ROUND=25
KKT_TOL=2e-5
FEAS_TOL=2e-7
DUAL_GAP_TOL=3e-4
OBJ_REGRET_TOL=2e-2
Q_TOL=1.0

def flags(r): return r in (2,4), r in (3,4)
def setup(sc,r):
    cold,cost=flags(r)
    A=[]; b=[]; names=[]
    if math.isfinite(sc.beans_available): A.append([sc.beans_hot,sc.beans_cold if cold else 0.]); b.append(sc.beans_available); names.append('beans')
    if math.isfinite(sc.water_available): A.append([sc.water_hot,sc.water_cold if cold else 0.]); b.append(sc.water_available); names.append('water')
    return cold,cost,np.asarray(A,float),np.asarray(b,float),names
def f(sc,r,i,q):
    cold,cost,_,_,_=setup(sc,r)
    if i==0: return expected_newsvendor_profit(q,sc.lambda_hot,sc.revenue_hot,sc.cost_hot if cost else 0.,sc.salvage_hot)
    return expected_newsvendor_profit(q,sc.lambda_cold,sc.revenue_cold,sc.cost_cold if cost else 0.,sc.salvage_cold)
def df(sc,r,i,q):
    cold,cost,_,_,_=setup(sc,r)
    if i==0: return expected_newsvendor_gradient(q,sc.lambda_hot,sc.revenue_hot,sc.cost_hot if cost else 0.,sc.salvage_hot)
    return expected_newsvendor_gradient(q,sc.lambda_cold,sc.revenue_cold,sc.cost_cold if cost else 0.,sc.salvage_cold)
def feasible(sc,r,x,t=FEAS_TOL):
    _,_,A,b,_=setup(sc,r)
    return bool(np.all(x>=-t) and np.all(A@x<=b+t))
def bounds(sc,r):
    cold,_,A,b,_=setup(sc,r); out=[]
    for j,lam in enumerate((sc.lambda_hot,sc.lambda_cold)):
        vals=[b[k]/A[k,j] for k in range(len(b)) if A[k,j]>1e-14]
        vals.append(20*max(lam,1)+100)
        out.append((0.,float(min(vals))))
    return out
def vertices(sc,r):
    cold,_,A,b,_=setup(sc,r); hi=bounds(sc,r)
    if not cold: return [np.array([0.,0.])]
    lines=[(np.array([1.,0.]),0.),(np.array([0.,1.]),0.)]
    lines += [(A[k],b[k]) for k in range(len(b))]
    lines += [(np.array([1.,0.]),hi[0][1]),(np.array([0.,1.]),hi[1][1])]
    pts=[]
    for i in range(len(lines)):
        for j in range(i+1,len(lines)):
            M=np.vstack((lines[i][0],lines[j][0]))
            if abs(np.linalg.det(M))<1e-12: continue
            p=np.linalg.solve(M,np.array([lines[i][1],lines[j][1]]))
            if feasible(sc,r,p,1e-6): pts.append(p)
    out=[]
    for p in pts:
        if not any(np.linalg.norm(p-q)<=1e-8 for q in out): out.append(p)
    return out
def exact_ref(sc,r):
    cold,_,A,b,_=setup(sc,r); cand=vertices(sc,r)
    if not cold:
        hi=bounds(sc,r)[0][1]
        g0,gh=df(sc,r,0,0),df(sc,r,0,hi)
        q=0. if g0<=0 else hi if gh>=0 else brentq(lambda z:df(sc,r,0,z),0,hi,xtol=1e-12,rtol=1e-12)
        return np.array([q,0.])
    hi=bounds(sc,r)
    q0=[]
    for j in (0,1):
        lo,h=hi[j]; g0,gh=df(sc,r,j,lo),df(sc,r,j,h)
        q0.append(lo if g0<=0 else h if gh>=0 else brentq(lambda z:df(sc,r,j,z),lo,h,xtol=1e-12,rtol=1e-12))
    q0=np.array(q0)
    if feasible(sc,r,q0,1e-6): cand.append(q0)
    # Every polygon edge is one active original constraint. Optimize its 1-D restriction.
    cons=[(np.array([1.,0.]),0.),(np.array([0.,1.]),0.)]+[(A[k],b[k]) for k in range(len(b))]
    for a,rhs in cons:
        ps=[p for p in vertices(sc,r) if abs(a@p-rhs)<=2e-6]
        for i in range(len(ps)):
            for j in range(i+1,len(ps)):
                p0,p1=ps[i],ps[j]
                if np.dot(p1-p0,p1-p0)<=1e-18: continue
                z=minimize_scalar(lambda t:-_round_objective(sc,True,r in (3,4),*(p0+t*(p1-p0))),bounds=(0,1),method='bounded',options={'xatol':1e-11})
                cand.extend([p0+float(t)*(p1-p0) for t in (0.,1.,float(z.x)) if feasible(sc,r,p0+float(t)*(p1-p0),1e-6)])
    return max(cand,key=lambda x:_round_objective(sc,cold,r in (3,4),float(x[0]),float(x[1])))
def multipliers(sc,r,q):
    cold,_,A,b,names=setup(sc,r); g=np.array([df(sc,r,0,q[0]),df(sc,r,1,q[1]) if cold else 0.])
    active=[k for k in range(len(b)) if abs(A[k]@q-b[k])<=2e-6]
    best=(np.inf,np.zeros(len(b)))
    if active:
        aa=A[active].T
        mu,rr=nnls(aa,g)
        res=np.max(np.abs(g-aa@mu))
        if res<best[0]:
            full=np.zeros(len(b)); full[active]=mu; best=(res,full)
    else: best=(np.max(np.maximum(g,0)),np.zeros(len(b)))
    return g,best[1],active,best[0]
def dual_value(sc,r,mu):
    cold,cost,A,b,_=setup(sc,r); c=A.T@mu if len(b) else np.zeros(2); total=float(mu@b) if len(b) else 0.
    for i in (0,1):
        if i==1 and not cold: continue
        lo,hi=bounds(sc,r)[i]
        slope0=df(sc,r,i,lo)
        # Supremum over q>=0. A finite root exists when the marginal value crosses c.
        if slope0<=c[i]+1e-12: q=0.
        else:
            # Find a sufficiently large point where derivative is below c.
            h=max(hi,sc.lambda_hot if i==0 else sc.lambda_cold,1.)
            while df(sc,r,i,h)>c[i] and h<1e8: h*=2
            if df(sc,r,i,h)>c[i]+1e-10: return math.inf
            q=brentq(lambda z:df(sc,r,i,z)-c[i],0,h,xtol=1e-11,rtol=1e-12)
        total += f(sc,r,i,q)-c[i]*q
    return float(total)
def scenario(rng,r):
    L=rng.uniform(10,160); ph=1. if r in (1,3) else rng.uniform(.25,.75); pc=0. if r in (1,3) else 1-ph
    rh,rc=rng.uniform(1.5,6),rng.uniform(1.5,6); ch=rng.uniform(.1,rh*.7) if r in (3,4) else 0.; cc=rng.uniform(.1,rc*.7) if r==4 else 0.
    bh,wh=rng.uniform(.5,2),rng.uniform(.5,2); bc,wc=(rng.uniform(.5,2),rng.uniform(.5,2)) if r in (2,4) else (0.,0.)
    return Scenario(L,ph,pc,rh,rc,ch,cc,0.,0.,rng.uniform(.4,1.)*L*max(bh,bc or bh),rng.uniform(.4,1.)*L*max(wh,wc or wh),bh,bc,wh,wc)
def main():
    rng=random.Random(SEED); rows=[]
    for r in (1,2,3,4):
        for i in range(CASES_PER_ROUND):
            sc=scenario(rng,r); q=exact_ref(sc,r); primal=_round_objective(sc,r in (2,4),r in (3,4),*q); g,mu,active,kkt=multipliers(sc,r,q); dual=dual_value(sc,r,mu); gap=dual-primal if math.isfinite(dual) else math.inf
            gr=solve_gurobi_round(sc,r,pwl_points=PWL_POINTS); qg=np.array([gr['Q_hot'],gr['Q_cold']]); exactg=_round_objective(sc,r in (2,4),r in (3,4),*qg); regret=max(0.,primal-exactg)
            rows.append({'round':r,'case':i,'reference_q':q.tolist(),'reference_objective':primal,'kkt_residual':float(kkt),'multipliers':mu.tolist(),'dual_objective':dual,'duality_gap':gap,'gurobi_q':qg.tolist(),'gurobi_exact_objective':exactg,'objective_regret':regret,'q_inf_error':float(np.max(np.abs(qg-q))),'feasible':feasible(sc,r,qg),'pass':bool(kkt<=KKT_TOL and gap<=DUAL_GAP_TOL and regret<=OBJ_REGRET_TOL and np.max(np.abs(qg-q))<=Q_TOL and feasible(sc,r,qg))})
    out={'schema':'gurobean.r7.2.kkt_duality.v6','seed':SEED,'cases':len(rows),'pwl_points':PWL_POINTS,'kkt_tol':KKT_TOL,'duality_gap_tol':DUAL_GAP_TOL,'objective_regret_tol':OBJ_REGRET_TOL,'q_tol':Q_TOL,'failures':sum(not x['pass'] for x in rows),'max_kkt':max(x['kkt_residual'] for x in rows),'max_duality_gap':max(x['duality_gap'] for x in rows),'max_regret':max(x['objective_regret'] for x in rows),'max_q_error':max(x['q_inf_error'] for x in rows),'status':'PASS' if all(x['pass'] for x in rows) else 'FAIL','results':rows}
    Path('r7_2_kkt_duality_v6.json').write_text(json.dumps(out,indent=2,allow_nan=True),encoding='utf-8')
    print('=== R7.2 v6 DEFINITIVE KKT / LAGRANGIAN DUAL ==='); print('CASES:',len(rows)); print('FAILURES:',out['failures']); print('MAX_KKT:',f"{out['max_kkt']:.12g}"); print('MAX_DUALITY_GAP:',f"{out['max_duality_gap']:.12g}"); print('MAX_REGRET:',f"{out['max_regret']:.12g}"); print('MAX_Q_ERROR:',f"{out['max_q_error']:.12g}"); print('R7.2 STATUS:',out['status']); print('ARTIFACT: r7_2_kkt_duality_v6.json'); return 0 if out['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
