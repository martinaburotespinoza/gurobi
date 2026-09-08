"""Authoritative R9 release gate for licensed production Gurobi certification.

The release gate is intentionally stricter than exploratory diagnostics:
- real Gurobi binding and valid license are mandatory;
- the working tree must be clean before certification;
- every R1-R4 case must return OPTIMAL;
- solver decisions must satisfy explicit resource constraints;
- exact analytical regret against the independent reference must be <= 2e-6;
- Gurobi's reported PWL objective must agree with the exact objective to <= 2e-6;
- the certified PWL mesh is fixed at 20,001 points;
- the artifact records the exact Git commit and final result for all 400 checks.

R5-R8 remain calibration/evidence-gated until authoritative equations and real
observations are promoted. No synthetic relationship is promoted here.
"""
from __future__ import annotations
import json,math,random,subprocess,sys
from dataclasses import asdict,dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import gurobean.model as model
import scripts.r9_end_to_end as r9
REF_TOL=r9.REFERENCE_OBJ_TOL
OBJ_TOL=2e-6
PWL_POINTS=20001
ARTIFACT=ROOT/'r9_release_certification.json'
@dataclass(frozen=True)
class CheckResult:
 case:int;round_number:int;pwl_points:int;reference_ok:bool;gurobi_status:int;feasible:bool;exact_objective:float;reference_objective:float;exact_regret:float;solver_objective:float;solver_objective_error:float;q_hot:float;q_cold:float;reference_q_hot:float;reference_q_cold:float;q_error:float;passed:bool;error:str|None=None
def _git_state():
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();dirty=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
 if len(commit)!=40:raise RuntimeError('invalid git HEAD for release certification')
 return commit,not bool(dirty)
def check(sc,rn,case):
 ref=r9._robust_reference(sc,rn);rq_h=float(ref['Q_hot']);rq_c=float(ref['Q_cold']);ref_obj=float(ref['objective']);exact_ref=float(r9._objective(sc,rn,rq_h,rq_c));referr=abs(ref_obj-exact_ref);refok=bool(r9._feasible(rq_h,rq_c,sc) and math.isfinite(exact_ref) and referr<=REF_TOL)
 if not refok:return CheckResult(case,rn,PWL_POINTS,False,-1,False,math.nan,exact_ref,math.inf,math.nan,math.inf,math.nan,math.nan,rq_h,rq_c,math.inf,False,'independent reference failed')
 g=model.solve_gurobi_round(sc,rn,pwl_points=PWL_POINTS);qh,qc=float(g['Q_hot']),float(g['Q_cold']);exact=float(r9._objective(sc,rn,qh,qc));solver=float(g['objective']);reg=abs(exact-exact_ref);serr=abs(solver-exact);feas=r9._gurobi_feasible(qh,qc,sc);status=int(g['status']);qerr=max(abs(qh-rq_h),abs(qc-rq_c));passed=bool(status==2 and feas and math.isfinite(exact) and math.isfinite(solver) and reg<=OBJ_TOL and serr<=OBJ_TOL)
 return CheckResult(case,rn,PWL_POINTS,True,status,feas,exact,exact_ref,reg,solver,serr,qh,qc,rq_h,rq_c,qerr,passed)
def main():
 print('=== R9 RELEASE CERTIFICATION ===')
 try:commit,clean=_git_state(); assert clean,'working tree is dirty; certification must run on an exact commit'
 except Exception as exc:print('STATUS: FAIL');print(f'RELEASE_STATE: FAIL ({exc!r})');return 1
 try:
  import gurobipy as gp
  version=tuple(int(x) for x in gp.gurobi.version());env=gp.Env(empty=True);env.setParam('OutputFlag',0);env.start();env.dispose()
 except Exception as exc:print('STATUS: FAIL');print(f'GUROBI_GATE: FAIL ({exc!r})');print(f'GIT_COMMIT: {commit}');return 1
 rng=random.Random(r9.SEED);records=[];failures=[]
 for i in range(r9.CASES):
  sc=r9._scenario(rng,i%4)
  for rn in r9.ROUNDS:
   try:r=check(sc,rn,i)
   except Exception as exc:r=CheckResult(i,rn,PWL_POINTS,False,-1,False,math.nan,math.nan,math.inf,math.nan,math.inf,math.nan,math.nan,math.nan,math.nan,math.inf,False,repr(exc))
   records.append(r)
   if not r.passed:failures.append(asdict(r))
 worst=max((r.exact_regret for r in records if math.isfinite(r.exact_regret)),default=0.);maxserr=max((r.solver_objective_error for r in records if math.isfinite(r.solver_objective_error)),default=0.);maxq=max((r.q_error for r in records if math.isfinite(r.q_error)),default=0.)
 status='PASS' if len(records)==400 and not failures else 'FAIL';artifact={'schema':'gurobean.r9.release-certification.v4','git_commit':commit,'git_clean':clean,'seed':r9.SEED,'cases':r9.CASES,'rounds':list(r9.ROUNDS),'total_checks':len(records),'gurobi_version':version,'pwl_points':PWL_POINTS,'release_objective_tolerance':OBJ_TOL,'reference_objective_tolerance':REF_TOL,'failures':len(failures),'max_exact_objective_regret':worst,'max_solver_objective_error':maxserr,'max_q_error_diagnostic':maxq,'gurobi_gate':'CHECKED','r5_r8_status':'CALIBRATION_GATED','status':status,'records':[asdict(r) for r in records],'failure_records':failures};tmp=ARTIFACT.with_suffix('.json.tmp');tmp.write_text(json.dumps(artifact,indent=2,sort_keys=True),encoding='utf-8');tmp.replace(ARTIFACT)
 print(f'GIT_COMMIT: {commit}');print(f'GUROBI_VERSION: {version}');print(f'CASES: {r9.CASES} x ROUNDS: {len(r9.ROUNDS)} = {len(records)}');print(f'PWL_POINTS: {PWL_POINTS}');print(f'RELEASE_OBJECTIVE_TOLERANCE: {OBJ_TOL:.12g}');print(f'FAILURES: {len(failures)}');print(f'MAX_EXACT_OBJECTIVE_REGRET: {worst:.12g}');print(f'MAX_SOLVER_OBJECTIVE_ERROR: {maxserr:.12g}');print(f'MAX_Q_ERROR: {maxq:.12g} (diagnostic)');print('GUROBI_GATE: CHECKED');print(f'R9 STATUS: {status}');print(f'ARTIFACT: {ARTIFACT.name}');return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
