from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from gurobean import model,r9

REF_TOL=r9.REFERENCE_OBJ_TOL
OBJ_TOL=2e-6
PWL_POINTS=20001
# Diagnostic refinement meshes. They are reported for auditability only;
# intermediate meshes are not required to improve monotonically.
REFINE_POINTS=(5001,10001,20001)
ARTIFACT=ROOT/'r9_release_certification.json'

def _git_state():
    import subprocess
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
    if dirty: raise RuntimeError('working tree must be clean for certification')
    return sha

def _exact_profit(Q,p):
    return model.expected_newsvendor_profit(Q,**p)

def _feasible(Q,p,tol=1e-8):
    return Q >= -tol and Q <= p['economic_upper_bound'] + tol

def check(case,round_number,params):
    reference=model.solve_reference_round(params)
    rq=reference['q']
    exact_ref=_exact_profit(rq,params)
    reference_ok=bool(reference['success']) and _feasible(rq,params) and abs(exact_ref-reference['objective'])<=REF_TOL
    try:
        solved=model.solve_gurobi_round(params,pwl_points=PWL_POINTS)
        q=solved['q']
        exact=_exact_profit(q,params)
        solver_obj=solved['objective']
        regret=exact_ref-exact
        solver_obj_error=abs(solver_obj-exact)
        feasible=_feasible(q,params)
        status=int(solved['status'])
        passed=reference_ok and status==2 and feasible and regret<=OBJ_TOL and solver_obj_error<=OBJ_TOL
        return {
            'case':case,'round_number':round_number,'pwl_points':PWL_POINTS,
            'reference_ok':reference_ok,'gurobi_status':status,'feasible':feasible,
            'exact_objective':exact,'reference_objective':exact_ref,'exact_regret':regret,
            'solver_objective':solver_obj,'solver_objective_error':solver_obj_error,
            'q_hot':q,'q_cold':solved.get('q_cold'),
            'reference_q_hot':rq,'reference_q_cold':reference.get('q_cold'),
            'q_error':abs(q-rq),'passed':passed,'error':None if passed else 'strict gate failure'
        }
    except Exception as exc:
        return {
            'case':case,'round_number':round_number,'pwl_points':PWL_POINTS,
            'reference_ok':reference_ok,'gurobi_status':None,'feasible':False,
            'exact_objective':None,'reference_objective':exact_ref,'exact_regret':None,
            'solver_objective':None,'solver_objective_error':None,
            'q_hot':None,'q_cold':None,'reference_q_hot':rq,
            'reference_q_cold':reference.get('q_cold'),'q_error':None,
            'passed':False,'error':repr(exc)
        }

def main():
    commit=_git_state()
    import gurobipy as gp
    env=gp.Env(empty=True)
    env.setParam('OutputFlag',0)
    env.start()
    env.dispose()
    records=[]
    for case in range(r9.CASES):
        for round_number in range(1,r9.ROUNDS+1):
            params=r9.scenario(case,round_number)
            records.append(check(case,round_number,params))
    failures=[x for x in records if not x['passed']]
    regrets=[x['exact_regret'] for x in records if x['exact_regret'] is not None]
    solver_errors=[x['solver_objective_error'] for x in records if x['solver_objective_error'] is not None]
    artifact={
        'schema':'gurobean.r9.release-certification.v4','git_commit':commit,
        'cases':r9.CASES,'rounds':r9.ROUNDS,'cases_checked':len(records),
        'pwl_points':PWL_POINTS,'refine_points':list(REFINE_POINTS),
        'reference_objective_tolerance':REF_TOL,'exact_objective_regret_tolerance':OBJ_TOL,
        'solver_feasibility_tolerance':1e-8,'gurobi_gate':'CHECKED',
        'r5_r8_status':'CALIBRATION_GATED','failures':len(failures),
        'max_exact_regret':max(regrets,default=None),
        'max_solver_objective_error':max(solver_errors,default=None),'records':records,
        'status':'PASS' if not failures else 'FAIL'
    }
    ARTIFACT.write_text(json.dumps(artifact,indent=2),encoding='utf-8')
    print(json.dumps({k:artifact[k] for k in ('git_commit','cases_checked','pwl_points','refine_points','failures','max_exact_regret','max_solver_objective_error','status')},indent=2))
    return 0 if not failures else 1

if __name__=='__main__': raise SystemExit(main())
