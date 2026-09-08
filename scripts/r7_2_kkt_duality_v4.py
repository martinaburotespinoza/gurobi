"""R7.2 v4 — exact 2D concave reference + KKT audit.

The reference solver is independent of Gurobi: for the two-variable concave
problem it enumerates polygon vertices, all feasible boundary segments, and
the unconstrained stationary point. This avoids SLSQP boundary clipping and
makes KKT a genuine certificate of the analytic reference optimum.
"""
from __future__ import annotations
import json, math, random
from pathlib import Path
import numpy as np
from scipy.optimize import brentq, minimize_scalar, nnls
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
    if math.isfinite(sc.beans_available):
        A.append([sc.beans_hot, sc.beans_cold if cold else 0.]); caps.append(sc.beans_available); names.append('beans')
    if math.isfinite(sc.water_available):
        A.append([sc.water_hot, sc.water_cold if cold else 0.]); caps.append(sc.water_available); names.append('water')
    return cold,cost,np.asarray(A,float),np.asarray(caps,float),names


def obj(sc,r,x):
    cold,cost,_,_,_=setup(sc,r)
    return float(_round_objective(sc,cold,cost,float(x[0]),float(x[1])))


def grad(sc,r,x):
    cold,cost,_,_,_=setup(sc,r)
    return np.array([
        expected_newsvendor_gradient(float(x[0]),sc.lambda_hot,sc.revenue_hot,sc.cost_hot if cost else 0.,sc.salvage_hot),
        expected_newsvendor_gradient(float(x[1]),sc.lambda_cold,sc.revenue_cold,sc.cost_cold if cost else 0.,sc.salvage_cold) if cold else 0.
    ],float)


def feasible(sc,r,x,t=FEAS_TOL):
    _,_,A,caps,_=setup(sc,r)
    return bool(np.all(np.asarray(x)>=-t) and all(A[i]@x<=caps[i]+t for i in range(len(caps))))


def box(sc,r):
    cold,_,A,caps,_=setup(sc,r)
    if not cold: return [(0.,0.),(0.,0.)]
    out=[]
    for j,lam in enumerate((sc.lambda_hot,sc.lambda_cold)):
        vals=[caps[i]/A[i,j] for i in range(len(caps)) if A[i,j]>1e-14]
        vals.append(20.*max(lam,1.)+100.)
        out.append((0.,max(0.,float(min(vals)))))
    return out


def stationary_1d(sc,r,j):
    b=box(sc,r)[j]
    if b[1]<=0: return float(b[0])
    def gj(q): return float(grad(sc,r,[q,0.] if j==0 else [0.,q])[j])
    g0=gj(b[0]); gh=gj(b[1])
    if g0<=0: return b[0]
    if gh>=0: return b[1]
    return float(brentq(gj,b[0],b[1],xtol=1e-12,rtol=1e-12))


def polygon(sc,r):
    """Return feasible vertices of the 2D resource polygon."""
    cold,_,A,caps,_=setup(sc,r)
    if not cold: return [np.array([0.,0.])]
    lines=[(np.array([1.,0.]),0.),(np.array([0.,1.]),0.)]
    for a,c in zip(A,caps): lines.append((np.asarray(a,float),float(c)))
    b=box(sc,r); lines += [(np.array([1.,0.]),b[0][1]),(np.array([0.,1.]),b[1][1])]
    pts=[]
    for i in range(len(lines)):
        for j in range(i+1,len(lines)):
            M=np.vstack([lines[i][0],lines[j][0]])
            if abs(np.linalg.det(M))<1e-12: continue
            p=np.linalg.solve(M,np.array([lines[i][1],lines[j][1]],float))
            if feasible(sc,r,p): pts.append(p)
    uniq=[]
    for p in pts:
        if not any(np.linalg.norm(p-q)<=1e-9 for q in uniq): uniq.append(p)
    return uniq


def edge_candidates(sc,r,vertices):
    """Optimize every polygon edge induced by an active constraint."""
    cold,_,A,caps,_=setup(sc,r)
    if not cold: return []
    # Candidate pairs are enough to identify every edge; only retain pairs
    # sharing one active original constraint (including coordinate axes).
    constraints=[(np.array([1.,0.]),0.),(np.array([0.,1.]),0.)]
    constraints += [(np.asarray(a,float),float(c)) for a,c in zip(A,caps)]
    candidates=[]
    for a,cap in constraints:
        pts=[p for p in vertices if abs(float(a@p-cap))<=1e-6]
        if len(pts)<2: continue
        for u in range(len(pts)):
            for v in range(u+1,len(pts)):
                p0,p1=pts[u],pts[v]; d=p1-p0
                dd=float(d@d)
                if dd<=1e-18: continue
                # Verify the whole segment is feasible (convexity makes the
                # endpoints sufficient, but retain this explicit guard).
                if not feasible(sc,r,(p0+p1)/2.,1e-6): continue
                fun=lambda t:-obj(sc,r,p0+t*d)
                z=minimize_scalar(fun,bounds=(0.,1.),method='bounded',options={'xatol':1e-12,'maxiter':500})
                for t in (float(z.x),0.,1.): candidates.append(p0+t*d)
    return candidates


