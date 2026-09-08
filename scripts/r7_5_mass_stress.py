"""R7.5 — deterministic mass stress over R1-R4.

Runs 500 cases per round against the exact independent reference and Gurobi/PWL.
This is intentionally separate from the smaller forensic audits so failures are
localized without changing production code.
"""
from __future__ import annotations
import json, random, time
from pathlib import Path
import numpy as np
from gurobean.model import Scenario, solve_gurobi_round, _round_objective
from r7_2_kkt_duality_v6 import exact_ref, feasible

SEED=20260908; CASES_PER_ROUND=500; PWL_POINTS=5001; OBJ_TOL=3e-2; Q_TOL=1.0

def scenario(rng,r):
    L=rng.uniform(5,250); ph=1. if r in (1,3) else rng.uniform(.1,.9); pc=0. if r in (1,3) else 1-ph
    rh,rc=rng.uniform(1.0,8.0),rng.uniform(1.0,8.0); ch=rng.uniform(0.,rh*.8) if r in (3,4) else 0.; cc=rng.uniform(0.,rc*.8) if r==4 else 0.
    bh,wh=rng.uniform(.2,2.5),rng.uniform(.2,2.5); bc,wc=(rng.uniform(.2,2.5),rng.uniform(.2,2.5)) if r in (2,4) else (0.,0.)
    b=rng.uniform(.25,1.2)*L*max(bh,bc or bh); w=rng.uniform(.25,1.2)*L*max(wh,wc or wh)
    return Scenario(L,ph,pc,rh,rc,ch,cc,0.,0.,b,w,bh,bc,wh,wc)

def main():
    rng=random.Random(SEED); failures=[]; total=0; max_reg=0.; max_q=0.; t0=time.time()
    for r in (1,2,3,4):
        for i in range(CASES_PER_ROUND):
            total+=1; sc=scenario(rng,r)
            try:
                q=exact_ref(sc,r); ref=_round_objective(sc,r in (2,4),r in (3,4),*q)
                g=solve_gurobi_round(sc,r,pwl_points=PWL_POINTS); qg=np.array([g['Q_hot'],g['Q_cold']],float); exact=_round_objective(sc,r in (2,4),r in (3,4),*qg)
                reg=max(0.,ref-exact); qe=float(np.max(np.abs(qg-q))); ok=feasible(sc,r,qg) and reg<=OBJ_TOL and qe<=Q_TOL
                max_reg=max(max_reg,reg); max_q=max(max_q,qe)
                if not ok: failures.append({'round':r,'case':i,'regret':reg,'q_error':qe,'feasible':feasible(sc,r,qg),'reference_q':q.tolist(),'gurobi_q':qg.tolist()})
            except Exception as e: failures.append({'round':r,'case':i,'error':repr(e)})
        print(f'R{r}: completed {CASES_PER_ROUND} cases')
    out={'schema':'gurobean.r7.5.mass_stress.v1','seed':SEED,'cases_per_round':CASES_PER_ROUND,'total_cases':total,'pwl_points':PWL_POINTS,'objective_regret_tol':OBJ_TOL,'q_tol':Q_TOL,'failures':len(failures),'max_exact_regret':max_reg,'max_q_inf_error':max_q,'elapsed_seconds':time.time()-t0,'status':'PASS' if not failures else 'FAIL','failure_cases':failures[:100]}
    Path('r7_5_mass_stress.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print('=== R7.5 MASS STRESS ==='); print('TOTAL CASES:',total); print('FAILURES:',len(failures)); print('MAX_EXACT_REGRET:',f"{max_reg:.12g}"); print('MAX_Q_INF_ERROR:',f"{max_q:.12g}"); print('R7.5 STATUS:',out['status']); print('ARTIFACT: r7_5_mass_stress.json'); return 0 if not failures else 1
if __name__=='__main__': raise SystemExit(main())
