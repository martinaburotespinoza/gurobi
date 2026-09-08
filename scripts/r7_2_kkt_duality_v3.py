"""R7.2 v3 — robust KKT audit for the exact analytic model.

The certification target is the exact concave objective. Gurobi/PWL is
compared separately; its analytic-gradient residual is diagnostic only.
"""
from __future__ import annotations
import json, math, random
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from gurobean.model import Scenario, expected_newsvendor_gradient, solve_gurobi_round, _round_objective

SEED=20260908
CASES_PER_ROUND=25
PWL_POINTS=5001
KKT_TOL=5e-6
FEAS_TOL=2e-7
OBJ_TOL=2e-2

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

def bounds(sc,r):
    cold,cost,A,caps,_=setup(sc,r); out=[]
    for j,lam in enumerate((sc.lambda_hot,sc.lambda_cold)):
        if j==1 and not cold: out.append((0.,0.)); continue
        rev=(sc.revenue_hot,sc.revenue_cold)[j]; c=(sc.cost_hot,sc.cost_cold)[j] if cost else 0.; s=(sc.salvage_hot,sc.salvage_cold)[j]
        # A safe finite box from resources. If a variable has no direct finite
        # cap, 20*lambda + 100 is ample for the certified positive-margin cases.
        caps_j=[caps[i]/A[i,j] for i in range(len(caps)) if A[i,j]>0]
        hi=min(caps_j+[20.*max(lam,1.)+100.])
        out.append((0.,max(0.,float(hi))))
    return out

def feasible(sc,r,x,t=FEAS_TOL):
    _,_,A,caps,_=setup(sc,r)
    return bool(np.all(x>=-t) and all(A[i]@x<=caps[i]+t for i in range(len(caps))))

def reference(sc,r):
    b=bounds(sc,r)
    cons=[]
    _,_,A,caps,_=setup(sc,r)
    for a,cap in zip(A,caps): cons.append({'type':'ineq','fun':lambda x,a=a,cap=cap: cap-a@x,'jac':lambda x,a=a:-a})
    starts=[np.array([min(sc.lambda_hot,b[0][1]),min(sc.lambda_cold,b[1][1])]),np.array([0.,0.])]
    if b[1][1]>0: starts += [np.array([b[0][1],0.]),np.array([0.,b[1][1]])]
    best=None
    for x0 in starts:
        if not feasible(sc,r,x0):
            for k in range(1,30):
                y=x0*(0.5**k)
                if feasible(sc,r,y): x0=y; break
        z=minimize(lambda x:-obj(sc,r,x),x0,jac=lambda x:-grad(sc,r,x),method='SLSQP',bounds=b,constraints=cons,options={'ftol':1e-12,'maxiter':2000})
        if z.success and feasible(sc,r,z.x) and (best is None or z.fun<best.fun): best=z
    if best is None: raise RuntimeError('independent analytic reference failed')
    return np.asarray(best.x,float)

def kkt(sc,r,x):
    _,_,A,caps,names=setup(sc,r); g=grad(sc,r,x)
    sl=caps-A@x if len(A) else np.empty(0)
    active=[i for i,s in enumerate(sl) if abs(float(s))<=2e-5]
    selected=[]; rank=0
    for i in active:
        M=A[selected+[i]].T if selected else A[[i]].T
        nr=np.linalg.matrix_rank(M,tol=1e-10)
        if nr>rank: selected.append(i); rank=nr
    M=A[selected].T if selected else np.zeros((2,0))
    lam=np.zeros(len(selected))
    if M.shape[1]: lam,_=__import__('scipy.optimize',fromlist=['nnls']).nnls(M,g)
    residual=g-(M@lam if M.shape[1] else 0.)
    # For x_j=0, KKT requires residual_j <= 0 (gradient cannot point into feasible domain).
    lower=np.zeros(2)
    for j in range(2):
        if x[j]<=2e-6: lower[j]=max(0.,-residual[j])
    station=residual+lower
    comp=max([abs(float(lam[k]*sl[selected[k]])) for k in range(len(selected))]+[abs(float(lower[j]*x[j])) for j in range(2)]+[0.])
    return {'gradient':g.tolist(),'active_constraints':[names[i] for i in selected],'multipliers':lam.tolist(),'lower_multipliers':lower.tolist(),'slacks':{names[i]:float(sl[i]) for i in range(len(names))},'stationarity_inf':float(np.max(np.abs(station))),'complementarity':float(comp),'primal_violation':float(max([0.]+[max(0.,-float(v)) for v in x]+[max(0.,-float(v)) for v in sl])),'kkt_residual':float(max(np.max(np.abs(station)),comp))}