def reference(sc,r):
    vertices=polygon(sc,r)
    candidates=list(vertices)
    # Independent analytic stationary point, if it is feasible.
    q=np.array([stationary_1d(sc,r,0),stationary_1d(sc,r,1)]) if r in (2,4) else np.array([stationary_1d(sc,r,0),0.])
    if feasible(sc,r,q): candidates.append(q)
    candidates.extend(edge_candidates(sc,r,vertices))
    # Axis optima are represented by edges, but explicitly add them for
    # numerical safety.
    if r in (2,4):
        for j in (0,1):
            qj=stationary_1d(sc,r,j); qx=np.array([qj,0.]) if j==0 else np.array([0.,qj])
            if feasible(sc,r,qx): candidates.append(qx)
    best=max((p for p in candidates if feasible(sc,r,p)),key=lambda p:obj(sc,r,p))
    return np.asarray(best,float)


def kkt(sc,r,x):
    _,_,A,caps,names=setup(sc,r); g=grad(sc,r,x)
    sl=caps-A@x if len(A) else np.empty(0)
    active=[i for i,s in enumerate(sl) if abs(float(s))<=2e-6]
    selected=[]; rank=0
    for i in active:
        M=A[selected+[i]].T if selected else A[[i]].T
        nr=np.linalg.matrix_rank(M,tol=1e-10)
        if nr>rank: selected.append(i); rank=nr
    M=A[selected].T if selected else np.zeros((2,0))
    lam=np.zeros(len(selected))
    if M.shape[1]: lam,_=nnls(M,g)
    residual=g-(M@lam if M.shape[1] else 0.)
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
    if M.shape[1]: pl,_=nnls(M,gd)
    diag=gd-(M@pl if M.shape[1] else 0.)
    return {'case':name,'round':r,'reference':{'Q_hot':float(qr[0]),'Q_cold':float(qr[1]),'objective':ro},'gurobi':{'Q_hot':float(qg[0]),'Q_cold':float(qg[1]),'exact_objective':go},'reference_kkt':kr,'pwl_exact_gradient_diagnostic':{'stationarity_inf':float(np.max(np.abs(diag))),'multipliers':pl.tolist()},'comparison':{'objective_abs_error':abs(go-ro),'q_inf_error':float(np.max(np.abs(qg-qr))),'gurobi_feasible':feasible(sc,r,qg)},'pass':bool(kr['kkt_residual']<=KKT_TOL and kr['primal_violation']<=FEAS_TOL and abs(go-ro)<=OBJ_TOL and float(np.max(np.abs(qg-qr)))<=1.)}


def main():
    rng=random.Random(SEED); results=[]
    for r in (1,2,3,4):
        for i in range(CASES_PER_ROUND):
            try: results.append(audit(scenario(rng,r),r,f'r{r}_{i:02d}'))
            except Exception as e: results.append({'case':f'r{r}_{i:02d}','round':r,'error':repr(e),'pass':False})
    failures=[x for x in results if not x.get('pass',False)]
    out={'schema':'gurobean.r7.2.kkt_duality.v4','seed':SEED,'cases':len(results),'failures':len(failures),'max_reference_kkt':max((x.get('reference_kkt',{}).get('kkt_residual',0.) for x in results),default=0.),'max_objective_error':max((x.get('comparison',{}).get('objective_abs_error',0.) for x in results),default=0.),'max_q_inf_error':max((x.get('comparison',{}).get('q_inf_error',0.) for x in results),default=0.),'max_pwl_exact_gradient_diagnostic':max((x.get('pwl_exact_gradient_diagnostic',{}).get('stationarity_inf',0.) for x in results),default=0.),'status':'PASS' if not failures else 'FAIL','results':results,'failure_cases':failures}
    Path('r7_2_kkt_duality_v4.json').write_text(json.dumps(out,indent=2),encoding='utf-8'); print('=== R7.2 v4 KKT / DUALITY AUDIT ==='); print(f"CASES: {len(results)}"); print(f"FAILURES: {len(failures)}"); print(f"MAX_REFERENCE_KKT: {out['max_reference_kkt']:.12g}"); print(f"MAX_OBJECTIVE_ERROR: {out['max_objective_error']:.12g}"); print(f"MAX_Q_INF_ERROR: {out['max_q_inf_error']:.12g}"); print(f"MAX_PWL_EXACT_GRADIENT_DIAGNOSTIC: {out['max_pwl_exact_gradient_diagnostic']:.12g}"); print(f"R7.2 v4 STATUS: {out['status']}"); print('ARTIFACT: r7_2_kkt_duality_v4.json'); return 0 if not failures else 1
if __name__=='__main__': raise SystemExit(main())
