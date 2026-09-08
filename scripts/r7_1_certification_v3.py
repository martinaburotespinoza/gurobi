"""R7.1 v3 — exact-reference certification for R1-R4.

Uses the same independent polygon/edge optimizer as definitive R7.2 v6,
then certifies feasibility, exact objective regret and KKT stationarity.
SLSQP is deliberately not used as the certifying reference.
"""
from __future__ import annotations
import json, random
from pathlib import Path
import numpy as np
from gurobean.model import Scenario, expected_newsvendor_gradient, solve_gurobi_round, _round_objective
from r7_2_kkt_duality_v6 import exact_ref, multipliers, feasible

SEED=20260908; CASES_PER_ROUND=25; PWL_POINTS=5001
OBJ_TOL=2e-2; Q_TOL=1.; KKT_TOL=2e-5

def scenario(rng,r):
    L=rng.uniform(10,160); ph=1. if r in (1,3) else rng.uniform(.25,.75); pc=0. if r in (1,3) else 1-ph
    rh,rc=rng.uniform(1.5,6),rng.uniform(1.5,6); ch=rng.uniform(.1,rh*.7) if r in (3,4) else 0.; cc=rng.uniform(.1,rc*.7) if r==4 else 0.
    bh,wh=rng.uniform(.5,2),rng.uniform(.5,2); bc,wc=(rng.uniform(.5,2),rng.uniform(.5,2)) if r in (2,4) else (0.,0.)
    return Scenario(L,ph,pc,rh,rc,ch,cc,0.,0.,rng.uniform(.4,1.)*L*max(bh,bc or bh),rng.uniform(.4,1.)*L*max(wh,wc or wh),bh,bc,wh,wc)

def main():
    rng=random.Random(SEED); rows=[]
    for r in (1,2,3,4):
        for i in range(CASES_PER_ROUND):
            sc=scenario(rng,r); q=exact_ref(sc,r); ref=_round_objective(sc,r in (2,4),r in (3,4),*q); _,mu,active,kkt=multipliers(sc,r,q)
            gr=solve_gurobi_round(sc,r,pwl_points=PWL_POINTS); qg=np.array([gr['Q_hot'],gr['Q_cold']],float); exactg=_round_objective(sc,r in (2,4),r in (3,4),*qg); regret=max(0.,ref-exactg)
            rows.append({'round':r,'case':i,'reference_q':q.tolist(),'reference_objective':ref,'kkt_residual':float(kkt),'active_resources':active,'multipliers':mu.tolist(),'gurobi_q':qg.tolist(),'gurobi_exact_objective':exactg,'objective_error':abs(exactg-ref),'exact_regret':regret,'q_inf_error':float(np.max(np.abs(qg-q))),'feasible':feasible(sc,r,qg),'pass':bool(kkt<=KKT_TOL and regret<=OBJ_TOL and np.max(np.abs(qg-q))<=Q_TOL and feasible(sc,r,qg))})
    out={'schema':'gurobean.r7.1.certification.v3','seed':SEED,'cases':len(rows),'pwl_points':PWL_POINTS,'failures':sum(not x['pass'] for x in rows),'max_objective_error':max(x['objective_error'] for x in rows),'max_exact_regret':max(x['exact_regret'] for x in rows),'max_q_inf_error':max(x['q_inf_error'] for x in rows),'max_kkt':max(x['kkt_residual'] for x in rows),'status':'PASS' if all(x['pass'] for x in rows) else 'FAIL','results':rows}
    Path('r7_1_certification_v3.json').write_text(json.dumps(out,indent=2,allow_nan=True),encoding='utf-8')
    print('=== R7.1 v3 EXACT MATHEMATICAL CERTIFICATION ==='); print('CASES:',len(rows)); print('FAILURES:',out['failures']); print('MAX_OBJECTIVE_ERROR:',f"{out['max_objective_error']:.12g}"); print('MAX_EXACT_REGRET:',f"{out['max_exact_regret']:.12g}"); print('MAX_Q_INF_ERROR:',f"{out['max_q_inf_error']:.12g}"); print('MAX_KKT:',f"{out['max_kkt']:.12g}"); print('R7.1 STATUS:',out['status']); print('ARTIFACT: r7_1_certification_v3.json'); return 0 if out['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