def scenario(rng,r):
    L=rng.uniform(10,160); ph=1. if r in (1,3) else rng.uniform(.25,.75); pc=0. if r in (1,3) else 1-ph
    rh,rc=rng.uniform(1.5,6),rng.uniform(1.5,6); ch=rng.uniform(.1,rh*.7) if r in (3,4) else 0.; cc=rng.uniform(.1,rc*.7) if r==4 else 0.
    bh,wh=rng.uniform(.5,2),rng.uniform(.5,2); bc,wc=(rng.uniform(.5,2),rng.uniform(.5,2)) if r in (2,4) else (0.,0.)
    return Scenario(L,ph,pc,rh,rc,ch,cc,0.,0.,rng.uniform(.4,1.)*L*max(bh,bc or bh),rng.uniform(.4,1.)*L*max(wh,wc or wh),bh,bc,wh,wc)

def audit(sc,r,name):
    qr=reference(sc,r); kr=kkt(sc,r,qr); gr=solve_gurobi_round(sc,r,pwl_points=PWL_POINTS); qg=np.array([float(gr['Q_hot']),float(gr['Q_cold'])]); ro=obj(sc,r,qr); go=obj(sc,r,qg)
    gd=grad(sc,r,qg); _,_,A,caps,names=setup(sc,r); active=[i for i,s in enumerate(caps-A@qg) if abs(float(s))<=5e-3]; M=A[active].T if active else np.zeros((2,0)); pl=np.zeros(len(active));
    if M.shape[1]: pl,_=__import__('scipy.optimize',fromlist=['nnls']).nnls(M,gd)
    diag=gd-(M@pl if M.shape[1] else 0.)
    return {'case':name,'round':r,'reference':{'Q_hot':float(qr[0]),'Q_cold':float(qr[1]),'objective':ro},'gurobi':{'Q_hot':float(qg[0]),'Q_cold':float(qg[1]),'exact_objective':go},'reference_kkt':kr,'pwl_exact_gradient_diagnostic':{'stationarity_inf':float(np.max(np.abs(diag))),'multipliers':pl.tolist()},'comparison':{'objective_abs_error':abs(go-ro),'q_inf_error':float(np.max(np.abs(qg-qr))),'gurobi_feasible':feasible(sc,r,qg)},'pass':bool(kr['kkt_residual']<=KKT_TOL and kr['primal_violation']<=FEAS_TOL and abs(go-ro)<=OBJ_TOL and float(np.max(np.abs(qg-qr)))<=1.)}

def main():
    rng=random.Random(SEED); results=[]
    for r in (1,2,3,4):
        for i in range(CASES_PER_ROUND):
            try: results.append(audit(scenario(rng,r),r,f'r{r}_{i:02d}'))
            except Exception as e: results.append({'case':f'r{r}_{i:02d}','round':r,'error':repr(e),'pass':False})
    failures=[x for x in results if not x.get('pass',False)]
    out={'schema':'gurobean.r7.2.kkt_duality.v3','seed':SEED,'cases':len(results),'failures':len(failures),'max_reference_kkt':max((x.get('reference_kkt',{}).get('kkt_residual',0.) for x in results),default=0.),'max_objective_error':max((x.get('comparison',{}).get('objective_abs_error',0.) for x in results),default=0.),'max_q_inf_error':max((x.get('comparison',{}).get('q_inf_error',0.) for x in results),default=0.),'max_pwl_exact_gradient_diagnostic':max((x.get('pwl_exact_gradient_diagnostic',{}).get('stationarity_inf',0.) for x in results),default=0.),'status':'PASS' if not failures else 'FAIL','results':results,'failure_cases':failures}
    Path('r7_2_kkt_duality_v3.json').write_text(json.dumps(out,indent=2),encoding='utf-8'); print('=== R7.2 v3 KKT / DUALITY AUDIT ==='); print(f"CASES: {len(results)}"); print(f"FAILURES: {len(failures)}"); print(f"MAX_REFERENCE_KKT: {out['max_reference_kkt']:.12g}"); print(f"MAX_OBJECTIVE_ERROR: {out['max_objective_error']:.12g}"); print(f"MAX_Q_INF_ERROR: {out['max_q_inf_error']:.12g}"); print(f"MAX_PWL_EXACT_GRADIENT_DIAGNOSTIC: {out['max_pwl_exact_gradient_diagnostic']:.12g}"); print(f"R7.2 v3 STATUS: {out['status']}"); print('ARTIFACT: r7_2_kkt_duality_v3.json'); return 0 if not failures else 1
if __name__=='__main__': raise SystemExit(main())
