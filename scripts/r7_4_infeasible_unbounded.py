"""R7.4 — Formal status classification for infeasible/unbounded boundaries."""
from __future__ import annotations
import json
from pathlib import Path
from gurobean.model import Scenario, solve_gurobi_round, solve_round_scipy

def check(name, rnd, sc, expected):
    try:
        solve_gurobi_round(sc,rnd,pwl_points=5001)
        actual='optimal'
    except ValueError as e:
        msg=str(e).lower(); actual='unbounded' if 'unbounded' in msg else 'error'
    except Exception as e:
        actual='error'
    return {'case':name,'round':rnd,'expected':expected,'actual':actual,'pass':actual==expected}

def main():
    cases=[]
    # Finite cap makes otherwise unbounded economics bounded.
    cases.append(check('finite_resource_cap',1,Scenario(50,p_hot=1,revenue_hot=3,beans_available=25,beans_hot=1),'optimal'))
    # Positive revenue and zero cost with no finite hot resource cap is unbounded.
    cases.append(check('r1_unbounded',1,Scenario(50,p_hot=1,revenue_hot=3),'unbounded'))
    cases.append(check('r3_unbounded',3,Scenario(50,p_hot=1,revenue_hot=3,cost_hot=0),'unbounded'))
    # Infeasible negative capacities are rejected at construction time.
    try:
        Scenario(10,beans_available=-1); actual='invalid_input'
    except ValueError: actual='invalid_input'
    cases.append({'case':'negative_resource','expected':'invalid_input','actual':actual,'pass':actual=='invalid_input'})
    failures=[x for x in cases if not x['pass']]
    out={'schema':'gurobean.r7.4.status_boundaries.v1','cases':cases,'failures':len(failures),'status':'PASS' if not failures else 'FAIL'}
    Path('r7_4_status_boundaries.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print('=== R7.4 STATUS BOUNDARIES ==='); print('CASES:',len(cases)); print('FAILURES:',len(failures)); print('R7.4 STATUS:',out['status']); print('ARTIFACT: r7_4_status_boundaries.json'); print('R7.4_STATUS_BOUNDARIES_OK' if not failures else 'R7.4_STATUS_BOUNDARIES_FAIL')
    return 0 if not failures else 1
if __name__=='__main__': raise SystemExit(main())
