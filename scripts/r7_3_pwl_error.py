"""R7.3 — Empirical certification of PWL approximation error.

Compares Gurobi solutions at multiple breakpoint counts against the exact
analytic objective evaluated at those solutions and against the independent
SciPy reference. The production default remains untouched.
"""
from __future__ import annotations
import json, random
from pathlib import Path
import numpy as np
from gurobean.model import Scenario, solve_gurobi_round, solve_round_scipy, _round_objective

SEED=20260908
POINTS=(1001,2501,5001,10001,20001)
CASES=40
OBJ_TOL=3e-2

def sc(rng,rnd):
    lam=rng.uniform(10,180)
    ph=1 if rnd in (1,3) else rng.uniform(.2,.8); pc=0 if rnd in (1,3) else 1-ph
    rh,rc=rng.uniform(1,6),rng.uniform(1,6)
    ch=rng.uniform(.05,1.5) if rnd in (3,4) else 0
    cc=rng.uniform(.05,1.5) if rnd==4 else 0
    bh,wh=rng.uniform(.4,2),rng.uniform(.4,2)
    bc,wc=(rng.uniform(.4,2),rng.uniform(.4,2)) if rnd in (2,4) else (0,0)
    b=rng.uniform(.35,1.0)*lam*max(bh,bc or bh); w=rng.uniform(.35,1.0)*lam*max(wh,wc or wh)
    return Scenario(lam,ph,pc,rh,rc,ch,cc,0,0,b,w,bh,bc,wh,wc)

def main():
    rng=random.Random(SEED); rows=[]
    for rnd in (1,2,3,4):
        for i in range(CASES):
            s=sc(rng,rnd); ref=solve_round_scipy(s,rnd); ro=float(ref['objective'])
            for pts in POINTS:
                g=solve_gurobi_round(s,rnd,pwl_points=pts); qh,qc=float(g['Q_hot']),float(g['Q_cold'])
                exact=float(_round_objective(s,rnd in (2,4),rnd in (3,4),qh,qc))
                rows.append({'round':rnd,'case':i,'pwl_points':pts,'Q_hot':qh,'Q_cold':qc,'exact_objective':exact,'reference_objective':ro,'objective_error':abs(exact-ro),'reference_regret':max(0,ro-exact)})
    maxerr=max(x['objective_error'] for x in rows)
    bypts={str(p):{'max_objective_error':max(x['objective_error'] for x in rows if x['pwl_points']==p),'mean_objective_error':float(np.mean([x['objective_error'] for x in rows if x['pwl_points']==p]))} for p in POINTS}
    out={'schema':'gurobean.r7.3.pwl_error.v1','seed':SEED,'points':POINTS,'cases_per_round':CASES,'total_runs':len(rows),'max_objective_error':maxerr,'by_points':bypts,'status':'PASS' if maxerr<=OBJ_TOL else 'FAIL','results':rows}
    Path('r7_3_pwl_error.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print('=== R7.3 PWL ERROR CERTIFICATION ==='); print('TOTAL RUNS:',len(rows)); print('MAX_OBJECTIVE_ERROR:',f'{maxerr:.12g}'); print('R7.3 STATUS:',out['status']); print('ARTIFACT: r7_3_pwl_error.json'); print('R7.3_PWL_ERROR_OK' if out['status']=='PASS' else 'R7.3_PWL_ERROR_FAIL')
    return 0 if out['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
